#!/usr/bin/env python3
"""
JSON schema validation for Mietspiegel city data.
Validates that every city JSON file has the required fields,
standard baujahr/lage values, and consistent structure.

Usage: python3 validate/run_validations.py
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')

# Canonical values
CANONICAL_LAGE = {'einfach', 'mittel', 'gut'}
LAGE_ALIASES = {'normal': 'mittel', 'sehr gut': 'gut'}
CANONICAL_BAUJAHR_START_YEARS = [1918, 1949, 1964, 1974, 1990, 2002, 2013]
SIZE_KEYS = {'bis_40', '40_60', '60_90', 'ueber_90'}

ERRORS = []
WARNINGS = []


def error(slug, msg):
    ERRORS.append(f"[ERROR] {slug}: {msg}")

def warning(slug, msg):
    WARNINGS.append(f"[WARN]  {slug}: {msg}")


def validate_city(slug, data):
    """Validate a single city JSON file."""
    # Required top-level fields
    required = ['city', 'city_slug', 'state', 'year', 'type',
                'lage_categories', 'baujahr_groups', 'size_categories', 'tables']
    for field in required:
        if field not in data:
            error(slug, f"Missing required field: {field}")

    # Check source_url
    if not data.get('source_url'):
        warning(slug, "Missing source_url")

    # Check tables structure
    tables = data.get('tables', [])
    for i, table in enumerate(tables):
        if 'lage' not in table:
            error(slug, f"Table {i}: missing 'lage' field")
            continue
        if 'rows' not in table:
            error(slug, f"Table {i} (lage={table.get('lage')}): missing 'rows' field")
            continue

        # Check lage is standard or known alias
        lage = table['lage']
        if lage not in CANONICAL_LAGE and lage not in LAGE_ALIASES:
            warning(slug, f"Table {i}: non-standard lage '{lage}'")

        # Check rows
        for j, row in enumerate(table['rows']):
            if 'baujahr' not in row:
                error(slug, f"Table {i} row {j}: missing 'baujahr' field")
                continue

            # Check size keys
            row_keys = set(row.keys()) - {'baujahr'}
            missing_keys = SIZE_KEYS - row_keys
            if missing_keys:
                warning(slug, f"Table {i} (lage={lage}) row baujahr={row['baujahr']}: missing size keys {missing_keys}")

            # Check rent values are positive numbers
            for key in SIZE_KEYS:
                if key in row and row[key] is not None:
                    val = row[key]
                    if not isinstance(val, (int, float)):
                        error(slug, f"Table {i} row {j} {key}: not a number ({val})")
                    elif val <= 0:
                        error(slug, f"Table {i} row {j} {key}: non-positive value ({val})")
                    elif val > 50:
                        warning(slug, f"Table {i} row {j} {key}: suspiciously high value ({val})")

    # Check lage_categories has at least 'mittel'
    lage_cats = data.get('lage_categories', [])
    if lage_cats and 'mittel' not in lage_cats and 'normal' not in lage_cats:
        warning(slug, f"lage_categories has no 'mittel': {lage_cats}")


def validate_index(cities):
    """Validate the cities_index.json file."""
    seen_slugs = set()
    for i, city in enumerate(cities):
        slug = city.get('slug', f'index[{i}]')

        # Required fields
        for field in ['city', 'slug', 'lat', 'lng', 'state', 'population']:
            if field not in city:
                error(slug, f"cities_index.json: missing field '{field}' for {city.get('city', '?')}")

        # Check for duplicate slugs
        if slug in seen_slugs:
            error(slug, f"Duplicate slug in cities_index.json")
        seen_slugs.add(slug)

        # Check state is not empty
        if not city.get('state'):
            warning(slug, f"Empty state for {city.get('city', '?')}")

        # Check population is reasonable
        pop = city.get('population', 0)
        if pop == 100000:
            warning(slug, f"Possibly placeholder population: {pop}")
        if pop < 50000:
            warning(slug, f"Low population: {pop}")

        # Check coordinates are within Germany
        lat = city.get('lat', 0)
        lng = city.get('lng', 0)
        if not (47 < lat < 55):
            warning(slug, f"Latitude outside Germany range: {lat}")
        if not (6 < lng < 15):
            warning(slug, f"Longitude outside Germany range: {lng}")


def main():
    # Load and validate cities_index.json
    index_path = os.path.join(DATA_DIR, 'cities_index.json')
    if not os.path.exists(index_path):
        print(f"FATAL: {index_path} not found")
        sys.exit(1)

    with open(index_path, encoding='utf-8') as f:
        cities = json.load(f)

    print(f"Validating {len(cities)} cities from cities_index.json...\n")
    validate_index(cities)

    # Validate each city JSON
    for city in cities:
        slug = city['slug']
        city_path = os.path.join(DATA_DIR, f'{slug}.json')
        if not os.path.exists(city_path):
            warning(slug, "No data file found")
            continue

        with open(city_path, encoding='utf-8') as f:
            data = json.load(f)
        validate_city(slug, data)

    # Report
    print(f"\n{'='*60}")
    print(f"VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Cities checked: {len(cities)}")
    print(f"Errors:   {len(ERRORS)}")
    print(f"Warnings: {len(WARNINGS)}")
    print(f"{'='*60}\n")

    if ERRORS:
        print("ERRORS:")
        for e in ERRORS:
            print(f"  {e}")
        print()

    if WARNINGS:
        print("WARNINGS:")
        for w in WARNINGS:
            print(f"  {w}")
        print()

    if not ERRORS and not WARNINGS:
        print("✓ All validations passed!")
    elif not ERRORS:
        print("✓ No errors (warnings only)")

    return 1 if ERRORS else 0


if __name__ == '__main__':
    sys.exit(main())
