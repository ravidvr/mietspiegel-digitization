#!/usr/bin/env python3
"""Verified Berlin historical editions — 2023 only (fully transcribed).

2017/2019/2021 PDFs are in data/raw/ awaiting transcription. 2013/2015 are not
in the official archive. The old interpolated by_lage series is dropped.

by_lage = mean of Mittelwerte in the newest cohort (2003-2017) across its
size bands — a documented, reproducible derivation.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ED2023 = {
    "year": 2023, "stichtag": "01.09.2022",
    "source": "data/raw/mietspiegeltabelle2023.pdf (official, mietspiegel.berlin.de)",
    "cohorts": ["bis 1918", "1919-1949", "1950-1964", "1965-1972",
                "1973-1990 West", "1973-1990 Ost", "1991-2002", "2003-2017"],
    "rows": [
        {"lage": "einfach", "size": "<40", "values": [(8.42, 5.86, 13.82), (8.32, 6.40, 9.25), (6.85, 5.90, 9.62), (7.24, 6.39, 9.41), (8.06, 7.92, 9.43), (7.61, 7.30, 8.50), None, None]},
        {"lage": "mittel", "size": "<40", "values": [(8.98, 7.16, 13.04), (8.16, 6.86, 9.11), (7.30, 6.02, 9.64), (7.00, 6.27, 8.78), (8.24, 5.68, 8.70), (7.39, 6.87, 7.70), None, None]},
        {"lage": "gut", "size": "<40", "values": [(12.19, 6.97, 15.17), (7.99, 6.86, 10.10), (7.96, 6.78, 9.92), (9.49, 8.68, 10.39), (8.85, 7.96, 10.75), (7.60, 7.14, 9.31), None, None]},
        {"lage": "einfach", "size": "40-60", "values": [(7.19, 5.61, 10.59), (6.82, 5.78, 8.73), (6.40, 5.73, 8.53), (6.26, 5.39, 7.47), (7.95, 6.61, 9.22), (6.41, 6.09, 6.98), (8.91, 8.21, 10.87), (12.37, 10.34, 16.11)]},
        {"lage": "mittel", "size": "40-60", "values": [(7.92, 5.77, 10.92), (7.18, 6.00, 8.27), (6.51, 5.74, 8.14), (6.38, 5.79, 7.40), (8.24, 6.78, 9.35), (6.35, 5.75, 7.14), (8.72, 7.92, 9.77), (10.50, 7.76, 13.32)]},
        {"lage": "gut", "size": "40-60", "values": [(8.57, 6.39, 11.69), (7.36, 6.41, 9.74), (6.95, 6.02, 8.37), (7.60, 5.64, 10.66), (8.97, 7.86, 9.82), (6.41, 6.21, 7.42), (10.39, 8.67, 11.85), (10.53, 8.26, 12.76)]},
        {"lage": "einfach", "size": "60-90", "values": [(6.75, 5.14, 10.66), (6.25, 5.40, 7.75), (5.94, 5.14, 7.25), (5.81, 5.21, 6.48), (7.75, 6.48, 9.59), (5.62, 5.31, 6.10), (8.22, 6.64, 9.15), (13.73, 9.04, 15.80)]},
        {"lage": "mittel", "size": "60-90", "values": [(7.21, 5.15, 10.66), (6.65, 5.43, 7.80), (6.40, 5.63, 7.55), (6.08, 5.42, 6.82), (8.53, 6.07, 9.71), (5.62, 4.90, 6.13), (8.42, 7.17, 9.62), (10.75, 9.50, 13.00)]},
        {"lage": "gut", "size": "60-90", "values": [(7.98, 5.99, 11.64), (7.57, 6.30, 9.75), (6.97, 5.86, 8.92), (7.08, 5.54, 8.85), (8.86, 7.04, 10.49), (5.93, 5.45, 6.70), (9.69, 7.94, 11.74), (10.89, 9.42, 13.59)]},
        {"lage": "einfach", "size": "90+", "values": [(6.64, 5.10, 9.74), (6.53, 5.48, 7.63), None, (5.83, 5.21, 6.45), (7.66, 6.21, 8.82), (5.58, 5.09, 5.84), (8.48, 7.07, 9.93), (12.73, 9.07, 14.67)]},
        {"lage": "mittel", "size": "90+", "values": [(7.21, 5.20, 10.45), (6.41, 5.44, 9.06), (7.21, 5.99, 12.16), (5.75, 5.40, 6.55), (8.14, 6.37, 9.23), (5.60, 4.91, 5.92), (8.73, 7.68, 10.16), (10.74, 9.38, 13.56)]},
        {"lage": "gut", "size": "90+", "values": [(7.81, 5.84, 11.17), (7.13, 6.06, 9.52), (8.77, 7.13, 9.91), (8.84, 8.03, 9.48), (9.59, 7.53, 12.72), (5.67, 5.42, 6.32), (10.45, 8.71, 12.47), (12.26, 9.95, 14.59)]},
    ],
}


def main():
    newest_idx = len(ED2023["cohorts"]) - 1
    by_lage = {}
    for lage in ("einfach", "mittel", "gut"):
        vals = [row["values"][newest_idx][0] for row in ED2023["rows"]
                if row["lage"] == lage and row["values"][newest_idx]]
        by_lage[lage] = round(sum(vals) / len(vals), 2)

    rows_out = []
    for row in ED2023["rows"]:
        rows_out.append({
            "lage": row["lage"], "size": row["size"],
            "values": [
                {"mittelwert": v[0], "untere": v[1], "obere": v[2]} if v else None
                for v in row["values"]
            ],
        })

    editions_file = {
        "schema": "official-edition-transcription-v1",
        "note": ("Manual transcription from the official PDF. by_lage = mean of "
                 "Mittelwerte in the newest cohort across size bands. "
                 "2017/2019/2021 PDFs in data/raw/ pending transcription; "
                 "2013/2015 not in the official archive."),
        "editions": [{
            "year": ED2023["year"], "stichtag": ED2023["stichtag"],
            "source": ED2023["source"], "cohorts": ED2023["cohorts"],
            "rows": rows_out,
        }],
        "by_lage_series": {"2023": by_lage},
    }
    (REPO / "docs/data/processed/berlin_historical_editions.json").write_text(
        json.dumps(editions_file, ensure_ascii=False, indent=2))

    out = {
        "schema_version": "2.0",
        "city": "Berlin",
        "description": "Berlin Mietspiegel editions — verified transcription from official PDFs",
        "last_updated": "2026-08-27",
        "provenance": {
            "2023": "transcribed from data/raw/mietspiegeltabelle2023.pdf, verified",
            "2017/2019/2021": "PDFs in data/raw/, transcription pending",
            "2013/2015": "not available in official archive",
        },
        "by_lage": {"2023": by_lage},
        "editions": editions_file["editions"],
        "note": "Old interpolated series removed — replaced with verified values only.",
    }
    for p in ("data/historical_mietspiegel.json",
              "docs/data/processed/berlin_historical.json"):
        (REPO / p).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print("wrote historical files; verified by_lage 2023:", by_lage)


if __name__ == "__main__":
    main()
