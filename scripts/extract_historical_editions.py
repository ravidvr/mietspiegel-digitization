#!/usr/bin/env python3
"""Extract the Berliner Mietspiegeltabelle 2017-2023 editions (wide-table format).

Unlike the 2024 edition (row-oriented), the 2017-2023 tables are a grid:
8 Bezugsfertigkeit columns x 12 rows (3 Wohnlage x 4 size bands).
Each cell carries a Mittelwert line and a "untere - obere Spanne" line.

Usage:
    python3 scripts/extract_historical_editions.py data/raw/mietspiegeltabelle2023.pdf --year 2023 --output docs/data/processed/berlin_historical_2023.json
"""
import argparse
import json
import re
from pathlib import Path

import pdfplumber


def extract_edition(pdf_path: str, year: int) -> dict:
    pdf = pdfplumber.open(pdf_path)
    page = pdf.pages[0]

    # Column headers: cohort names in the header band (top ~18% of page)
    h = page.height
    header = [w for w in page.extract_words() if w["top"] < h * 0.18]
    cohort_tokens = {}
    for w in header:
        txt = w["text"].strip()
        if re.match(r"^(bis|19\d\d|20\d\d)", txt):
            cohort_tokens[(round(w["x0"] / 10), round(w["top"] / 10))] = txt

    # Reconstruct cohort columns: cluster tokens by x, take the first-line tokens
    cohort_header = []
    for (x, top), txt in sorted(cohort_tokens.items()):
        # collect the full phrase per column by x-cluster
        cluster = [w["text"] for (wx, wt), w in zip(cohort_tokens.keys(), header)
                   if abs(wx - x) <= 2 and wt == top and w["text"].strip()]
        phrase = " ".join(cluster).strip()
        if phrase and not any(phrase == c for c in cohort_header):
            cohort_header.append(phrase)

    # Data rows: rows are the lage+size labels (einfach/mittel/gut + size band)
    rows_out = []
    words = page.extract_words()
    lage_map = {"einfach": "einfach", "mittel": "mittel", "gut": "gut"}
    size_bands = [
        ("bis unter 40 m²", 0.0, 40.0),
        ("40 m² bis unter 60 m²", 40.0, 60.0),
        ("60 m² bis unter 90 m²", 60.0, 90.0),
        ("90 m² und mehr", 90.0, None),
    ]

    # Group rows by y-band of the lage label; then by size label position
    # The 2023 table has 12 rows. Each row = one lage label + one size label.
    # We parse values per cohort column using word x-positions.
    col_xs = sorted({round(w["x0"] / 10) for w in words if re.match(r"^\d", w["text"]) and w["top"] > h * 0.18})
    # Cluster col_xs into 8 columns
    cols = []
    for cx in col_xs:
        if cols and cx - cols[-1] <= 4:
            continue
        cols.append(cx)
    cols = cols[:8]

    # Find row anchors: lines containing 'einfach'/'mittel'/'gut' + size text
    row_lines = []
    for w in words:
        if w["text"].strip() in lage_map and w["top"] > h * 0.18:
            row_lines.append(w)

    for anchor in row_lines:
        lage = lage_map[anchor["text"].strip()]
        # find the size band: the text between lage and the values
        y = anchor["top"]
        # size label is the word at similar y on the left side; values are on the right
        row_words = [w for w in words if abs(w["top"] - y) < 5 and w["x0"] > anchor["x0"]]
        # values: numbers with , or . and €
        vals = [w for w in row_words if re.match(r"^[\d.,]+", w["text"]) and "€" not in w["text"]]
        # group vals by column
        cell_vals = {}
        for v in vals:
            for ci, cx in enumerate(cols):
                if abs(v["x0"] - cx * 10) < 40:
                    cell_vals.setdefault(ci, []).append(v["text"])
                    break
        # for each cohort column with 2 values (mittelwert, spanne), add row
        for ci, vlist in cell_vals.items():
            if len(vlist) < 2:
                continue
            mittel = parse_de(vlist[0])
            spanne = vlist[1] if len(vlist) >= 2 else None
            if mittel is None:
                continue
            cohort = cohort_header[ci] if ci < len(cohort_header) else f"col{ci}"
            # find size band by row position: the y order maps to size bands
            # (rows repeat per lage: 4 size bands each)
            rows_out.append({
                "jahr": year,
                "lage": lage,
                "baujahr": cohort,
                "size_band": "unknown",
                "mittelwert": mittel,
                "spanne": spanne,
            })

    pdf.close()
    return {"year": year, "rows": rows_out, "note": "coordinate-based extraction; size_band requires manual verification"}


def parse_de(txt: str):
    txt = txt.replace(",", ".").replace("€", "").strip()
    try:
        return float(txt)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    data = extract_edition(args.pdf, args.year)
    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"extracted {len(data['rows'])} rows -> {args.output}")


if __name__ == "__main__":
    main()
