# Experiments

Four standalone Python scripts. Only the first one feeds the website.

| Script | Question | Output | On the site |
|---|---|---|---|
| [`generate_experiment_results.py`](generate_experiment_results.py) | How big must a city-wide rent rise be before Berlin's data can reliably detect it? | Writes `docs/data/processed/experiment_results.json` | Yes: the Experiments page |
| [`rent_impact_simulator.py`](rent_impact_simulator.py) | What-if rent scenarios over the 23 city Mietspiegel tables | Prints a report | No |
| [`city_comparison_tests.py`](city_comparison_tests.py) | How much do the 23 cities' rent tables differ? | Prints a report | No |
| [`berlin_mietpreisbremse_did.py`](berlin_mietpreisbremse_did.py) | Did Berlin's rent trend change after the June 2015 Mietpreisbremse? | Writes 5 CSVs to `exports/` | Its CSVs are linked from the Data page. It no longer runs ([§4](#4-mietpreisbremse-before-and-after-berlin_mietpreisbremse_didpy)) |

Some code and output still say "A/B testing framework". Nothing here runs an A/B test: there are no randomised groups, no household-level data, and no guardrail metrics or decision rules.

## 1. Minimum detectable effect: `generate_experiment_results.py`

Works out the minimum detectable effect (MDE): the smallest city-wide change in mean asking rent that a two-sided, two-sample z-test comparing Berlin's grid cells before and after a change would detect with 80% power at α = 0.05.

- **Input:** `docs/data/processed/berlin_immoscout.json`, Immoscout24 asking rents from RWI-GEO-REDX PUF v16: n = 361 one-kilometre grid cells after cleaning (467 raw), mean €12.07/m², standard deviation σ = €3.27/m².
- **Formula:** MDE = (z<sub>α/2</sub> + z<sub>β</sub>) · √(2σ²/n) = (1.96 + 0.84) · √(2 · 3.27² / 361) = **€0.68/m²**, 5.6% of the mean.
- **Scenarios:** a uniform +5% rise (€0.60/m²) falls below the MDE (`"detectable": false`); +10% (€1.21/m²) clears it (`true`). `mde_vs_effect` is the rise divided by the MDE (0.9 and 1.8).
- **Output:** `experiment_results.json` with `methodology`, `mde`, `scenarios` and `counterfactuals`. The one counterfactual ("If Berlin rents reached Munich levels") is a name and a pointer to §2; it has no numbers.
- Python standard library only. Re-running it reproduces the committed file byte for byte.

```bash
python3 experiments/generate_experiment_results.py
```

The Experiments page (`docs/experiments.html`) reads this file. Section 7 of the overview (`docs/index.html`) repeats its numbers as typed text, so update that by hand if the output changes.

**Limits.** σ is the spread across grid cells, and the formula treats "before" and "after" as two independent samples of 361 cells. A paired comparison of the same cells over time would usually detect much smaller changes, because each cell is compared with itself.

## 2. What-if rent scenarios: `rent_impact_simulator.py`

A calculator, not a statistical test. It loads every city table, builds one row per city × Wohnlage × building-age band (23 cities and 417 rows on the published tables), and prints up to three scenarios:

- **`percentage`:** raises every table value by `--pct` percent (default 5). For the top 15 cities it prints the change in average €/m² and a euro total per month and per year: the change × 70 m² × estimated rental flats (population × 0.55 ÷ 2).
- **`counterfactual`:** gives every other city the rents of the `--target` city (default `muenchen`), matching rows by identical Wohnlage and building-age labels and skipping rows without a match. Per city it prints the monthly rent of a 70 m² flat before and after, the yearly euro total, and whether the new rent would cross 30% of an assumed €3,500 monthly income where the old one didn't.
- **`distributional`:** the average euro increase from `--pct` by size band, by building age (pre-1950 vs post-2010, picked out by their labels) and by Wohnlage.

**Assumptions typed into the code, not sourced:** 55% of residents rent, 2 people per household, every flat is 70 m², €3,500 monthly income, a 30% rent-burden line. Populations come from each city's JSON.

**Limits.**

- The euro totals multiply table averages by those assumptions, so they are rough orders of magnitude. The website doesn't show them.
- Munich's table is marked `"verification_status": "no_source_document"`, so the default counterfactual compares against a table without a source PDF.
- A uniform percentage rise gives each group a euro increase proportional to its starting rent, so the distributional view restates which groups already pay more.
- It works on the official Mietspiegel tables, while §1 uses Immoscout24 asking rents, so their +5% figures differ (Berlin: €0.45/m² here, €0.60/m² in §1).

```bash
pip install pandas numpy        # both are in requirements.txt
# first time only: copy the city tables (see "Data for §2 and §3" below)
MIETSPIEGEL_ROOT=. python3 experiments/rent_impact_simulator.py               # all three scenarios, +5%
MIETSPIEGEL_ROOT=. python3 experiments/rent_impact_simulator.py --scenario percentage --pct 10
MIETSPIEGEL_ROOT=. python3 experiments/rent_impact_simulator.py --scenario counterfactual --target hamburg
```

### Data for §2 and §3

Both scripts read the city tables from `$MIETSPIEGEL_ROOT/data/processed/`. The default root is `/Users/ruhvee/mietspiegel-digitization` (the author's machine), and `data/processed/` is the build's staging folder, which isn't in git. The published copies are in `docs/data/processed/`, but pointing `MIETSPIEGEL_ROOT` at `docs` fails: that folder also holds `brw_2025_slim.json`, a JSON list the loader can't read (`AttributeError: 'list' object has no attribute 'get'`). From a fresh clone, run this once from the repo root (`data/processed/` is git-ignored):

```bash
mkdir -p data/processed
cp docs/data/processed/*.json data/processed/
rm data/processed/brw_2025_slim.json
```

## 3. City comparison tests: `city_comparison_tests.py`

Treats each filled cell of a city's table (one size band × building age × Wohnlage) as one observation: 1,638 cells across 23 cities on the published tables. It prints:

1. A summary per city: mean and standard deviation of its cells, the gut and einfach means, and their ratio (the "spread").
2. Welch t-tests for all 253 city pairs, Bonferroni-corrected, with Cohen's d.
3. A one-way ANOVA of rent by Bundesland (13 states), with η², Levene's test and Shapiro–Wilk normality warnings.
4. Tukey HSD between states (needs statsmodels).
5. Correlations across cities: population vs mean rent (Pearson and Spearman), population vs gut/einfach spread, and number of building-age bands vs mean rent (Pearson).
6. How the 253 effect sizes are distributed.

**Limits.**

- The cells are published band averages, not individual rents, and the tests treat them as independent samples. Read the p-values as a description of how far apart the tables are, not as evidence about individual flats.
- Only 6 of the 23 tables are marked verified, and 10 have no source document (see `verification_status` in each city JSON).
- statsmodels isn't in `requirements.txt`. Without it the Bonferroni step falls back to multiplying the p-values (same result) and Tukey HSD is skipped.

```bash
pip install pandas numpy scipy statsmodels
# first time only: the same data copy as for §2
MIETSPIEGEL_ROOT=. python3 experiments/city_comparison_tests.py
```

## 4. Mietpreisbremse before and after: `berlin_mietpreisbremse_did.py`

**It no longer runs.** Written in July 2026, it reads a 2013–2023 Berlin series in the old format of `data/historical_mietspiegel.json`. On 27 Aug 2026 (commit `dd99d3e`) that interpolated series was removed because its values couldn't be reproduced from the official tables. The file now holds the 2017–2023 editions extracted from the official PDFs, in a new format, and the script stops with `KeyError: 'cities'`. Its project root is also hard-coded on line 18 (`/Users/ruhvee/mietspiegel-digitization`, with no `MIETSPIEGEL_ROOT` override).

What it did, for reference:

- **Trend comparison:** despite "DiD" in the name, there's no comparison group, so it isn't a difference-in-differences analysis. It compares Berlin's own trend before and after the law (June 2015), using straight lines between the end editions of each period (2013→2015 and 2015→2023), and extends the 2013–2015 line to 2023 as the counterfactual. There's no significance test.
- **Rent burden:** the average Mietspiegel 2024 rent for 40, 60 and 90 m² flats against 30% of an assumed €2,450 net monthly household income, cold and with €2.50/m² added for utilities.
- **Districts:** the cheapest and the priciest Bezirk, from `docs/data/processed/berlin_districts_comparison.json`.
- **Market vs official:** Immoscout24 asking rents vs the Mietspiegel average vs Zensus 2022 rents.
- **Exports:** five CSVs in `exports/`: `berlin_mietspiegel_2024.csv`, `berlin_rent_cells.csv`, `berlin_districts.csv`, `berlin_historical_trend.csv` and `berlin_mietpreisbremse_analysis.csv`.

The CSVs in `exports/` are from its last run (29 Jul 2026), so `berlin_historical_trend.csv` and `berlin_mietpreisbremse_analysis.csv` still hold the removed series. The Data page links all five. It uses only the Python standard library.
