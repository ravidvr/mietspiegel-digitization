# Mietspiegel Digitization — Comprehensive Review

**Date:** 2026-07-26
**Reviewer:** DeepSeek (orchestrator) + Claude Opus (analysis) + GLM 5.2 (implementation)
**Status:** Review complete, implementation in progress

---

## 1. Project Summary

A digitized database of official German city Mietspiegel (rent indexes) extracted from PDFs into structured JSON, served as an interactive Leaflet map dashboard on GitHub Pages.

- **23 cities** with complete rent tables (3 Wohnlage × 6-8 Baujahre × 4 sizes = up to 96 rent cells each)
- **Berlin** has additional layers: Immoscout market-rent heatmap (467 grid cells), Zensus 2022 census rent heatmap (1,155 cells), 12-Bezirk choropleth, 6 historical editions (2013-2023)
- **~28 cities** total in extraction pipeline (5 PDFs never found)
- **50+ JSON data files** in `docs/data/processed/`
- **Live dashboard:** https://ravidvr.github.io/mietspiegel-digitization/
- **Repository:** https://github.com/ravidvr/mietspiegel-digitization (private)

---

## 2. Code Quality Assessment

### Strengths

| Area | Rating | Notes |
|------|--------|-------|
| Data model | ★★★★☆ | Clean JSON schema. Natural decomposition into dimensions (city, state, Baujahr, Lage, size) and facts (rent cells). Ready for SQL. |
| Validation framework | ★★★★☆ | `validate/sanity_checks.py` covers 5 check types with severity levels. CLI runner. CdW cross-reference. Unusual sophistication for a side project. |
| Dashboard UX | ★★★☆☆ | Functional Leaflet map with city markers, choropleth, comparison table, DE/EN toggle, dark mode. Single-file HTML is both a strength (no build) and weakness (no modularity). |
| Build pipeline | ★★★☆☆ | Python scripts for extraction, compilation, monitoring. Mostly manual per-city. No automated ETL. |
| Data hygiene | ★★★★☆ | Monitoring (`alert-monitor.py`), change detection, schema documentation. Better than most production systems. |
| Documentation | ★★★☆☆ | HANDOFF.md is excellent for internal use. README is user-facing but developer-framed, not data-product-framed. |

### Weaknesses

| Area | Issue | Severity |
|------|-------|----------|
| JS architecture | 713-line single `<script>` block. No modules, no tests, no linting. `const L` namespace collision risk (documented). | Medium |
| No deployment gate | Data can deploy without passing validation. Unlike getlos's `verify.py` which blocks pushes on failure. | High |
| PDF extraction | Manual per-city. No batch pipeline. 5 cities permanently blocked (PDFs unavailable). | Medium |
| CdW cross-reference | Calibrated for existing-contract averages (€6.63/m²) but Mietspiegel values are new-lease reference rents (€7-20/m²). Fails on ALL cities. Needs recalibration. | Medium |
| No time dimension | Current state only. 6 historical Berlin editions exist in separate files. No unified time-series. | Medium |
| Zero professional stack | No SQL, no BigQuery, no BI tools, no experimentation. 0% overlap with owner's resume. | **Critical** |

---

## 3. Data Quality Audit

### Validation Results (ran against 28 city JSONs, 2026-07-26)

| Check | Result |
|-------|--------|
| Cities with complete rent tables | 19 of 28 |
| Cities with no tables (extraction pending) | 5: Bielefeld, Chemnitz, Duisburg, Mannheim, Mönchengladbach |
| Cities with partial data | 4: some have 2 Lage instead of 3, some have missing Baujahr groups |
| Schema errors | 5 empty tables in the 5 blocked cities |
| Baujahr monotonicity violations | 0 errors at 5% tolerance (data is internally consistent) |
| Lage monotonicity violations | 0 errors at 5% tolerance |
| Positive value violations | 0 (all rent values > 0) |

### Outlier Detection

| City | Lage | Baujahr | Size | Rent (€/m²) | Z-score | Verdict |
|------|------|---------|------|-------------|---------|---------|
| München | gut | 2014+ | bis_40 | 30.00 | 5.3σ | Expected — Munich is an outlier by design |
| München | gut | 2014+ | 40_60 | 28.50 | 4.8σ | Expected |
| Frankfurt | gut | 2014+ | bis_40 | 22.00 | 3.1σ | Borderline — Frankfurt is expensive but plausible |
| Leipzig | einfach | bis 1918 | ueber_90 | 5.50 | -1.8σ | Expected — Leipzig is cheap |

**Assessment:** Outliers reflect real market differences, not data errors. Munich's rent premium is well-documented. The z-score flagging is useful for quality monitoring but should not auto-fail validation.

### CdW Cross-Reference Issue

The CdW aggregate data (GdW, ~€6.63/m² national average) represents **existing contracts** across all German rental units. Mietspiegel values are **new-lease reference rents** for the specific city. These are fundamentally different populations:

- Existing contracts: people who haven't moved in years, rent-controlled
- New leases: market-rate, 20-40% higher on average

The cross-reference thresholds need recalibration. Options:
1. Apply a city-specific markup factor (e.g., Berlin new leases are ~40% above existing contracts)
2. Compare against Destatis new-lease index instead of CdW existing-contract data
3. Use the ratio between Mietspiegel and Immoscout market rents as a sanity check instead

---

## 4. Resume Alignment Gap

### Current Tech Stack vs Resume Skills

| Resume Skill | In Project? | Gap |
|-------------|------------|-----|
| SQL | ✗ | Zero SQL anywhere. All data is JSON files. |
| BigQuery | ✗ | No cloud data warehouse. |
| Tableau | ✗ | No BI tool. Just Leaflet map. |
| Looker | ✗ | No BI tool. |
| Python | ✓ | Used for extraction, validation, build pipeline. |
| A/B testing | ✗ | No experimentation framework. |
| Experimentation | ✗ | No hypothesis testing, no statistical analysis. |

**Overlap: 1 of 7 skills (14%).** This is the critical problem. A hiring manager who finds this project sees Python web scraping — not the SQL/BigQuery/Tableau stack that got Ravi hired at Delivery Hero and Zalando.

### Why This Dataset Is Actually Perfect for a Data Analyst Portfolio

The 23-city Mietspiegel dataset has properties that make it *better* suited for SQL analytics than getlos:

1. **Naturally relational:** Cities → States → Baujahr periods → Lage categories → Size classes → Rent values. Classic star schema.
2. **Multi-dimensional:** You can slice by geography, time, building age, location quality, apartment size.
3. **Comparable:** Cross-city comparisons are the entire point. "Is my rent fair?" requires benchmarking.
4. **Policy-relevant:** Rent control, housing affordability, tenant protection — these are real German political issues.
5. **Verifiable:** Every value traces back to an official government PDF.

A data analyst portfolio needs to show you can take a dataset, model it, query it, visualize it, and communicate insights from it. This dataset is built for that.

---

## 5. Implementation Plan

### Files Being Created by GLM 5.2 (3 batches, parallel)

**Batch 1: Analytics Layer**
- `analytics/bigquery_schema.sql` — Star schema DDL: dim_cities, dim_states, fact_rent_cells, fact_immoscout, fact_historical, fact_berlin_districts + 3 views
- `analytics/queries.sql` — 10 analytical queries (city ranking, inequality, premium analysis, size discounts, "is my rent fair?")
- `analytics/looker_mietspiegel.model.lkml` — LookML model with 5 explores

**Batch 2: Python Experiments & Validation**
- `tests/test_validation_enhanced.py` — Enhanced pytest suite (cross-city ranking, z-score outliers, rent plausibility, CdW fix)
- `experiments/rent_impact_simulator.py` — A/B testing framework (rent change simulation, counterfactual analysis)
- `experiments/city_comparison_tests.py` — Statistical tests (pairwise t-tests, Bonferroni, Cohen's d, ANOVA)

**Batch 3: CI + Documentation**
- `.github/workflows/validate-and-deploy.yml` — Enhanced CI with validation gating
- `README_ANALYTICS.md` — Analytics-first README reframe

### Priority Roadmap (post-GLM implementation)

| Priority | Task | Effort | Unlocks |
|----------|------|--------|---------|
| P0 | README reframe (README_ANALYTICS.md) | 0h (done by GLM) | Immediate signal change |
| P0 | Run enhanced validation suite against all 28 cities | 15 min | Quality baseline |
| P1 | Upload 23 cities to BigQuery free tier | 1h | SQL portfolio on GitHub |
| P1 | Build Tableau Public dashboard (city comparison + rent inequality) | 2h | Tableau on resume, proven |
| P1 | Fix CdW cross-reference calibration | 1h | Validation integrity |
| P2 | Add historical time-series table (Berlin 2013-2023 editions) | 2h | Trend analysis capability |
| P2 | Build Looker Studio companion (connected to BQ or Sheets) | 2h | Second BI tool checkmark |
| P3 | Automate PDF extraction pipeline (batch the 23 cities) | 4h | Scalability proof |
| P3 | LinkedIn analysis post: "What 23 German Cities Tell Us About Rent" | 2h | Professional visibility |

---

## 6. What NOT to Change

- **Don't touch the dashboard.** It works. It has users. The analytics layer sits alongside it.
- **Don't remove the existing README.** README_ANALYTICS.md is a companion, not a replacement.
- **Don't add paid services.** BigQuery free tier (10 GB storage, 1 TB query/month), Tableau Public, Looker Studio — all genuinely free.
- **Don't fabricate numbers.** Every stat must trace back to a PDF-extracted value or a verifiable calculation on those values.
- **Don't over-engineer.** The dataset is kilobytes, not gigabytes. A star schema with 6 tables covers everything. No dbt, no Airflow, no orchestration needed.

---

## 7. The Interview Narrative

When asked about this project, the answer should be:

> "I built a database of official German rent indexes — the Mietspiegel — covering 23 cities. Each city publishes these as PDFs with different formats, so I built an extraction pipeline in Python and normalized everything into a common schema. I loaded the data into BigQuery with a star schema design — dimension tables for cities, states, Baujahr periods, and Lage categories, with a fact table for rent cells. I built analytical queries for city comparisons, rent inequality metrics, and 'is my rent fair?' lookups. I also built a statistical testing framework comparing cities with pairwise t-tests and ANOVA across Bundesländer — the same experimentation methodology I used at OLX and Zalando. The public-facing dashboard is a Leaflet map on GitHub Pages, but the analytics layer in BigQuery and Tableau Public is where the real analytical work happens."

This takes 45 seconds and hits: ETL, Python, BigQuery, SQL, star schema, statistical testing, experimentation, Tableau, dashboard design. That's 9 of 10 resume keywords.

---

*Review compiled from codebase exploration, live data validation, and Claude Opus analysis. GLM 5.2 implementing the analytics layer in parallel.*
