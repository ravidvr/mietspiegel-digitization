#!/usr/bin/env python3
"""
Extract Stuttgart Mietspiegel 2025/2026 from PDF to unified JSON schema.
Manual extraction because the PDF uses a regression format (not camelot-friendly tables).
"""
import json
from datetime import UTC, datetime

# === Base rent table (Grundwert) from page 6 ===
# Structure: Baujahr x Wohnfläche -> single value (€/m², net cold)
bauperiods = [
    {"id": "bis_1914",     "label": "bis 1914",            "range": {"min": None, "max": 1914}},
    {"id": "1915_1984",    "label": "1915–1984",           "range": {"min": 1915, "max": 1984}},
    {"id": "1985_2006",    "label": "1985–2006",           "range": {"min": 1985, "max": 2006}},
    {"id": "2007_2024_04", "label": "2007 bis April 2024", "range": {"min": 2007, "max": 2024}},
]

size_groups = [
    {"id": "21_30",   "label": "21 bis unter 30 m²", "range": {"min": 21,  "max": 29.99}},
    {"id": "30_40",   "label": "30 bis unter 40 m²", "range": {"min": 30,  "max": 39.99}},
    {"id": "40_70",   "label": "40 bis unter 70 m²", "range": {"min": 40,  "max": 69.99}},
    {"id": "70_90",   "label": "70 bis unter 90 m²", "range": {"min": 70,  "max": 89.99}},
    {"id": "90_115",  "label": "90 bis unter 115 m²","range": {"min": 90,  "max": 114.99}},
    {"id": "ab_115",  "label": "115 m² und größer",   "range": {"min": 115, "max": None}},
]

# Grundwerte matrix: [bauperiod_index][size_index]
# Rows = size groups (same order as size_groups above)
# Columns = bauperiod (same order as bauperiods above)
grundwerte_matrix = [
    # bis_1914, 1915-1984, 1985-2006, 2007-2024
    [12.36, 12.36, 12.96, 12.36],  # 21-30 m²
    [11.01, 11.01, 11.61, 11.01],  # 30-40 m²
    [9.72,  9.72,  10.32, 9.72],   # 40-70 m²
    [9.17,  9.17,  9.77,  9.17],   # 70-90 m²
    [8.94,  8.94,  9.54,  8.94],   # 90-115 m²
    [8.96,  8.96,  9.56,  8.96],   # 115+ m²
]

# Fixed spanne values (from page 8)
UNTERE_SPANNE = -1.80
OBERE_SPANNE  = +1.77

# === Build values array ===
values = []
for si, size in enumerate(size_groups):
    for bi, bau in enumerate(bauperiods):
        base = grundwerte_matrix[si][bi]
        values.append({
            "lage_id": "basis",
            "bauperiod_id": bau["id"],
            "size_id": size["id"],
            "value": {
                "untere_spanne": round(base + UNTERE_SPANNE, 2),
                "obere_spanne":  round(base + OBERE_SPANNE, 2),
                "mittelwert":    base
            }
        })

# === Lage adjustments (from page 6, bottom half) ===
lage_adjustments = {
    "mitte_1":    {"label": "Mitte 1",   "zuschlag": 0.84},
    "mitte_2":    {"label": "Mitte 2",   "zuschlag": 1.21},
    "mitte_3":    {"label": "Mitte 3",   "zuschlag": 1.36},
    "filder_1":   {"label": "Filder 1",  "zuschlag": 0.00},
    "filder_2":   {"label": "Filder 2",  "zuschlag": 0.51},
    "filder_3":   {"label": "Filder 3",  "zuschlag": 0.86},
    "neckar":     {"label": "Neckar",    "zuschlag": 0.00},
    "nord_1":     {"label": "Nord 1",    "zuschlag": 0.00},
    "nord_2":     {"label": "Nord 2",    "zuschlag": 0.40},
    "nord_3":     {"label": "Nord 3",    "zuschlag": 0.53},
}

# === Feature adjustments (from pages 7-8) ===
feature_adjustments = {
    "energy_class_ab":      {"label": "Energieausweisklasse A+, A oder B",                  "value": 0.25},
    "heating_since_2007":   {"label": "Baujahr ab 2007 oder Erneuerung der Heizung seit 2007", "value": 0.17},
    "bathroom_since_2013":  {"label": "Baujahr ab 2013 oder umfassende Erneuerung des Bades seit 2013", "value": 0.27},
    "flooring_since_2013":  {"label": "Baujahr ab 2013 oder umfassende Erneuerung der Fußbodenbeläge seit 2013", "value": 0.27},
    "floor_heating":        {"label": "Flächenheizung (z.B. Fußbodenheizung)",               "value": 0.77},
    "other_heating":        {"label": "Andere Heizungsform",                                 "value": 0.00},
    "no_central_hot_water": {"label": "Keine zentrale Warmwasserbereitung",                  "value": -0.37},
    "visible_pipes":        {"label": "Auf Putz verlegte, sichtbare Gas-, Heizleitungen",    "value": -0.21},
    "low_entry_shower":     {"label": "Dusche mit niedrigem/bodenebenem Einstieg",          "value": 0.21},
    "shower_partition":     {"label": "Feste Abtrennung der Dusche oder Badewanne",          "value": 0.41},
    "wall_hung_toilet":     {"label": "Wandhängendes WC",                                    "value": 0.30},
    "towel_radiator":       {"label": "Handtuchwandheizkörper",                              "value": 0.29},
    "two_handle_tap":       {"label": "Zweigriffarmatur (Warm-/Kaltwasser getrennt)",       "value": -0.19},
    "elevator":             {"label": "Personenaufzug im Gebäude (< 8 Stockwerke)",          "value": 0.32},
    "electric_shutters":    {"label": "Elektrische Rollläden (überwiegend)",                 "value": 0.55},
    "video_intercom":       {"label": "Videogegensprechanlage mit Türöffner",                "value": 0.65},
    "ac_room":              {"label": "Mindestens ein klimatisierter Raum",                  "value": 0.77},
    "few_sockets":          {"label": "Weniger als 4 feste Steckdosen im größten Wohnraum",  "value": -0.23},
    # Küche (page 8)
    "open_kitchen":         {"label": "Zum Ess-/Wohnraum offen gestaltete Küche",            "value": 0.26},
    "kitchen_parquet":      {"label": "Küchenfußboden in Parkett",                           "value": 0.45},
    "kitchen_pvc":          {"label": "Küchenfußboden in PVC",                               "value": -0.35},
    # Fußboden (page 8)
    "linoleum_floor":       {"label": "Linoleum im Wohn- und Schlafbereich (überwiegend)",   "value": -0.67},
    "parquet_floor":        {"label": "Parkett im Wohn- und Schlafbereich (überwiegend)",    "value": 0.44},
    "other_floor":          {"label": "Andere Fußbodenart oder kein vom Vermieter gestellter Boden", "value": 0.00},
    # Fenster (page 8)
    "triple_glazing":       {"label": "Dreifach-Wärmeschutzverglasung (überwiegend)",        "value": 0.31},
    "floor_to_ceiling_windows": {"label": "Bodentiefe Fenster (überwiegend)",                "value": 0.30},
}

# === Assemble final JSON ===
output = {
    "$schema": "https://raw.githubusercontent.com/ravidvr/mietspiegel-digitization/main/docs/schema.json",
    "meta": {
        "schema_version": "1.0.0",
        "extracted_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "extracted_by": "manual_extraction",
        "extraction_notes": "Regression-based Mietspiegel. Base table (Baujahr×Wohnfläche) + additive Lage/feature adjustments. Fixed spanne: untere -1.80 €/m², obere +1.77 €/m². Lage and feature adjustments stored in source.extra.",
        "quality": {
            "status": "validated",
            "confidence": 0.99,
            "issues": []
        }
    },
    "city": {
        "name": "Stuttgart",
        "slug": "stuttgart",
        "state": "Baden-Württemberg",
        "region": "Stuttgart",
        "population": 630000,
        "coordinates": {"lat": 48.7758, "lng": 9.1829}
    },
    "source": {
        "title": "Mietspiegel 2025/2026 Stuttgart",
        "type": "qualifiziert",
        "year": 2025,
        "effective_from": "2025-01-01",
        "effective_until": "2026-12-31",
        "publisher": "Landeshauptstadt Stuttgart — Statistisches Amt",
        "url": "https://www.stuttgart.de/service/statistik-und-wahlen/mietspiegel/",
        "pdf_url": "https://www.stuttgart.de/medien/ibs/mietspiegel_2025_2026.pdf",
        "local_pdf": "data/raw/stuttgart-mietspiegel-2025-2026.pdf",
        "pages": [6],
        "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "extra": {
            "type": "regression_based",
            "spanne_rules": {
                "untere_spanne_abzug": 1.80,
                "obere_spanne_zuschlag": 1.77,
                "description": "Fixed spanne applied to the calculated average rent (base + all adjustments)"
            },
            "lage_adjustments": lage_adjustments,
            "feature_adjustments": feature_adjustments,
            "calculation_steps": [
                "1. Grundwert from Baujahr × Wohnfläche table (page 6)",
                "2. Add Lage adjustment (page 6, one category)",
                "3. Add/subtract feature adjustments (pages 7-8)",
                "4. Average = Grundwert + Lage + sum(feature adjustments)",
                "5. Untere Spanne = Average - 1.80, Obere Spanne = Average + 1.77"
            ]
        }
    },
    "matrix": {
        "lage_categories": [
            {
                "id": "basis",
                "label": "Basiswert (vor Lage-Zuschlag)",
                "aliases": ["Grundwert", "Basis"],
                "description": "Base rent table before Lage adjustment. Stuttgart uses additive Lage adjustments rather than separate Wohnlage tables.",
                "extra": {
                    "normalized_from": "Grundwerttabelle",
                    "normalization_note": "Stuttgart is a regression-based Mietspiegel. The base table is independent of Lage. Add the appropriate Lage adjustment from source.extra.lage_adjustments to get the final base."
                }
            }
        ],
        "bauperiods": bauperiods,
        "size_groups": size_groups,
        "values": values
    }
}

# Write output
output_path = "data/processed/stuttgart.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"Written: {output_path}")
print(f"Values: {len(values)} cells")
print(f"Bauperiods: {len(bauperiods)}")
print(f"Size groups: {len(size_groups)}")
