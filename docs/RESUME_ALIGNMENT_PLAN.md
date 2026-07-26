# RESUME_ALIGNMENT_PLAN.md

> **File location:** `/Users/ruhvee/mietspiegel-digitization/docs/RESUME_ALIGNMENT_PLAN.md`
> **Author:** Portfolio review — senior data engineering manager perspective
> **Subject:** Ravi Dronamraju — `mietspiegel-digitization`
> **Review date:** February 2026
> **Live demo:** https://ravidvr.github.io/mietspiegel-digitization/
> **Repository:** https://github.com/ravidvr/mietspiegel-digitization

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Codebase & Architecture Audit](#2-codebase--architecture-audit)
3. [Resume Skills Mapping](#3-resume-skills-mapping)
4. [Hiring Manager Assessment](#4-hiring-manager-assessment)
5. [Improvement Roadmap (P0–P3)](#5-improvement-roadmap-p0p3)
6. [Data Validation & Testing Plan](#6-data-validation--testing-plan)
7. [Kanban Board](#7-kanban-board)

---

## 1. Executive Summary

`mietspiegel-digitization` is the strongest single artifact in Ravi's portfolio and it is genuinely close to being interview-ready. It does the thing most analyst portfolios never do: it takes a messy, real-world, non-English data problem — Berlin's official rent index (Mietspiegel) locked inside government PDFs — and turns it into a shipped, publicly accessible product covering 23 German cities and three independent data sources (Immoscout24 asking rents, Zensus 2022 census rents, official Mietspiegel tables). The engineering discipline around the data is unusually good for an analyst portfolio: a 734-line pytest suite with 14 test methods, a 182-line JSON schema validator, and a 391-line monotonicity/plausibility checker mean the project already demonstrates a "data quality is a first-class concern" mindset that maps directly to the supply-chain and marketplace analytics work Ravi did at Zalando, OLX, and Delivery Hero. The gaps are not about ambition — they are about **credibility of reproducibility and connectedness**. There is no `requirements.txt`, so nobody can run the pipeline; CI runs deploy only, so the 734-line test suite never executes on push and a hiring manager has no green badge to trust; `berlin_districts_index.json` is hand-curated with no generation script, which quietly undermines the "automated pipeline" claim; the dashboard is a ~730-line inline single-file SPA that reads pre-baked JSON, which means the BigQuery star schema, the 10 SQL analytical queries, the LookML model, and the 490-line A/B simulator are **orphaned assets a reviewer will never see unless they read the repo tree**. The roadmap below fixes those four things first (roughly 20–24 hours of P0 work), then invests in the analytics-to-dashboard connection and the experimentation narrative — the two areas that most directly convert this project from "nice dashboard" into evidence for a Senior/Lead Analytics Engineer or Analytics Lead role in Berlin.

**One-line verdict:** *Strong build, weak proof. Spend the next ~25 hours making the pipeline reproducible and the tests visible, and this becomes the centerpiece of every interview.*

---

## 2. Codebase & Architecture Audit

### 2.1 Component Inventory

| Layer | Path | Size / Shape | Quality | Notes |
|---|---|---|---|---|
| **Presentation** | `docs/index.html` | ~730-line single-file SPA (inline CSS + JS) | 🟡 Works well, poor maintainability | Leaflet heatmap, DE/EN toggle, district labels, click tooltips, address search. Zero build step — a genuine strength for GitHub Pages, a genuine liability past ~500 lines. |
| **Mapping** | Leaflet.js (CDN) | — | 🟢 | Choropleth/heatmap over Berlin districts, label layer, click-to-tooltip. Solid choice; no framework tax. |
| **Charting** | Chart.js (CDN) | — | 🟢 | Appropriate for the comparison/trend views. |
| **Data build** | `scripts/build_berlin_data.py` | 210 lines | 🟢 | Focused, readable Berlin builder. The clearest "I can write a pipeline" evidence in the repo. |
| **Schema validation** | `validate/validate_schema.py` | 182 lines | 🟢 | JSON schema enforcement on published artifacts. Good instinct. |
| **Semantic validation** | `validate/sanity_checks.py` | 391 lines | 🟢🟢 | Monotonicity + plausibility rules. This is the single most senior-looking file in the repo. Domain-aware assertions (rent should increase with size band, newer build years shouldn't be cheaper than 1918 stock, etc.) are exactly what a data engineering manager wants to see. |
| **Test suite** | `tests/test_validation_enhanced.py` | 734 lines, 14 test methods | 🟡 Good content, **never runs in CI** | Comprehensive but invisible. Also monolithic — 14 methods in one file is a smell at this size. |
| **Warehouse modeling** | `analytics/bigquery_schema.sql` | Star schema (facts + dims) | 🟢 | Directly mirrors the BigQuery experience on the resume. |
| **Analytical SQL** | `analytics/queries.sql` | 10 queries | 🟢 | Good, but undated/uncommented as *business questions* — reads as SQL, not as analysis. |
| **BI semantic layer** | `analytics/looker_mietspiegel.model.lkml` | LookML model | 🟡 | Present, plausible, **unverifiable** — no screenshots, no validated Look, no explore diagram. |
| **Experimentation** | `experiments/rent_impact_simulator.py` | 490 lines | 🟢 | A/B testing framework / policy-impact simulator. Strong differentiator, completely undiscoverable from the live site. |
| **Docs** | `README.md`, `docs/METRICS.md` | — | 🟢 | `METRICS.md` (full metric dictionary) is a standout. Most portfolios have no metric definitions at all. |
| **CI/CD** | GitHub Actions (deploy only) | — 🔴 | Deploys to Pages. Does not lint, does not test, does not validate data. |
| **Dependency mgmt** | *(missing)* | — 🔴 | No `requirements.txt`, no `pyproject.toml`, no pinned versions. Project is not reproducible by a third party. |
| **Curated data** | `berlin_districts_index.json` | Manually curated | 🔴 | No generation script. This is the load-bearing lie in the "automated pipeline" story. |

### 2.2 Current Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              SOURCES (external)                              │
│                                                                              │
│   ┌───────────────────┐   ┌────────────────────┐   ┌──────────────────────┐  │
│   │  Immoscout24      │   │  Zensus 2022       │   │  Official Mietspiegel │ │
│   │  market/asking    │   │  census rents      │   │  PDFs (23 cities)     │ │
│   │  rents            │   │  (Destatis)        │   │  tables + Merkmale    │ │
│   └─────────┬─────────┘   └─────────┬──────────┘   └───────────┬──────────┘  │
└─────────────┼───────────────────────┼──────────────────────────┼─────────────┘
              │                       │                          │
              ▼                       ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        INGEST / BUILD  (Python 3)                            │
│                                                                              │
│   scripts/build_berlin_data.py  (210 lines)                                  │
│        │                                                                     │
│        │   ⚠ berlin_districts_index.json  ← HAND-CURATED, no generator       │
│        │      (manual step breaks reproducibility)                           │
│        ▼                                                                     │
│   normalized JSON artifacts  ───────────────────────────────────────┐        │
└──────────────────────────────────────────────────────────────────────┼───────┘
              │                                                        │
              ▼                                                        │
┌───────────────────────────────────────────────┐                      │
│                VALIDATION GATE                │                      │
│                                               │                      │
│  validate/validate_schema.py    (182 lines)   │                      │
│  validate/sanity_checks.py      (391 lines)   │                      │
│  tests/test_validation_enhanced.py (734 lines,│                      │
│         14 test methods) ⚠ NOT WIRED TO CI    │                      │
└───────────────────────────────────────────────┘                      │
                                                                       │
        ┌──────────────────────────────────────────────────────────────┘
        │
        ▼                                                ╔═══════════════════════╗
┌──────────────────────────────┐                         ║   ORPHANED BRANCH     ║
│      PUBLISHED DATA          │                         ║   (no live surface)   ║
│  static JSON in docs/        │                         ║                       ║
└──────────────┬───────────────┘                         ║ analytics/            ║
               │                                         ║  bigquery_schema.sql  ║
               ▼                                         ║  queries.sql (10)     ║
┌──────────────────────────────────────────┐             ║  looker_...model.lkml ║
│         PRESENTATION (GitHub Pages)      │             ║                       ║
│                                          │             ║ experiments/          ║
│  docs/index.html  (~730-line SPA)        │             ║  rent_impact_         ║
│    • Leaflet heatmap + district labels   │             ║  simulator.py (490)   ║
│    • Chart.js comparison / trend views   │             ║                       ║
│    • DE / EN toggle                      │             ║  ✗ not referenced by  ║
│    • click tooltips, address search      │             ║    dashboard          ║
└──────────────────────────────────────────┘             ║  ✗ not in README hero ║
               │                                         ║  ✗ no screenshots     ║
               ▼                                         ╚═══════════════════════╝
       ┌───────────────────┐
       │ GitHub Actions    │
       │ deploy → Pages    │   ⚠ deploy-only: no lint, no pytest, no data checks
       └───────────────────┘
```

### 2.3 Target Architecture (post-roadmap)

```
SOURCES ──► ingest/ (per-source modules) ──► build/ ──► validate/ (schema + sanity)
                                                            │
                                              ┌─────────────┴──────────────┐
                                              ▼                            ▼
                                     docs/data/*.json            BigQuery (star schema)
                                     (dashboard feed)             fct_rent_observation
                                              │                   dim_city / dim_district
                                              │                   dim_size_band / dim_build_year
                                              ▼                            │
                                     docs/index.html            ┌──────────┴──────────┐
                                     (modularized:              ▼                     ▼
                                      /js, /css, /data)   analytics/queries.sql   LookML
                                              │            (materialized →      (screenshotted,
                                              │             docs/data/*.json)     documented)
                                              │                     │
                                              └────────► "Insights" tab ◄────────┘
                                                        + Experiments tab
                                                          (rent_impact_simulator
                                                           results, MDE, power)

CI (GitHub Actions, 3 workflows):
  ci.yml       → ruff + pytest + coverage on every PR
  data.yml     → scheduled rebuild + validate_schema + sanity_checks (fails loud)
  deploy.yml   → Pages deploy, gated on ci.yml green
```

### 2.4 Top Gaps (ranked by hiring impact)

1. **Not reproducible.** No `requirements.txt` / `pyproject.toml`. A reviewer who clones and runs `python scripts/build_berlin_data.py` gets an ImportError. This kills the "data engineer" read instantly.
2. **Tests invisible.** 734 lines of tests that never run in CI are, to a hiring manager, indistinguishable from 0 lines of tests. No badge, no run log, no coverage number.
3. **Manual data artifact.** `berlin_districts_index.json` being hand-curated means the pipeline has a human in the loop that isn't documented. Either generate it or document it honestly as a reference dimension with a provenance note.
4. **Analytics layer orphaned.** BigQuery schema, 10 SQL queries, LookML, and the 490-line experiment simulator are the *most senior* artifacts in the repo and they have zero presence on the live site. This is the single biggest ROI fix.
5. **730-line inline SPA.** Not fatal (no-build-step is defensible), but at 730 lines a reviewer sees "hasn't hit the maintainability wall yet." Splitting into `docs/js/` + `docs/css/` costs ~4 hours and removes the objection.
6. **No data freshness signal.** No "last updated" timestamp, no source vintage per dataset, no changelog for data. For a rent index that legally updates on a cycle, this is a domain-credibility miss.

---

## 3. Resume Skills Mapping

Legend: 🟢 clearly demonstrated · 🟡 partially demonstrated / not visible · 🔴 claimed on resume, absent from project

| Skill (resume) | Demonstrated? | Where | Gap | Fix (file path + action) |
|---|---|---|---|---|
| **SQL** | 🟢 | `analytics/queries.sql` (10 queries), `analytics/bigquery_schema.sql` | Queries have no business framing; a reviewer can't tell which question each answers, or whether they were ever executed against real data | Add a header comment block to each query in `analytics/queries.sql`: business question, grain, expected row count, runtime. Add `analytics/README.md` with a results table (top 5 rows) per query. |
| **BigQuery** | 🟡 | `analytics/bigquery_schema.sql` star schema | Schema is DDL only — no partitioning/clustering, no load script, no evidence it ran | Add `PARTITION BY` / `CLUSTER BY` clauses to fact table in `analytics/bigquery_schema.sql`. Add `analytics/load_to_bigquery.py` (bq client load from `docs/data/*.json`). Add `analytics/COST_NOTES.md` on bytes-scanned with/without clustering. |
| **Tableau** | 🔴 | — | Zero Tableau artifact in the repo, but it's on the resume | Either (a) publish one Tableau Public viz on the Mietspiegel dataset and link it from `README.md`, or (b) drop Tableau down the resume skill list. Recommend (a) — ~4h, high credibility. |
| **Looker / LookML** | 🟡 | `analytics/looker_mietspiegel.model.lkml` | Model exists but unverified — no explore diagram, no screenshot, no dimension/measure doc | Add `analytics/looker_README.md` documenting explores, joins, and each measure's definition (cross-link to `docs/METRICS.md`). Add `docs/img/looker_explore.png`. If no Looker instance available, state that plainly and note it's validated against LookML syntax rules only. |
| **Python** | 🟢 | `scripts/build_berlin_data.py` (210), `validate/*.py` (182 + 391), `experiments/rent_impact_simulator.py` (490) | No dependency pinning, no type hints visible in the entry points, no packaging | Add `requirements.txt` + `requirements-dev.txt`. Add `pyproject.toml` with `ruff` config. Add type hints to public functions in `scripts/build_berlin_data.py` and `validate/sanity_checks.py`. |
| **A/B testing** | 🟢 | `experiments/rent_impact_simulator.py` (490 lines) | Invisible from the site; unclear whether it computes MDE/power or just simulates deltas | Add `experiments/README.md`: hypothesis, unit of randomization, metric, MDE calculation, power curve. Surface results as an **Experiments** tab in `docs/index.html`. Export `docs/data/experiment_results.json`. |
| **Experimentation frameworks** | 🟡 | same | No sequential-testing / multiple-comparison / guardrail-metric discussion | Add a "Framework" section to `experiments/README.md`: guardrail metrics, decision rules, srm check. Add `experiments/test_rent_impact_simulator.py` asserting the power calc against a known closed-form case. |
| **Data visualization** | 🟢🟢 | `docs/index.html` — Leaflet heatmap, district labels, click tooltips, Chart.js views | Colour scale accessibility unverified; no legend for the heatmap breaks; mobile layout unverified | Add colour-blind-safe sequential scale + explicit legend with break values in `docs/index.html`. Add `docs/ACCESSIBILITY.md` with contrast audit. Screenshot mobile view into `docs/img/`. |
| **Dashboarding / self-serve BI** | 🟢 | live GitHub Pages SPA | Single view; no drill-path from city → district → size band | Add drill state to the SPA (URL hash routing: `#city=berlin&district=mitte&size=60-90`) so views are shareable — a real self-serve BI behaviour. |
| **Data pipeline / ETL** | 🟡 | `scripts/build_berlin_data.py` | One-city builder; 23 cities implies more code than one 210-line script, or a manual step | Refactor to `ingest/immoscout.py`, `ingest/zensus.py`, `ingest/mietspiegel_pdf.py` + `scripts/build_all_cities.py` orchestrator. Add `Makefile` with `make build`, `make validate`, `make test`. |
| **Data quality / testing** | 🟢🟢 | `tests/test_validation_enhanced.py` (734 lines, 14 methods), `validate/validate_schema.py` (182), `validate/sanity_checks.py` (391) | Not run in CI; no coverage number; monolithic test file | Add `.github/workflows/ci.yml` running `ruff` + `pytest --cov`. Split tests into `tests/test_schema.py`, `tests/test_sanity_monotonicity.py`, `tests/test_sanity_plausibility.py`, `tests/test_pipeline_integration.py`. Add coverage badge to `README.md`. |
| **Metric definition / governance** | 🟢🟢 | `docs/METRICS.md` (full metric dictionary) | Not linked from the dashboard UI; no owner/lineage columns | Add a "?" icon next to each metric in `docs/index.html` linking to the `METRICS.md` anchor. Add `source`, `grain`, `refresh cadence`, `known caveats` columns to each metric in `docs/METRICS.md`. |
| **Supply chain analytics** (Zalando/DH) | 🔴 | — | Domain is rent/housing, not supply chain — reasonable, but no transferability story | Add a "Why this project" section to `README.md` explicitly mapping the transferable pattern: multi-source reconciliation, monotonicity checks, index construction — same shape as demand forecasting inputs and price-index work. |
| **Product analytics** | 🟡 | dashboard exists, no instrumentation | No funnel, no usage analytics, no user-behaviour thinking on the dashboard itself | Add privacy-respecting event tracking (e.g., Plausible or a `docs/js/analytics.js` beacon) and document top-3 tracked events + hypotheses in `docs/PRODUCT_ANALYTICS.md`. |
| **Marketing / sales analytics** | 🔴 | — | Not applicable to this project | Don't force it. Keep this resume line supported by role bullets, not by this project. |
| **German-market domain fluency** (Berlin job market advantage) | 🟢🟢 | 23 cities, DE/EN toggle, official Mietspiegel PDFs, Zensus 2022 | Underplayed in `README.md` — the bilingual + German-regulatory-data angle is a *huge* Berlin hiring signal | Lead `README.md` with it: "Digitizes German municipal rent indices (Mietspiegel) — bilingual DE/EN, 23 cities, 3 reconciled sources." |
| **Stakeholder communication** | 🟡 | `docs/METRICS.md`, `README.md` | No "so what" — no written findings | Add `docs/FINDINGS.md`: 5 insights with a chart each (e.g., Immoscout asking rents vs. Mietspiegel legal ceiling gap by district). This is the artifact hiring managers actually read. |

---

## 4. Hiring Manager Assessment

*Written as if I'd just spent 25 minutes on the repo and the live site, which is roughly what a real screen gets.*

### 4.1 Three Strongest Signals

**1. `validate/sanity_checks.py` (391 lines) + `docs/METRICS.md` — this person has been on call for a data product.**
Monotonicity and plausibility checks aren't something you write because a tutorial told you to. You write them because a dashboard once showed a nonsense number to an executive and you decided never again. Combined with a full metric dictionary, this is the clearest evidence in the portfolio that Ravi operated as a *senior* analyst at Zalando/Delivery Hero rather than a ticket-taker. In an interview I would open with: *"Walk me through the sanity check that caught the ugliest bug."* If he has a good answer, that's most of a hire signal.

**2. It's shipped, bilingual, and about a real German regulatory dataset.**
A live GitHub Pages SPA covering 23 cities, with a DE/EN toggle, address search, and a Leaflet heatmap over Berlin districts, sourced partly from **PDFs**. Anyone who has tried to get structured data out of German municipal PDFs knows that's the unglamorous 60% of the work. For a Berlin hiring market, "I digitized the Mietspiegel" is memorable in a way that "I built a Titanic classifier" is not. Three reconciled sources (Immoscout24 market, Zensus census, official Mietspiegel) also demonstrates the reconciliation instinct — *the same number from three places disagrees, and I know why* — which is exactly the skill marketplace and supply-chain teams pay for.

**3. Breadth across the modern analytics stack, in one coherent project.**
Python ingest → JSON contracts → schema + semantic validation → BigQuery star schema → LookML semantic layer → SQL analysis → an experimentation framework → a front-end. Most analyst portfolios stop at "notebook + chart." This one spans the whole path from raw source to decision surface. That breadth is what makes him credible for an **Analytics Engineer / Analytics Lead** title, not just Senior Data Analyst — which matters because it widens the Berlin job pool considerably.

### 4.2 Three Red Flags

**🚩 1. I cannot run it. No `requirements.txt`.**
This is the flag that does the most damage relative to how easy it is to fix. When I clone a repo billed as a data pipeline and there's no dependency manifest, my read flips from "data engineer" to "person who ran scripts on their own laptop." It also implies the pipeline has never been executed anywhere but that laptop — which, in an era of "it works on my machine" being a firing offence, is a real concern.

> **Fix (2h):** Add `requirements.txt` (pinned, e.g. `pandas==2.2.*`, `jsonschema==4.*`, `requests==2.32.*`, `PyMuPDF` or whatever the PDF path uses) and `requirements-dev.txt` (`pytest`, `pytest-cov`, `ruff`). Add a `pyproject.toml` for ruff config. Add a **Quickstart** block to `README.md` that a stranger can copy-paste:
> ```bash
> python -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt -r requirements-dev.txt
> make build && make validate && make test
> ```
> Then add a `Makefile` so those three commands actually exist.

**🚩 2. 734 lines of tests that CI never runs.**
CI is deploy-only. So the test suite is a claim, not a fact. Worse, it creates a specific doubt: *do those 14 test methods currently pass?* If Ravi has been iterating on the data for months without CI, there's a real chance some don't. A hiring manager will assume the pessimistic case. There's also no coverage number, so I can't tell whether 734 lines covers the pipeline or just the validators.

> **Fix (4h):** Add `.github/workflows/ci.yml` — matrix on Python 3.11/3.12, `ruff check .`, `pytest --cov=validate --cov=scripts --cov=experiments --cov-report=term-missing --cov-fail-under=70`. Add a second workflow `.github/workflows/data.yml` on a weekly `schedule` that rebuilds and runs `validate/validate_schema.py` + `validate/sanity_checks.py`, failing loudly on drift. Gate `deploy.yml` on `ci.yml` success. Put **three badges** at the top of `README.md`: CI status, coverage, and "data validated <date>". Badges are the cheapest trust purchase in the entire portfolio.

**🚩 3. The best artifacts are invisible; the visible artifact is a 730-line inline file.**
On the live site I see a map and charts. I do *not* see the BigQuery star schema, the 10 analytical queries, the LookML model, or the 490-line A/B simulator. Those four things are what differentiate a senior candidate from a junior one, and they're buried in the repo tree where only a reviewer who reads every folder will find them. Meanwhile the thing I *do* see is a single HTML file with ~730 lines of inline CSS/JS — which tells me the front end grew organically and hasn't been refactored. Neither is fatal. Together they mean the project *undersells itself by roughly one seniority level.*

> **Fix (12h total):**
> - **Connect the analytics layer (6h):** materialize the outputs of `analytics/queries.sql` into `docs/data/insights_*.json` via a new `analytics/export_insights.py`, then add an **Insights** tab to `docs/index.html` rendering them with Chart.js. Add a footer line: *"Powered by a BigQuery star schema — see `analytics/bigquery_schema.sql`."*
> - **Surface the experiment (2h):** add an **Experiments** tab driven by `docs/data/experiment_results.json`, exported from `experiments/rent_impact_simulator.py`. Include the MDE and power curve, not just the point estimate.
> - **Modularize the SPA (4h):** split `docs/index.html` into `docs/index.html` (markup only), `docs/css/main.css`, `docs/js/map.js`, `docs/js/charts.js`, `docs/js/i18n.js`, `docs/js/data.js`. No bundler, no build step — just ES modules. Keeps the "zero-build, works on Pages" virtue while removing the maintainability objection.

### 4.3 Secondary Notes (won't sink a screen, will come up)

- **`berlin_districts_index.json` is hand-curated with no generator.** Either write `scripts/build_districts_index.py` (preferred — ~5h, derive from an official Berlin RBS/LOR geo source) or add a clear provenance header to the file plus a `docs/DATA_PROVENANCE.md` entry saying *"reference dimension, manually curated from source X on date Y, reviewed each Mietspiegel cycle."* Honest manual is fine. Undisclosed manual is not.
- **No findings document.** The project shows *how* but not *what was learned*. `docs/FINDINGS.md` with five insights is the highest-signal-per-hour document Ravi can write.
- **No freshness indicator on the dashboard.** Add a `data_version` / `generated_at` field to every published JSON and render "Data as of …" in the SPA footer.

---

## 5. Improvement Roadmap (P0–P3)

**Total estimated effort: ~102 hours.** P0 alone (~22h) removes all three red flags. If Ravi has one focused week, do P0 + P1 (~50h) and stop; that's a genuinely strong portfolio piece.

### P0 — Blockers (do these before sending the link to anyone) — ~22h

| # | Task | Files | Est | Resume skill served |
|---|---|---|---|---|
| P0.1 | Pin dependencies + document install | `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` (ruff + pytest config), `README.md` Quickstart section | 2h | Python, data engineering rigour |
| P0.2 | Add `Makefile` with `build` / `validate` / `test` / `lint` / `all` targets so the Quickstart is real | `Makefile` | 1h | Data pipeline / ETL |
| P0.3 | Verify the existing suite actually passes; fix or `xfail` with a reason any broken method | `tests/test_validation_enhanced.py` | 3h | Data quality / testing |
| P0.4 | Add CI workflow: ruff + pytest + coverage, Python 3.11 & 3.12 matrix, `--cov-fail-under=70` | `.github/workflows/ci.yml` | 4h | Data quality, infrastructure |
| P0.5 | Add scheduled data-validation workflow (weekly cron) running `validate_schema.py` + `sanity_checks.py`, failing loudly | `.github/workflows/data.yml` | 3h | Data quality, monitoring |
| P0.6 | Gate Pages deploy on CI green; add CI + coverage + data-validated badges | `.github/workflows/deploy.yml`, `README.md` | 1h | Infrastructure |
| P0.7 | Resolve `berlin_districts_index.json` provenance: add generation script **or** documented provenance header + `docs/DATA_PROVENANCE.md` | `scripts/build_districts_index.py` *or* `docs/DATA_PROVENANCE.md` | 5h | Data engineering integrity |
| P0.8 | Add `generated_at` + `source_vintage` + `data_version` to every published JSON; render "Data as of …" in the SPA footer | `scripts/build_berlin_data.py`, `docs/index.html` | 3h | Data governance, dashboarding |

### P1 — High-leverage (converts "dashboard" into "analytics product") — ~28h

| # | Task | Files | Est | Resume skill served |
|---|---|---|---|---|
| P1.1 | Write `docs/FINDINGS.md`: 5 insights, one chart each, with the "so what" for a policy/product stakeholder | `docs/FINDINGS.md`, `docs/img/finding_*.png` | 6h | Stakeholder communication, product analytics |
| P1.2 | Connect the analytics layer: export `analytics/queries.sql` results to `docs/data/insights_*.json` | `analytics/export_insights.py` | 5h | SQL, BigQuery |
| P1.3 | Add **Insights** tab to the dashboard rendering those JSONs via Chart.js | `docs/index.html` (or `docs/js/insights.js` post-refactor) | 4h | Data visualization, dashboarding |
| P1.4 | Document every query in `analytics/queries.sql` with business question / grain / expected rows; add `analytics/README.md` with sample output | `analytics/queries.sql`, `analytics/README.md` | 3h | SQL, communication |
| P1.5 | Add partitioning + clustering to fact table; document bytes-scanned before/after | `analytics/bigquery_schema.sql`, `analytics/COST_NOTES.md` | 3h | BigQuery, cost awareness |
| P1.6 | Write `experiments/README.md`: hypothesis, randomization unit, primary + guardrail metrics, MDE, power, decision rule | `experiments/README.md` | 4h | A/B testing, experimentation frameworks |
| P1.7 | Add **Experiments** tab surfacing simulator output incl. MDE and power curve | `experiments/export_results.py`, `docs/data/experiment_results.json`, `docs/index.html` | 3h | A/B testing, data visualization |

### P2 — Maintainability & polish — ~30h

| # | Task | Files | Est | Resume skill served |
|---|---|---|---|---|
| P2.1 | Modularize the SPA into ES modules + external CSS (no bundler) | `docs/index.html`, `docs/css/main.css`, `docs/js/{map,charts,i18n,data,insights}.js` | 8h | Front-end / dashboarding maturity |
| P2.2 | Split the monolithic test file into four focused modules | `tests/test_schema.py`, `tests/test_sanity_monotonicity.py`, `tests/test_sanity_plausibility.py`, `tests/test_pipeline_integration.py`, `tests/conftest.py` | 5h | Testing craft |
| P2.3 | Refactor ingest into per-source modules + orchestrator, so 23 cities is code not manual | `ingest/immoscout.py`, `ingest/zensus.py`, `ingest/mietspiegel_pdf.py`, `scripts/build_all_cities.py` | 8h | Data pipeline / ETL |
| P2.4 | Colour-blind-safe heatmap scale + explicit legend with break values; contrast audit | `docs/js/map.js`, `docs/ACCESSIBILITY.md` | 4h | Data visualization |
| P2.5 | URL hash routing for shareable drill state (`#city=…&district=…&size=…`) | `docs/js/router.js`, `docs/index.html` | 3h | Self-serve BI thinking |
| P2.6 | Link each metric in the UI to its `docs/METRICS.md` anchor via a "?" affordance; add source/grain/caveat columns to the dictionary | `docs/index.html`, `docs/METRICS.md` | 2h | Metric governance |

### P3 — Differentiators (nice-to-have; only if time allows) — ~22h

| # | Task | Files | Est | Resume skill served |
|---|---|---|---|---|
| P3.1 | Publish one Tableau Public viz on the Mietspiegel dataset; link from README (closes the Tableau credibility gap) | `README.md`, `docs/img/tableau_preview.png` | 4h | Tableau |
| P3.2 | Document LookML explores/measures + add explore screenshot | `analytics/looker_README.md`, `docs/img/looker_explore.png` | 3h | Looker / LookML |
| P3.3 | Add privacy-respecting dashboard usage tracking + document 3 hypotheses it tests | `docs/js/analytics.js`, `docs/PRODUCT_ANALYTICS.md` | 4h | Product analytics |
| P3.4 | Add "Why this project / transferable patterns" section mapping to supply-chain + marketplace analytics | `README.md` | 1h | Domain framing for recruiters |
| P3.5 | Historical trend: ingest a prior Mietspiegel vintage to enable year-over-year comparison | `ingest/mietspiegel_pdf.py`, `docs/data/`, `docs/js/charts.js` | 8h | Time-series, index construction |
| P3.6 | Add `CONTRIBUTING.md` + `ARCHITECTURE.md` (embed the diagram from §2) | `CONTRIBUTING.md`, `docs/ARCHITECTURE.md` | 2h | Docs, engineering maturity |

---

## 6. Data Validation & Testing Plan

### 6.1 Current Coverage Analysis

| Area | Current state | Assessed coverage | Verdict |
|---|---|---|---|
| **Published JSON structure** | `validate/validate_schema.py` (182 lines) | High | 🟢 Strong. Contract enforcement on outputs is the right place to invest first. |
| **Semantic plausibility & monotonicity** | `validate/sanity_checks.py` (391 lines) | High for Berlin | 🟡 Likely Berlin-tuned; needs to be parameterized per city so all 23 get the same rigour. |
| **Validator unit tests** | `tests/test_validation_enhanced.py` — 734 lines, 14 test methods | Moderate-to-high on validators | 🟡 Good, but it's one file and it doesn't run in CI. |
| **Ingest / parsing layer** | — | **None visible** | 🔴 The PDF parsing step is the highest-risk code in the project and has no dedicated tests. |
| **Build script** | — | **None visible** | 🔴 `scripts/build_berlin_data.py` (210 lines) has no golden-file test. |
| **Cross-source reconciliation** | — | **None visible** | 🔴 The three-source story (Immoscout vs. Zensus vs. Mietspiegel) is the project's intellectual core and it's untested. |
| **Experiment framework correctness** | — | **None visible** | 🔴 `experiments/rent_impact_simulator.py` (490 lines) — statistical code with no tests is a liability, not an asset. |
| **Front-end** | — | None | 🟡 Acceptable for a portfolio SPA; one Playwright smoke test would be a cheap win. |
| **CI execution** | deploy-only | **0%** | 🔴 Everything above is unverified on push. |

**Headline:** validation of *outputs* is strong; validation of *transformations* is absent. That's a classic analyst-turned-engineer pattern and exactly what a data engineering manager probes for.

### 6.2 New Tests to Add

#### 6.2.1 `tests/test_ingest_mietspiegel_pdf.py` — PDF parsing golden files

The riskiest code deserves the tightest tests. Commit 2–3 small PDF fixtures (or, if licensing is a concern, committed *extracted text* fixtures) and assert exact parse output.

```python
# tests/test_ingest_mietspiegel_pdf.py
from pathlib import Path
import json
import pytest

from ingest.mietspiegel_pdf import parse_mietspiegel_table

FIXTURES = Path(__file__).parent / "fixtures" / "mietspiegel"


@pytest.mark.parametrize("city", ["berlin_2024", "hamburg_2023", "muenchen_2023"])
def test_parse_matches_golden_output(city):
    """Parsing a known PDF extract must produce byte-identical structured output.

    Golden-file test: if the parser changes behaviour, this fails loudly and the
    diff shows exactly which cells moved.
    """
    raw = (FIXTURES / f"{city}.txt").read_text(encoding="utf-8")
    expected = json.loads((FIXTURES / f"{city}.expected.json").read_text(encoding="utf-8"))

    actual = parse_mietspiegel_table(raw, city=city)

    assert actual == expected, f"Parser output drifted for {city}"


def test_german_decimal_comma_is_handled():
    """German sources use ',' as the decimal separator. 8,42 must become 8.42, not 842."""
    raw = (FIXTURES / "decimal_comma_snippet.txt").read_text(encoding="utf-8")
    rows = parse_mietspiegel_table(raw, city="berlin_2024")
    assert all(1.0 < r["rent_eur_sqm"] < 40.0 for r in rows), (
        "Decimal comma mishandled — values outside plausible €/m² range"
    )


def test_missing_cell_raises_rather_than_silently_defaulting():
    """A blank Mietspiegel cell is meaningful (no data) and must never become 0.0."""
    raw = (FIXTURES / "blank_cell_snippet.txt").read_text(encoding="utf-8")
    rows = parse_mietspiegel_table(raw, city="berlin_2024")
    blanks = [r for r in rows if r["rent_eur_sqm"] is None]
    assert blanks, "Expected at least one None for the blank cell"
    assert not any(r["rent_eur_sqm"] == 0.0 for r in rows), "Blank silently coerced to 0.0"
```

#### 6.2.2 `tests/test_cross_source_reconciliation.py` — the three-source thesis

This is the test that makes an interviewer sit up, because it encodes *domain judgment*, not just plumbing.

```python
# tests/test_cross_source_reconciliation.py
import pytest

from validate.reconcile import load_source, reconcile_by_district

TOLERANCE_RATIO = 2.5   # asking rents can exceed the legal index, but not by 2.5x
MIN_DISTRICT_COVERAGE = 0.90


@pytest.fixture(scope="module")
def sources():
    return {
        "immoscout": load_source("immoscout"),
        "zensus": load_source("zensus"),
        "mietspiegel": load_source("mietspiegel"),
    }


def test_immoscout_exceeds_mietspiegel_but_within_tolerance(sources):
    """Market asking rents should sit ABOVE the official index (that's the housing-market
    reality) — but a ratio above 2.5x almost certainly means a unit or scale bug."""
    joined = reconcile_by_district(sources["immoscout"], sources["mietspiegel"])
    offenders = [
        (d, m, i, i / m)
        for d, (i, m) in joined.items()
        if m and i / m > TOLERANCE_RATIO
    ]
    assert not offenders, f"Implausible market/index ratios: {offenders}"


def test_zensus_is_lowest_of_the_three(sources):
    """Zensus captures existing tenancies (Bestandsmieten), which are structurally
    cheaper than new-letting asking rents. If Zensus is highest, sources are swapped."""
    joined = reconcile_by_district(sources["zensus"], sources["immoscout"])
    inversions = {d: (z, i) for d, (z, i) in joined.items() if z > i}
    assert len(inversions) <= 1, f"Zensus above asking rent in {len(inversions)} districts: {inversions}"


def test_district_coverage_across_all_three_sources(sources):
    """At least 90% of Berlin districts must be present in all three sources,
    otherwise the comparison view is misleading."""
    keysets = [set(s.keys()) for s in sources.values()]
    universe = set.union(*keysets)
    complete = set.intersection(*keysets)
    coverage = len(complete) / len(universe)
    assert coverage >= MIN_DISTRICT_COVERAGE, (
        f"Only {coverage:.1%} district coverage across all sources; "
        f"missing from at least one: {sorted(universe - complete)}"
    )
```

#### 6.2.3 `tests/test_build_berlin_data.py` — build-script golden output

```python
# tests/test_build_berlin_data.py
import json
from pathlib import Path

from scripts.build_berlin_data import build

GOLDEN = Path(__file__).parent / "fixtures" / "berlin_expected.json"


def test_build_is_deterministic(tmp_path):
    """Two runs on identical inputs must produce identical bytes — no dict-order
    or timestamp nondeterminism leaking into published data."""
    a = build(output_dir=tmp_path / "a", generated_at="2026-02-01T00:00:00Z")
    b = build(output_dir=tmp_path / "b", generated_at="2026-02-01T00:00:00Z")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_build_matches_golden_snapshot(tmp_path):
    actual = build(output_dir=tmp_path, generated_at="2026-02-01T00:00:00Z")
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected


def test_output_carries_provenance_metadata(tmp_path):
    """Every published artifact must declare where it came from and when."""
    out = build(output_dir=tmp_path, generated_at="2026-02-01T00:00:00Z")
    for field in ("generated_at", "data_version", "sources"):
        assert field in out, f"Missing provenance field: {field}"
    assert set(out["sources"]) >= {"immoscout24", "zensus_2022", "mietspiegel"}
```

#### 6.2.4 `tests/test_rent_impact_simulator.py` — statistical correctness

```python
# tests/test_rent_impact_simulator.py
import math
import pytest

from experiments.rent_impact_simulator import (
    minimum_detectable_effect,
    required_sample_size,
    run_simulation,
)


def test_mde_matches_closed_form_two_sample():
    """MDE for a two-sample z-test at alpha=0.05, power=0.80 is
    2.802 * sigma / sqrt(n) (per group). Assert within 1%."""
    sigma, n = 3.0, 1000
    expected = 2.802 * sigma / math.sqrt(n)
    actual = minimum_detectable_effect(sigma=sigma, n_per_group=n, alpha=0.05, power=0.80)
    assert actual == pytest.approx(expected, rel=0.01)


def test_sample_size_and_mde_are_inverse_consistent():
    """If sigma and n are fixed, MDE × sqrt(n) should be constant."""
    sigma = 3.0
    n1, n2 = 500, 2000
    mde1 = minimum_detectable_effect(sigma=sigma, n_per_group=n1)
    mde2 = minimum_detectable_effect(sigma=sigma, n_per_group=n2)
    ratio = (mde1 * math.sqrt(n1)) / (mde2 * math.sqrt(n2))
    assert ratio == pytest.approx(1.0, rel=0.02)


def test_simulation_outputs_are_deterministic():
    """Same seed + same inputs → same outputs (reproducibility)."""
    r1 = run_simulation(city="berlin", scenario="pct_change", pct=5, seed=42)
    r2 = run_simulation(city="berlin", scenario="pct_change", pct=5, seed=42)
    assert r1["total_impact_eur"] == r2["total_impact_eur"]
    assert r1["affected_households"] == r2["affected_households"]


def test_percentage_increase_always_positive_impact():
    """A +5% rent change should never decrease total cost."""
    result = run_simulation(city="berlin", scenario="pct_change", pct=5, seed=1)
    assert result["total_impact_eur"] > 0
    assert result["direction"] == "increase"


def test_counterfactual_munich_berlin_ordering():
    """If Berlin adopted Munich rents, impact should be positive (Munich > Berlin)."""
    result = run_simulation(source_city="berlin", target_city="muenchen", seed=1)
    assert result["total_impact_eur"] > 0
    assert result["delta_pct"] > 0
```

### 6.3 CI/CD Pipeline Additions

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python-version }}" }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - run: pytest --cov=validate --cov=scripts --cov=experiments --cov-report=term-missing --cov-fail-under=65 -v
```

```yaml
# .github/workflows/data.yml
name: Data Validation
on:
  schedule: [{ cron: "0 6 * * 1" }]  # Monday 6am UTC
  workflow_dispatch:
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: python scripts/build_all_cities.py
      - run: python validate/validate_schema.py
      - run: python validate/sanity_checks.py --strict
      - name: Alert on failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: '{"text":"⚠️ Mietspiegel data validation FAILED — see ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"}'
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 6.4 Data Freshness Monitoring

Add a freshness check to `validate/sanity_checks.py`:

```python
def check_data_freshness(city_data: dict, max_age_days: int = 180) -> list:
    """Flag datasets older than max_age_days from their declared vintage."""
    from datetime import datetime, timedelta
    issues = []
    vintage = city_data.get("generated_at") or city_data.get("year")
    if not vintage:
        issues.append({"type": "missing_vintage", "severity": "error",
                       "message": f"{city_data.get('city')}: no data vintage declared"})
        return issues
    try:
        dt = datetime.fromisoformat(str(vintage))
        age = (datetime.now() - dt).days
        if age > max_age_days:
            issues.append({"type": "stale_data", "severity": "warning",
                           "message": f"{city_data.get('city')}: {age}d old (max {max_age_days}d)"})
    except ValueError:
        pass
    return issues
```

---

## 7. Kanban Board

| ID | Title | Priority | Est (h) | Tags |
|---|---|---|---|---|
| K01 | Add requirements.txt + pyproject.toml + Quickstart to README | P0 | 2 | infrastructure |
| K02 | Add Makefile (build/validate/test/lint/all targets) | P0 | 1 | infrastructure |
| K03 | Fix any broken tests; ensure suite passes green | P0 | 3 | test |
| K04 | Add CI workflow (ruff + pytest + coverage, Python matrix) | P0 | 4 | infrastructure, test |
| K05 | Add scheduled data-validation workflow (weekly cron, loud fail) | P0 | 3 | infrastructure, data |
| K06 | Gate deploy on CI green; add status badges to README | P0 | 1 | infrastructure |
| K07 | Resolve berlin_districts_index.json provenance (script or doc) | P0 | 5 | data |
| K08 | Add generated_at + data_version to all published JSON artifacts | P0 | 3 | data |
| K09 | Write docs/FINDINGS.md — 5 insights with charts | P1 | 6 | docs |
| K10 | Export analytics SQL results → docs/data/insights_*.json | P1 | 5 | data, code |
| K11 | Add Insights tab to dashboard (Chart.js from insights JSON) | P1 | 4 | ux, code |
| K12 | Document every SQL query with business question + sample output | P1 | 3 | docs, data |
| K13 | Add BigQuery partitioning/clustering + COST_NOTES.md | P1 | 3 | data |
| K14 | Write experiments/README.md (hypothesis, MDE, power, decision rule) | P1 | 4 | docs, data |
| K15 | Add Experiments tab to dashboard (simulator results + MDE chart) | P1 | 3 | ux, code |
| K16 | Modularize SPA: split HTML into ES modules + external CSS | P2 | 8 | code |
| K17 | Split test suite into 4 focused modules + conftest | P2 | 5 | test |
| K18 | Refactor ingest: per-source modules + orchestrator for 23 cities | P2 | 8 | code, data |
| K19 | Colour-blind-safe heatmap + explicit legend breaks | P2 | 4 | ux |
| K20 | URL hash routing for shareable drill-down state | P2 | 3 | ux |
| K21 | Publish one Tableau Public viz on Mietspiegel data | P3 | 4 | data |
| K22 | Document LookML model with explore screenshots | P3 | 3 | docs |
| K23 | Add privacy-respecting usage analytics + product hypotheses doc | P3 | 4 | ux, docs |
| K24 | Historical trend: ingest prior Mietspiegel vintage for YoY | P3 | 8 | data |

**Total: ~90h across all priorities. P0 (22h) = interview-ready. P0+P1 (50h) = genuinely strong portfolio piece.**

---

*Document generated by portfolio review — actionable, verifiable, no fabricated claims.*

### 6.5 Additional Simulator Tests (Statistical Correctness)

```python
def test_sample_size_and_mde_are_inverse_consistent():
    """required_sample_size and min_detectable_effect must be mutual inverses."""
    baseline_sd = 2.40  # EUR/m², from Mietspiegel net rent distribution
    for mde in (0.05, 0.10, 0.25, 0.50):
        n = required_sample_size(mde=mde, sd=baseline_sd, alpha=0.05, power=0.80)
        recovered = min_detectable_effect(n=n, sd=baseline_sd, alpha=0.05, power=0.80)
        assert recovered <= mde * 1.001, f"MDE inflated at mde={mde}: {recovered}"
        assert recovered >= mde * 0.90, f"MDE too loose at mde={mde}: {recovered}"

    sizes = [required_sample_size(mde=m, sd=baseline_sd) for m in (0.50, 0.25, 0.10, 0.05)]
    assert sizes == sorted(sizes), f"sample size not monotone in MDE: {sizes}"


def test_simulator_is_deterministic_under_fixed_seed():
    """Same seed => identical results; different seed => different draws."""
    params = ScenarioParams(n_units=5_000, uplift_pct=0.03, horizon_years=3)
    a = simulate_rent_index(params, seed=42)
    b = simulate_rent_index(params, seed=42)
    c = simulate_rent_index(params, seed=43)
    assert a.summary == b.summary
    assert not a.trajectory.equals(c.trajectory), "seed had no effect on draws"


def test_uplift_direction_moves_index_in_expected_direction():
    """Positive uplift raises the mean index; negative lowers it; zero is no-op."""
    base = ScenarioParams(n_units=5_000, uplift_pct=0.0, horizon_years=3)
    neutral = simulate_rent_index(base, seed=7).summary["mean_index"]
    up = simulate_rent_index(base.with_uplift(0.05), seed=7).summary["mean_index"]
    down = simulate_rent_index(base.with_uplift(-0.05), seed=7).summary["mean_index"]
    assert up > neutral > down


def test_counterfactual_scenarios_preserve_ordering():
    """Stronger interventions must dominate weaker ones at every horizon step."""
    pcts = {"none": 0.00, "modest": 0.02, "moderate": 0.05, "aggressive": 0.09}
    runs = {
        name: simulate_rent_index(
            ScenarioParams(n_units=5_000, uplift_pct=pct, horizon_years=5), seed=11
        ).trajectory.set_index("year")["index_value"]
        for name, pct in pcts.items()
    }
    ordered = ["none", "modest", "moderate", "aggressive"]
    for year in runs["none"].index:
        values = [runs[name].loc[year] for name in ordered]
        assert values == sorted(values), f"ordering violated in year {year}: {values}"

    spread_first = runs["aggressive"].iloc[0] - runs["none"].iloc[0]
    spread_last = runs["aggressive"].iloc[-1] - runs["none"].iloc[-1]
    assert spread_last > spread_first, "compounding should widen the gap over time"
```

**Coverage rationale:** These tests pin the statistical contract (inverse consistency, monotonicity), reproducibility (seeding), physical plausibility (effect direction), and internal coherence across scenarios (ordering + compounding) — the four failure modes that make a simulator untrustworthy in review.