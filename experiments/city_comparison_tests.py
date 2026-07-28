#!/usr/bin/env python3
"""
Statistical Hypothesis Testing on 23-City Mietspiegel Dataset.

Tests:
  1. Pairwise t-tests between cities with Bonferroni correction
  2. Cohen's d effect size for meaningful differences
  3. ANOVA across Bundesländer (do states differ significantly?)
  4. Correlation: population vs rent level, city size vs rent spread
  5. Tukey HSD post-hoc for ANOVA

Uses scipy.stats and statsmodels. Prints a formatted statistical report.

Requirements:
    pip install scipy statsmodels pandas

Usage:
    python experiments/city_comparison_tests.py
"""
from __future__ import annotations

import json
import os
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import (
    f_oneway,
    levene,
    pearsonr,
    shapiro,
    spearmanr,
    ttest_ind,
)

try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    HAS_TUKEY = True
except ImportError:
    HAS_TUKEY = False

try:
    from statsmodels.stats.multitest import multipletests
    HAS_MULTIPLETEST = True
except ImportError:
    HAS_MULTIPLETEST = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(os.environ.get(
    "MIETSPIEGEL_ROOT",
    "/Users/ruhvee/mietspiegel-digitization",
))
DATA_DIR = PROJECT_ROOT / "data" / "processed"

SIZE_KEYS = ["bis_40", "40_60", "60_90", "ueber_90"]

# Significance levels
ALPHA = 0.05
BONFERRONI_ALPHA = 0.05  # Will be divided by number of comparisons


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_cities() -> dict[str, dict]:
    """Load all valid city JSON files from data/processed/."""
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


def _build_city_summary(cities: dict[str, dict]) -> pd.DataFrame:
    """
    Build a per-city summary DataFrame.
    Columns: city, slug, state, population, year, avg_rent, std_rent,
             gut_avg, einfach_avg, rent_spread, baujahr_count, n_cells.
    """
    rows: list[dict[str, Any]] = []

    for slug, data in cities.items():
        city = data.get("city", slug)
        state = data.get("state", "")
        population = data.get("population", 0)
        year = data.get("year", 0)

        all_values: list[float] = []
        gut_values: list[float] = []
        einfach_values: list[float] = []
        baujahr_set: set = set()

        for table in data.get("tables", []):
            lage = table.get("lage", "").lower()
            for row in table.get("rows", []):
                bj = row.get("baujahr", "")
                if bj:
                    baujahr_set.add(bj)
                for sk in SIZE_KEYS:
                    val = row.get(sk)
                    if isinstance(val, (int, float)) and val > 0:
                        all_values.append(float(val))
                        if lage == "gut":
                            gut_values.append(float(val))
                        elif lage == "einfach":
                            einfach_values.append(float(val))

        if not all_values:
            continue

        avg_rent = np.mean(all_values)
        std_rent = np.std(all_values, ddof=1)
        gut_avg = np.mean(gut_values) if gut_values else None
        einfach_avg = np.mean(einfach_values) if einfach_values else None
        rent_spread = (gut_avg / einfach_avg) if (gut_avg and einfach_avg and einfach_avg > 0) else None

        rows.append({
            "city": city,
            "slug": slug,
            "state": state,
            "population": population,
            "year": year,
            "avg_rent": round(avg_rent, 2),
            "std_rent": round(std_rent, 2),
            "gut_avg": round(gut_avg, 2) if gut_avg else None,
            "einfach_avg": round(einfach_avg, 2) if einfach_avg else None,
            "rent_spread": round(rent_spread, 2) if rent_spread else None,
            "baujahr_count": len(baujahr_set),
            "n_cells": len(all_values),
        })

    return pd.DataFrame(rows)


def _build_flat_rents(cities: dict[str, dict]) -> dict[str, list]:
    """
    Build per-city DataFrames of all rent values for t-test pairing.
    Returns dict: slug -> list of rent values.
    """
    city_rents: dict[str, list[float]] = {}
    for slug, data in cities.items():
        vals: list[float] = []
        for table in data.get("tables", []):
            for row in table.get("rows", []):
                for sk in SIZE_KEYS:
                    val = row.get(sk)
                    if isinstance(val, (int, float)) and val > 0:
                        vals.append(float(val))
        if vals:
            city_rents[slug] = vals
    return city_rents


def _build_state_data(cities: dict[str, dict]) -> dict[str, list[float]]:
    """Build per-state lists of rent values for ANOVA."""
    state_data: dict[str, list[float]] = defaultdict(list)
    for slug, data in cities.items():
        state = data.get("state", "Unbekannt")
        for table in data.get("tables", []):
            for row in table.get("rows", []):
                for sk in SIZE_KEYS:
                    val = row.get(sk)
                    if isinstance(val, (int, float)) and val > 0:
                        state_data[state].append(float(val))
    return state_data


from collections import defaultdict

# ---------------------------------------------------------------------------
# 1. Cohen's d effect size
# ---------------------------------------------------------------------------

def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """
    Compute Cohen's d effect size between two independent groups.

    Cohen's d interpretation:
      - 0.2: small effect
      - 0.5: medium effect
      - 0.8: large effect
      - 1.2+: very large effect
    """
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0

    mean1, mean2 = np.mean(group1), np.mean(group2)
    var1 = np.var(group1, ddof=1)
    var2 = np.var(group2, ddof=1)

    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0

    d = (mean1 - mean2) / pooled_std
    return d


def interpret_cohens_d(d: float) -> str:
    """Human-readable interpretation of Cohen's d."""
    d_abs = abs(d)
    if d_abs < 0.2:
        return "negligible"
    elif d_abs < 0.5:
        return "small"
    elif d_abs < 0.8:
        return "medium"
    elif d_abs < 1.2:
        return "large"
    else:
        return "very large"


# ---------------------------------------------------------------------------
# 2. Pairwise t-tests with Bonferroni correction
# ---------------------------------------------------------------------------

def run_pairwise_t_tests(
    city_rents: dict[str, list[float]],
    city_names: dict[str, str],
) -> pd.DataFrame:
    """
    Run independent t-tests between all city pairs with Bonferroni correction.

    Returns DataFrame with: city_a, city_b, t_stat, p_value, cohens_d,
    significant (Bonferroni corrected), mean_a, mean_b, n_a, n_b.
    """
    slugs = sorted(city_rents.keys())
    n_comparisons = len(slugs) * (len(slugs) - 1) // 2
    bonferroni_threshold = ALPHA / n_comparisons if n_comparisons > 0 else ALPHA

    results: list[dict[str, Any]] = []

    for s1, s2 in combinations(slugs, 2):
        vals1 = np.array(city_rents[s1])
        vals2 = np.array(city_rents[s2])

        # Welch's t-test (doesn't assume equal variance)
        t_stat, p_val = ttest_ind(vals1, vals2, equal_var=False)

        # Cohen's d
        d = cohens_d(vals1, vals2)

        results.append({
            "city_a": city_names.get(s1, s1),
            "city_b": city_names.get(s2, s2),
            "slug_a": s1,
            "slug_b": s2,
            "t_statistic": round(t_stat, 4),
            "p_value": p_val,
            "cohens_d": round(d, 3),
            "effect_size": interpret_cohens_d(d),
            "mean_a": round(np.mean(vals1), 2),
            "mean_b": round(np.mean(vals2), 2),
            "n_a": len(vals1),
            "n_b": len(vals2),
        })

    df_results = pd.DataFrame(results)

    # Bonferroni correction
    if HAS_MULTIPLETEST and len(df_results) > 0:
        _, corrected_p, _, _ = multipletests(
            df_results["p_value"].values, alpha=ALPHA, method="bonferroni"
        )
        df_results["p_bonferroni"] = corrected_p
        df_results["significant"] = df_results["p_bonferroni"] < ALPHA
    else:
        df_results["p_bonferroni"] = df_results["p_value"] * n_comparisons
        df_results["p_bonferroni"] = df_results["p_bonferroni"].clip(upper=1.0)
        df_results["significant"] = df_results["p_bonferroni"] < ALPHA

    return df_results


# ---------------------------------------------------------------------------
# 3. ANOVA across Bundesländer
# ---------------------------------------------------------------------------

def run_anova_by_state(state_data: dict[str, list[float]]) -> dict[str, Any]:
    """
    One-way ANOVA: do mean rents differ significantly across Bundesländer?

    Assumptions checked:
      - Normality (Shapiro-Wilk, approximate)
      - Homogeneity of variance (Levene's test)
    """
    states = sorted(state_data.keys())
    groups = [np.array(state_data[s]) for s in states]

    if len(groups) < 2:
        return {"error": "Need at least 2 states for ANOVA."}

    # ANOVA
    f_stat, p_val = f_oneway(*groups)

    # Effect size: eta-squared
    all_values = np.concatenate(groups)
    grand_mean = np.mean(all_values)
    ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups)
    ss_total = sum((v - grand_mean) ** 2 for v in all_values)
    eta_sq = ss_between / ss_total if ss_total > 0 else 0

    # Levene's test for homogeneity of variance
    try:
        levene_stat, levene_p = levene(*groups)
    except Exception:
        levene_stat, levene_p = None, None

    # Normality check (sampled, as full test is expensive with large n)
    normality_warnings: list[str] = []
    for state, group in zip(states, groups):
        if len(group) > 5000:
            sample = np.random.choice(group, size=min(5000, len(group)), replace=False)
        else:
            sample = group
        if len(sample) >= 3:
            _, shapiro_p = shapiro(sample[:500])  # Cap at 500 for speed
            if shapiro_p < 0.01:
                normality_warnings.append(
                    f"{state}: Shapiro-Wilk p={shapiro_p:.4f} (non-normal, but ANOVA robust for large n)"
                )

    # State summaries
    state_summaries = []
    for state in states:
        vals = state_data[state]
        state_summaries.append({
            "state": state,
            "n": len(vals),
            "mean": round(np.mean(vals), 2),
            "std": round(np.std(vals, ddof=1), 2),
            "min": round(np.min(vals), 2),
            "max": round(np.max(vals), 2),
        })

    return {
        "test": "One-way ANOVA (rent ~ Bundesland)",
        "f_statistic": round(f_stat, 4),
        "p_value": p_val,
        "significant": p_val < ALPHA,
        "eta_squared": round(eta_sq, 4),
        "eta_sq_interpretation": (
            "small" if eta_sq < 0.01 else "medium" if eta_sq < 0.06 else "large"
        ),
        "levene_statistic": round(levene_stat, 4) if levene_stat else None,
        "levene_p_value": levene_p,
        "equal_variances": levene_p > ALPHA if levene_p else None,
        "normality_warnings": normality_warnings,
        "state_summaries": state_summaries,
        "n_states": len(states),
        "n_total": len(all_values),
    }


# ---------------------------------------------------------------------------
# 4. Tukey HSD post-hoc
# ---------------------------------------------------------------------------

def run_tukey_hsd(state_data: dict[str, list[float]]) -> pd.DataFrame | None:
    """
    Tukey Honestly Significant Difference post-hoc test for ANOVA.

    Only runs if statsmodels is available and ANOVA is significant.
    """
    if not HAS_TUKEY:
        return None

    # Build long-format data
    values: list[float] = []
    labels: list[str] = []
    for state, vals in state_data.items():
        values.extend(vals)
        labels.extend([state] * len(vals))

    try:
        tukey = pairwise_tukeyhsd(
            endog=np.array(values),
            groups=np.array(labels),
            alpha=ALPHA,
        )
        # Convert to DataFrame
        df_tukey = pd.DataFrame(
            data=tukey.summary().data[1:],
            columns=tukey.summary().data[0],
        )
        return df_tukey
    except Exception as e:
        print(f"  Tukey HSD failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 5. Correlation analysis
# ---------------------------------------------------------------------------

def run_correlation_analysis(df_summary: pd.DataFrame) -> dict[str, Any]:
    """
    Correlation analysis:
      - Population vs average rent (Pearson r)
      - Population vs rent spread (gut/einfach ratio)
      - City size (n_cells proxy) vs rent variance
    """
    results: dict[str, Any] = {}

    # Filter to cities with data
    df = df_summary.dropna(subset=["avg_rent", "population"]).copy()
    if len(df) < 3:
        return {"error": "Not enough cities for correlation analysis."}

    # 1. Population vs average rent
    if len(df) >= 3:
        r_pop, p_pop = pearsonr(df["population"].values, df["avg_rent"].values)
        rho_pop, p_rho_pop = spearmanr(df["population"].values, df["avg_rent"].values)
        results["population_vs_rent"] = {
            "pearson_r": round(r_pop, 4),
            "pearson_p": p_pop,
            "significant": p_pop < ALPHA,
            "spearman_rho": round(rho_pop, 4),
            "spearman_p": p_rho_pop,
            "interpretation": (
                f"City size explains {r_pop**2 * 100:.1f}% of rent variance"
                if p_pop < ALPHA
                else "No significant correlation between population and rent level"
            ),
        }

    # 2. Population vs rent spread (gut/einfach)
    df_spread = df.dropna(subset=["rent_spread"]).copy()
    if len(df_spread) >= 3:
        r_sp, p_sp = pearsonr(df_spread["population"].values, df_spread["rent_spread"].values)
        results["population_vs_spread"] = {
            "pearson_r": round(r_sp, 4),
            "pearson_p": p_sp,
            "significant": p_sp < ALPHA,
            "interpretation": (
                f"Larger cities have {'wider' if r_sp > 0 else 'narrower'} rent spreads "
                f"(r={r_sp:.3f}, p={p_sp:.4f})"
            ),
        }

    # 3. Baujahr count vs avg rent
    df_bj = df.dropna(subset=["baujahr_count"]).copy()
    if len(df_bj) >= 3:
        r_bj, p_bj = pearsonr(df_bj["baujahr_count"].values, df_bj["avg_rent"].values)
        results["baujahr_count_vs_rent"] = {
            "pearson_r": round(r_bj, 4),
            "pearson_p": p_bj,
            "significant": p_bj < ALPHA,
        }

    return results


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def print_statistical_report(
    pairwise_results: pd.DataFrame,
    anova_results: dict[str, Any],
    tukey_results: pd.DataFrame | None,
    correlation_results: dict[str, Any],
    df_summary: pd.DataFrame,
    city_rents: dict[str, list[float]],
) -> None:
    """Print a formatted statistical analysis report."""

    print("=" * 78)
    print("  STATISTICAL ANALYSIS OF 23-CITY MIETSPIEGEL DATASET")
    print("  Hypothesis Testing: t-tests, ANOVA, Effect Sizes, Correlations")
    print("=" * 78)

    # ---- City summary ----
    print(f"\n{'─' * 78}")
    print("  CITY SUMMARY STATISTICS")
    print(f"{'─' * 78}")
    print(
        f"  {'City':<25s} {'State':<22s} {'Pop':>8s} {'Avg €/m²':>9s} "
        f"{'Std':>7s} {'Gut':>8s} {'Einf':>7s} {'Spread':>7s}"
    )
    print(f"  {'─'*25} {'─'*22} {'─'*8} {'─'*9} {'─'*7} {'─'*8} {'─'*7} {'─'*7}")
    for _, row in df_summary.sort_values("avg_rent", ascending=False).iterrows():
        print(
            f"  {row['city']:<25s} {row['state']:<22s} "
            f"{row['population']:>8,} "
            f"€{row['avg_rent']:>7.2f} "
            f"€{row['std_rent']:>5.2f} "
            f"€{str(row['gut_avg']):>6s} "
            f"€{str(row['einfach_avg']):>5s} "
            f"{str(row['rent_spread']):>7s}"
        )

    # ---- Pairwise t-tests ----
    print(f"\n{'─' * 78}")
    print("  1. PAIRWISE T-TESTS WITH BONFERRONI CORRECTION")
    print(f"{'─' * 78}")

    n_comparisons = len(pairwise_results)
    n_significant = pairwise_results["significant"].sum() if "significant" in pairwise_results.columns else 0
    bonf_threshold = ALPHA / n_comparisons if n_comparisons > 0 else ALPHA

    print(f"  Cities compared: {int(np.sqrt(2 * n_comparisons + 0.25) + 0.5)}")
    print(f"  Pairwise comparisons: {n_comparisons}")
    print(f"  Bonferroni-corrected α: {bonf_threshold:.6f}")
    print(f"  Significantly different pairs: {n_significant} / {n_comparisons}")

    # Top significant differences
    sig_pairs = pairwise_results[pairwise_results["significant"]].nlargest(20, "cohens_d")
    print("\n  Top significant differences (by effect size):")
    print(f"  {'City A':<22s} {'City B':<22s} {'Cohens d':>9s} {'Effect':>12s} {'Mean A':>7s} {'Mean B':>7s} {'p(adj)':>10s}")
    print(f"  {'─'*22} {'─'*22} {'─'*9} {'─'*12} {'─'*7} {'─'*7} {'─'*10}")
    for _, row in sig_pairs.head(15).iterrows():
        print(
            f"  {row['city_a']:<22s} {row['city_b']:<22s} "
            f"{row['cohens_d']:>+9.3f} {row['effect_size']:>12s} "
            f"€{row['mean_a']:>5.2f} €{row['mean_b']:>5.2f} "
            f"{row['p_bonferroni']:>10.6f}"
        )

    # ---- Top 5 effect sizes overall ----
    top_effects = pairwise_results.nlargest(10, "cohens_d")
    print("\n  Top 10 effect sizes (Cohen's d), regardless of significance:")
    for _, row in top_effects.iterrows():
        sig_mark = "✓" if row["significant"] else " "
        print(
            f"    {sig_mark} {row['city_a']} vs {row['city_b']}: "
            f"d={row['cohens_d']:+.3f} ({row['effect_size']}), "
            f"p(adj)={row['p_bonferroni']:.6f}"
        )

    # ---- ANOVA ----
    print(f"\n{'─' * 78}")
    print("  2. ONE-WAY ANOVA: RENT ~ BUNDESLAND")
    print(f"{'─' * 78}")

    if "error" in anova_results:
        print(f"  ERROR: {anova_results['error']}")
    else:
        print(f"  F-statistic: {anova_results['f_statistic']}")
        print(f"  p-value:     {anova_results['p_value']:.6e}")
        print(f"  Significant: {'✓ YES' if anova_results['significant'] else '✗ NO'} (α={ALPHA})")
        print(f"  eta²:        {anova_results['eta_squared']} ({anova_results['eta_sq_interpretation']} effect)")
        if anova_results["levene_p_value"] is not None:
            print(f"  Levene's:    W={anova_results['levene_statistic']}, p={anova_results['levene_p_value']:.4f} "
                  f"({'equal variances' if anova_results['equal_variances'] else 'unequal variances — use Welch ANOVA'})")

        print("\n  State-level summary:")
        print(f"  {'State':<25s} {'n':>6s} {'Mean €/m²':>10s} {'Std':>7s} {'Min':>7s} {'Max':>7s}")
        print(f"  {'─'*25} {'─'*6} {'─'*10} {'─'*7} {'─'*7} {'─'*7}")
        for s in sorted(anova_results["state_summaries"], key=lambda x: x["mean"], reverse=True):
            print(
                f"  {s['state']:<25s} {s['n']:>6,} "
                f"€{s['mean']:>8.2f} €{s['std']:>5.2f} "
                f"€{s['min']:>5.2f} €{s['max']:>5.2f}"
            )

        if anova_results.get("normality_warnings"):
            print("\n  Normality warnings:")
            for w in anova_results["normality_warnings"]:
                print(f"    ⚠ {w}")

    # ---- Tukey HSD ----
    if tukey_results is not None:
        print(f"\n{'─' * 78}")
        print("  3. TUKEY HSD POST-HOC TEST")
        print(f"{'─' * 78}")
        print("  Significant pairwise differences between states:\n")
        # Filter to significant only
        try:
            # Tukey output columns: group1, group2, meandiff, p-adj, lower, upper, reject
            tukey_sig = tukey_results[tukey_results["reject"] == True] if "reject" in tukey_results.columns else tukey_results
            print(tukey_sig.to_string(index=False, max_rows=30))
        except Exception:
            print(tukey_results.to_string(index=False, max_rows=30))

    # ---- Correlations ----
    print(f"\n{'─' * 78}")
    print("  4. CORRELATION ANALYSIS")
    print(f"{'─' * 78}")

    if "error" in correlation_results:
        print(f"  {correlation_results['error']}")
    else:
        for key, result in correlation_results.items():
            name = key.replace("_", " ").title()
            sig = "✓" if result.get("significant") else "✗"
            r = result.get("pearson_r", "N/A")
            p = result.get("pearson_p", "N/A")
            rho = result.get("spearman_rho")
            p_rho = result.get("spearman_p")

            print(f"\n  {name}:")
            print(f"    Pearson r = {r}, p = {p:.6f} [{sig}]")
            if rho is not None:
                print(f"    Spearman ρ = {rho:.4f}, p = {p_rho:.6f}")
            if "interpretation" in result:
                print(f"    → {result['interpretation']}")

    # ---- Effect size summary ----
    print(f"\n{'─' * 78}")
    print("  5. EFFECT SIZE DISTRIBUTION")
    print(f"{'─' * 78}")

    d_values = pairwise_results["cohens_d"].abs()
    categories = {
        "Negligible (< 0.2)": (d_values < 0.2).sum(),
        "Small (0.2–0.5)": ((d_values >= 0.2) & (d_values < 0.5)).sum(),
        "Medium (0.5–0.8)": ((d_values >= 0.5) & (d_values < 0.8)).sum(),
        "Large (0.8–1.2)": ((d_values >= 0.8) & (d_values < 1.2)).sum(),
        "Very large (≥ 1.2)": (d_values >= 1.2).sum(),
    }
    for cat, count in categories.items():
        bar = "█" * int(count / max(1, sum(categories.values())) * 40)
        print(f"  {cat:<22s} {count:>4d}  {bar}")

    print(f"\n{'=' * 78}")
    print("  Statistical analysis complete.")
    print(f"{'=' * 78}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading city data...")
    cities = _load_cities()
    city_rents = _build_flat_rents(cities)
    city_names = {slug: data.get("city", slug) for slug, data in cities.items()}
    df_summary = _build_city_summary(cities)

    print(f"Loaded {len(cities)} cities.")
    print(f"Total rent observations: {sum(len(v) for v in city_rents.values()):,}\n")

    # 1. Pairwise t-tests
    print("Running pairwise t-tests with Bonferroni correction...")
    pairwise_results = run_pairwise_t_tests(city_rents, city_names)
    n_sig = pairwise_results["significant"].sum() if "significant" in pairwise_results.columns else 0
    print(f"  {len(pairwise_results)} comparisons, {n_sig} significant after correction.\n")

    # 2. ANOVA
    print("Running ANOVA across Bundesländer...")
    state_data = _build_state_data(cities)
    anova_results = run_anova_by_state(state_data)
    sig_str = "SIGNIFICANT" if anova_results.get("significant") else "not significant"
    print(f"  F={anova_results.get('f_statistic', 'N/A')}, p={anova_results.get('p_value', 0):.6e} — {sig_str}\n")

    # 3. Tukey HSD
    if HAS_TUKEY:
        print("Running Tukey HSD post-hoc...")
        tukey_results = run_tukey_hsd(state_data)
    else:
        print("Tukey HSD not available (install statsmodels).")
        tukey_results = None

    # 4. Correlation analysis
    print("Running correlation analysis...")
    correlation_results = run_correlation_analysis(df_summary)

    # Print report
    print_statistical_report(
        pairwise_results=pairwise_results,
        anova_results=anova_results,
        tukey_results=tukey_results,
        correlation_results=correlation_results,
        df_summary=df_summary,
        city_rents=city_rents,
    )


if __name__ == "__main__":
    main()
