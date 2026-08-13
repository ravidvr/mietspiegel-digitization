#!/usr/bin/env python3
"""Re-extract Braunschweig Mietspiegel 2025 correctly.

Formula-based (like Aachen) but with ABSOLUTE € adjustments:

  Vergleichsmiete = Basis-Nettomiete(floor area) + Baujahr€ + Lage€

Table 1: base rent by floor area (151 pairs, 20-170 m²)
Table 2 Kategorie 1 (Baujahr, absolute €):
  vor 1919 +0.20, 1919-1983 ±0, 1984-1994 +0.47, 1995-2001 +0.53,
  2002-2009 +1.28, 2010-2015 +1.48, 2016-2024 +1.84
Kategorie 5 (Lage): street-specific continuous € (Straßenverzeichnis).
  Distribution: median -0.13, q1 -0.25, q3 +0.07. We use representative
  bands: einfach = -0.25, mittel = -0.13, gut = +0.07.
"""
import json, os

# Table 1 base rent by floor area (m² -> €/m²), full 151-pair list
BASE_RENT = [
    (20,10.83),(21,10.43),(22,10.07),(23,9.75),(24,9.46),(25,9.20),(26,8.97),
    (27,8.75),(28,8.56),(29,8.38),(30,8.22),(31,8.08),(32,7.94),(33,7.82),
    (34,7.71),(35,7.61),(36,7.51),(37,7.43),(38,7.35),(39,7.27),
    (40,7.20),(41,7.13),(42,7.07),(43,7.01),(44,6.95),(45,6.90),(46,6.85),
    (47,6.80),(48,6.76),(49,6.72),(50,6.68),(51,6.66),(52,6.64),(53,6.63),
    (54,6.62),(55,6.62),(56,6.62),(57,6.62),(58,6.62),(59,6.63),(60,6.62),
    (61,6.61),(62,6.61),(63,6.60),(64,6.60),(65,6.59),(66,6.59),(67,6.58),
    (68,6.58),(69,6.58),(70,6.58),(71,6.58),(72,6.57),(73,6.57),(74,6.57),
    (75,6.57),(76,6.57),(77,6.58),(78,6.58),(79,6.58),(80,6.58),(81,6.58),
    (82,6.58),(83,6.58),(84,6.58),(85,6.58),(86,6.58),(87,6.58),(88,6.58),
    (89,6.58),(90,6.58),(91,6.58),(92,6.58),(93,6.58),(94,6.58),(95,6.58),
    (96,6.58),(97,6.58),(98,6.58),(99,6.57),(100,6.57),(101,6.57),(102,6.57),
    (103,6.56),(104,6.56),(105,6.55),(106,6.55),(107,6.55),(108,6.54),
    (109,6.53),(110,6.53),(111,6.52),(112,6.51),(113,6.51),(114,6.50),
    (115,6.49),(116,6.48),(117,6.47),(118,6.46),(119,6.45),(120,6.44),
    (121,6.43),(122,6.42),(123,6.41),(124,6.40),(125,6.39),(126,6.38),
    (127,6.37),(128,6.36),(129,6.35),(130,6.34),(131,6.33),(132,6.32),
    (133,6.31),(134,6.30),(135,6.29),(136,6.28),(137,6.27),(138,6.15),
    (139,6.13),(140,6.11),(141,6.09),(142,6.07),(143,6.04),(144,6.02),
    (145,5.99),(146,5.97),(147,5.94),(148,5.92),(149,5.89),(150,5.86),
    (151,5.83),(152,5.80),(153,5.77),(154,5.74),(155,5.71),(156,5.68),
    (157,5.65),(158,5.62),(159,5.59),(160,5.56),(161,5.53),(162,5.50),
    (163,5.47),(164,5.44),(165,5.41),(166,5.38),(167,5.35),(168,5.32),
    (169,5.29),(170,5.26),
]

# Baujahr absolute € adjustments
BAUJAHR_ADJ = [
    ("vor 1919", 0.20),
    ("1919-1983", 0.00),
    ("1984-1994", 0.47),
    ("1995-2001", 0.53),
    ("2002-2009", 1.28),
    ("2010-2015", 1.48),
    ("2016-2024", 1.84),
]

# Lage representative bands (from street directory distribution)
LAGE_BANDS = [
    ("einfach", -0.25),
    ("mittel", -0.13),
    ("gut", 0.07),
]

SIZE_CLASSES = [
    ("bis_40", 20, 40),
    ("40_60", 41, 60),
    ("60_90", 61, 90),
    ("ueber_90", 91, 170),
]


def size_base_rents():
    out = {}
    for key, lo, hi in SIZE_CLASSES:
        vals = [v for (a, v) in BASE_RENT if lo <= a <= hi]
        out[key] = round(sum(vals) / len(vals), 2) if vals else None
    return out


def build():
    sbr = size_base_rents()
    tables = []
    for lage, lage_eur in LAGE_BANDS:
        rows = []
        for bj, bj_eur in BAUJAHR_ADJ:
            row = {"baujahr": bj}
            for sk, _, _ in SIZE_CLASSES:
                base = sbr.get(sk)
                row[sk] = round(base + bj_eur + lage_eur, 2) if base is not None else None
            rows.append(row)
        tables.append({"lage": lage, "rows": rows})

    return {
        "city": "Braunschweig",
        "city_slug": "braunschweig",
        "slug": "braunschweig",
        "state": "Niedersachsen",
        "lat": 52.2689, "lng": 10.5268,
        "population": 250000,
        "year": 2025,
        "type": "qualifiziert",
        "lage_categories": [l for l, _ in LAGE_BANDS],
        "baujahr_groups": [b for b, _ in BAUJAHR_ADJ],
        "size_categories": ["bis 40 m²", "40-60 m²", "60-90 m²", "über 90 m²"],
        "source_url": "https://www.braunschweig.de/politik_verwaltung/politik/stadtrecht/2_07_Mietspiegel_Braunschweig_2025.pdf",
        "tables": tables,
        "notes": "Formula: Basis-Nettomiete(floor area) + Baujahr€ (absolute) + Lage€. Lage is street-specific continuous; bands einfache=-0.25/mittel=-0.13/gut=+0.07 represent distribution quartiles. Source: Mietspiegel Braunschweig 2025 PDF."
    }


def main():
    data = build()
    for p in ["/Users/ruhvee/mietspiegel-digitization/data/processed/braunschweig.json",
              "/Users/ruhvee/mietspiegel-digitization/docs/data/processed/braunschweig.json"]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("wrote", p)
    for t in data["tables"]:
        print(t["lage"], t["rows"][0])


if __name__ == "__main__":
    main()
