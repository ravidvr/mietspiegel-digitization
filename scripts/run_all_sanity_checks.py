#!/usr/bin/env python3
"""Run all sanity checks across all city JSON files. Exits 1 on errors."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from validate.sanity_checks import run_all_sanity_checks

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'data', 'processed')

errors = 0
for f in sorted(os.listdir(DATA)):
    if not f.endswith('.json'):
        continue
    if f in ('cities_index.json', 'cities_comparison.json', 'berlin-districts-geo.json'):
        continue
    with open(os.path.join(DATA, f)) as fh:
        data = json.load(fh)
    if 'tables' not in data:
        continue
    result = run_all_sanity_checks(data)
    if result['errors'] > 0:
        print(f"FAIL {result['city']}: {result['errors']} errors, {result['warnings']} warnings")
        errors += result['errors']
        for v in result['violations']:
            if v.get('severity') == 'error':
                print(f"  {v.get('message', v)}")

if errors > 0:
    print(f'\n{errors} total errors across cities')
    sys.exit(1)
print('All sanity checks passed')
