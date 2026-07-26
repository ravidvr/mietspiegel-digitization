# Experiments: Rent Impact Simulator

This directory contains the experimental framework and policy counterfactuals for `rent_impact_simulator.py` (490 lines). 

The simulator models the financial and behavioral impact of various rent adjustment policies (e.g., rent caps, subsidizations, percentage increases) on a synthetic or historical population of households.

---

## 1. Hypotheses per Scenario
The simulator evaluates counterfactual policy interventions against a status-quo baseline. 

*   **Scenario A: Strict Rent Cap (e.g., max +2% YoY)**
    *   *Hypothesis:* Implementing a strict rent cap will significantly reduce aggregate tenant housing costs without pushing landlord churn outside of acceptable operational bounds.
*   **Scenario B: Targeted Subsidy (e.g., -10% for low-income brackets)**
    *   *Hypothesis:* Direct rent reductions for the bottom income quartile will result in a proportional decrease in housing cost burden without triggering gentrification displacement.
*   **Scenario C: Aggressive Market Correction (e.g., +8% YoY catch-up)**
    *   *Hypothesis:* Accelerating rent to market rate will increase overall portfolio revenue, but will result in a marginal, statistically insignificant increase in default/eviction rates.

## 2. Unit of Analysis
*   **Primary Unit:** The Household (encoded by `household_id`).
*   **Aggregation Level:** Impacts are calculated at the household level and aggregated to the census-tract or portfolio level for policy-wide evaluation.

## 3. Primary and Secondary Metrics
*   **Primary Metric:** `total_impact_eur`
    *   *Definition:* The absolute financial difference (in Euros) between the counterfactual rent policy and the baseline rent for a given household over the simulated period. 
*   **Secondary Metric:** `affected_households_delta_pct`
    *   *Definition:* The percentage change in the number of households crossing a predefined distress threshold (e.g., rent > 40% of monthly income) compared to the baseline.

## 4. Guardrail Metrics
To ensure policies do not cause unintended catastrophic side effects, the simulator tracks the following guardrails. If these are breached, the policy is rejected regardless of the primary metric's success.
*   `simulated_default_rate`: Must not increase by > 1.0 percentage point.
*   `landlord_exit_rate`: Proportion of landlords opting to sell/remove units from the market; must not exceed 2.0%.
*   `simulation_runtime_sec`: System guardrail to ensure the simulation complexity remains computationally tractable (< 60 seconds).

## 5. Minimum Detectable Effect (MDE) Calculation
Before running counterfactuals, we establish the MDE to understand what magnitude of change the experiment can reliably detect. 

Using the standard formula for a two-sample t-test MDE:
`MDE = (μ_baseline * δ)`

Where the standardized effect size (`δ`) is determined by:
`δ = (Z_α/2 + Z_β) * √(2 * σ² / n)`

*   `Z_α/2` = 1.96 (for 95% confidence)
*   `Z_β` = 0.84 (for 80% power)
*   `σ²` = Variance of historical rent impacts
*   `n` = Sample size of households

*Note: In `rent_impact_simulator.py`, MDE is calculated dynamically based on the input dataset's variance to prevent drawing conclusions from noise.*

## 6. Power Analysis
To avoid Type II errors (false negatives—failing to detect a real policy impact), a power analysis is conducted prior to execution.

*   **Alpha (α):** 0.05
*   **Power (1 - β):** 0.80
*   **Assumed Baseline Variance:** Derived from historical rent distribution logs.
*   **Actionable Output:** If the input dataset's `n` is too small to achieve 80% power for a realistic policy effect (e.g., €15/month impact), the simulator will issue a `PowerWarning` and advise the user to bootstrap the sample or pool regional data.

## 7. Decision Rules
A counterfactual policy is considered viable for real-world A/B rollout *only* if it meets all the following logical gates:

1.  **Significance:** `p-value` of `total_impact_eur` < 0.05.
2.  **Magnitude:** Observed effect size > MDE.
3.  **Directionality:** `total_impact_eur` favors the target demographic (e.g., negative cost for tenants in Scenario B).
4.  **Guardrail Integrity:** No guardrail metrics are breached.

## 8. Limitations (Honest Assessment)
The `rent_impact_simulator.py` is a simplified mathematical model and suffers from the following constraints:
*   **Rational Actor Assumption:** The simulator assumes tenants and landlords react to price changes instantly. It does not model complex behavioral economics (e.g., inertia, emotional attachment to homes).
*   **Macroeconomic Blindness:** It does not natively model inflation rates, sudden unemployment shocks, or interest rate changes on landlord mortgages unless explicitly passed as exogenous time-series variables.
*   **Codebase Scope:** At 490 lines, the simulator is highly optimized for speed and interpretability rather than hyper-local spatial accuracy. It uses normal/log-normal distributions for price generation, which may smooth over localized housing shortages.

---

## 9. Run Command

To execute a specific counterfactual simulation, use the following CLI command:

```bash
python rent_impact_simulator.py \
    --input-data data/historical_tenants.csv \
    --scenario rent_cap_2pct \
    --output-dir experiments/results/ \
    --mde-alpha 0.05 \
    --power 0.80
```

---

## Resume Snippet: A/B Testing Competency

*(To be included on a Senior Data Analyst resume under "Skills" or "Core Competencies")*

**Experimental Design & Causal Inference:** 
*   Designed and evaluated counterfactual A/B testing frameworks, translating ambiguous business policies into testable hypotheses. 
*   Proficient in end-to-end experiment lifecycle: establishing Units of Analysis, defining Primary/Secondary Metrics, and setting strict Guardrail Metrics. 
*   Deep understanding of statistical rigor, regularly performing Power Analysis (80% power, 95% significance) and Minimum Detectable Effect (MDE) calculations to ensure experiment validity and prevent Type I/II errors. 
*   Experienced in applying rigid Decision Rules to experimental readouts and clearly communicating statistical limitations to non-technical stakeholders.