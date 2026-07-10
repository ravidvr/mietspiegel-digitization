#!/usr/bin/env python3
"""Build national rent map GeoJSON from RWI-GEO-REDX grid data."""
import json
import os

BASE = "/Users/ruhvee/mietspiegel-digitization"
INPUT = os.path.join(BASE, "data/processed/redx_grid_rent.json")
OUTPUT = os.path.join(BASE, "docs/data/processed/national-rent-grid.geojson")

with open(INPUT) as f:
    rwi = json.load(f)

features = []
for g in rwi["grids"]:
    if "pi2025" not in g or "lat" not in g or "lng" not in g:
        continue
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [g["lng"], g["lat"]]
        },
        "properties": {
            "pi2025": round(g["pi2025"], 1),
            "pi2018": round(g.get("pi2018", 0), 1),
            "change_pct": round(g.get("change_pct", 0), 1),
            "n2025": g.get("n2025", 0),
            "grid": g["grid"]
        }
    })

geojson = {
    "type": "FeatureCollection",
    "features": features
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, "w") as f:
    json.dump(geojson, f)

size_kb = os.path.getsize(OUTPUT) / 1024
print(f"Wrote {len(features)} grid cells → {OUTPUT} ({size_kb:.0f} KB)")
