#!/usr/bin/env python3
"""Rebuild historical Mietspiegel edition data from the official PDFs.

Extracts all four archived editions (2017/2019/2021/2023) with the
coordinate-based parser (scripts/extract_wide_editions.py) and derives two
documented series:

- by_lage: mean of Mittelwerte in the NEWEST cohort (2003-2015 for 2017,
  2003-2017 for 2019+) across its non-empty size bands, excluding cells the
  official table flags as low-sample (* /**).
- by_lage_same_cohort: same, but for the 1991-2002 cohort — present in ALL
  editions with full data, so it is the apples-to-apples time series.

Writes:
- docs/data/processed/berlin_historical_editions.json  (full transcription)
- data/historical_mietspiegel.json
- docs/data/processed/berlin_historical.json

Usage:
    python3 scripts/build_historical.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from extract_wide_editions import extract_wide  # noqa: E402

RAW = REPO / "data" / "raw"
EDITIONS = [
    (2017, "01.09.2016"),
    (2019, "01.09.2018"),
    (2021, "01.09.2020"),
    (2023, "01.09.2022"),
]


def cohort_mean(edition, cohort_label, lage, exclude_low_sample=True):
    """Mean of Mittelwerte for a cohort across its size bands for one Lage."""
    ci = edition["cohorts"].index(cohort_label)
    vals = []
    for row in edition["rows"]:
        if row["lage"] != lage:
            continue
        v = row["values"][ci]
        if not v or v["mittelwert"] is None:
            continue
        if exclude_low_sample and v.get("low_sample"):
            continue
        vals.append(v["mittelwert"])
    return round(sum(vals) / len(vals), 2) if vals else None


def main():
    editions = []
    for year, stichtag in EDITIONS:
        raw = extract_wide(str(RAW / f"mietspiegeltabelle{year}.pdf"), year)
        if raw["n_medians"] != 12 or raw["n_spannes"] != 12 or raw["n_columns"] != 8:
            raise SystemExit(
                f"edition {year}: structure check failed "
                f"(medians={raw['n_medians']}, spannes={raw['n_spannes']}, "
                f"cols={raw['n_columns']})"
            )
        lage_mismatch = [r for r in raw["rows"] if r["lage"] != r["lage_check"]]
        if lage_mismatch:
            raise SystemExit(f"edition {year}: lage label mismatch: {lage_mismatch}")
        editions.append({
            "year": year,
            "stichtag": stichtag,
            "source": (f"data/raw/mietspiegeltabelle{year}.pdf "
                       f"(official, mietspiegel.berlin.de archive)"),
            "cohorts": raw["cohorts"],
            "rows": [{"lage": r["lage"], "size": r["size"], "values": r["values"]}
                     for r in raw["rows"]],
        })

    # derived series
    by_lage = {}
    by_lage_1991 = {}
    for e in editions:
        newest = e["cohorts"][-1]
        by_lage[e["year"]] = {
            lage: cohort_mean(e, newest, lage) for lage in ("einfach", "mittel", "gut")
        }
        by_lage_1991[e["year"]] = {
            lage: cohort_mean(e, "1991-2002", lage)
            for lage in ("einfach", "mittel", "gut")
        }

    editions_file = {
        "schema": "official-edition-extraction-v1",
        "note": (
            "Extracted deterministically from the official PDFs with "
            "scripts/extract_wide_editions.py (coordinate-based). low_sample "
            "marks cells the official table flags with * or ** (< 30 "
            "Mietwerte). 2013/2015 are not in the official archive."
        ),
        "editions": editions,
        "by_lage_series": {str(y): v for y, v in by_lage.items()},
        "by_lage_same_cohort_series": {str(y): v for y, v in by_lage_1991.items()},
    }
    (REPO / "docs/data/processed/berlin_historical_editions.json").write_text(
        json.dumps(editions_file, ensure_ascii=False, indent=2))

    out = {
        "schema_version": "2.0",
        "city": "Berlin",
        "description": "Berlin Mietspiegel editions — extracted from official PDFs",
        "last_updated": "2026-08-27",
        "provenance": {
            "2023": "extracted from data/raw/mietspiegeltabelle2023.pdf, verified",
            "2021": "extracted from data/raw/mietspiegeltabelle2021.pdf, verified",
            "2019": "extracted from data/raw/mietspiegeltabelle2019.pdf, verified",
            "2017": "extracted from data/raw/mietspiegeltabelle2017.pdf, verified",
            "2013/2015": "not available in official archive",
        },
        "derivation": {
            "by_lage": ("mean of Mittelwerte in the NEWEST cohort across its "
                        "non-empty size bands, excluding low-sample cells. "
                        "Cohort boundary: 2003-2015 for 2017, 2003-2017 for "
                        "2019/2021/2023."),
            "by_lage_same_cohort": ("mean of Mittelwerte in the 1991-2002 cohort "
                                    "(present in all editions) — the "
                                    "apples-to-apples time series."),
        },
        "by_lage": {str(y): v for y, v in by_lage.items()},
        "by_lage_same_cohort": {str(y): v for y, v in by_lage_1991.items()},
        "editions": editions,
    }
    for p in ("data/historical_mietspiegel.json",
              "docs/data/processed/berlin_historical.json"):
        (REPO / p).write_text(json.dumps(out, ensure_ascii=False, indent=2))

    print("wrote editions + historical files")
    print("by_lage (newest cohort):", json.dumps(by_lage))
    print("by_lage_same_cohort (1991-2002):", json.dumps(by_lage_1991))


if __name__ == "__main__":
    main()
