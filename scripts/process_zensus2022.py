#!/usr/bin/env python3
"""Process Zensus 2022 100m grid rent data into dashboard-compatible JSON.

Converts LAEA → WGS84, filters invalid rows, aggregates to 1km grid."""
import csv
import json
import os
from collections import defaultdict

from pyproj import Transformer

BASE = os.environ.get("MIETSPIEGEL_REPO", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(BASE, "data/external/Zensus2022_Durchschn_Nettokaltmiete_100m-Gitter.csv")
OUT_PATH = os.path.join(BASE, "docs/data/processed/zensus2022_rent_1km.json")

# CRS transform: ETRS89-LAEA → WGS84
transformer = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)

# Aggregate to 1km grid: key = (km_east, km_north)
grid = defaultdict(lambda: {"values": [], "count": 0})

total = 0
valid = 0
flagged = 0

print("Processing Zensus 2022 100m grid...")
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=";")
    for row in reader:
        total += 1
        if total % 250000 == 0:
            print(f"  {total/1e6:.1f}M rows...")

        # Skip flagged rows (confidential / low sample)
        flag = row.get("werterlaeuternde_Zeichen", "").strip()
        if flag:
            flagged += 1
            continue

        try:
            x = float(row["x_mp_100m"])  # easting in meters
            y = float(row["y_mp_100m"])  # northing in meters
            rent = float(row["durchschnMieteQM"].replace(",", "."))
        except (ValueError, KeyError):
            continue

        # Convert to WGS84
        lng, lat = transformer.transform(x, y)

        # Aggregate to 1km grid
        km_east = int(x / 1000)
        km_north = int(y / 1000)
        key = f"{km_east}_{km_north}"
        grid[key]["values"].append(rent)
        grid[key]["count"] += 1
        valid += 1

print(f"\nTotal rows: {total:,}")
print(f"Valid rent values: {valid:,}")
print(f"Flagged/confidential: {flagged:,}")
print(f"1km grid cells: {len(grid):,}")

# Compute average per 1km cell
output = []
for key, data in grid.items():
    avg = sum(data["values"]) / len(data["values"])
    km_east, km_north = map(int, key.split("_"))
    lng, lat = transformer.transform(km_east * 1000 + 500, km_north * 1000 + 500)  # center of km cell
    output.append({
        "grid": key,
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "rent": round(avg, 2),
        "n": data["count"],
    })

# Sort by rent for better compression
output.sort(key=lambda x: x.get("rent", 0))

# Stats
rents = [g["rent"] for g in output]
mean = sum(rents) / len(rents)
std = (sum((r - mean)**2 for r in rents) / len(rents)) ** 0.5

result = {
    "source": "Zensus 2022 — Durchschnittliche Nettokaltmiete (Destatis)",
    "license": "Datenlizenz Deutschland – Namensnennung 2.0",
    "year": 2022,
    "grid_size": "1km (aggregated from 100m)",
    "total_cells": len(output),
    "mean": round(mean, 2),
    "std": round(std, 2),
    "cells": output,
}

with open(OUT_PATH, "w") as f:
    json.dump(result, f)

size_mb = os.path.getsize(OUT_PATH) / (1024 * 1024)
print(f"\nSaved: {OUT_PATH} ({size_mb:.1f} MB)")
print(f"Mean rent: €{mean:.2f}/m², σ=€{std:.2f}")
print(f"Rent range: €{min(rents):.2f} – €{max(rents):.2f}")
