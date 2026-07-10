#!/usr/bin/env python3
"""Build national rent map GeoJSON from RWI-GEO-REDX grid data.

Uses the MOST RECENT available year per grid cell (not just 2025).
This gives ~4x more coverage than 2025-only.
"""
import json
import os

BASE = "/Users/ruhvee/mietspiegel-digitization"
INPUT = os.path.join(BASE, "data/processed/redx_grid_rent.json")
OUTPUT = os.path.join(BASE, "docs/data/processed/national-rent-grid.geojson")

YEARS = [2008, 2013, 2018, 2023, 2024, 2025]

with open(INPUT) as f:
    rwi = json.load(f)

features = []
year_counts = {y: 0 for y in YEARS}

for g in rwi["grids"]:
    if "lat" not in g or "lng" not in g:
        continue

    # Pick most recent year with data
    best_year = None
    best_pi = None
    for y in reversed(YEARS):
        if f"pi{y}" in g:
            best_year = y
            best_pi = g[f"pi{y}"]
            break

    if best_year is None:
        continue

    year_counts[best_year] += 1

    # Include all available years for popup timeseries
    pi_vals = {}
    for y in YEARS:
        if f"pi{y}" in g:
            pi_vals[str(y)] = round(g[f"pi{y}"], 1)

    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [g["lng"], g["lat"]]
        },
        "properties": {
            "pi": round(best_pi, 1),
            "year": best_year,
            "grid": g["grid"],
            "pi_all": pi_vals,
            "n": g.get(f"n{best_year}", 0),
            "change_pct": round(g.get("change_pct", 0), 1),
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
print(f"Year distribution:")
for y in YEARS:
    if year_counts[y]:
        print(f"  {y}: {year_counts[y]:>5} grids")
