#!/usr/bin/env python3
"""
Rent Impact Simulator — A/B testing framework for rent policy simulation.

Simulates:
  1. Before/after rent change: What if Mietspiegel values increased/decreased by X%?
  2. Economic impact: Total € impact across population × affected units.
  3. Counterfactual analysis: "If Berlin adopted Munich's rent levels..."
  4. Distributional impact: Does a change disproportionately affect small/old apartments?

Uses the 23-city dataset from data/processed/. Prints a formatted report.

Usage:
    python experiments/rent_impact_simulator.py
    python experiments/rent_impact_simulator.py --scenario all
    python experiments/rent_impact_simulator.py --scenario percentage --pct 5
"""
import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(os.environ.get(
    "MIETSPIEGEL_ROOT",
    "/Users/ruhvee/mietspiegel-digitization",
))
DATA_DIR = PROJECT_ROOT / "data" / "processed"

SIZE_KEYS = ["bis_40", "40_60", "60_90", "ueber_90"]
SIZE_LABELS = {
    "bis_40": "bis 40 m²",
    "40_60": "40–60 m²",
    "60_90": "60–90 m²",
    "ueber_90": "über 90 m²",
}

# Estimated share of housing units per city (rental units / population × avg household size)
# Rough estimate: ~40% of population lives in rental housing, avg 2.0 persons/household
HOUSEHOLD_SIZE = 2.0
RENTAL_SHARE = 0.55  # Approximate share of rental housing in German cities

# Expected rent ranking for counterfactual analysis
HIGH_RENT_CITY = "muenchen"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_cities() -> dict[str, dict]:
    """Load all valid city JSON files."""
    cities = {}
    skip_files = {
        "cities_index", "cities_comparison", "berlin-districts",
        "berlin-districts-geo", "redx_grid_rent", "redx_district_rent",
        "hamburg_streets", "kiel_streets", "saarbruecken_streets",
    }
    for fpath in sorted(DATA_DIR.glob("*.json")):
        name = fpath.stem
        if name in skip_files:
            continue
        with open(fpath) as f:
            data = json.load(f)
        if data.get("tables") or data.get("matrix"):
            cities[name] = data
    return cities


def _build_dataframe(cities: dict[str, dict]) -> pd.DataFrame:
    """
    Build a flat DataFrame from all city data.
    Columns: city, slug, state, population, lage, baujahr, bis_40, 40_60, 60_90, ueber_90
    """
    rows: list[dict[str, Any]] = []
    for slug, data in cities.items():
        city = data.get("city", slug)
        state = data.get("state", "")
        pop = data.get("population", 0)
        for table in data.get("tables", []):
            lage = table.get("lage", "")
            for row in table.get("rows", []):
                bj = row.get("baujahr", "")
                entry = {
                    "city": city,
                    "slug": slug,
                    "state": state,
                    "population": pop,
                    "lage": lage,
                    "baujahr": bj,
                }
                for sk in SIZE_KEYS:
                    val = row.get(sk)
                    entry[sk] = float(val) if isinstance(val, (int, float)) else np.nan
                rows.append(entry)
    return pd.DataFrame(rows)


def _estimated_rental_units(population: float) -> float:
    """Estimate number of rental housing units in a city."""
    return (population * RENTAL_SHARE) / HOUSEHOLD_SIZE


# ---------------------------------------------------------------------------
# Scenario 1: Percentage rent change
# ---------------------------------------------------------------------------

def simulate_percentage_change(
    df: pd.DataFrame,
    pct: float = 5.0,
) -> dict[str, Any]:
    """
    Simulate a uniform percentage change in all Mietspiegel rents.

    Args:
        df: City data DataFrame.
        pct: Percentage change (positive = increase, negative = decrease).

    Returns:
        Dict with summary statistics.
    """
    factor = 1.0 + pct / 100.0
    df_sim = df.copy()
    for sk in SIZE_KEYS:
        df_sim[sk] = df[sk] * factor

    # Compute city-level impact
    city_impact: list[dict[str, Any]] = []
    for slug, grp in df.groupby("slug"):
        city = grp.iloc[0]["city"]
        pop = grp.iloc[0]["population"]
        state = grp.iloc[0]["state"]
        units = _estimated_rental_units(pop)

        orig_avg = grp[SIZE_KEYS].mean().mean()
        new_avg = df_sim[df_sim["slug"] == slug][SIZE_KEYS].mean().mean()

        # Monthly impact: avg sqm * avg apartment size (~70 m²) * units
        avg_apartment_sqm = 70.0
        monthly_impact = (new_avg - orig_avg) * avg_apartment_sqm * units
        annual_impact = monthly_impact * 12

        city_impact.append({
            "city": city,
            "state": state,
            "population": pop,
            "estimated_units": round(units),
            "orig_avg_rent": round(orig_avg, 2),
            "new_avg_rent": round(new_avg, 2),
            "change_per_sqm": round(new_avg - orig_avg, 2),
            "monthly_impact_millions": round(monthly_impact / 1e6, 2),
            "annual_impact_millions": round(annual_impact / 1e6, 2),
        })

    total_annual = sum(c["annual_impact_millions"] for c in city_impact)
    return {
        "scenario": f"{pct:+.1f}% uniform change",
        "factor": factor,
        "city_impacts": sorted(city_impact, key=lambda x: x["annual_impact_millions"], reverse=True),
        "total_annual_impact_millions": round(total_annual, 1),
    }


# ---------------------------------------------------------------------------
# Scenario 2: Counterfactual analysis
# ---------------------------------------------------------------------------

def simulate_counterfactual(
    df: pd.DataFrame,
    target_city_slug: str = HIGH_RENT_CITY,
) -> dict[str, Any]:
    """
    What if every city adopted the target city's rent levels?
    Shows how many tenants would be "priced out" based on affordability thresholds.

    Args:
        df: City data DataFrame.
        target_city_slug: Slug of the city whose rent levels are applied.

    Returns:
        Dict with affordability impact analysis.
    """
    target_df = df[df["slug"] == target_city_slug]
    if target_df.empty:
        return {"error": f"Target city '{target_city_slug}' not found."}

    # Build target city's rent table: (lage, baujahr) -> avg rent
    target_rents: dict[tuple[str, str], dict[str, float]] = {}
    for _, row in target_df.iterrows():
        key = (str(row["lage"]), str(row["baujahr"]))
        target_rents[key] = {sk: row[sk] for sk in SIZE_KEYS if not pd.isna(row[sk])}

    # Apply target rents to all cities, matching (lage, baujahr)
    city_impact: list[dict[str, Any]] = []
    affordability_threshold = 0.30  # 30% of income on rent = "burdened"

    total_units_affected = 0
    total_extra_cost_millions = 0.0

    for slug, grp in df.groupby("slug"):
        if slug == target_city_slug:
            continue

        city = grp.iloc[0]["city"]
        pop = grp.iloc[0]["population"]
        units = _estimated_rental_units(pop)
        avg_apartment_sqm = 70.0

        orig_total_monthly = 0.0
        new_total_monthly = 0.0
        match_count = 0

        for _, row in grp.iterrows():
            key = (str(row["lage"]), str(row["baujahr"]))
            if key in target_rents:
                orig_avg = row[SIZE_KEYS].mean()
                new_avg = np.nanmean(list(target_rents[key].values()))
                if not np.isnan(orig_avg) and not np.isnan(new_avg):
                    orig_total_monthly += orig_avg * avg_apartment_sqm
                    new_total_monthly += new_avg * avg_apartment_sqm
                    match_count += 1

        if match_count > 0:
            orig_per_unit = orig_total_monthly / match_count
            new_per_unit = new_total_monthly / match_count
            extra_per_month = (new_per_unit - orig_per_unit) * units
            extra_per_year = extra_per_month * 12

            # Priced out: tenants spending >30% of local median income on rent
            # Estimate: median income ~€3500/month
            median_income = 3500.0
            orig_burden = orig_per_unit / median_income
            new_burden = new_per_unit / median_income
            newly_burdened = new_burden > affordability_threshold and orig_burden <= affordability_threshold

            city_impact.append({
                "city": city,
                "orig_avg_monthly": round(orig_per_unit, 2),
                "new_avg_monthly": round(new_per_unit, 2),
                "increase_pct": round((new_per_unit - orig_per_unit) / orig_per_unit * 100, 1),
                "annual_extra_millions": round(extra_per_year / 1e6, 2),
                "newly_burdened": newly_burdened,
                "orig_burden_rate": round(orig_burden * 100, 1),
                "new_burden_rate": round(new_burden * 100, 1),
            })
            total_units_affected += units
            total_extra_cost_millions += extra_per_year / 1e6

    target_city_name = df[df["slug"] == target_city_slug].iloc[0]["city"]
    return {
        "scenario": f"All cities adopt {target_city_name} rent levels",
        "target_city": target_city_name,
        "target_city_avg_rent": round(
            target_df[SIZE_KEYS].mean().mean(), 2
        ),
        "city_impacts": sorted(city_impact, key=lambda x: x["increase_pct"], reverse=True),
        "total_units_affected": round(total_units_affected),
        "total_annual_extra_cost_millions": round(total_extra_cost_millions, 1),
    }


# ---------------------------------------------------------------------------
# Scenario 3: Distributional impact
# ---------------------------------------------------------------------------

def simulate_distributional_impact(df: pd.DataFrame, pct: float = 5.0) -> dict[str, Any]:
    """
    Analyze how a uniform rent increase disproportionately affects:
      - Small apartments (bis_40) vs large (ueber_90)
      - Old buildings (vorkrieg) vs new (2014+)
      - Simple Lage vs premium Lage
    """
    factor = 1.0 + pct / 100.0

    def is_old_building(bj: str) -> bool:
        bj_lower = str(bj).lower()
        return any(term in bj_lower for term in ["bis 1918", "vor 1918", "1918", "1919-1949"])

    def is_new_building(bj: str) -> bool:
        bj_lower = str(bj).lower()
        return any(term in bj_lower for term in ["2014+", "2011-2024", "2020", "2016", "aktuell"])

    # Absolute increase per sqm
    df_impact = df.copy()
    for sk in SIZE_KEYS:
        df_impact[f"{sk}_delta"] = df[sk] * (factor - 1.0)

    # By size class
    size_impact = {}
    for sk, label in SIZE_LABELS.items():
        delta_col = f"{sk}_delta"
        if sk in df.columns and delta_col in df_impact.columns:
            size_impact[label] = {
                "mean_orig_rent": round(df[sk].mean(), 2),
                "mean_abs_increase": round(df_impact[delta_col].mean(), 2),
                "mean_pct_increase": pct,
            }

    # By building age
    old_mask = df["baujahr"].apply(is_old_building)
    new_mask = df["baujahr"].apply(is_new_building)

    old_avg = df[old_mask][SIZE_KEYS].mean().mean() if old_mask.any() else 0
    new_avg = df[new_mask][SIZE_KEYS].mean().mean() if new_mask.any() else 0
    old_delta = old_avg * (factor - 1.0)
    new_delta = new_avg * (factor - 1.0)

    # By Lage
    lage_impact = {}
    for lage in df["lage"].unique():
        lage_mask = df["lage"] == lage
        lage_avg = df[lage_mask][SIZE_KEYS].mean().mean()
        lage_impact[str(lage)] = {
            "mean_orig_rent": round(lage_avg, 2),
            "mean_abs_increase": round(lage_avg * (factor - 1.0), 2),
        }

    # Disproportionality analysis
    if old_avg > 0 and new_avg > 0:
        ratio = old_delta / new_delta if new_delta > 0 else float("inf")
        elderly_burden = (
            "Old buildings bear MORE of the increase"
            if ratio > 1.0
            else "New buildings bear MORE of the increase"
        )
    else:
        ratio = 1.0
        elderly_burden = "Insufficient data"

    return {
        "scenario": f"{pct:+.1f}% distributional impact analysis",
        "size_class_impact": size_impact,
        "building_age_impact": {
            "old_buildings": {
                "mean_orig_rent": round(old_avg, 2),
                "mean_abs_increase": round(old_delta, 2),
            },
            "new_buildings": {
                "mean_orig_rent": round(new_avg, 2),
                "mean_abs_increase": round(new_delta, 2),
            },
            "old_vs_new_increase_ratio": round(ratio, 2),
            "analysis": elderly_burden,
        },
        "lage_impact": lage_impact,
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def print_report(results: list[dict[str, Any]]) -> None:
    """Print a formatted simulation report."""
    print("=" * 78)
    print("  RENT POLICY IMPACT SIMULATION REPORT")
    print("  Mietspiegel Digitization — A/B Testing Framework")
    print("=" * 78)

    for result in results:
        if "error" in result:
            print(f"\n  ERROR: {result['error']}")
            continue

        scenario = result.get("scenario", "Unknown")
        print(f"\n{'─' * 78}")
        print(f"  SCENARIO: {scenario}")
        print(f"{'─' * 78}")

        # Scenario 1: Percentage change
        if "total_annual_impact_millions" in result:
            print(f"\n  Total annual impact: €{result['total_annual_impact_millions']:,.1f}M\n")
            print(f"  {'City':<25s} {'State':<22s} {'Rent Δ/m²':>9s} {'Annual €M':>10s} {'Units':>8s}")
            print(f"  {'─'*25} {'─'*22} {'─'*9} {'─'*10} {'─'*8}")
            for c in result["city_impacts"][:15]:
                print(
                    f"  {c['city']:<25s} {c['state']:<22s} "
                    f"€{c['change_per_sqm']:>7.2f} "
                    f"€{c['annual_impact_millions']:>9.1f}M "
                    f"{c['estimated_units']:>8,}"
                )

        # Scenario 2: Counterfactual
        if "target_city" in result:
            print(f"\n  Target: {result['target_city']} (avg €{result['target_city_avg_rent']}/m²)")
            print(f"  Total units affected: {result['total_units_affected']:,}")
            print(f"  Total annual extra cost: €{result['total_annual_extra_cost_millions']:,.1f}M\n")
            print(f"  {'City':<25s} {'Orig €/mo':>10s} {'New €/mo':>10s} {'Increase':>8s} {'Burdened':>9s} {'Extra €M/yr':>11s}")
            print(f"  {'─'*25} {'─'*10} {'─'*10} {'─'*8} {'─'*9} {'─'*11}")
            for c in result["city_impacts"][:15]:
                burdened = "⚠ YES" if c["newly_burdened"] else "no"
                print(
                    f"  {c['city']:<25s} €{c['orig_avg_monthly']:>8.0f} "
                    f"€{c['new_avg_monthly']:>8.0f} "
                    f"{c['increase_pct']:>+7.1f}% "
                    f"{burdened:>9s} "
                    f"€{c['annual_extra_millions']:>9.1f}M"
                )

        # Scenario 3: Distributional
        if "size_class_impact" in result:
            print("\n  ** By Apartment Size **")
            for size, vals in result["size_class_impact"].items():
                print(
                    f"    {size:<15s}  orig €{vals['mean_orig_rent']:.2f}/m²  "
                    f"→ +€{vals['mean_abs_increase']:.2f}/m² (+{vals['mean_pct_increase']:.1f}%)"
                )

            print("\n  ** By Building Age **")
            old_val = result["building_age_impact"]["old_buildings"]
            new_val = result["building_age_impact"]["new_buildings"]
            print(f"    Pre-1950 buildings:  orig €{old_val['mean_orig_rent']:.2f}/m² → +€{old_val['mean_abs_increase']:.2f}/m²")
            print(f"    Post-2010 buildings: orig €{new_val['mean_orig_rent']:.2f}/m² → +€{new_val['mean_abs_increase']:.2f}/m²")
            print(f"    Old/New increase ratio: {result['building_age_impact']['old_vs_new_increase_ratio']:.2f}")
            print(f"    → {result['building_age_impact']['analysis']}")

            print("\n  ** By Lage Category **")
            for lage, vals in result["lage_impact"].items():
                print(
                    f"    {lage:<12s}  orig €{vals['mean_orig_rent']:.2f}/m²  "
                    f"→ +€{vals['mean_abs_increase']:.2f}/m²"
                )

    print(f"\n{'=' * 78}")
    print("  Report complete.")
    print(f"{'=' * 78}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rent Policy Impact Simulator — A/B testing for Mietspiegel data"
    )
    parser.add_argument(
        "--scenario",
        choices=["percentage", "counterfactual", "distributional", "all"],
        default="all",
        help="Which scenario to simulate (default: all)",
    )
    parser.add_argument(
        "--pct",
        type=float,
        default=5.0,
        help="Percentage change for percentage/distributional scenarios (default: 5.0)",
    )
    parser.add_argument(
        "--target",
        default=HIGH_RENT_CITY,
        help=f"Target city slug for counterfactual analysis (default: {HIGH_RENT_CITY})",
    )
    args = parser.parse_args()

    # Load data
    print("Loading city data...")
    cities = _load_cities()
    df = _build_dataframe(cities)
    print(f"Loaded {len(cities)} cities, {len(df)} data rows.")

    # Run scenarios
    results: list[dict[str, Any]] = []

    if args.scenario in ("percentage", "all"):
        print(f"\nRunning percentage change scenario ({args.pct:+.1f}%)...")
        results.append(simulate_percentage_change(df, pct=args.pct))

    if args.scenario in ("counterfactual", "all"):
        print(f"\nRunning counterfactual scenario (target: {args.target})...")
        results.append(simulate_counterfactual(df, target_city_slug=args.target))

    if args.scenario in ("distributional", "all"):
        print(f"\nRunning distributional impact analysis ({args.pct:+.1f}%)...")
        results.append(simulate_distributional_impact(df, pct=args.pct))

    # Print report
    print_report(results)


if __name__ == "__main__":
    main()
