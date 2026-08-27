#!/usr/bin/env python3
"""Rebuild the Berlin Mietspiegel 2024 dashboard table from the RAW extraction.

Source of truth: docs/data/processed/berlin_raw_2024.json (163 rows, extracted
from the official PDF and diff-verified by scripts/verify_berlin_extraction.py).

Output: docs/data/processed/berlin.json — preserves the OFFICIAL cohorts and
size bands. No invented groups, no interpolation. Each row carries the real
Mittelwert plus untere/obere Spanne (the legal range used by Mietpreisbremse).

Usage:
    python3 scripts/build_city_tables.py
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "docs/data/processed/berlin_raw_2024.json"
OUT = REPO / "docs/data/processed/berlin.json"


def parse_size_band(label: str):
    """'bis unter 35 m²' -> (0, 35) | '40 m² bis unter 45 m²' -> (40, 45) | 'ab 105 m²' -> (105, None)"""
    label = label.replace("\u00b2", "").strip()
    if m := re.match(r"bis unter (\d+)\s*m", label):
        return (0.0, float(m.group(1)))
    if m := re.match(r"(\d+)\s*m bis unter (\d+)\s*m", label):
        return (float(m.group(1)), float(m.group(2)))
    if m := re.match(r"ab (\d+)\s*m", label):
        return (float(m.group(1)), None)
    if "alle" in label.lower():
        return (0.0, None)
    return (None, None)


def main():
    raw = json.loads(RAW.read_text())
    rows = raw["data"]
    if len(rows) != 163:
        raise SystemExit(f"expected 163 raw rows, got {len(rows)}")

    official_tables: dict[str, list[dict]] = {}
    for r in rows:
        lage = r["_lage"]
        s_min, s_max = parse_size_band(r["size_range"])
        official_tables.setdefault(lage, []).append({
            "baujahr": r["baujahr"],
            "size_min_m2": s_min,
            "size_max_m2": s_max,
            "size_range": r["size_range"],
            "mittelwert": r["mittelwert"],
            "untere_spanne": r["untere_spanne"],
            "obere_spanne": r["obere_spanne"],
        })

    # Legacy 4-band table (bis_40/40_60/60_90/ueber_90): mean of the official
    # Mittelwerte whose size band falls inside the legacy bucket. Derived,
    # clearly labeled, so existing consumers keep working.
    LEGACY_BANDS = {
        "bis_40": (0.0, 40.0),
        "40_60": (40.0, 60.0),
        "60_90": (60.0, 90.0),
        "ueber_90": (90.0, None),
    }
    legacy_tables = []
    for lage, orows in official_tables.items():
        leg_rows = []
        for cohort in sorted({r["baujahr"] for r in orows}):
            cohort_rows = [r for r in orows if r["baujahr"] == cohort]
            out = {"baujahr": cohort}
            for key, (lo, hi) in LEGACY_BANDS.items():
                in_band = [r for r in cohort_rows
                           if (lo is None or (r["size_min_m2"] or 0) >= lo)
                           and (hi is None or (r["size_min_m2"] or 0) < hi)]
                if in_band:
                    out[key] = round(sum(r["mittelwert"] for r in in_band) / len(in_band), 2)
            leg_rows.append(out)
        legacy_tables.append({"lage": lage, "rows": leg_rows})

    out = {
        "city": "Berlin",
        "city_slug": "berlin",
        "slug": "berlin",
        "state": "Berlin",
        "lat": 52.52,
        "lng": 13.405,
        "population": 3700000,
        "year": 2024,
        "type": "qualifiziert",
        "source": "Berliner Mietspiegel 2024, Tabelle 9.1-9.3 (Stichtag 01.09.2023)",
        "source_url": "https://www.berlin.de/mietspiegel/",
        "source_file": "data/raw/berlin-mietspiegeltabelle-2024.pdf",
        "schema_note": "official_rows preserves the official cohorts and size bands verbatim. "
                        "tables is a derived 4-band rollup (mean of official Mittelwerte per band) "
                        "kept for legacy consumers; use official_rows for legal comparisons.",
        "lage_categories": ["einfach", "mittel", "gut"],
        "official_rows": [
            {"lage": lage, "rows": official_tables[lage]}
            for lage in ["einfach", "mittel", "gut"]
        ],
        "tables": legacy_tables,
        "generated_at": raw.get("generated_at"),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"wrote {OUT} — {len(rows)} official rows + legacy 4-band rollup")


if __name__ == "__main__":
    main()
