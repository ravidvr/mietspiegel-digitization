#!/usr/bin/env python3
"""Validate stuttgart.json against schema and PDF values."""
import json

import jsonschema

with open('docs/schema.json') as f:
    schema = json.load(f)
with open('data/processed/stuttgart.json') as f:
    data = json.load(f)

print(f'Top-level keys: {list(data.keys())}')
print()

try:
    jsonschema.validate(data, schema)
    print('SCHEMA: PASSED')
except jsonschema.ValidationError as e:
    print(f'SCHEMA: FAILED: {e}')
    raise

matrix = data['matrix']
values = matrix['values']
print(f'Matrix: {len(matrix["lage_categories"])} lage x {len(matrix["bauperiods"])} periods x {len(matrix["size_groups"])} sizes = {len(values)} cells')

seen = set()
for v in values:
    key = (v['lage_id'], v['bauperiod_id'], v['size_id'])
    assert key not in seen, f'DUPLICATE: {key}'
    seen.add(key)
print(f'Unique cells: {len(seen)}')

pdf_ref = {
    ('21_30','bis_1914'):12.36,('21_30','1915_1984'):12.36,('21_30','1985_2006'):12.96,('21_30','2007_2024_04'):12.36,
    ('30_40','bis_1914'):11.01,('30_40','1915_1984'):11.01,('30_40','1985_2006'):11.61,('30_40','2007_2024_04'):11.01,
    ('40_70','bis_1914'):9.72,('40_70','1915_1984'):9.72,('40_70','1985_2006'):10.32,('40_70','2007_2024_04'):9.72,
    ('70_90','bis_1914'):9.17,('70_90','1915_1984'):9.17,('70_90','1985_2006'):9.77,('70_90','2007_2024_04'):9.17,
    ('90_115','bis_1914'):8.94,('90_115','1915_1984'):8.94,('90_115','1985_2006'):9.54,('90_115','2007_2024_04'):8.94,
    ('ab_115','bis_1914'):8.96,('ab_115','1915_1984'):8.96,('ab_115','1985_2006'):9.56,('ab_115','2007_2024_04'):8.96,
}
errors = []
for v in values:
    key = (v['size_id'], v['bauperiod_id'])
    expected = pdf_ref.get(key)
    if expected is None:
        errors.append(f'UNEXPECTED: {key}')
        continue
    base = v['value']['mittelwert']
    if abs(base - expected) > 0.005:
        errors.append(f'MISMATCH {key}: got={base}, pdf={expected}')
assert not errors, f'PDF value mismatches: {errors}'
print('PDF values: 24/24 correct')

src = data['source']
city = data['city']
print(f'Source: {src["title"]} ({src["type"]}, {src["year"]})')
print(f'Effective: {src["effective_from"]} -> {src["effective_until"]}')
print(f'Publisher: {src["publisher"]}')
print(f'Lage adjustments: {len(src["extra"]["lage_adjustments"])}')
print(f'Feature adjustments: {len(src["extra"]["feature_adjustments"])}')
print(f'City: {city["name"]} ({city["slug"]}), {city["state"]}')
print(f'PDF URL: {src["pdf_url"]}')

print()
print('ALL VERIFICATIONS PASSED')
