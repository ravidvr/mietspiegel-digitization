# Validation Framework — Methodology

## Overview

The validation framework (`/validate/`) provides automated quality assurance for extracted Mietspiegel data. It runs two categories of checks:

1. **Sanity Checks** — Internal consistency of each city's data
2. **GdW Cross-Reference** — Comparison against external benchmarks from the GdW (German Housing Association)

---

## 1. Sanity Checks

### 1.1 Baujahr Monotonicity

**Principle:** Rents should increase with newer construction periods. A newer building offers better insulation, modern amenities, and higher energy efficiency — reflected in higher net cold rent per sqm.

**Check:** For each Lage category (einfach/mittel/gut) and size class, verify that rent values do not decrease as Baujahr periods progress chronologically.

**Threshold:** A decrease of more than 5% (configurable via `--tolerance`) is flagged as an error. Decreases of >10% are flagged at higher severity.

**Typical violations:**
- A 1950-era apartment costs more than a 2020 apartment in the same Lage → extraction error
- Missing values cause a row to appear empty → flagged during extraction validation

### 1.2 Lage Monotonicity

**Principle:** Rents increase as Wohnlage (location quality) improves:
- **Einfach (simple)** → **Mittel (medium)** → **Gut (good)**

**Check:** For each Baujahr period and size class, verify that rent values increase monotonically across Lage categories.

**Threshold:** Same as above (5% tolerance, configurable).

**Note:** Some cities use 2-tier or 4-tier systems. The normalizer maps these to the 3-tier standard where possible. Cities with non-standard lage systems may produce warnings rather than errors.

### 1.3 Positive Values

**Check:** All numeric rent values must be positive (>0).

**Violations:** Negative or zero values indicate corrupt extraction (e.g., malformed PDF table parsing, missing data).

### 1.4 Field Completeness

**Check:** Every row in every table must have at least one non-null numeric value.

**Violations:** An empty row means the Baujahr period was parsed but no rent values were extracted — likely a table parsing failure.

### 1.5 Size-Conditional Checks (Informational)

**Principle:** Larger apartments typically have a slightly lower per-sqm cost (economy of scale in utilities and maintenance).

**Check:** For each Lage and Baujahr period, verify that larger size classes don't cost significantly *more* per sqm than smaller ones.

**Severity:** Informational only — some markets deviate from this pattern.

---

## 2. GdW Cross-Reference

### 2.1 Source Data

The GdW (Gesamtverband der Wohnungswirtschaft) publishes annual statistics on the German housing market. Key reference points:

| Level | Value | Notes |
|-------|-------|-------|
| National average | €6.63/m² | Across all GdW member stock |
| By state | Varies | See `data/reference/gdw_aggregate.json` |
| By population tier | Varies | Major cities significantly higher |

**Important:** GdW data represents the social/cooperative housing stock, not the entire private market. City Mietspiegel values for major cities (Munich, Frankfurt, Stuttgart, Hamburg) are typically *above* GdW averages. The reference is a **benchmark for spotting extreme outliers**, not a hard correctness test.

### 2.2 Checks Performed

#### 2.2.1 City vs GdW State Average

**Flag threshold:** City average >50% above or >30% below GdW state average.

- **Above threshold:** The city may genuinely be expensive (Munich, Frankfurt), or data may contain high-end values that skew the average. Manual review recommended.
- **Below threshold:** Possibly incomplete data (only einfache Lage extracted), or a genuinely cheap city. Manual review recommended.

#### 2.2.2 City vs GdW State Range

- **Above state range high:** City average outside the documented range for that state. Most common for major cities where Mietspiegel values are higher than cooperative housing stock.
- **Below state range low:** Unusually low — likely incomplete extraction.

#### 2.2.3 Absolute Plausibility

- **>€25/sqm:** Likely mis-extracted (wrong units, currency, or column mapping).
- **<€2/sqm:** Likely incomplete or zero-filled.

### 2.3 Customizing Thresholds

Thresholds are in `data/reference/gdw_aggregate.json` under `sanitiy_check_thresholds`:

```json
{
  "pct_above_gdw_state_avg_max": 50.0,
  "pct_below_gdw_state_avg_min": -30.0,
  "max_rent_per_sqm_plausible": 25.0,
  "min_rent_per_sqm_plausible": 2.0
}
```

Modify these if tuning for specific market conditions.

---

## 3. Usage

### Validate all cities:

```bash
cd /path/to/mietspiegel-digitization
python3 -m validate.run_validations
```

### Validate a single city:

```bash
python3 -m validate.run_validations --city berlin
```

### Adjust tolerance for monotonicity checks (e.g., 10%):

```bash
python3 -m validate.run_validations --tolerance 0.10
```

### JSON output for programmatic consumption:

```bash
python3 -m validate.run_validations --json
```

### Save report to file:

```bash
python3 -m validate.run_validations --output validation_report.txt
python3 -m validate.run_validations --json --output validation_report.json
```

---

## 4. Output Format

### Text output (default):

```
══════════════════════════════════════════════════════════════════════
MIETSPIEGEL VALIDATION REPORT
  Run: 2026-07-06T14:50:59.200435Z
  Cities validated: 2
══════════════════════════════════════════════════════════════════════

✗ Fehlerburg (2024) — FAILED
   Tables: 3 lage categories, 27 total rows
   Average rent: €8.56/sqm
   vs GdW state avg: €6.95/sqm (+23.2%)
   vs GdW national avg: €6.63/sqm (+29.2%)
   Sanity checks: 8 errors, 0 warnings
      ✗ [gut] Rent decreases from 1919-1949 (€11.00) to 1950-1964 (€6.60)...

──────────────────────────────────────────────────────────────────────
OVERALL: 0 passed, 0 warnings, 2 failed
  10 total flags, 0 total warnings
══════════════════════════════════════════════════════════════════════
```

### JSON output:

```json
{
  "city": "Fehlerburg",
  "overall_status": "failed",
  "sanity_checks": { "errors": 8, "violations": [...] },
  "gdw_crossref": { "flags": [...], "warnings": [...] }
}
```

---

## 5. Extending

To add new validation checks:

1. Add the check function to `sanity_checks.py`
2. Call it from `run_all_sanity_checks()` in the same file
3. It will automatically be included in all validation runs

Validation results are surfaced in both the text report and the JSON output.
