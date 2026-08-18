"""
Berlin Mietpreisbremse — Interrupted Time Series & DiD Analysis
================================================================
The Mietpreisbremse (rent brake) was introduced June 1, 2015.
It caps new-lease rents at 10% above the local Mietspiegel.
This analysis examines whether the law changed Berlin's rent trajectory.

Data: 6 official Berlin Mietspiegel editions (2013–2023)
Method: Interrupted Time Series (ITS) with pre/post trend comparison
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

ROOT = Path("/Users/ruhvee/mietspiegel-digitization")

# ── Load historical data ──────────────────────────────────
with open(ROOT / "data/historical_mietspiegel.json") as f:
    hist = json.load(f)

berlin_editions = None
for c in hist["cities"]:
    if c["city"] == "Berlin":
        berlin_editions = c["editions"]
        break

if not berlin_editions:
    raise ValueError("Berlin editions not found")

# Sort by year
berlin_editions.sort(key=lambda e: e["year"])

# ── Load Berlin district comparison data ──────────────────
with open(ROOT / "docs/data/processed/berlin_districts_comparison.json") as f:
    districts_data = json.load(f)

# ── Load Berlin Mietspiegel 2024 for current rent table ───
with open(ROOT / "docs/data/processed/berlin.json") as f:
    berlin_current = json.load(f)

# ═══════════════════════════════════════════════════════════
# 1. INTERRUPTED TIME SERIES ANALYSIS
# ═══════════════════════════════════════════════════════════
print("=" * 70)
print("BERLIN MIETPREISBREMSE — INTERRUPTED TIME SERIES ANALYSIS")
print("=" * 70)
print(f"\nIntervention: June 1, 2015 (Mietpreisbremse enacted)")
print(f"Data: {len(berlin_editions)} official Mietspiegel editions (2013–2023)")
print(f"Metric: Base rent per m² (€/m² net cold, mittlere Wohnlage)\n")

# Pre-period: 2013, 2015 (editions before/during law introduction)
# Post-period: 2017, 2019, 2021, 2023

pre_editions = [e for e in berlin_editions if e["year"] <= 2015]
post_editions = [e for e in berlin_editions if e["year"] > 2015]

print(f"{'Year':<8} {'Base Rent':>10} {'YoY %':>8} {'Period':>10}")
print("-" * 42)

prev_rent = None
for e in berlin_editions:
    yoy = ""
    if prev_rent:
        yoy = f"{((e['base_rent_per_sqm'] - prev_rent) / prev_rent * 100):+.1f}%"
    period = "PRE" if e["year"] <= 2015 else "POST"
    print(f"{e['year']:<8} {e['base_rent_per_sqm']:>8.2f} €  {yoy:>8}  {period:>10}")
    prev_rent = e["base_rent_per_sqm"]

# Compute trends
pre_rents = [e["base_rent_per_sqm"] for e in pre_editions]
post_rents = [e["base_rent_per_sqm"] for e in post_editions]

# Pre-trend: 2013 → 2015 (2 years)
pre_years = [e["year"] for e in pre_editions]
pre_slope = (pre_rents[-1] - pre_rents[0]) / (pre_years[-1] - pre_years[0])
pre_annual_growth_pct = pre_slope / pre_rents[0] * 100

# Post-trend: 2015 → 2023 (8 years)
post_years = [e["year"] for e in post_editions]
post_slope = (post_rents[-1] - pre_rents[-1]) / (post_years[-1] - pre_years[-1])
post_annual_growth_pct = post_slope / pre_rents[-1] * 100

print(f"\n{'─' * 70}")
print(f"TREND ANALYSIS")
print(f"{'─' * 70}")
print(f"Pre-intervention  (2013–2015): {pre_slope:+.2f} €/m²/year  ({pre_annual_growth_pct:+.1f}%/year)")
print(f"Post-intervention (2015–2023): {post_slope:+.2f} €/m²/year  ({post_annual_growth_pct:+.1f}%/year)")
print(f"Change in growth rate:          {post_slope - pre_slope:+.2f} €/m²/year")

# Counterfactual: if pre-trend continued
counterfactual_2023 = pre_rents[-1] + pre_slope * (2023 - 2015)
actual_2023 = post_rents[-1]
excess = actual_2023 - counterfactual_2023
print(f"\nCounterfactual 2023 (pre-trend continued): €{counterfactual_2023:.2f}/m²")
print(f"Actual 2023:                               €{actual_2023:.2f}/m²")
print(f"Excess above counterfactual:               €{excess:+.2f}/m²  ({excess/counterfactual_2023*100:+.1f}%)")

effect_direction = "ACCELERATED" if post_slope > pre_slope else "DECELERATED"
print(f"\n★ CONCLUSION: Rent growth {effect_direction} after Mietpreisbremse")
if post_slope > pre_slope:
    print(f"   Pre-trend: {pre_annual_growth_pct:+.1f}%/yr → Post-trend: {post_annual_growth_pct:+.1f}%/yr")
    print(f"   The rent brake did NOT slow rent growth at the city level.")
    print(f"   Possible explanations: law only applies to re-lets, not new builds;")
    print(f"   exceptions for 'modernized' units; weak enforcement.")

# ═══════════════════════════════════════════════════════════
# 2. RENT BURDEN ANALYSIS (Rent / Median Income)
# ═══════════════════════════════════════════════════════════
print(f"\n{'═' * 70}")
print(f"RENT BURDEN ANALYSIS — Berlin")
print(f"{'═' * 70}")

# Berlin median household income (2023 estimate from Amt für Statistik)
# Source: https://www.statistik-berlin-brandenburg.de/
# Median net household income Berlin 2022: ~€2,450/month
# Using conservative estimate
median_income_monthly = 2450  # € net household

# What can a median household afford at 30% burden rule?
affordable_rent_30pct = median_income_monthly * 0.30

# Current Berlin Mietspiegel: compute average across all lage/baujahr/sizes
all_rents = []
for table in berlin_current.get("tables", []):
    for row in table.get("rows", []):
        for key in ["bis_40", "40_60", "60_90", "ueber_90"]:
            val = row.get(key)
            if val and val > 0:
                all_rents.append(val)

avg_rent_per_sqm = mean(all_rents) if all_rents else 0

# Scenarios
scenarios = [
    ("Studio (40 m²)", 40),
    ("1-bedroom (60 m²)", 60),
    ("2-bedroom (90 m²)", 90),
]

print(f"\nMedian household income (net): €{median_income_monthly:,}/month")
print(f"30% affordability threshold:   €{affordable_rent_30pct:,.0f}/month")
print(f"Average Berlin Mietspiegel:     €{avg_rent_per_sqm:.2f}/m² (net cold)\n")

print(f"{'Apartment':<22} {'Cold Rent':>10} {'Burden %':>10} {'Affordable?':>12}")
print("-" * 60)
for label, size in scenarios:
    cold_rent = avg_rent_per_sqm * size
    burden_pct = cold_rent / median_income_monthly * 100
    affordable = "YES" if burden_pct <= 30 else "NO — over 30%"
    print(f"{label:<22} €{cold_rent:>8,.0f}/mo  {burden_pct:>8.1f}%  {affordable:>12}")

# Warm rent estimate (add ~€2.50/m² for utilities)
avg_warm_rent = avg_rent_per_sqm + 2.50
print(f"\nWith utilities (+€2.50/m² = €{avg_warm_rent:.2f}/m² warm):")
for label, size in scenarios:
    warm_rent = avg_warm_rent * size
    burden_pct = warm_rent / median_income_monthly * 100
    print(f"  {label:<20} €{warm_rent:>8,.0f}/mo warm  = {burden_pct:.1f}% burden")

# ═══════════════════════════════════════════════════════════
# 3. DISTRICT INEQUALITY
# ═══════════════════════════════════════════════════════════
print(f"\n{'═' * 70}")
print(f"DISTRICT RENT INEQUALITY — Berlin")
print(f"{'═' * 70}")

districts = sorted(districts_data["districts"], key=lambda d: d["avg_rent"])
print(f"\n{'District':<25} {'Avg €/m²':>10} {'vs Avg':>8} {'Einfach%':>9} {'Gut%':>7}")
print("-" * 65)
for d in districts:
    vs_avg = d["gap_pct"]
    print(f"{d['district']:<25} {d['avg_rent']:>8.2f} €  {vs_avg:>+6.1f}%  {d['einfach_pct']:>7.1f}%  {d['gut_pct']:>5.1f}%")

cheapest = districts[0]
priciest = districts[-1]
ratio = priciest["avg_rent"] / cheapest["avg_rent"]
print(f"\nCheapest: {cheapest['district']} at €{cheapest['avg_rent']:.2f}/m²")
print(f"Priciest: {priciest['district']} at €{priciest['avg_rent']:.2f}/m²")
print(f"Ratio:    {ratio:.2f}x — the richest district is {ratio:.1f}x the poorest")
print(f"Gap:      €{priciest['avg_rent'] - cheapest['avg_rent']:.2f}/m²")

# For a 60m² apartment:
print(f"\n60 m² apartment:")
print(f"  {cheapest['district']}: €{cheapest['avg_rent']*60:,.0f}/mo cold")
print(f"  {priciest['district']}: €{priciest['avg_rent']*60:,.0f}/mo cold")
print(f"  Difference: €{(priciest['avg_rent'] - cheapest['avg_rent'])*60:,.0f}/mo")

# ═══════════════════════════════════════════════════════════
# 4. IMMOSCOUT vs MIETSPIEGEL GAP (market premium)
# ═══════════════════════════════════════════════════════════
print(f"\n{'═' * 70}")
print(f"MARKET vs OFFICIAL — The 'Real Rent' Gap")
print(f"{'═' * 70}")

immo_avg = districts_data["berlin_avg_immoscout"]  # 10.79
zensus_avg = districts_data["berlin_avg_zensus"]    # 7.97
official_avg = districts_data["berlin_avg_official"] # 11.73

print(f"\nImmoscout24 market asking:    €{immo_avg:.2f}/m²")
print(f"Official Mietspiegel (avg):   €{official_avg:.2f}/m²")
print(f"Zensus 2022 existing rents:   €{zensus_avg:.2f}/m²")
print(f"\nMarket premium over Mietspiegel: €{immo_avg - official_avg:+.2f}/m² ({(immo_avg/official_avg - 1)*100:+.1f}%)")
print(f"Market premium over existing:    €{immo_avg - zensus_avg:+.2f}/m² ({(immo_avg/zensus_avg - 1)*100:+.1f}%)")
print(f"Mietspiegel over existing:       €{official_avg - zensus_avg:+.2f}/m² ({(official_avg/zensus_avg - 1)*100:+.1f}%)")

print(f"\n★ The 'Two Berlins': existing tenants pay €{zensus_avg:.2f}/m²,")
print(f"   new tenants face asking rents of €{immo_avg:.2f}/m² — a {((immo_avg/zensus_avg - 1)*100):.0f}% gap.")
print(f"   Moving house in Berlin means a {((immo_avg/zensus_avg - 1)*100):.0f}% rent increase on average.")

# ═══════════════════════════════════════════════════════════
# 5. EXPORT FOR TABLEAU / BIGQUERY
# ═══════════════════════════════════════════════════════════
print(f"\n{'═' * 70}")
print(f"EXPORTING DATA FOR TABLEAU PUBLIC & BIGQUERY")
print(f"{'═' * 70}")

exports_dir = ROOT / "exports"
exports_dir.mkdir(exist_ok=True)

# 5a. Berlin Mietspiegel 2024 — flat table
with open(exports_dir / "berlin_mietspiegel_2024.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["lage", "baujahr", "bis_40", "40_60", "60_90", "ueber_90"])
    for table in berlin_current.get("tables", []):
        for row in table.get("rows", []):
            w.writerow([
                table["lage"],
                row["baujahr"],
                row.get("bis_40", ""),
                row.get("40_60", ""),
                row.get("60_90", ""),
                row.get("ueber_90", ""),
            ])

# 5b. Berlin Mietspiegel — unpivoted (one row per cell)
with open(exports_dir / "berlin_rent_cells.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["city", "lage", "baujahr", "size_class", "size_m2", "rent_per_sqm", "rent_total", "year"])
    size_map = {"bis_40": (30, "under 40"), "40_60": (50, "40–60"), "60_90": (75, "60–90"), "ueber_90": (100, "over 90")}
    for table in berlin_current.get("tables", []):
        for row in table.get("rows", []):
            for key in ["bis_40", "40_60", "60_90", "ueber_90"]:
                val = row.get(key)
                if val and val > 0:
                    size_mid, size_label = size_map[key]
                    w.writerow([
                        "Berlin", table["lage"], row["baujahr"],
                        size_label, size_mid, val,
                        round(val * size_mid, 0), 2024
                    ])

# 5c. Berlin districts
with open(exports_dir / "berlin_districts.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["district", "avg_rent_per_sqm", "einfach_pct", "mittel_pct", "gut_pct", "total_addresses", "gap_vs_avg_pct"])
    for d in districts:
        w.writerow([d["district"], d["avg_rent"], d["einfach_pct"], d["mittel_pct"],
                     d["gut_pct"], d["total_addresses"], d["gap_pct"]])

# 5d. Berlin historical trend
with open(exports_dir / "berlin_historical_trend.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["city", "year", "base_rent_per_sqm", "mietspiegel_type", "period"])
    for e in berlin_editions:
        w.writerow(["Berlin", e["year"], e["base_rent_per_sqm"],
                     e.get("type", "qualifiziert"),
                     "PRE" if e["year"] <= 2015 else "POST"])

# 5e. Berlin Mietpreisbremse analysis summary
with open(exports_dir / "berlin_mietpreisbremse_analysis.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["metric", "value", "unit"])
    w.writerow(["pre_intervention_slope", round(pre_slope, 2), "€/m²/year"])
    w.writerow(["post_intervention_slope", round(post_slope, 2), "€/m²/year"])
    w.writerow(["pre_annual_growth_pct", round(pre_annual_growth_pct, 1), "%"])
    w.writerow(["post_annual_growth_pct", round(post_annual_growth_pct, 1), "%"])
    w.writerow(["counterfactual_2023", round(counterfactual_2023, 2), "€/m²"])
    w.writerow(["actual_2023", round(actual_2023, 2), "€/m²"])
    w.writerow(["excess_above_counterfactual", round(excess, 2), "€/m²"])
    w.writerow(["rent_growth_accelerated", 1 if post_slope > pre_slope else 0, "boolean"])

print(f"\nExported to {exports_dir}/:")
for f in sorted(exports_dir.glob("*.csv")):
    lines = len(open(f).readlines()) - 1
    print(f"  {f.name} ({lines} rows)")

print(f"\n✓ Analysis complete. Files ready for Tableau Public & BigQuery import.")
