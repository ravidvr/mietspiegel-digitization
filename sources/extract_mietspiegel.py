#!/usr/bin/env python3
"""
Mietspiegel PDF Extraction Pipeline
====================================
Extracts tabular Mietspiegel data from German city PDFs into structured JSON.

Usage:
    python3 extract_mietspiegel.py <pdf_path> [--city CITY] [--year YYYY] [--output OUTPUT]

Dependencies:
    pip3 install pdfplumber camelot-py pandas

Author: Hermes Agent
Date:   2026-07-06
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
    import pdfplumber
except ImportError as e:
    print(f"ERROR: Missing dependency — {e}", file=sys.stderr)
    print("Run: pip3 install pdfplumber pandas", file=sys.stderr)
    sys.exit(1)


# ─── Normalisation helpers ─────────────────────────────────────────────


def parse_price(euro_str: str):
    """Parse German-formatted price like '9,87 €' or '12,34 €' to float."""
    m = re.search(r'([\d.,]+)', euro_str.replace('.', '').replace(',', '.'))
    if m:
        return round(float(m.group(1)), 2)
    return None


def classify_lage(page_text: str):
    """Detect which Wohnlage (einfach/mittel/gut) a page belongs to."""
    for lage in ['einfach', 'mittel', 'gut']:
        if lage in page_text.lower():
            # need a stronger signal
            pass
    if 'Einfache Wohnlage' in page_text:
        return 'einfach'
    if 'Mittlere Wohnlage' in page_text:
        return 'mittel'
    if 'Gute Wohnlage' in page_text:
        return 'gut'
    return None


def normalise_baujahr(raw: str) -> str:
    """Normalise baujahr period strings."""
    raw = raw.strip().rstrip('*').strip()
    replacements = {
        'bis 1918': 'bis 1918',
        '1919 bis 1949': '1919-1949',
        '1950 bis 1964': '1950-1964',
        '1965 bis 1972': '1965-1972',
        '1973 bis 1985 West': '1973-1985 West',
        '1973 bis 1990 Ost': '1973-1990 Ost',
        '1986 bis 1990 West': '1986-1990 West',
        '1973 bis 1990': '1973-1990',
        '1973 bis 1985': '1973-1985',
        '1973 bis 1990 Ost*': '1973-1990 Ost',
        '1986 bis 1990 West*': '1986-1990 West',
        '1991 bis 2001': '1991-2001',
        '1991 bis 2002': '1991-2002',
        '2002 bis 2009': '2002-2009',
        '2010 bis 2015': '2010-2015',
        '2016 bis 2022': '2016-2022',
    }
    if raw in replacements:
        return replacements[raw]
    # fallback: replace "bis" with "-"
    return raw.replace(' bis ', '-')


def normalise_size_range(parts: list[str]) -> str:
    """Reconstruct a size range from split columns."""
    text = ' '.join(p.strip() for p in parts if p.strip())
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ─── Extraction methods ────────────────────────────────────────────────


def extract_with_pdfplumber(pdf_path: str) -> dict:
    """
    Primary extractor using pdfplumber text extraction.
    Works on all digital-native PDFs with selectable text.
    """
    pdf = pdfplumber.open(pdf_path)
    result = {
        'pdf_pages': len(pdf.pages),
        'lage_tables': {'einfach': [], 'mittel': [], 'gut': []},
        'raw_pages': [],
    }

    current_lage = None
    page_texts = []

    for pi, page in enumerate(pdf.pages):
        text = page.extract_text()
        page_texts.append(text)

        # Detect lage category from page text
        lage = classify_lage(text)
        if lage:
            current_lage = lage

        # Parse data lines
        for line in text.split('\n'):
            line = line.strip()
            # Data lines start with a row number and contain € symbols
            if re.match(r'^\d+\s', line) and '€' in line:
                # Parse fields: row_num, baujahr?, size_low, size_high, unit?, untere, mittel, obere
                parts = line.split()
                if len(parts) >= 7:
                    row_num = int(parts[0])

                    # The tricky part: baujahr can span 1-4 tokens, size_range 2-4 tokens
                    # Find price tokens (these always end with €)
                    price_indices = [i for i, p in enumerate(parts) if '€' in p]

                    if len(price_indices) >= 3:
                        untere_idx = price_indices[0]
                        mittel_idx = price_indices[1]
                        obere_idx = price_indices[2]

                        untere = parse_price(parts[untere_idx])
                        mittel = parse_price(parts[mittel_idx])
                        obere = parse_price(parts[obere_idx])

                        # Everything between row number and first price is baujahr + size
                        middle = ' '.join(parts[1:untere_idx])

                        # Use camelot's structured output for proper field splitting
                        # Since pdfplumber text is a flattened string, we rely on camelot
                        # for column-level segmentation

                        row_data = {
                            'row': row_num,
                            'raw': line,
                            'untere_spanne': untere,
                            'mittelwert': mittel,
                            'obere_spanne': obere,
                        }

                        if current_lage and current_lage in result['lage_tables']:
                            result['lage_tables'][current_lage].append(row_data)

        result['raw_pages'].append({
            'page': pi + 1,
            'lines': len(text.split('\n')),
            'lage': current_lage,
        })

    pdf.close()
    return result


def extract_with_camelot(pdf_path: str, edge_tol: int = 50, row_tol: int = 10) -> list[dict]:
    """
    Extractor using camelot-py (stream flavor).
    Returns a list of data rows sorted by row number.
    Best for tables with clear column gaps.
    """
    try:
        import camelot
    except ImportError as exc:
        raise RuntimeError("camelot-py not installed — run: pip3 install camelot-py[cv]") from exc

    tables = camelot.read_pdf(pdf_path, pages='1-5', flavor='stream',
                              edge_tol=edge_tol, row_tol=row_tol)

    all_rows = {}

    for ti, t in enumerate(tables):
        df = t.df

        # Find header row
        header_idx = None
        for ri in range(min(5, df.shape[0])):
            row_vals = [str(v).strip() for v in df.iloc[ri].values]
            if 'Zeile' in row_vals or 'Bezugsfertigkeit' in row_vals:
                header_idx = ri
                break

        if header_idx is None:
            continue

        # Determine lage category from the table
        lage_text = ''
        for ri in range(header_idx):
            row_vals = [str(v).strip() for v in df.iloc[ri].values]
            row_text = ' '.join(v for v in row_vals if v)
            if 'Einfache' in row_text:
                lage_text = 'einfach'
            elif 'Mittlere' in row_text:
                lage_text = 'mittel'
            elif 'Gute' in row_text:
                lage_text = 'gut'

        # Process data rows
        for ri in range(header_idx + 1, df.shape[0]):
            vals = [str(v).strip() for v in df.iloc[ri].values]
            if not vals[0] or not vals[0].isdigit():
                continue

            row_num = int(vals[0])
            baujahr = vals[1] if vals[1] else None
            size_text = normalise_size_range(vals[2:5])
            untere = parse_price(vals[5])
            mittel = parse_price(vals[6])
            obere = parse_price(vals[7])

            if untere is None and mittel is None:
                continue

            row_data = {
                'row': row_num,
                'baujahr': normalise_baujahr(baujahr) if baujahr else None,
                'size_range': size_text,
                'untere_spanne': untere,
                'mittelwert': mittel,
                'obere_spanne': obere,
                '_lage': lage_text,
            }
            all_rows[row_num] = row_data

    return sorted(all_rows.values(), key=lambda r: r['row'])


def extract_with_pdfplumber_detailed(pdf_path: str) -> list[dict]:
    """
    Full-structured extractor using pdfplumber extract_text() line-by-line parsing.
    Parses Berlin Mietspiegel format where each line is: row_num baujahr? size_range prices.
    Uses camelot-aligned field segmentation (8-column structure).
    """
    import pdfplumber

    pdf = pdfplumber.open(pdf_path)
    all_rows = []
    current_baujahr = None
    current_lage = None

    # Regex for data row: starts with digits, contains € symbol
    data_row_re = re.compile(r'^(\d+)\s(.+?)(\d[\d.,]+\s?€)\s+(\d[\d.,]+\s?€)\s+(\d[\d.,]+\s?€)\s*$')

    for pi, page in enumerate(pdf.pages):
        text = page.extract_text()

        for line in text.split('\n'):
            line = line.strip()
            # Section headers can appear MID-PAGE (e.g. page 2 carries both
            # "9.1 ... Einfache (Fortsetzung)" and "9.2 ... Mittlere Wohnlage").
            # Switch lage as soon as the header line appears.
            header_lage = classify_lage(line)
            if header_lage:
                current_lage = header_lage
            m = re.match(r'^(\d+)\s', line)
            if not m or '€' not in line:
                continue

            row_num = int(m.group(1))
            rest = line[m.end():].strip()

            # Find prices (3 values with €)
            price_parts = re.findall(r'(\d[\d.,]+)\s*€', rest)
            if len(price_parts) >= 3:
                untere = parse_price(price_parts[0] + ' €')
                mittel = parse_price(price_parts[1] + ' €')
                obere = parse_price(price_parts[2] + ' €')

                # Remove prices from rest to get baujahr + size
                middle = rest
                for pp in price_parts:
                    middle = middle.replace(pp + ' €', '', 1)

                middle = re.sub(r'\s+', ' ', middle).strip()

                # Try to parse baujahr from middle
                detected_baujahr = None
                size_text = middle

                # Common baujahr patterns
                baujahr_patterns = re.findall(
                    r'(bis\s+1918|1919\s+bis\s+1949|1950\s+bis\s+1964|'
                    r'1965\s+bis\s+1972|1973\s+bis\s+(?:1985\s+West|1990\s+Ost|1990)|'
                    r'1986\s+bis\s+1990\s+West|1991\s+bis\s+(?:2001|2002)|'
                    r'2002\s+bis\s+2009|2010\s+bis\s+2015|2016\s+bis\s+2022)',
                    middle
                )

                if baujahr_patterns:
                    detected_baujahr = normalise_baujahr(baujahr_patterns[0])
                    # Remove baujahr from middle to get size
                    size_text = middle.replace(baujahr_patterns[0], '', 1).strip()
                    current_baujahr = detected_baujahr
                elif current_baujahr:
                    # Inherit baujahr from previous row
                    detected_baujahr = current_baujahr
                    size_text = middle
                else:
                    size_text = middle

                # Footnote markers (* /**) belong to the baujahr, not the size
                size_text = re.sub(r'^\*+\s*', '', size_text)
                size_text = re.sub(r'\s+', ' ', size_text).strip()

                row_data = {
                    'row': row_num,
                    'baujahr': detected_baujahr,
                    'size_range': size_text,
                    'untere_spanne': untere,
                    'mittelwert': mittel,
                    'obere_spanne': obere,
                    '_lage': current_lage,
                }
                all_rows.append(row_data)

    pdf.close()
    return all_rows


# ─── Main CLI ──────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description='Extract Mietspiegel table data from PDFs'
    )
    parser.add_argument('pdf_path', help='Path to Mietspiegel PDF')
    parser.add_argument('--city', default='unknown',
                        help='City name (e.g. Berlin)')
    parser.add_argument('--year', type=int, default=None,
                        help='Edition year (e.g. 2024)')
    parser.add_argument('--output', '-o', default=None,
                        help='Output JSON path')
    parser.add_argument('--method', choices=['pdfplumber', 'camelot', 'pdfplumber-detailed'],
                        default='camelot',
                        help='Extraction method (default: camelot)')
    args = parser.parse_args()

    pdf_path = args.pdf_path
    if not Path(pdf_path).exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting: {pdf_path}")
    print(f"Method:     {args.method}")

    if args.method == 'pdfplumber':
        result = extract_with_pdfplumber(pdf_path)
        output = result
    elif args.method == 'camelot':
        rows = extract_with_camelot(pdf_path)
        output = {
            'city': args.city,
            'year': args.year,
            'pdf_pages': len(pdfplumber.open(pdf_path).pages) if pdfplumber else 0,
            'rows_extracted': len(rows),
            'data': rows,
        }
        if pdfplumber:
            pdfplumber.open(pdf_path).close()
    else:  # pdfplumber-detailed
        rows = extract_with_pdfplumber_detailed(pdf_path)
        output = {
            'city': args.city,
            'year': args.year,
            'rows_extracted': len(rows),
            'data': rows,
        }

    # Print summary
    print(f"\nRows extracted: {len(output.get('data', output.get('lage_tables', {}).get('einfach', [])))}")

    # Save if output path given
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Saved to:   {args.output}")
    else:
        # Print first 5 rows as sample
        if args.method == 'pdfplumber':
            for lage, rows in output['lage_tables'].items():
                if rows:
                    print(f"\n{lage.title()}: {len(rows)} rows")
                    for r in rows[:3]:
                        print(f"  {r}")
        else:
            print("\nFirst 5 rows:")
            for r in output['data'][:5]:
                print(f"  {r}")


if __name__ == '__main__':
    main()
