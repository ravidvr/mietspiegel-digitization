#!/usr/bin/env python3
"""Re-extract Aachen Mietspiegel 2024 correctly.

The original extraction mislabeled Table 1 (base rent by FLOOR AREA) as
Baujahr rows. Aachen is formula-based:

  Vergleichsmiete = Basis-Nettomiete(floor area) × (1 + Baujahr% + Lage%)

Table 1: 63 base-rent pairs (floor area → €/m²)
Table 2 Kategorie 1 (Baujahr): bis1918 +10, 1919-1948 +8, 1949-1960 +8,
         1961-1976 0, 1977-1981 +4, 1982-1993 +6, 1994-2006 +10,
         2007-2015 +15, 2016-2023 +24
Table 2 Kategorie 4 (Lage): einfach -5, mittel 0, gut +6, sehr gut +10
"""
import json, os

BASE_RENT = [
    (15,16,12.85),(47,48,7.69),(79,80,7.28),(111,112,7.53),
    (17,18,11.90),(49,50,7.62),(81,82,7.29),(113,114,7.56),
    (19,20,11.14),(51,52,7.56),(83,84,7.29),(115,116,7.58),
    (21,22,10.54),(53,54,7.51),(85,86,7.30),(117,118,7.61),
    (23,24,10.05),(55,56,7.46),(87,88,7.31),(119,120,7.64),
    (25,26,9.64),(57,58,7.42),(89,90,7.32),(121,122,7.67),
    (27,28,9.30),(59,60,7.39),(91,92,7.34),(123,124,7.69),
    (29,30,9.01),(61,62,7.36),(93,94,7.35),(125,126,7.72),
    (31,32,8.77),(63,64,7.34),(95,96,7.37),(127,128,7.75),
    (33,34,8.56),(65,66,7.32),(97,98,7.38),(129,130,7.78),
    (35,36,8.37),(67,68,7.31),(99,100,7.40),(131,132,7.81),
    (37,38,8.22),(69,70,7.29),(101,102,7.42),(133,134,7.84),
    (39,40,8.08),(71,72,7.29),(103,104,7.44),(135,136,7.88),
    (41,42,7.96),(73,74,7.28),(105,106,7.46),(137,138,7.91),
    (43,44,7.86),(75,76,7.28),(107,108,7.49),(139,140,7.94),
    (45,46,7.77),(77,78,7.28),(109,110,7.51),
]

# Baujahr adjustment (percentage)
BAUJAHR_ADJ = [
    ("bis 1918", 10),
    ("1919-1948", 8),
    ("1949-1960", 8),
    ("1961-1976", 0),
    ("1977-1981", 4),
    ("1982-1993", 6),
    ("1994-2006", 10),
    ("2007-2015", 15),
    ("2016-2023", 24),
]

# Lage adjustment (percentage)
LAGE_ADJ = [
    ("einfach", -5),
    ("mittel", 0),
    ("gut", 6),
]

# Size classes -> floor-area bounds for averaging Table 1
SIZE_CLASSES = [
    ("bis_40", 15, 40),
    ("40_60", 41, 60),
    ("60_90", 61, 90),
    ("ueber_90", 91, 140),
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
                if base is None:
                    row[sk] = None
                else:
                    row[sk] = round(base * (1 + (bj_pct + lage_pct) / 100.0), 2)
            rows.append(row)
        tables.append({"lage": lage, "rows": rows})

    return {
        "city": "Aachen",
        "city_slug": "aachen",
        "slug": "aachen",
        "state": "Nordrhein-Westfalen",
        "lat": 50.7753, "lng": 6.0839,
        "population": 250000,
        "year": 2024,
        "type": "qualifiziert",
        "lage_categories": [l for l, _ in LAGE_ADJ],
        "baujahr_groups": [b for b, _ in BAUJAHR_ADJ],
        "size_categories": ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"],
        "source_url": "https://serviceportal.aachen.de/suche/-/vr-bis-detail/dienstleistung/3218/show",
        "tables": tables,
        "notes": "Formula: Basis-Nettomiete(floor area, Table 1) × (1 + Baujahr% + Lage%). Baujahr: bis1918+10 ... 2016-2023+24. Lage: einfach -5, mittel 0, gut +6. Source: Mietspiegel Aachen 2024 PDF."
    }


def main():
    data = build()
    paths = [
        "/Users/ruhvee/mietspiegel-digitization/data/processed/aachen.json",
        "/Users/ruhvee/mietspiegel-digitization/docs/data/processed/aachen.json",
    ]
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("wrote", p)

    # sanity print
    for t in data["tables"]:
        r0 = t["rows"][0]
        print(t["lage"], r0)


if __name__ == "__main__":
    main()
