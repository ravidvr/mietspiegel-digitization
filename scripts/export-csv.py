#!/usr/bin/env python3
"""
Mietspiegel CSV Export Utility

Usage:
  python3 scripts/export-csv.py                         # Export all cities, mittel lage
  python3 scripts/export-csv.py --lage gut              # Export "gut" Wohnlage
  python3 scripts/export-csv.py --state Berlin          # Filter by Bundesland
  python3 scripts/export-csv.py --include-history       # Include historical trend data
  python3 scripts/export-csv.py --output data.csv       # Custom output path

Output: CSV with columns for all Wohnlage × Baujahr × Size combinations,
plus optional historical data rows.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data' / 'processed'

LAGE_NAMES = {'einfach': 'Einfach', 'mittel': 'Mittel', 'gut': 'Gut'}
SIZE_KEYS = ['size_under_40', 'size_40_60', 'size_60_90', 'size_over_90']
SIZE_LABELS = {'size_under_40': '<40m²', 'size_40_60': '40-60m²', 'size_60_90': '60-90m²', 'size_over_90': '>90m²'}


def load_cities():
    """Load all city data files."""
    cities = {}
    for fpath in sorted(DATA_DIR.glob('*.json')):
        if fpath.name in ('stadt-index.json', 'cities.json'):
            continue
        with open(fpath, encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                continue
            slug = data.get('city_slug', fpath.stem)
            cities[slug] = data
    return cities


def export_current(cities, lage='mittel', state=None):
    """Export current Mietspiegel edition as CSV rows."""
    rows = []
    for slug, data in cities.items():
        if state and data.get('state') != state:
            continue

        tables = data.get('current_edition', {}).get('tables', {})
        lage_data = tables.get(lage, [])
        if not lage_data:
            continue

        edition_year = data.get('current_edition', {}).get('year', '—')
        for row in lage_data:
            r = {
                'City': data.get('city', slug),
                'State': data.get('state', ''),
                'Population': data.get('population', 0),
                'Wohnlage': LAGE_NAMES.get(lage, lage),
                'Baujahr': row.get('baujahr', ''),
                'Edition_Year': edition_year,
            }
            for sk in SIZE_KEYS:
                r[SIZE_LABELS.get(sk, sk)] = row.get(sk, '')
            rows.append(r)
    return rows


def export_history(cities, state=None):
    """Export historical trend data as CSV rows."""
    rows = []
    for slug, data in cities.items():
        if state and data.get('state') != state:
            continue

        history = data.get('history', [])
        for h in history:
            for key in ['base_rent_mittel_60_90', 'base_rent_mittel_1919_1949']:
                if key in h:
                    label = 'Mittelwert 60-90m²' if '60_90' in key else 'Mittelwert Baujahr 1919-1949'
                    rows.append({
                        'City': data.get('city', slug),
                        'State': data.get('state', ''),
                        'Population': data.get('population', 0),
                        'Year': h.get('year', ''),
                        'Category': label,
                        'Rent_Value': h[key],
                        'Data_Type': 'Historical',
                    })
    return rows


def main():
    parser = argparse.ArgumentParser(description='Export Mietspiegel data as CSV')
    parser.add_argument('--lage', choices=['einfach', 'mittel', 'gut'], default='mittel',
                        help='Wohnlage to export (default: mittel)')
    parser.add_argument('--state', default=None, help='Filter by Bundesland')
    parser.add_argument('--include-history', action='store_true',
                        help='Include historical trend data')
    parser.add_argument('--output', '-o', default=None,
                        help='Output file path (default: stdout)')
    args = parser.parse_args()

    cities = load_cities()
    if not cities:
        print("No city data found. Run extraction first.", file=sys.stderr)
        sys.exit(1)

    rows = export_current(cities, lage=args.lage, state=args.state)
    hist_rows = []
    if args.include_history:
        hist_rows = export_history(cities, state=args.state)

    if not rows and not hist_rows:
        print("No data matches the filter criteria.", file=sys.stderr)
        sys.exit(0)

    # Merge fieldnames
    current_fields = list(rows[0].keys()) if rows else []
    hist_fields = list(hist_rows[0].keys()) if hist_rows else []
    fieldnames = list(dict.fromkeys(current_fields + hist_fields))

    outfile = open(args.output, 'w', newline='', encoding='utf-8-sig') if args.output else sys.stdout
    try:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
        writer.writerows(hist_rows)
        total = len(rows) + len(hist_rows)
        print(f"\n✓ Exported {total} rows to {'STDOUT' if args.output is None else args.output}",
              file=sys.stderr)
    finally:
        if args.output:
            outfile.close()


if __name__ == '__main__':
    main()
