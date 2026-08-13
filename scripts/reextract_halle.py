#!/usr/bin/env python3
"""Re-extract Halle (Saale) Mietspiegel 2026-2027 correctly.

Formula-based with PERCENTAGE adjustments:

  Vergleichsmiete = Basiswert(floor area) × (1 + (Baujahr% + Lage%)/100)

Table 1: base value by floor area (65 pairs, 20-150 m²)
Table 2 Kategorie 1 (Baujahr %):
  bis 1918 +5, 1919-1948 +6, 1949-1960 +10, 1961-1972 0,
  1973-1989 -7, 1990-2002 +11, 2003-2015 +25, 2016+ +50
Kategorie 4 (Wohnlage %): A +15, B +10, C +5, D 0
"""
import json, os

BASE_RENT = [
    (20,21,7.86),(22,23,7.53),(24,25,7.24),(26,27,7.03),(28,29,6.83),
    (30,31,6.67),(32,33,6.55),(34,35,6.43),(36,37,6.34),(38,39,6.26),
    (40,41,6.19),(42,43,6.14),(44,45,6.14),(46,47,6.05),(48,49,6.02),
    (50,51,5.99),(52,53,5.97),(54,55,5.96),(56,57,5.95),(58,59,5.95),
    (60,61,5.94),(62,63,5.94),(64,65,5.95),(66,67,5.95),(68,69,5.96),
    (70,71,5.97),(72,73,5.98),(74,75,6.00),(76,77,6.01),(78,79,6.03),
    (80,81,6.05),(82,83,6.08),(84,85,6.10),(86,87,6.12),(88,89,6.15),
    (90,91,6.17),(92,93,6.20),(94,95,6.22),(96,97,6.25),(98,99,6.28),
    (100,101,6.32),(102,103,6.35),(104,105,6.38),(106,107,6.41),(108,109,6.44),
    (110,111,6.47),(112,113,6.50),(114,115,6.53),(116,117,6.58),(118,119,6.61),
    (120,121,6.64),(122,123,6.68),(124,125,6.71),(126,127,6.75),(128,129,6.79),
    (130,131,6.83),(132,133,6.86),(134,135,6.90),(136,137,6.94),(138,139,6.97),
    (140,141,7.02),(142,143,7.06),(144,145,7.09),(146,147,7.13),(148,150,7.18),
]

BAUJAHR_ADJ = [
    ("bis 1918", 5),
    ("1919-1948", 6),
    ("1949-1960", 10),
    ("1961-1972", 0),
    ("1973-1989", -7),
    ("1990-2002", 11),
    ("2003-2015", 25),
    ("2016 und später", 50),
]

LAGE_ADJ = [
    ("einfach", 0),    # Wohnlage D
    ("mittel", 5),     # Wohnlage C
    ("gut", 10),       # Wohnlage B (A=+15 mapped to gut as upper bound)
]

SIZE_CLASSES = [
    ("bis_40", 20, 40),
    ("40_60", 41, 60),
    ("60_90", 61, 90),
    ("ueber_90", 91, 150),
]


def size_base_rents():
    out = {}
    for key, lo, hi in SIZE_CLASSES:
        vals = [v for (a, b, v) in BASE_RENT if a >= lo and b <= hi]
        out[key] = round(sum(vals) / len(vals), 2) if vals else None
    return out


def build():
    sbr = size_base_rents()
    tables = []
    for lage, lage_pct in LAGE_ADJ:
        rows = []
        for bj, bj_pct in BAUJAHR_ADJ:
            row = {"baujahr": bj}
            for sk, _, _ in SIZE_CLASSES:
                base = sbr.get(sk)
                row[sk] = round(base * (1 + (bj_pct + lage_pct) / 100.0), 2) if base is not None else None
            rows.append(row)
        tables.append({"lage": lage, "rows": rows})

    return {
        "city": "Halle (Saale)",
        "city_slug": "halle",
        "slug": "halle",
        "state": "Sachsen-Anhalt",
        "lat": 51.4828, "lng": 11.9700,
        "population": 240000,
        "year": 2026,
        "type": "qualifiziert",
        "lage_categories": [l for l, _ in LAGE_ADJ],
        "baujahr_groups": [b for b, _ in BAUJAHR_ADJ],
        "size_categories": ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"],
        "source_url": "https://halle.de/leben-in-halle/bauen-und-wohnen/mietspiegel",
        "tables": tables,
        "notes": "Formula: Basiswert(floor area) × (1 + (Baujahr% + Lage%)/100). Baujahr: bis1918+5 ... 2016++50. Wohnlage A-D mapped to gut=+10(B)/mittel=+5(C)/einfach=0(D). Source: Mietspiegel Halle (Saale) 2026-2027 PDF."
    }


def main():
    data = build()
    for p in ["/Users/ruhvee/mietspiegel-digitization/data/processed/halle.json",
              "/Users/ruhvee/mietspiegel-digitization/docs/data/processed/halle.json"]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("wrote", p)
    for t in data["tables"]:
        print(t["lage"], t["rows"][0])


if __name__ == "__main__":
    main()
