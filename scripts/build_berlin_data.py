#!/usr/bin/env python3
"""
Build Berlin-only data files from national datasets.

Filters RWI-GEO-REDX grids and Zensus 2022 census data to Berlin bounding box,
recalculates local z-scores, and writes the files that berlin.html expects.

Usage:
    python3 scripts/build_berlin_data.py

Inputs:
    data/processed/redx_grid_rent.json     — RWI price indices per 1km grid cell
    docs/data/processed/zensus2022_rent_1km.json  — Zensus census rents per 1km cell

Outputs:
    docs/data/processed/berlin_immoscout.json
    docs/data/processed/berlin_zensus.json
"""

import json
import math
import os
import sys
from datetime import UTC, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Berlin bounding box (slightly padded)
BBOX = {"lat_min": 52.35, "lat_max": 52.65, "lng_min": 13.05, "lng_max": 13.75}

# Most recent year to pull from the RWI data (only last 5 years)
YEARS = [2021, 2022, 2023, 2024, 2025]


def in_berlin(lat, lng):
    return (
        BBOX["lat_min"] <= lat <= BBOX["lat_max"]
        and BBOX["lng_min"] <= lng <= BBOX["lng_max"]
    )


def build_immoscout():
    """Filter redx_grid_rent.json to Berlin cells, pick most recent year, compute local stats."""
    input_path = os.path.join(REPO, "data/processed/redx_grid_rent.json")
    output_path = os.path.join(REPO, "docs/data/processed/berlin_immoscout.json")

    if not os.path.exists(input_path):
        print(f"  ⚠ Input not found: {input_path}")
        print("    Run `scripts/build.sh` or `python3 scripts/process_redx.py` first")
        return False

    with open(input_path) as f:
        data = json.load(f)

    all_grids = data.get("grids", [])
    print(f"  Loaded {len(all_grids)} national grids")

    # Filter to Berlin: bounding box + location in Berlin
    berlin_grids = []
    for g in all_grids:
        lat = g.get("lat")
        lng = g.get("lng")
        if lat is None or lng is None:
            continue
        if not in_berlin(lat, lng):
            continue
        # Exclude non-Berlin locations that fall inside the bounding box
        loc = (g.get("location") or "")
        if "Berlin" not in loc:
            continue

        # Pick most recent year with price index data
        best_year = None
        best_pi = None
        for y in reversed(YEARS):
            pi = g.get(f"pi{y}")
            if pi is not None and pi > 0:
                best_year = y
                best_pi = pi
                break

        if best_pi is None:
            continue  # no price data for this grid

        n = g.get(f"n{best_year}", 0)

        berlin_grids.append({
            "lat": lat,
            "lng": lng,
            "rent": round(best_pi, 2),
            "year": best_year,
            "n": n,
            "plz": g.get("plz", ""),
            "location": g.get("location", ""),
            "grid": g.get("grid", ""),
        })

    if not berlin_grids:
        print("  ⚠ No Berlin cells found in redx data")
        return False

    # Compute Berlin-specific stats
    rents = [g["rent"] for g in berlin_grids]
    mean = sum(rents) / len(rents)
    variance = sum((r - mean) ** 2 for r in rents) / len(rents)
    std = math.sqrt(variance)

    output = {
        "source": "RWI-GEO-REDX PUF v16",
        "doi": "https://doi.org/10.7807/IMMO:REDX:PUF:V16",
        "description": "Berlin-only Immoscout24 market rent grid cells (price indices as €/m²)",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_version": "1.0",
        "years": sorted(set(g["year"] for g in berlin_grids)),
        "total_grids": len(berlin_grids),
        "mean": round(mean, 2),
        "std": round(std, 2),
        "clean": len(berlin_grids),
        "grids": berlin_grids,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✓ Wrote {len(berlin_grids)} Berlin grids → {output_path}")
    print(f"    Mean: €{mean:.2f}/m², Std: €{std:.2f}/m²")
    print(f"    Years: {output['years']}")
    return True


def build_zensus():
    """Filter zensus2022_rent_1km.json to Berlin cells."""
    input_path = os.path.join(REPO, "docs/data/processed/zensus2022_rent_1km.json")
    output_path = os.path.join(REPO, "docs/data/processed/berlin_zensus.json")

    if not os.path.exists(input_path):
        print(f"  ⚠ Input not found: {input_path}")
        print("    Run `python3 scripts/process_zensus2022.py` first")
        return False

    with open(input_path) as f:
        data = json.load(f)

    all_cells = data.get("cells", [])
    print(f"  Loaded {len(all_cells)} national Zensus cells")

    # Filter to Berlin
    berlin_cells = []
    for c in all_cells:
        lat = c.get("lat")
        lng = c.get("lng")
        rent = c.get("rent")
        if lat is None or lng is None or rent is None:
            continue
        if not in_berlin(lat, lng):
            continue
        berlin_cells.append([lat, lng, rent])

    if not berlin_cells:
        print("  ⚠ No Berlin cells found in Zensus data")
        return False

    # Compute Berlin-specific stats
    rents = [c[2] for c in berlin_cells]
    mean = sum(rents) / len(rents)
    variance = sum((r - mean) ** 2 for r in rents) / len(rents)
    std = math.sqrt(variance)

    output = {
        "source": "Zensus 2022 — Durchschnittliche Nettokaltmiete (Destatis)",
        "license": "Datenlizenz Deutschland – Namensnennung 2.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_version": "1.0",
        "year": 2022,
        "grid_size": "1km (aggregated from 100m)",
        "total_cells": len(berlin_cells),
        "mean": round(mean, 2),
        "std": round(std, 2),
        "cells_slim": berlin_cells,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✓ Wrote {len(berlin_cells)} Berlin Zensus cells → {output_path}")
    print(f"    Mean: €{mean:.2f}/m², Std: €{std:.2f}/m²")
    return True


def main():
    print("═══ Berlin Data Builder ═══\n")

    immo_ok = build_immoscout()
    print()
    zensus_ok = build_zensus()
    print()

    if immo_ok and zensus_ok:
        print("✓ Both Berlin datasets ready — berlin.html heatmap will work")
        return 0
    elif immo_ok:
        print("✓ Only Immoscout data ready — Zensus toggle will be disabled")
        return 1
    elif zensus_ok:
        print("✓ Only Zensus data ready — Immoscout layer missing")
        return 1
    else:
        print("✗ Neither dataset available. See errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
