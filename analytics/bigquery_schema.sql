-- =============================================================================
-- Mietspiegel Digitization — BigQuery Star Schema DDL
-- =============================================================================
-- German rent index (Mietspiegel) analytics warehouse.
-- Sources: per-city JSON extracts at data/processed/<city>.json
--           23+ cities with official Mietspiegel tables
--           Berlin: Immoscout24 REDX grid, Zensus 2022, district aggregates,
--           historical editions (2013–2023)
--
-- Design: star schema with a central fact_rent_cells table, city/state
-- dimensions, and supplementary fact tables for Berlin-specific layers.
-- Partitioning by city_slug for multi-tenant isolation; clustering on
-- dimensional attributes for query performance.
-- =============================================================================

-- =============================================================================
-- DIMENSION: dim_states — 16 German Bundesländer
-- =============================================================================
CREATE OR REPLACE TABLE `mietspiegel.dim_states` (
  state_id         STRING    NOT NULL,  -- ISO 3166-2:DE code (DE-BE, DE-BY, ...)
  state_name       STRING    NOT NULL,  -- Full Bundesland name
  capital          STRING,              -- State capital
  region           STRING,              -- Macro-region: Nord, Ost, Süd, West
  population_2022  INT64,               -- Destatis 2022 census population
  area_km2         FLOAT64,             -- Land area
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY state_id
CLUSTER BY region
OPTIONS (
  description = 'German Bundesländer lookup — 16 states'
);

-- =============================================================================
-- DIMENSION: dim_cities — city metadata (slowly-changing Type 1)
-- =============================================================================
CREATE OR REPLACE TABLE `mietspiegel.dim_cities` (
  city_slug            STRING    NOT NULL,  -- URL-safe (berlin, frankfurt-am-main)
  city_name            STRING    NOT NULL,  -- Display name (Berlin, Frankfurt am Main)
  state_id             STRING    NOT NULL,  -- FK → dim_states
  lat                  FLOAT64,             -- Centroid latitude
  lng                  FLOAT64,             -- Centroid longitude
  population           INT64,               -- Municipal population (approx.)
  mietspiegel_year     INT64,               -- Most recent Mietspiegel edition year
  mietspiegel_type     STRING,              -- qualifiziert, einfach
  lage_categories      ARRAY<STRING>,       -- [einfach, mittel, gut]
  baujahr_groups       ARRAY<STRING>,       -- e.g. ["bis 1918", "1919-1949", ...]
  size_categories      ARRAY<STRING>,       -- e.g. ["bis 40 m²", "40-60 m²", ...]
  source_url           STRING,              -- Official Mietspiegel URL
  has_rent_data        BOOL      DEFAULT TRUE,  -- FALSE for cities with empty tables[]
  created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY city_slug
CLUSTER BY state_id, mietspiegel_year
OPTIONS (
  description = 'City metadata — one row per city, Type-1 SCD'
);

-- =============================================================================
-- FACT: fact_rent_cells — atomic rent cell (grain: city × lage × baujahr × size)
-- =============================================================================
-- Unpivoted from JSON: {bis_40: 8.03, 40_60: 7.68, ...} → one row per size class.
-- This is the core analytical table. ~23 cities × 3 lage × 8 baujahr × 4 size
-- ≈ 2,200 rows (growing as new cities/years are added).
-- =============================================================================
CREATE OR REPLACE TABLE `mietspiegel.fact_rent_cells` (
  rent_cell_id       STRING    NOT NULL,  -- Surrogate: <city_slug>/<lage>/<baujahr>/<size>
  city_slug          STRING    NOT NULL,  -- FK → dim_cities
  lage               STRING    NOT NULL,  -- einfach | mittel | gut
  baujahr            STRING    NOT NULL,  -- e.g. "bis 1918", "2011-2024", "aktuell"
  size_class         STRING    NOT NULL,  -- bis_40 | 40_60 | 60_90 | ueber_90
  size_label         STRING,              -- Display label: "bis 40 m²", "40-60 m²", etc.
  rent_euro_per_sqm  FLOAT64   NOT NULL,  -- Net cold rent (€/m²)
  mietspiegel_year   INT64     NOT NULL,  -- Edition year (denormalised for convenience)
  -- Derived baujahr metadata
  baujahr_start      INT64,               -- Parsed start year (NULL for "aktuell" or "bis 1918")
  baujahr_end        INT64,               -- Parsed end year (NULL for "aktuell" or "2014+")
  is_aktuell         BOOL      DEFAULT FALSE,  -- TRUE for single-value "aktuell" rows
  is_prewar          BOOL      DEFAULT FALSE,  -- TRUE when baujahr_end < 1945
  is_postwar         BOOL      DEFAULT FALSE,  -- TRUE when baujahr_start >= 1945 AND baujahr_start < 1991
  is_reunification   BOOL      DEFAULT FALSE,  -- TRUE when baujahr_start >= 1991 AND baujahr_start < 2011
  is_newbuild        BOOL      DEFAULT FALSE,  -- TRUE when baujahr_start >= 2011
  created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY city_slug
CLUSTER BY lage, baujahr, size_class
OPTIONS (
  description = 'Core fact: one row per rent cell (city × Lage × Baujahr × Size)'
);

-- =============================================================================
-- FACT: fact_immoscout — Berlin market rent grid cells (RWI-GEO-REDX PUF v16)
-- =============================================================================
CREATE OR REPLACE TABLE `mietspiegel.fact_immoscout` (
  grid_id            STRING    NOT NULL,  -- REDX grid ID (e.g. "4613_3263")
  lat                FLOAT64,
  lng                FLOAT64,
  plz                STRING,              -- Postal code
  pi_2008            FLOAT64,             -- Hedonic price index 2008
  n_2008             INT64,               -- Observation count 2008
  pi_2013            FLOAT64,
  n_2013             INT64,
  pi_2018            FLOAT64,
  n_2018             INT64,
  pi_2023            FLOAT64,
  n_2023             INT64,
  pi_2024            FLOAT64,
  n_2024             INT64,
  pi_2025            FLOAT64,
  n_2025             INT64,
  change_pct         FLOAT64,             -- % change (earliest→latest available)
  city_slug          STRING    DEFAULT 'berlin',
  created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY RANGE_BUCKET(FARM_FINGERPRINT(grid_id), 100)
CLUSTER BY plz
OPTIONS (
  description = 'Berlin Immoscout24 market rent grid cells (1km²) from RWI-GEO-REDX PUF v16'
);

-- =============================================================================
-- FACT: fact_historical_trends — year-over-year Mietspiegel values
-- =============================================================================
CREATE OR REPLACE TABLE `mietspiegel.fact_historical_trends` (
  city_slug          STRING    NOT NULL,  -- FK → dim_cities
  year               INT64     NOT NULL,  -- Edition year (2013, 2015, 2017, ...)
  lage               STRING    NOT NULL,  -- einfach | mittel | gut
  base_rent_per_sqm  FLOAT64   NOT NULL,  -- Base rent for reference cohort (1965-1974, 60-90m²)
  baujahr_cohort     STRING,              -- Reference Baujahr used (typically "1965-1974")
  source             STRING,              -- e.g. "Berliner Mietspiegel 2013"
  created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY city_slug
CLUSTER BY year, lage
OPTIONS (
  description = 'Historical Mietspiegel editions with base rent per Wohnlage'
);

-- =============================================================================
-- FACT: fact_berlin_districts — Bezirk-level Wohnlage aggregates
-- =============================================================================
CREATE OR REPLACE TABLE `mietspiegel.fact_berlin_districts` (
  bezirk_name        STRING    NOT NULL,  -- Charlottenburg-Wilmersdorf, ...
  wohnlage_einfach   INT64     DEFAULT 0, -- Address count: einfache Wohnlage
  wohnlage_mittel    INT64     DEFAULT 0, -- Address count: mittlere Wohnlage
  wohnlage_gut       INT64     DEFAULT 0, -- Address count: gute Wohnlage
  total_addresses    INT64     NOT NULL,  -- Total address points in Bezirk
  einfach_pct        FLOAT64,             -- % einfache Wohnlage
  mittel_pct         FLOAT64,             -- % mittlere Wohnlage
  gut_pct            FLOAT64,             -- % gute Wohnlage
  estimated_rent     FLOAT64,             -- Estimated avg rent (from district geo join)
  created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY bezirk_name
CLUSTER BY bezirk_name
OPTIONS (
  description = 'Berlin 12 Bezirke — Wohnlage distribution from 400K WFS address points'
);

-- =============================================================================
-- VIEW: vw_city_ranking — ranked by median rent (gut Lage, mid-size 60-90 m²)
-- =============================================================================
CREATE OR REPLACE VIEW `mietspiegel.vw_city_ranking` AS
SELECT
  RANK() OVER (ORDER BY f.rent_euro_per_sqm DESC) AS rank,
  f.city_slug,
  c.city_name,
  c.state_id,
  c.population,
  f.lage,
  f.baujahr,
  f.size_class,
  f.rent_euro_per_sqm,
  c.mietspiegel_year,
  c.mietspiegel_type
FROM `mietspiegel.fact_rent_cells` f
JOIN `mietspiegel.dim_cities` c USING (city_slug)
WHERE f.lage = 'gut'
  AND f.size_class = '60_90'
  AND f.baujahr = (
    -- Pick the most recent (largest start year) baujahr for each city
    -- to get the "newest comparable build" for gut Lage
    SELECT baujahr FROM `mietspiegel.fact_rent_cells` f2
    WHERE f2.city_slug = f.city_slug AND f2.lage = 'gut' AND f2.size_class = '60_90'
    ORDER BY f2.baujahr_start DESC NULLS LAST LIMIT 1
  );

-- =============================================================================
-- VIEW: vw_rent_inequality — gut/einfach ratio per city
-- =============================================================================
CREATE OR REPLACE VIEW `mietspiegel.vw_rent_inequality` AS
WITH gut_avg AS (
  SELECT city_slug, AVG(rent_euro_per_sqm) AS avg_gut
  FROM `mietspiegel.fact_rent_cells`
  WHERE lage = 'gut'
  GROUP BY city_slug
),
einfach_avg AS (
  SELECT city_slug, AVG(rent_euro_per_sqm) AS avg_einfach
  FROM `mietspiegel.fact_rent_cells`
  WHERE lage = 'einfach'
  GROUP BY city_slug
)
SELECT
  c.city_slug,
  c.city_name,
  c.state_id,
  c.population,
  ROUND(e.avg_einfach, 2) AS avg_rent_einfach,
  ROUND(g.avg_gut, 2) AS avg_rent_gut,
  ROUND(g.avg_gut - e.avg_einfach, 2) AS rent_spread_abs,
  ROUND(SAFE_DIVIDE(g.avg_gut, e.avg_einfach), 3) AS gut_to_einfach_ratio,
  ROUND(SAFE_DIVIDE(g.avg_gut - e.avg_einfach, e.avg_einfach) * 100, 1) AS premium_pct
FROM `mietspiegel.dim_cities` c
LEFT JOIN gut_avg g USING (city_slug)
LEFT JOIN einfach_avg e USING (city_slug)
WHERE g.avg_gut IS NOT NULL
  AND e.avg_einfach IS NOT NULL
ORDER BY gut_to_einfach_ratio DESC;

-- =============================================================================
-- VIEW: vw_size_discount — % decrease in rent/m² as apartment size increases
-- =============================================================================
CREATE OR REPLACE VIEW `mietspiegel.vw_size_discount` AS
WITH size_avg AS (
  SELECT
    city_slug,
    lage,
    size_class,
    AVG(rent_euro_per_sqm) AS avg_rent
  FROM `mietspiegel.fact_rent_cells`
  WHERE size_class IN ('bis_40', '40_60', '60_90', 'ueber_90')
  GROUP BY city_slug, lage, size_class
),
pivoted AS (
  SELECT
    city_slug,
    lage,
    MAX(CASE WHEN size_class = 'bis_40' THEN avg_rent END) AS rent_bis_40,
    MAX(CASE WHEN size_class = '40_60' THEN avg_rent END) AS rent_40_60,
    MAX(CASE WHEN size_class = '60_90' THEN avg_rent END) AS rent_60_90,
    MAX(CASE WHEN size_class = 'ueber_90' THEN avg_rent END) AS rent_ueber_90
  FROM size_avg
  GROUP BY city_slug, lage
)
SELECT
  p.city_slug,
  c.city_name,
  c.state_id,
  p.lage,
  ROUND(p.rent_bis_40, 2) AS rent_bis_40,
  ROUND(p.rent_40_60, 2) AS rent_40_60,
  ROUND(p.rent_60_90, 2) AS rent_60_90,
  ROUND(p.rent_ueber_90, 2) AS rent_ueber_90,
  ROUND(SAFE_DIVIDE(p.rent_bis_40 - p.rent_ueber_90, p.rent_bis_40) * 100, 1) AS total_size_discount_pct,
  ROUND(SAFE_DIVIDE(p.rent_40_60 - p.rent_bis_40, p.rent_bis_40) * 100, 1) AS step_1_discount_pct,
  ROUND(SAFE_DIVIDE(p.rent_60_90 - p.rent_40_60, p.rent_40_60) * 100, 1) AS step_2_discount_pct,
  ROUND(SAFE_DIVIDE(p.rent_ueber_90 - p.rent_60_90, p.rent_60_90) * 100, 1) AS step_3_discount_pct
FROM pivoted p
JOIN `mietspiegel.dim_cities` c USING (city_slug)
WHERE p.rent_bis_40 IS NOT NULL
ORDER BY total_size_discount_pct DESC;
