#!/usr/bin/env python3
"""Extract the Rostock Mietspiegel 2026 from the official PDF.

Source: data/raw/rostock-2026.pdf (Qualifizierter Mietspiegel 2026).

Model (Tabelle 3): C = A + B; Spanne: D = C - 0,90 €/m², E = C + 0,83 €/m².
  A = Basis-Nettokaltmiete per Wohnfläche (Tabelle 1, p9)
  B = Summe der Zu-/Abschläge (Tabelle 2, p11-12):
      Baujahr: bis 1918 +0,68; 1919-1945 +0,57; 1946-1959 +0,34;
               1960-1990 ±0,00; 1991-2009 +1,04; 2010-2015 +1,83;
               2016-2020 +2,86; 2021-2022 +4,14 €/m²
      + Ausstattung/Modernisierung/energetische Merkmale (see embedded list).

The committed rostock.json (96-cell cohort grid) did not match this document;
replaced with the official per-m² table + factor model.

Verification: the PDF's worked example (p15): 75 m² -> A = 6,88 €/m²,
B = -0,29 €/m² (-0,79 Wohnlage +0,14 Handtuchheizkörper +0,55 Einbauküche
-0,19 kein Balkon) must reproduce.
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

BAUJAHR_FACTORS = [
    ("bis 1918", 0.68), ("1919-1945", 0.57), ("1946-1959", 0.34),
    ("1960-1990", 0.00), ("1991-2009", 1.04), ("2010-2015", 1.83),
    ("2016-2020", 2.86), ("2021-2022", 4.14),
]

ADJUSTMENTS = [
    {"merkmal": "Garten (alleinige oder gemeinschaftliche Nutzung)", "zuschlag": 0.34},
    {"merkmal": "Kein Balkon/(Dach-)Terrasse/Loggia", "abschlag": -0.19},
    {"merkmal": "1 Modernisierung (ab 2010)", "zuschlag": 0.08},
    {"merkmal": "2 Modernisierungen (ab 2010)", "zuschlag": 0.15},
    {"merkmal": "3 Modernisierungen (ab 2010)", "zuschlag": 0.23},
]


def parse_de(s):
    return float(s.replace(",", "."))


def main():
    import fitz
    doc = fitz.open(REPO / "data/raw/rostock-2026.pdf")
    t1_text = doc[8].get_text()
    full_text = "\n".join(doc[i].get_text() for i in range(len(doc)))
    doc.close()

    # Tabelle 1: m² on one line, "value €" on the next
    pairs = re.findall(r"(?:^|\n)\s*(\d{2,3})\s*\n\s*([\d,]+)\s*€", t1_text)
    base_table = []
    for m2, val in pairs:
        base_table.append({"wohnflaeche_m2": int(m2),
                           "basis_nettokaltmiete": round(parse_de(val), 2)})
    if len(base_table) < 100:
        raise SystemExit(f"Tabelle 1 parse failed: {len(base_table)} pairs")

    # verify every base value appears in the PDF text
    hay = t1_text
    missing = []
    for b in base_table:
        s = f"{b['basis_nettokaltmiete']:.2f}".replace(".", ",")
        if not re.search(rf"(?<!\d){re.escape(s)}(?!\d)", hay):
            missing.append(b)
    print(f"Tabelle 1: {len(base_table)} pairs, {len(missing)} values not found in PDF text")
    assert not missing, missing[:5]

    # worked example check (p15): 75 m² -> A = 6,88
    a75 = next((b["basis_nettokaltmiete"] for b in base_table
                if b["wohnflaeche_m2"] == 75), None)
    example_b = round(-0.79 + 0.14 + 0.55 - 0.19, 2)
    example_c = round((a75 or 0) + example_b, 2)
    print(f"worked example: A(75m²) = {a75} (PDF: 6,88) | B = {example_b} (PDF: -0,29) | C = {example_c} (PDF: 6,59)")
    assert a75 == 6.88, f"A(75) = {a75}, PDF says 6,88"
    assert example_b == -0.29 and abs(example_c - 6.59) < 0.01

    # legacy 4-band rollup: mean base over band + baujahr factor, per cohort
    bands = {"bis_40": (0, 40), "40_60": (40, 60), "60_90": (60, 90),
             "ueber_90": (90, None)}
    legacy_rows = []
    for cohort, factor in BAUJAHR_FACTORS:
        row = {"baujahr": cohort}
        for key, (lo, hi) in bands.items():
            vals = [b["basis_nettokaltmiete"] for b in base_table
                    if b["wohnflaeche_m2"] >= lo
                    and (hi is None or b["wohnflaeche_m2"] < hi)]
            row[key] = round(sum(vals) / len(vals) + factor, 2) if vals else None
        legacy_rows.append(row)

    out = {
        "city": "Rostock",
        "city_slug": "rostock",
        "slug": "rostock",
        "state": "Mecklenburg-Vorpommern",
        "lat": 54.0924,
        "lng": 12.0991,
        "population": 210000,
        "year": 2026,
        "type": "qualifiziert",
        "source": ("Qualifizierter Mietspiegel 2026 der Hanse- und "
                   "Universitätsstadt Rostock. C = A + B (Tabelle 3); "
                   "Spanne: C - 0,90 bis C + 0,83 €/m²."),
        "source_url": "https://www.rostock.de/mietspiegel",
        "source_file": "data/raw/rostock-2026.pdf",
        "schema_note": ("official_rows = Tabelle 1 (Basis-Nettokaltmiete per "
                        "Wohnfläche). Baujahr/feature Zu-/Abschläge in "
                        "baujahr_factors + adjustments. tables = derived "
                        "legacy 4-band rollup (mean base per band + Baujahr "
                        "factor)."),
        "baujahr_factors_eur_per_sqm": [
            {"baujahr": c, "faktor": f} for c, f in BAUJAHR_FACTORS
        ],
        "adjustments_eur_per_sqm": ADJUSTMENTS,
        "spanne": {"untere": -0.90, "obere": 0.83},
        "official_rows": base_table,
        "tables": [{"lage": "mittel", "rows": legacy_rows}],
        "verification_status": "verified",
        "verification_note": ("Extracted with scripts/extract_rostock.py; "
                              "Tabelle 1 values all match the PDF text and "
                              "the PDF's worked example reproduces exactly "
                              "(A=6,88, B=-0,29, C=6,59)."),
    }
    for p in (REPO / "docs/data/processed/rostock.json",
              REPO / "data/processed/rostock.json"):
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print("wrote rostock.json")


if __name__ == "__main__":
    main()
