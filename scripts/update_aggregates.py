#!/usr/bin/env python3
"""Update aggregate JSON files after Dresden extraction."""
import json, datetime

# 1. Update stadt-index.json timestamp
with open('/Users/ruhvee/mietspiegel-digitization/data/processed/stadt-index.json', 'r') as f:
    idx = json.load(f)
idx['generated_at'] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
with open('/Users/ruhvee/mietspiegel-digitization/data/processed/stadt-index.json', 'w') as f:
    json.dump(idx, f, indent=2, ensure_ascii=False)
print("Updated stadt-index.json")

# 2. Read dresden data
with open('/Users/ruhvee/mietspiegel-digitization/data/processed/dresden.json') as f:
    dd = json.load(f)

# 3. Append to mietspiegel_katalog
with open('/Users/ruhvee/mietspiegel-digitization/data/processed/mietspiegel_katalog.json', 'r') as f:
    kat = json.load(f)

dresden_entry = {"city": "Dresden", "city_slug": "dresden", "state": "Sachsen", "year": 2025}
slugs = [c.get("city_slug") for c in kat.get("cities", [])]
if "dresden" not in slugs:
    kat["cities"].append(dresden_entry)
    with open('/Users/ruhvee/mietspiegel-digitization/data/processed/mietspiegel_katalog.json', 'w') as f:
        json.dump(kat, f, indent=2, ensure_ascii=False)
    print("Added Dresden to mietspiegel_katalog")
else:
    print("Dresden already in mietspiegel_katalog")

print("\nFiles updated. Dresden extraction complete.")
