#!/usr/bin/env python3
"""Normalize Mietspiegel data for the Leaflet dashboard.

Reads from:
  - /tmp/ms-repo/data/processed/cities.json  (14 cities with tables)
  - /tmp/ms-repo/data/processed/{slug}.json   (per-city data with current_edition)
  - workspace extraction files (newly extracted cities)

Outputs:
  - data/processed/cities_index.json  (city list for map markers)
  - data/processed/{slug}.json        (per-city data for detail view)
"""

import json
import os
import sys
from pathlib import Path

REPO_DATA = Path("/tmp/ms-repo/data/processed")

# Known city coordinates for all cities in scope
CITY_COORDS = {
    "berlin": (52.5200, 13.4050),
    "hamburg": (53.5511, 9.9937),
    "muenchen": (48.1351, 11.5820),
    "cologne": (50.9375, 6.9603),
    "koeln": (50.9375, 6.9603),
    "frankfurt": (50.1109, 8.6821),
    "stuttgart": (48.7758, 9.1829),
    "duesseldorf": (51.2277, 6.7735),
    "leipzig": (51.3397, 12.3731),
    "dresden": (51.0504, 13.7373),
    "hannover": (52.3759, 9.7320),
    "aachen": (50.7753, 6.0839),
    "augsburg": (48.3705, 10.8978),
    "braunschweig": (52.2689, 10.5268),
    "chemnitz": (50.8278, 12.9214),
    "halle": (51.4828, 11.9700),
    "kiel": (54.3233, 10.1228),
    "moenchengladbach": (51.1805, 6.4428),
    "bielefeld": (52.0302, 8.5325),
    "bonn": (50.7374, 7.0982),
    "duisburg": (51.4344, 6.7624),
    "mannheim": (49.4875, 8.4660),
    "nuernberg": (49.4521, 11.0766),
    "fehlerburg": (51.0, 10.0),
}

CITY_POPULATIONS = {
    "berlin": 3700000,
    "hamburg": 1900000,
    "muenchen": 1500000,
    "cologne": 1100000,
    "koeln": 1100000,
    "frankfurt": 760000,
    "stuttgart": 630000,
    "duesseldorf": 620000,
    "leipzig": 600000,
    "dresden": 560000,
    "hannover": 540000,
    "aachen": 250000,
    "augsburg": 300000,
    "braunschweig": 250000,
    "chemnitz": 245000,
    "halle": 240000,
    "kiel": 250000,
    "moenchengladbach": 260000,
    "bielefeld": 340000,
    "bonn": 330000,
    "duisburg": 500000,
    "mannheim": 310000,
    "nuernberg": 520000,
}

# Build slug map: city name -> slug
CITY_SLUG_MAP = {
    "Berlin": "berlin", "Hamburg": "hamburg", "München": "muenchen",
    "Munich": "muenchen", "Köln": "koeln", "Cologne": "cologne",
    "Frankfurt": "frankfurt", "Stuttgart": "stuttgart",
    "Düsseldorf": "duesseldorf", "Leipzig": "leipzig",
    "Dresden": "dresden", "Hannover": "hannover",
    "Aachen": "aachen", "Augsburg": "augsburg",
    "Braunschweig": "braunschweig", "Chemnitz": "chemnitz",
    "Halle (Saale)": "halle", "Kiel": "kiel",
    "Mönchengladbach": "moenchengladbach", "Bielefeld": "bielefeld",
    "Bonn": "bonn", "Duisburg": "duisburg",
    "Mannheim": "mannheim", "Nürnberg": "nuernberg",
}


def get_slug(city_name):
    """Get slug from city name."""
    return CITY_SLUG_MAP.get(city_name, city_name.lower().replace(" ", "_").replace("ü", "ue").replace("ö", "oe").replace("ä", "ae").replace("ß", "ss"))


def normalize_table_row(row, size_labels=None):
    """Normalize a table row to {bis_40, 40_60, 60_90, ueber_90, baujahr}."""
    result = {}
    
    if isinstance(row, dict):
        # Check for size_rows format (cities.json format)
        if "size_rows" in row:
            # This is a {lage, baujahr_group, size_rows} entry
            result["baujahr"] = row.get("baujahr_group", "")
            for sr in row.get("size_rows", []):
                label = sr.get("label", "")
                val = sr.get("mittelwert") or sr.get("value")
                if val is not None:
                    key = size_label_to_key(label)
                    result[key] = val
            return result
        
        # Direct row format
        result["baujahr"] = row.get("baujahr", row.get("baujahr_group", ""))
        
        # size_under_40, size_40_60, etc. format
        if "size_under_40" in row:
            result["bis_40"] = row["size_under_40"]
            result["40_60"] = row.get("size_40_60")
            result["60_90"] = row.get("size_60_90")
            result["ueber_90"] = row.get("size_over_90")
        elif "bis_40" in row:
            result["bis_40"] = row.get("bis_40")
            result["40_60"] = row.get("40_60")
            result["60_90"] = row.get("60_90")
            result["ueber_90"] = row.get("ueber_90")
        
        # Single value (e.g. base_rent)
        if "base_rent" in row:
            result["bis_40"] = row["base_rent"]
            result["40_60"] = row["base_rent"]
            result["60_90"] = row["base_rent"]
            result["ueber_90"] = row["base_rent"]
    
    return result


def size_label_to_key(label):
    """Convert size label like 'bis 40 m²' to key like 'bis_40'."""
    if not label:
        return None
    label = label.lower().replace("²", "").replace(" ", "").replace("m", "")
    if "bis" in label and "40" in label:
        return "bis_40"
    if "40" in label and "60" in label:
        return "40_60"
    if "60" in label and "90" in label:
        return "60_90"
    if "über" in label or "ueber" in label or ">" in label:
        return "ueber_90"
    return None


def normalize_city_data(city_entry, per_city_data=None):
    """Normalize a city entry to dashboard format."""
    city_name = city_entry.get("city", "Unknown")
    slug = city_entry.get("city_slug", city_entry.get("slug", get_slug(city_name)))
    
    # Coordinates & population
    coords = CITY_COORDS.get(slug)
    if per_city_data:
        lat = per_city_data.get("lat") or (coords[0] if coords else 51.0)
        lng = per_city_data.get("lng") or (coords[1] if coords else 10.0)
        pop = per_city_data.get("population") or CITY_POPULATIONS.get(slug, 100000)
    else:
        coords_arr = city_entry.get("coordinates")
        if coords_arr:
            lat, lng = coords_arr[0], coords_arr[1]
        elif coords:
            lat, lng = coords
        else:
            lat, lng = 51.0, 10.0
        pop = CITY_POPULATIONS.get(slug, 100000)
    
    state = city_entry.get("state", per_city_data.get("state", "") if per_city_data else "")
    
    # ---- Try format A: current_edition format (berlin.json style) ----
    if per_city_data and "current_edition" in per_city_data:
        ed = per_city_data["current_edition"]
        tables_dict = ed.get("tables", {})
        tables = []
        for lage_key, rows in tables_dict.items():
            norm_rows = []
            for row in rows:
                nr = normalize_table_row(row)
                if nr.get("bis_40") is not None:
                    norm_rows.append(nr)
            if norm_rows:
                tables.append({"lage": lage_key, "rows": norm_rows})
        
        lage_categories = per_city_data.get("lage_categories", list(tables_dict.keys()))
        baujahr_groups = []
        size_categories = ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"]
        if tables:
            for t in tables:
                for r in t["rows"]:
                    if r.get("baujahr") and r["baujahr"] not in baujahr_groups:
                        baujahr_groups.append(r["baujahr"])
        
        return {
            "city": city_name, "city_slug": slug, "slug": slug,
            "state": state, "lat": lat, "lng": lng, "population": pop,
            "year": ed.get("year", city_entry.get("year")),
            "type": per_city_data.get("type", city_entry.get("type")),
            "lage_categories": lage_categories,
            "baujahr_groups": baujahr_groups,
            "size_categories": size_categories,
            "source_url": ed.get("source_url", ""),
            "tables": tables,
        }
    
    # ---- Try format B: cities.json compact format (tables as [{lage, baujahr_group, size_rows}]) ----
    raw_tables = city_entry.get("tables", [])
    if raw_tables and isinstance(raw_tables[0], dict) and "lage" in raw_tables[0] and "baujahr_group" in raw_tables[0]:
        tables_map = {}  # lage -> rows
        for t in raw_tables:
            lage = t.get("lage", "mittel")
            if lage not in tables_map:
                tables_map[lage] = []
            norm = {"baujahr": t.get("baujahr_group", "")}
            for sr in t.get("size_rows", []):
                label = sr.get("label", "")
                val = sr.get("mittelwert") or sr.get("value")
                if val is not None:
                    key = size_label_to_key(label)
                    if key:
                        norm[key] = val
            if norm.get("bis_40") is not None:
                tables_map[lage].append(norm)
        
        tables = [{"lage": k, "rows": v} for k, v in tables_map.items() if v]
        
        lage_categories = city_entry.get("categories", {}).get("lage", list(tables_map.keys()))
        baujahr_groups = city_entry.get("categories", {}).get("baujahr_groups", [])
        size_categories = city_entry.get("categories", {}).get("size_groups", ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"])
        
        return {
            "city": city_name, "city_slug": slug, "slug": slug,
            "state": state, "lat": lat, "lng": lng, "population": pop,
            "year": city_entry.get("year"),
            "type": city_entry.get("type", "qualifiziert"),
            "lage_categories": lage_categories,
            "baujahr_groups": baujahr_groups,
            "size_categories": size_categories,
            "source_url": city_entry.get("source_url", ""),
            "tables": tables,
        }
    
    # ---- Try format C: extracted table data (tables as [{type, rows, header}]) ----
    if raw_tables and isinstance(raw_tables[0], dict) and "type" in raw_tables[0]:
        # Extract what we can
        lage_categories = city_entry.get("categories", {}).get("lage", ["mittel"])
        if not lage_categories:
            lage_categories = ["mittel"]
        baujahr_groups = city_entry.get("categories", {}).get("baujahr_groups", [])
        size_groups = city_entry.get("categories", {}).get("size_groups", [])
        
        # For the dashboard, create single-table with whatever data we have
        rows = []
        for t in raw_tables:
            for row in t.get("rows", []):
                nr = {}
                # Try to map this row
                if "size" in row and "base_rent" in row:
                    nr = {"baujahr": "aktuell", "bis_40": row["base_rent"],
                          "40_60": row["base_rent"], "60_90": row["base_rent"],
                          "ueber_90": row["base_rent"]}
                elif "values" in row:
                    # Augsburg-style: values array aligned with header
                    pass  # too complex for auto-normalization
                if nr.get("bis_40") is not None:
                    rows.append(nr)
        
        tables = [{"lage": lage_categories[0], "rows": rows}] if rows else []
        
        return {
            "city": city_name, "city_slug": slug, "slug": slug,
            "state": state, "lat": lat, "lng": lng, "population": pop,
            "year": city_entry.get("year"),
            "type": city_entry.get("type", "qualifiziert"),
            "lage_categories": lage_categories,
            "baujahr_groups": baujahr_groups if baujahr_groups else ["aktuell"],
            "size_categories": size_groups if size_groups else ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"],
            "source_url": city_entry.get("source_url", ""),
            "tables": tables,
        }
    
    # Fallback
    return {
        "city": city_name, "city_slug": slug, "slug": slug,
        "state": state, "lat": lat, "lng": lng, "population": pop,
        "year": city_entry.get("year"),
        "type": city_entry.get("type", "qualifiziert"),
        "lage_categories": ["einfach", "mittel", "gut"],
        "baujahr_groups": [],
        "size_categories": ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"],
        "source_url": "",
        "tables": [],
    }


def main():
    output_dir = Path("/Users/ruhvee/.hermes/kanban/boards/mietspiegel-digitization/workspaces/t_5d8fc893/data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load main cities.json
    cities_json_path = REPO_DATA / "cities.json"
    if not cities_json_path.exists():
        print(f"ERROR: {cities_json_path} not found")
        sys.exit(1)
    
    with open(cities_json_path) as f:
        cities_data = json.load(f)
    
    print(f"Loaded {len(cities_data)} cities from cities.json")
    
    # 2. Load per-city data
    per_city = {}
    for f in sorted(REPO_DATA.glob("*.json")):
        slug = f.stem
        if slug in ("cities", "index", "stadt-index", "mietspiegel_katalog",
                     "berlin_extracted_camelot", "berlin_extracted_pdfplumber",
                     "dresden-extended", "fehlerburg"):
            continue
        try:
            with open(f) as fh:
                data = json.load(fh)
            if isinstance(data, dict) and "city" in data:
                per_city[slug] = data
        except:
            pass
    
    print(f"Loaded {len(per_city)} per-city data files")
    
    # 3. Also check extraction workspace data
    workspace_paths = [
        Path("/Users/ruhvee/.hermes/kanban/boards/mietspiegel-digitization/workspaces/t_275a8410/data/processed"),
        Path("/Users/ruhvee/.hermes/kanban/boards/mietspiegel-digitization/workspaces/t_b3ea9811/data/processed"),
    ]
    for wp in workspace_paths:
        if wp.exists():
            for f in sorted(wp.glob("*.json")):
                slug = f.stem
                if slug in per_city or slug in ("index",):
                    continue
                try:
                    with open(f) as fh:
                        data = json.load(fh)
                    if isinstance(data, dict) and "city" in data:
                        per_city[slug] = data
                        print(f"  Added from workspace: {slug}")
                except:
                    pass
    
    # 4. Normalize all cities
    city_index = []
    city_slugs_seen = set()
    
    for entry in cities_data:
        city_name = entry.get("city", "Unknown")
        slug = entry.get("city_slug", get_slug(city_name))
        
        if slug in city_slugs_seen:
            continue
        city_slugs_seen.add(slug)
        
        pcd = per_city.get(slug)
        norm = normalize_city_data(entry, pcd)
        
        # Write per-city file
        city_file = output_dir / f"{slug}.json"
        with open(city_file, "w") as f:
            json.dump(norm, f, indent=2, ensure_ascii=False)
        
        # Add to index
        city_index.append({
            "city": norm["city"],
            "slug": slug,
            "lat": norm["lat"],
            "lng": norm["lng"],
            "state": norm["state"],
            "population": norm["population"],
        })
        
        table_count = len(norm.get("tables", []))
        row_count = sum(len(t.get("rows", [])) for t in norm.get("tables", []))
        print(f"  {city_name:25s} ({slug:15s})  {norm['year']}  {norm['type']:30s}  {table_count} tables, {row_count} rows")
    
    # 4b. Also add workspace-only cities not in the main index
    # Map alternative slugs to canonical slugs
    ALIAS_SLUGS = {"cologne": "koeln", "munich": "muenchen"}
    
    workspace_only = [s for s in per_city if s not in city_slugs_seen and not s.endswith("_standardized") and s not in ALIAS_SLUGS]
    for slug in sorted(workspace_only):
        data = per_city[slug]
        city_name = data.get("city", slug)
        if not isinstance(city_name, str):
            if isinstance(city_name, dict):
                city_name = city_name.get("name", city_name.get("city", slug))
            else:
                city_name = str(city_name)
        
        # Build a minimal entry for the dashboard
        lage_cats = data.get("lage_categories", data.get("categories", {}).get("lage", ["mittel"]))
        if not lage_cats:
            lage_cats = ["mittel"]
        baujahr_gps = data.get("categories", {}).get("baujahr_groups", [])
        size_cats = data.get("categories", {}).get("size_groups", ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"])
        
        # Try to extract tables
        raw_tables = data.get("tables", [])
        rows = []
        for t in raw_tables:
            if "rows" in t:
                for row in t["rows"]:
                    if "size" in row and "base_rent" in row:
                        rows.append({"baujahr": "aktuell", "bis_40": row["base_rent"],
                                      "40_60": row["base_rent"], "60_90": row["base_rent"],
                                      "ueber_90": row["base_rent"]})
                    elif "values" in row and "header" in t:
                        # Augsburg-style: find the mid-size column
                        header = t.get("header", [])
                        for i, h in enumerate(header):
                            if "60" in str(h) and "70" in str(h) and i < len(row.get("values", [])):
                                val = row["values"][i]
                                if val is not None:
                                    rows.append({"baujahr": h, "bis_40": val, "40_60": val, "60_90": val, "ueber_90": val})
                                break
        
        coords = CITY_COORDS.get(slug, (51.0, 10.0))
        # Try to get coordinates from per-city data if it's a dict format
        if isinstance(data.get("city"), dict) and "coordinates" in data["city"]:
            c = data["city"]["coordinates"]
            if isinstance(c, dict):
                coords = (c.get("lat", coords[0]), c.get("lng", coords[1]))
            elif isinstance(c, (list, tuple)) and len(c) >= 2:
                coords = (c[0], c[1])
        # Also try lat/lng directly in data
        if data.get("lat") and data.get("lng"):
            coords = (data["lat"], data["lng"])
        norm = {
            "city": city_name, "city_slug": slug, "slug": slug,
            "state": data.get("state", ""),
            "lat": coords[0], "lng": coords[1],
            "population": CITY_POPULATIONS.get(slug, 100000),
            "year": data.get("year"),
            "type": data.get("type", "qualifiziert"),
            "lage_categories": lage_cats,
            "baujahr_groups": baujahr_gps if baujahr_gps else ["aktuell"],
            "size_categories": size_cats if size_cats else ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"],
            "source_url": data.get("source_url", ""),
            "tables": [{"lage": lage_cats[0], "rows": rows}] if rows else [],
        }
        
        city_file = output_dir / f"{slug}.json"
        with open(city_file, "w") as f:
            json.dump(norm, f, indent=2, ensure_ascii=False)
        
        city_index.append({
            "city": city_name, "slug": slug,
            "lat": coords[0], "lng": coords[1],
            "state": data.get("state", ""),
            "population": CITY_POPULATIONS.get(slug, 100000),
        })
        
        tc = len(norm["tables"])
        rc = sum(len(t.get("rows", [])) for t in norm["tables"])
        print(f"  {city_name:25s} ({slug:15s})  {norm['year']}  {norm['type']:30s}  {tc} tables, {rc} rows  [workspace-only]")
    
    # 5. Sort index alphabetically and write
    city_index.sort(key=lambda c: c["city"])
    index_path = output_dir / "cities_index.json"
    with open(index_path, "w") as f:
        json.dump(city_index, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Written {len(city_index)} cities to {output_dir}")
    print(f"   Index: {index_path}")
    
    # 6. List per-city files
    files = sorted(output_dir.glob("*.json"))
    print(f"   Per-city files: {len(files)}")


if __name__ == "__main__":
    main()
