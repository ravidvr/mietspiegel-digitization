#!/usr/bin/env python3
"""Build national rent map GeoJSON from RWI-GEO-REDX grid data.

Uses the MOST RECENT available year per grid cell (not just 2025).
Spatially joins each grid to its German district (Kreis) for human-readable location names.
"""
import json
import os
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

BASE = "/Users/ruhvee/mietspiegel-digitization"
INPUT = os.path.join(BASE, "data/processed/redx_grid_rent.json")
KREISE = os.path.join(BASE, "data/external/germany-kreise.geojson")
OUTPUT = os.path.join(BASE, "docs/data/processed/national-rent-grid.geojson")

YEARS = [2008, 2013, 2018, 2023, 2024, 2025]

# ─── Load and index districts ───────────────────────────────────
with open(KREISE) as f:
    kreise_gj = json.load(f)

districts = []
for feat in kreise_gj["features"]:
    props = feat["properties"]
    name = props["NAME_3"]
    state = props["NAME_1"]
    # Clean up: remove " Städte" suffix from city-district names
    name = name.replace(" Städte", "")
    # Avoid duplication when name == state (e.g. "Berlin, Berlin")
    if name == state:
        label = name
    elif name == state + " Städte":
        label = state
    else:
        label = f"{name}, {state}"
    geom = shape(feat["geometry"])
    districts.append((geom, label, name, state))

# Build spatial index
print(f"Indexing {len(districts)} districts...")
tree = STRtree([d[0] for d in districts])

# ─── Build grid features ────────────────────────────────────────
with open(INPUT) as f:
    rwi = json.load(f)

features = []
year_counts = {y: 0 for y in YEARS}
match_count = 0

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

    # Reverse geocode: which district contains this point?
    pt = Point(g["lng"], g["lat"])
    location = None
    candidates = tree.query(pt, predicate="intersects")
    if candidates.size > 0:
        # Take first match — for a well-formed partition, there should be exactly one
        _, district_name, district_short, state_name = districts[candidates[0]]
        location = district_name
        match_count += 1

    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [g["lng"], g["lat"]]
        },
        "properties": {
            "pi": round(best_pi, 1),
            "year": best_year,
            "location": location,
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
print(f"District matches: {match_count}/{len(features)} ({100*match_count/len(features):.1f}%)")
print(f"Year distribution:")
for y in YEARS:
    if year_counts[y]:
        print(f"  {y}: {year_counts[y]:>5} grids")

# Show some location examples
print(f"\nSample locations:")
for f in features[:8]:
    print(f"  {f['properties']['grid']:12s} → {f['properties']['location']}")
