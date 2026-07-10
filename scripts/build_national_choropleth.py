#!/usr/bin/env python3
"""Build national rent map GeoJSON from RWI-GEO-REDX grid data.

- Uses most recent available year per grid cell (not just 2025).
- Spatial join to German district (Kreis) for city/region names.
- Nearest-neighbor match to 8,299 PLZ codes for ZIP-level granularity.
"""
import csv
import json
import os
from shapely.geometry import Point, shape
from shapely.strtree import STRtree
from scipy.spatial import KDTree

BASE = "/Users/ruhvee/mietspiegel-digitization"
INPUT = os.path.join(BASE, "data/processed/redx_grid_rent.json")
KREISE = os.path.join(BASE, "data/external/germany-kreise.geojson")
PLZ_CSV = os.path.join(BASE, "data/external/plz_centroids.csv")
OUTPUT = os.path.join(BASE, "docs/data/processed/national-rent-grid.geojson")

YEARS = [2008, 2013, 2018, 2023, 2024, 2025]

# ─── Load PLZ centroids ─────────────────────────────────────────
plz_coords = []   # [(lat, lng)]
plz_codes  = []   # [plz_string]
with open(PLZ_CSV, newline="") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith(','):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        try:
            plz_code = parts[0].strip()
            lat = float(parts[1])
            lng = float(parts[2])
            plz_codes.append(plz_code)
            plz_coords.append((lat, lng))
        except ValueError:
            continue

print(f"Loaded {len(plz_coords)} PLZ centroids")
plz_tree = KDTree(plz_coords)

# ─── Load and index districts ───────────────────────────────────
with open(KREISE) as f:
    kreise_gj = json.load(f)

districts = []
for feat in kreise_gj["features"]:
    props = feat["properties"]
    name = props["NAME_3"].replace(" Städte", "")
    state = props["NAME_1"]
    if name == state:
        label = name
    else:
        label = f"{name}, {state}"
    geom = shape(feat["geometry"])
    districts.append((geom, label))

print(f"Indexing {len(districts)} districts...")
tree = STRtree([d[0] for d in districts])

# ─── Build grid features ────────────────────────────────────────
with open(INPUT) as f:
    rwi = json.load(f)

features = []
year_counts = {y: 0 for y in YEARS}
district_hits = 0

for g in rwi["grids"]:
    if "lat" not in g or "lng" not in g:
        continue

    lat, lng = g["lat"], g["lng"]

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

    # Timeseries
    pi_vals = {}
    for y in YEARS:
        if f"pi{y}" in g:
            pi_vals[str(y)] = round(g[f"pi{y}"], 1)

    # District match
    pt = Point(lng, lat)
    location = None
    candidates = tree.query(pt, predicate="intersects")
    if candidates.size > 0:
        location = districts[candidates[0]][1]
        district_hits += 1

    # Nearest PLZ
    dist, idx = plz_tree.query([(lat, lng)])
    plz = plz_codes[int(idx.item())]

    features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {
            "pi": round(best_pi, 1),
            "year": best_year,
            "location": location,
            "plz": plz,
            "grid": g["grid"],
            "pi_all": pi_vals,
            "n": g.get(f"n{best_year}", 0),
            "change_pct": round(g.get("change_pct", 0), 1),
        }
    })

geojson = {"type": "FeatureCollection", "features": features}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, "w") as f:
    json.dump(geojson, f)

size_kb = os.path.getsize(OUTPUT) / 1024
print(f"\nWrote {len(features)} grid cells → {OUTPUT} ({size_kb:.0f} KB)")
print(f"District matches: {district_hits}/{len(features)} ({100*district_hits/len(features):.1f}%)")
print(f"PLZ matches: {len(features)}/{len(features)} (100%)")
print(f"Year distribution:")
for y in YEARS:
    if year_counts[y]:
        print(f"  {y}: {year_counts[y]:>5} grids")
print(f"\nSample locations:")
for f in features[:8]:
    print(f"  {f['properties']['grid']:12s} → PLZ {f['properties']['plz']} · {f['properties']['location']}")
