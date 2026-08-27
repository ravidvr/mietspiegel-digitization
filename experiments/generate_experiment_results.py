#!/usr/bin/env python3
"""Regenerate docs/data/processed/experiment_results.json with verifiable math.

MDE formula (two-sample z-test, two-sided):
    MDE = (Z_α/2 + Z_β) · √(2σ² / n)
with α = 0.05 → Z_α/2 = 1.96, power 0.80 → Z_β = 0.84.

σ and n are read from the ACTUAL data file (berlin_immoscout.json), so the
result always matches the dataset. This replaces the previous hand-rolled
value (€0.28/m²) which was computed with the wrong σ.

Usage:
    python3 experiments/generate_experiment_results.py
"""
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
IMMO = REPO / "docs/data/processed/berlin_immoscout.json"
OUT = REPO / "docs/data/processed/experiment_results.json"

ALPHA = 0.05      # significance level
POWER = 0.80      # target power
Z_ALPHA_2 = 1.96  # two-sided
Z_BETA = 0.84     # 80% power


def main():
    immo = json.loads(IMMO.read_text())
    sigma = immo["std"]
    n = immo["clean"]  # 361 cleaned grid cells
    mean = immo["mean"]

    mde = (Z_ALPHA_2 + Z_BETA) * math.sqrt(2 * sigma**2 / n)
    pct = mde / mean * 100

    out = {
        "title": "A/B Testing Framework for Berlin Rent Policy",
        "methodology": (
            "Two-sample z-test, two-sided. MDE = (Z_α/2 + Z_β)·√(2σ²/n) with "
            f"α={ALPHA} (Z={Z_ALPHA_2}), power={POWER} (Z={Z_BETA}), "
            f"σ=€{sigma:.2f}/m² (Immoscout grid std), n={n} cleaned grid cells."
        ),
        "mde": {
            "description": (
                f"Minimum detectable effect for Berlin "
                f"(σ=€{sigma:.2f}/m², n={n} grid cells)"
            ),
            "value_eur_per_sqm": round(mde, 2),
            "pct_of_avg": round(pct, 1),
            "interpretation": (
                f"Can detect a €{mde:.2f}/m² rent change ({pct:.1f}% of Berlin "
                f"avg €{mean:.2f}) with {POWER:.0%} power at α={ALPHA}"
            ),
            "formula": f"MDE = ({Z_ALPHA_2} + {Z_BETA}) × √(2 × {sigma:.2f}² / {n}) = {mde:.2f}",
        },
        "scenarios": [
            {
                "scenario": "A: +5% uniform rent increase",
                "hypothesis": "H₀: No change vs H₁: μ_after > μ_before",
                "rent_delta_per_sqm": round(0.05 * mean, 2),
                "detectable": 0.05 * mean > mde,
                "mde_vs_effect": round((0.05 * mean) / mde, 1),
            },
            {
                "scenario": "B: +10% uniform rent increase",
                "hypothesis": "H₀: No change vs H₁: μ_after > μ_before",
                "rent_delta_per_sqm": round(0.10 * mean, 2),
                "detectable": 0.10 * mean > mde,
                "mde_vs_effect": round((0.10 * mean) / mde, 1),
            },
        ],
        "counterfactuals": [
            {
                "name": "If Berlin rents reached Munich levels",
                "note": "See experiments/rent_impact_simulator.py for the simulation.",
            }
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"wrote {OUT}")
    print(f"MDE = €{mde:.2f}/m² ({pct:.1f}% of avg) | scenarios: "
          f"A={0.05*mean:.2f} ({'detectable' if 0.05*mean > mde else 'below MDE'}), "
          f"B={0.10*mean:.2f} ({'detectable' if 0.10*mean > mde else 'below MDE'})")


if __name__ == "__main__":
    main()
