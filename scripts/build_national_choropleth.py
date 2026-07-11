#!/usr/bin/env python3
"""Build national rent map GeoJSON from RWI-GEO-REDX grid data.

Converts 1km² grid cells (ETRS89-LAEA) to WGS84 polygons for a proper
choropleth/heatmap view instead of point dots.

- Uses most recent available year per grid cell.
- Spatial join to German district (Kreis) for names.
- Nearest-neighbor match to 8,299 PLZ codes for ZIP granularity.
"""
import csv
import json
import os
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.strtree import STRtree
from scipy.spatial import KDTree

BASE = os.environ.get("MIETSPIEGEL_REPO", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT = os.path.join(BASE, "data/processed/redx_grid_rent.json")
KREISE = os.path.join(BASE, "data/external/germany-kreise.geojson")
PLZ_CSV = os.path.join(BASE, "data/external/plz_centroids.csv")
OUTPUT = os.path.join(BASE, "docs/data/processed/national-rent-grid.geojson")

YEARS = [2008, 2013, 2018, 2023, 2024, 2025]

# ─── Coordinate transformer: LAEA (EPSG:3035) → WGS84 (EPSG:4326) ──
# Grid IDs are E_XXXX_N_YYYY where X=easting(km), Y=northing(km)
transformer = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)

def grid_to_polygon(grid_id):
    """Convert a grid ID like '4041_3077' to a WGS84 polygon (5-point ring)."""
    parts = grid_id.split("_")
    if len(parts) != 2:
        return None
    try:
        ex = int(parts[0])
        ny = int(parts[1])
    except ValueError:
        return None
    # LAEA: 1 grid unit = 1 km → multiply by 1000 for meters
    x0, y0 = ex * 1000, ny * 1000
    x1, y1 = x0 + 1000, y0 + 1000
    # Four corners in LAEA, reprojected to WGS84
    corners = [
        transformer.transform(x0, y0),
        transformer.transform(x1, y0),
        transformer.transform(x1, y1),
        transformer.transform(x0, y1),
        transformer.transform(x0, y0),  # close the ring
    ]
    return [[c[0], c[1]] for c in corners]

# ─── Load PLZ centroids ─────────────────────────────────────────
plz_coords, plz_codes = [], []
with open(PLZ_CSV, newline="") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith(','):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        try:
            plz_codes.append(parts[0].strip())
            plz_coords.append((float(parts[1]), float(parts[2])))
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
    label = name if name == state else f"{name}, {state}"
    districts.append((shape(feat["geometry"]), label))

print(f"Indexing {len(districts)} districts...")
tree = STRtree([d[0] for d in districts])

# ─── Build polygon features ─────────────────────────────────────
with open(INPUT) as f:
    rwi = json.load(f)

features = []
year_counts = {y: 0 for y in YEARS}
district_hits = 0
poly_errors = 0

for g in rwi["grids"]:
    if "lat" not in g or "lng" not in g:
        continue

    lat, lng = g["lat"], g["lng"]
    grid_id = g.get("grid", "")

    # Polygon from grid ID
    ring = grid_to_polygon(grid_id)
    if ring is None:
        poly_errors += 1
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

    # Timeseries
    pi_vals = {}
    for y in YEARS:
        if f"pi{y}" in g:
            pi_vals[str(y)] = round(g[f"pi{y}"], 1)

    # District match (using centroid)
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
        "geometry": {
            "type": "Polygon",
            "coordinates": [ring]
        },
        "properties": {
            "pi": round(best_pi, 1),
            "year": best_year,
            "location": location,
            "plz": plz,
            "grid": grid_id,
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
print(f"\nWrote {len(features)} polygons → {OUTPUT} ({size_kb:.0f} KB)")
print(f"Polygon errors: {poly_errors}")
print(f"District matches: {district_hits}/{len(features)} ({100*district_hits/len(features):.1f}%)")
print(f"Year distribution:")
for y in YEARS:
    if year_counts[y]:
        print(f"  {y}: {year_counts[y]:>5} grids")
print(f"\nSample:")
for f in features[:4]:
    p = f["properties"]
    print(f"  {p['grid']:12s} → PLZ {p['plz']} · {p['location']} → €{p['pi']}/m²")
