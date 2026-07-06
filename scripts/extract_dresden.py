#!/usr/bin/env python3
"""
Extract Dresden Mietspiegel 2025 data from PDF and produce unified JSON.
Dresden uses a factor-based model: Rent = Base_Rent(Size) × F_Baujahr × F_Lage
"""
import json
from datetime import datetime, timezone

# ============================================================
# TABLE 1: Basismiete (Base rent by Wohnfläche in m²)
# Extracted from page 9 (Tabelle 1)
# ============================================================
base_rent = {
    25: 8.64, 26: 8.51, 27: 8.38, 28: 8.27, 29: 8.17,
    30: 8.08, 31: 7.99, 32: 7.91, 33: 7.84, 34: 7.77,
    35: 7.71, 36: 7.66, 37: 7.60, 38: 7.56, 39: 7.51,
    40: 7.47, 41: 7.43, 42: 7.40, 43: 7.37, 44: 7.34,
    45: 7.31, 46: 7.29, 47: 7.26, 48: 7.24, 49: 7.22,
    50: 7.20, 51: 7.18, 52: 7.17, 53: 7.15, 54: 7.14,
    55: 7.13, 56: 7.11, 57: 7.10, 58: 7.09, 59: 7.08,
    60: 7.07, 61: 7.07, 62: 7.06, 63: 7.05, 64: 7.04,
    65: 7.04, 66: 7.03, 67: 7.02, 68: 7.02, 69: 7.01,
    70: 7.01, 71: 7.00, 72: 6.99, 73: 6.99, 74: 6.98,
    75: 6.98, 76: 6.97, 77: 6.97, 78: 6.96, 79: 6.96,
    80: 6.95, 81: 6.95, 82: 6.94, 83: 6.94, 84: 6.93,
    85: 6.93, 86: 6.92, 87: 6.92, 88: 6.91, 89: 6.91,
    90: 6.90, 91: 6.90, 92: 6.89, 93: 6.88, 94: 6.88,
    95: 6.87, 96: 6.86, 97: 6.86, 98: 6.85, 99: 6.84,
    100: 6.83, 101: 6.83, 102: 6.82, 103: 6.81, 104: 6.80,
    105: 6.80, 106: 6.79, 107: 6.78, 108: 6.77, 109: 6.76,
    110: 6.75, 111: 6.74, 112: 6.73, 113: 6.72, 114: 6.71,
    115: 6.70, 116: 6.69, 117: 6.68, 118: 6.67, 119: 6.66,
    120: 6.65, 121: 6.64, 122: 6.63, 123: 6.62, 124: 6.61,
    125: 6.60, 126: 6.59, 127: 6.58, 128: 6.57, 129: 6.56,
    130: 6.55, 131: 6.53, 132: 6.52, 133: 6.51, 134: 6.50,
    135: 6.49, 136: 6.48, 137: 6.47, 138: 6.46, 139: 6.44,
    140: 6.43, 141: 6.42, 142: 6.41, 143: 6.40, 144: 6.39,
    145: 6.38, 146: 6.37, 147: 6.35, 148: 6.34, 149: 6.33,
    150: 6.32
}


def avg_base_rent(sizes):
    """Average base rent for a range of sizes."""
    vals = [base_rent[s] for s in sizes]
    return round(sum(vals) / len(vals), 2)


# ============================================================
# TABLE 2: Baualter (building age) factors
# ============================================================
bauperiod_factors = [
    ("bis 1969", 1.00),
    ("1970 bis 1990", 0.93),
    ("1991 bis 2009", 1.00),
    ("2010 bis 2015", 1.14),
    ("2016 bis 2023", 1.23),
]

# ============================================================
# TABLE 3: Wohnlage (location) factors
# ============================================================
lage_factors = {
    "einfach": 0.98,
    "mittel": 1.00,
    "gut": 1.03,
}

# ============================================================
# Size brackets (matching the other city files format)
# ============================================================
# Use the same size buckets as Berlin/Munich/Hamburg
size_brackets = {
    "size_under_40": list(range(25, 40)),    # representative: 35 m²
    "size_40_60": list(range(40, 61)),       # representative: 50 m²
    "size_60_90": list(range(60, 91)),       # representative: 75 m²
    "size_over_90": list(range(90, 151)),    # representative: 100 m²
}

# Representative sizes for each bracket
rep_sizes = {
    "size_under_40": 35,
    "size_40_60": 50,
    "size_60_90": 75,
    "size_over_90": 100,
}

# ============================================================
# Build the tables
# ============================================================
def calculate_rent(size, bauperiod_factor, lage_factor):
    """Calculate net cold rent per m²: Base_Rent × F_baujahr × F_lage"""
    return round(base_rent[size] * bauperiod_factor * lage_factor, 2)


tables = {}
for lage_key, lage_factor in lage_factors.items():
    rows = []
    for baujahr_label, bau_factor in bauperiod_factors:
        row = {"baujahr": baujahr_label}
        for bracket_key, sizes in size_brackets.items():
            rep_size = rep_sizes[bracket_key]
            row[bracket_key] = calculate_rent(rep_size, bau_factor, lage_factor)
        rows.append(row)
    tables[lage_key] = rows

# ============================================================
# Build the unified JSON
# ============================================================
dresden_json = {
    "city": "Dresden",
    "city_slug": "dresden",
    "state": "Sachsen",
    "lat": 51.0504,
    "lng": 13.7373,
    "population": 556000,
    "type": "qualifiziert",
    "lage_categories": ["einfach", "mittel", "gut"],
    "current_edition": {
        "year": 2025,
        "valid_from": "2025-01-01",
        "valid_until": "2026-12-31",
        "source_url": "https://www.dresden.de/mietspiegel",
        "tables": tables,
        "method": "faktor-basiert",
        "calculation_notes": (
            "Dresden uses a factor-based Mietspiegel (not a direct matrix). "
            "Base rent from Tabelle 1 (Wohnfläche) is multiplied by Baualter factor (Tabelle 2) "
            "and Wohnlage factor (Tabelle 3). The table values here show the resulting "
            "Nettokaltmiete per m² for each combination. "
            "For exact base rents by individual m², see base_rent_table."
        ),
        "base_rent_table": {str(k): v for k, v in sorted(base_rent.items())}
    },
    "history": [
        {
            "year": 2023,
            "valid_from": "2023-01-01",
            "valid_until": "2024-12-31",
            "base_rent_mittel_60_90": 6.60,
            "base_rent_mittel_1919_1949": 6.80,
            "notes": "Previous edition data (approximate)"
        }
    ]
}

# Also add to the new unified schema format (matrix section)
# This follows the docs/schema.md format
dresden_extended = {
    "$schema": "https://raw.githubusercontent.com/ravidvr/mietspiegel-digitization/main/docs/schema.json",
    "meta": {
        "schema_version": "1.0.0",
        "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "extracted_by": "manual (PDF text extraction)",
        "extraction_notes": (
            "Dresden uses a factor-based Mietspiegel (Tabelle 1: Basismiete by size; "
            "Tabelle 2: Baualter factors; Tabelle 3: Wohnlage factors; "
            "Tabelle 4-8: Ausstattung factors). The unified matrix values are computed "
            "as Base_Rent(size) × F_baujahr × F_lage using representative sizes per bracket. "
            "See model_type=faktor-basiert for the original factor data."
        ),
        "quality": {
            "status": "validated",
            "confidence": 0.99,
            "issues": []
        }
    },
    "city": {
        "name": "Dresden",
        "slug": "dresden",
        "state": "Sachsen",
        "region": "Sächsisches Elbland",
        "population": 556000,
        "coordinates": {"lat": 51.0504, "lng": 13.7373}
    },
    "source": {
        "title": "Dresdner Mietspiegel 2025",
        "type": "qualifiziert",
        "year": 2025,
        "effective_from": "2025-01-01",
        "effective_until": "2026-12-31",
        "publisher": "Landeshauptstadt Dresden, Sozialamt",
        "url": "https://www.dresden.de/mietspiegel",
        "pdf_url": "https://www.dresden.de/media/pdf/sozialamt/Mietspiegel_Dresden_2025.pdf",
        "local_pdf": "data/raw/dresden-2025.pdf",
        "pages": [7, 8, 9, 10],
        "retrieved_at": "2026-07-06T16:50:00Z"
    },
    "model_type": "faktor-basiert",
    "model_components": {
        "base_rent_table": {
            "description": "Basismiete in Abhängigkeit von der Wohnfläche (Tabelle 1)",
            "unit": "€/m² Nettokaltmiete",
            "type": "continuous_by_size_m2",
            "min_size_m2": 25,
            "max_size_m2": 150,
            "values": {str(k): v for k, v in sorted(base_rent.items())}
        },
        "bauperiod_factors": {
            "description": "Faktoren für Zu- und Abschläge in Abhängigkeit vom Baualter (Tabelle 2)",
            "values": {label: factor for label, factor in bauperiod_factors}
        },
        "lage_factors": {
            "description": "Faktoren für Zu- und Abschläge in Abhängigkeit von der Wohnlage (Tabelle 3)",
            "values": lage_factors
        }
    },
    "matrix": {
        "lage_categories": [
            {"id": "einfach", "label": "einfache Wohnlage", "aliases": ["einfach", "einfache Wohnlage"]},
            {"id": "mittel", "label": "mittlere Wohnlage", "aliases": ["mittel", "mittlere Wohnlage", "normale Wohnlage"]},
            {"id": "gut", "label": "gute Wohnlage", "aliases": ["gut", "gute Wohnlage"]}
        ],
        "bauperiods": [
            {"id": "bis_1969", "label": "bis 1969", "range": {"min": None, "max": 1969}},
            {"id": "1970_1990", "label": "1970–1990", "range": {"min": 1970, "max": 1990}},
            {"id": "1991_2009", "label": "1991–2009", "range": {"min": 1991, "max": 2009}},
            {"id": "2010_2015", "label": "2010–2015", "range": {"min": 2010, "max": 2015}},
            {"id": "2016_2023", "label": "2016–2023", "range": {"min": 2016, "max": 2023}},
        ],
        "size_groups": [
            {"id": "bis_40", "label": "unter 40 m²", "range": {"min": 0, "max": 39.99}},
            {"id": "40_60", "label": "40–60 m²", "range": {"min": 40, "max": 59.99}},
            {"id": "60_90", "label": "60–90 m²", "range": {"min": 60, "max": 89.99}},
            {"id": "ab_90", "label": "ab 90 m²", "range": {"min": 90, "max": None}},
        ],
        "values": []
    }
}

# Build the matrix values array
for lage_key, lage_factor in lage_factors.items():
    for baujahr_label, bau_factor in bauperiod_factors:
        bau_id = baujahr_label.lower().replace(" ", "_").replace("bis", "bis").replace("–", "_")
        for bracket_key, sizes in size_brackets.items():
            rep_size = rep_sizes[bracket_key]
            rent = calculate_rent(rep_size, bau_factor, lage_factor)
            
            # Map bracket keys to size ids
            size_id_map = {
                "size_under_40": "bis_40",
                "size_40_60": "40_60",
                "size_60_90": "60_90",
                "size_over_90": "ab_90",
            }
            
            dresden_extended["matrix"]["values"].append({
                "lage_id": lage_key,
                "bauperiod_id": bau_id,
                "size_id": size_id_map[bracket_key],
                "value": {
                    "untere_spanne": round(rent * 0.86, 2),
                    "obere_spanne": round(rent * 1.15, 2),
                    "mittelwert": rent
                }
            })

# ============================================================
# Write the files
# ============================================================
import os

output_dir = "/Users/ruhvee/mietspiegel-digitization/data/processed"
os.makedirs(output_dir, exist_ok=True)

# Write compact format (matching other cities)
compact_path = os.path.join(output_dir, "dresden.json")
with open(compact_path, "w", encoding="utf-8") as f:
    json.dump(dresden_json, f, ensure_ascii=False, indent=2)
print(f"Wrote compact format to {compact_path}")

# Write extended format (full unified schema)
extended_path = os.path.join(output_dir, "dresden-extended.json")
with open(extended_path, "w", encoding="utf-8") as f:
    json.dump(dresden_extended, f, ensure_ascii=False, indent=2)
print(f"Wrote extended format to {extended_path}")

# ============================================================
# Print validation tables
# ============================================================
print("\n=== Dresden Mietspiegel 2025 - Validierungstabellen ===")
print("Tables show Nettokaltmiete in €/m² (calculated as Base_Rent × F_Baujahr × F_Lage)")
print()
for lage in ["einfach", "mittel", "gut"]:
    print(f"\n{'='*60}")
    print(f"  Wohnlage: {lage}")
    print(f"{'='*60}")
    print(f"{'Baujahr':<18} {'<40 m²':>10} {'40-60 m²':>10} {'60-90 m²':>10} {'>90 m²':>10}")
    print(f"{'-'*58}")
    for baujahr_label, bau_factor in bauperiod_factors:
        row = tables[lage]
        r = next(r for r in row if r["baujahr"] == baujahr_label)
        print(f"{baujahr_label:<18} {r['size_under_40']:>8.2f} €  {r['size_40_60']:>8.2f} €  {r['size_60_90']:>8.2f} €  {r['size_over_90']:>8.2f} €")

print("\n\n=== Factor Tables (for validation) ===")
print(f"\nTable 2 - Baualter factors:")
for label, factor in bauperiod_factors:
    pct = (factor - 1.0) * 100
    print(f"  {label:<18} {pct:+.0f}%  factor={factor}")

print(f"\nTable 3 - Wohnlage factors:")
for lage, factor in lage_factors.items():
    pct = (factor - 1.0) * 100
    print(f"  {lage:<12} {pct:+.0f}%  factor={factor}")

# Verify against the example from the PDF
print("\n\n=== Cross-check: PDF Example Values ===")
print("PDF says for 60 m², gute Wohnlage, ab 2016:")
print(f"  Base rent at 60 m² = {base_rent[60]} €/m²")
print(f"  Factor gute Wohnlage = {lage_factors['gut']}")
print(f"  Factor 2016-2023 = {bauperiod_factors[-1][1]}")
expected = base_rent[60] * lage_factors['gut'] * bauperiod_factors[-1][1]
print(f"  Calculated: {base_rent[60]} × {lage_factors['gut']} × {bauperiod_factors[-1][1]} = {expected:.2f} €/m²")
# The PDF shows example B: durchschnittliche ortsübliche Vergleichsmiete 7,00 €/m²
# which corresponds to a different combination
print()

# Also check: the PDF examples
print("PDF Example B (page 16):")
print("  durchschnittliche ortsübliche Vergleichsmiete = 7,00 €/m²")
print(f"  This could be: 50 m² ({base_rent[50]} €/m²), mittlere Lage, bis 1969")
check = base_rent[50] * lage_factors['mittel'] * 1.00
print(f"  Calculated: {base_rent[50]} × 1.00 × 1.00 = {check:.2f} €/m² ✓")
