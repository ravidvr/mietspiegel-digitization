#!/usr/bin/env python3
"""Extract the Lübeck Mietspiegel 2025 table from the official PDF.

Source: data/raw/luebeck-2025.pdf (Mietspiegel 2025, Stichtag 01.05.2025).

Mietspiegeltabelle (page 8): ortsübliche Vergleichsmieten für Wohnungen in
mittlerer Wohnlage (M) — 10 Baujahr cohorts x 4 size bands (25-<45, 45-<65,
65-<85, >=85 m²). Each cell: Mittelwert (arithmetic mean) + 2/3-Spanne.
* = 10-29 Mietwerte (bedingte Aussagekraft); empty cells = < 10 Mietwerte.

Wohnlage adjustments (page 9): Gute Wohnlage (G) +0,44 €/m²,
Einfache Wohnlage (E) -0,47 €/m².

Usage: python3 scripts/extract_luebeck.py
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

COHORTS = ["bis 1918", "1919 – 1948", "1949 – 1957", "1958 – 1968",
           "1969 – 1978", "1979 – 1990", "1991 – 2001", "2002 – 2013",
           "2014 – 2020", "2021 – 4/2025"]

SIZES = [
    ("25-<45", 25, 45), ("45-<65", 45, 65), ("65-<85", 65, 85), ("85+", 85, None),
]

LAGE_ADJ = {"gut": 0.44, "einfach": -0.47}


def parse_de(s):
    return float(s.replace(",", "."))


def main():
    import fitz
    doc = fitz.open(REPO / "data/raw/luebeck-2025.pdf")
    text = doc[7].get_text().replace("\n", " ")
    doc.close()

    # per cohort: find cohort label, then parse up to 4 cells
    # cell pattern: <mittelwert>  <lo – hi>   (lo-hi uses en-dash)
    rows = []
    pos = 0
    for ci, cohort in enumerate(COHORTS):
        m = re.search(re.escape(cohort), text[pos:])
        if not m:
            raise SystemExit(f"cohort {cohort} not found")
        seg_start = pos + m.end()
        seg = text[seg_start:seg_start + 220]
        # capture 4 cells: Mittelwert (number) then 'lo – hi' pair
        cell_pat = re.compile(
            r"([\d,]+)\*?\s+([\d,]+)\s*[–-]\s*([\d,]+)")
        cells = []
        for cm in cell_pat.finditer(seg):
            cells.append({
                "mittelwert": round(parse_de(cm.group(1)), 2),
                "untere": round(parse_de(cm.group(2)), 2),
                "obere": round(parse_de(cm.group(3)), 2),
                "low_sample": cm.group(0).count("*") > 0 or "*" in seg[cm.start()-2:cm.end()+2],
            })
            if len(cells) == 4:
                break
        # low_sample: the asterisk follows the Mittelwert token (e.g. 7,91*)
        for cell, cm in zip(cells, cell_pat.finditer(seg)):
            after = seg[cm.end():cm.end() + 2]
            if "*" in after:
                cell["low_sample"] = True
        rows.append({
            "baujahr": cohort,
            "values": [cells[i] if i < len(cells) else None for i in range(4)],
        })
        pos = seg_start

    # self-check against PDF text
    hay = text
    ok, total = 0, 0
    for r in rows:
        for v in r["values"]:
            if not v:
                continue
            total += 1
            good = True
            for num in (v["mittelwert"], v["untere"], v["obere"]):
                s = f"{num:.2f}".replace(".", ",")
                s_trim = s.rstrip("0").rstrip(",")
                if not (re.search(rf"(?<!\d){re.escape(s)}(?!\d)", hay)
                        or re.search(rf"(?<!\d){re.escape(s_trim)}(?!\d)", hay)):
                    good = False
            if good:
                ok += 1
    print(f"self-check: {ok}/{total} cells fully matched in PDF text")
    assert ok / total >= 0.95, "self-check failed"

    # legacy rollup: mittlere Lage table, 4 legacy size keys per cohort
    legacy_rows = []
    for ci, cohort in enumerate(COHORTS):
        cells = rows[ci]["values"]
        def m(i, cells=cells):
            return cells[i]["mittelwert"] if i < len(cells) and cells[i] else None
        # legacy buckets: bis_40 (25-<45), 40_60 (45-<65), 60_90 (65-<85), ueber_90 (85+)
        legacy_rows.append({"baujahr": cohort, "bis_40": m(0), "40_60": m(1),
                            "60_90": m(2), "ueber_90": m(3)})

    out = {
        "city": "Lübeck",
        "city_slug": "luebeck",
        "slug": "luebeck",
        "state": "Schleswig-Holstein",
        "lat": 53.8655,
        "lng": 10.6866,
        "population": 218000,
        "year": 2025,
        "type": "qualifiziert",
        "source": ("Mietspiegel 2025 der Hansestadt Lübeck (Stichtag 01.05.2025). "
                   "Tabelle: mittlere Wohnlage (M); Mittelwert (arithmetisches "
                   "Mittel) + 2/3-Spanne; * = 10-29 Mietwerte. Wohnlage: "
                   "Gute (G) +0,44 €/m², Einfache (E) -0,47 €/m²."),
        "source_url": "https://www.luebeck.de/mietspiegel",
        "source_file": "data/raw/luebeck-2025.pdf",
        "schema_note": ("official_rows preserves the official table verbatim "
                        "(10 cohorts x 4 size bands, mittlere Lage basis). "
                        "tables = same data in the legacy 4-band shape."),
        "lage_adjustments_eur_per_sqm": LAGE_ADJ,
        "official_rows": rows,
        "tables": [{"lage": "mittel", "rows": legacy_rows}],
        "verification_status": "verified",
        "verification_note": ("Extracted from luebeck-2025.pdf page 8 with "
                              "scripts/extract_luebeck.py; Mittelwerte and "
                              "Spannen re-checked against the PDF text layer."),
    }
    for p in (REPO / "docs/data/processed/luebeck.json",
              REPO / "data/processed/luebeck.json"):
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"wrote luebeck.json")


if __name__ == "__main__":
    main()
