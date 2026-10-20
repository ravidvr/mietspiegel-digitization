-- Berlin Rent Analytics — BigQuery Schema
-- For deployment to BigQuery Sandbox (free tier: 10GB storage, 1TB query/mo)
-- Dataset: berlin_rent
-- Run: bq mk --dataset berlin_rent
-- Then: bq load --source_format=CSV berlin_rent.<table> gs://...

-- ═══════════════════════════════════════════════════════════
-- DIMENSION: Mietspiegel table (official 2024 rent index, averaged into 4 size bands)
-- ═══════════════════════════════════════════════════════════
CREATE OR REPLACE TABLE berlin_rent.mietspiegel_2024 (
    lage         STRING  NOT NULL,   -- einfach | mittel | gut
    baujahr      STRING  NOT NULL,   -- bis 1918 | 1919-1949 | ...
    bis_40       FLOAT64,            -- €/m² net cold
    _40_60       FLOAT64,
    _60_90       FLOAT64,
    ueber_90     FLOAT64
);

-- ═══════════════════════════════════════════════════════════
-- FACT: Rent cells (unpivoted — one row per cell)
-- ═══════════════════════════════════════════════════════════
CREATE OR REPLACE TABLE berlin_rent.rent_cells (
    city          STRING  NOT NULL,   -- Berlin
    lage          STRING  NOT NULL,   -- einfach | mittel | gut
    baujahr       STRING  NOT NULL,   -- building age group
    size_class    STRING  NOT NULL,   -- under 40 | 40–60 | 60–90 | over 90
    size_m2       INT64   NOT NULL,   -- midpoint size (30, 50, 75, 100)
    rent_per_sqm  FLOAT64 NOT NULL,   -- €/m² net cold
    rent_total    FLOAT64 NOT NULL,   -- total monthly rent (rent_per_sqm × size_m2)
    year          INT64   NOT NULL    -- Mietspiegel edition year
)
PARTITION BY year
CLUSTER BY lage, baujahr;

-- ═══════════════════════════════════════════════════════════
-- DIMENSION: Districts (Bezirke) with Wohnlage distribution
-- ═══════════════════════════════════════════════════════════
CREATE OR REPLACE TABLE berlin_rent.districts (
    district            STRING  NOT NULL,   -- Bezirk name
    avg_rent_per_sqm    FLOAT64 NOT NULL,   -- weighted avg rent
    einfach_pct         FLOAT64,            -- % addresses in einfache Lage
    mittel_pct          FLOAT64,            -- % addresses in mittlere Lage
    gut_pct             FLOAT64,            -- % addresses in gute Lage
    total_addresses     INT64,              -- address points counted
    gap_vs_avg_pct      FLOAT64             -- % deviation from Berlin avg
);

-- ═══════════════════════════════════════════════════════════
-- VIEW: Affordable apartments (30% income rule)
-- ═══════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW berlin_rent.vw_affordable AS
SELECT
    lage,
    baujahr,
    size_class,
    size_m2,
    rent_per_sqm,
    rent_total,
    rent_total / 2450.0 * 100 AS burden_pct,     -- 30% of €2,450 median income
    CASE WHEN rent_total <= 735 THEN 'YES'        -- €735 = 30% threshold
         ELSE 'NO' END AS affordable_30pct
FROM berlin_rent.rent_cells
WHERE year = 2024
ORDER BY rent_total;

-- ═══════════════════════════════════════════════════════════
-- VIEW: District affordability (60m² apartment)
-- ═══════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW berlin_rent.vw_district_affordability AS
SELECT
    district,
    avg_rent_per_sqm,
    avg_rent_per_sqm * 60 AS rent_60m2,
    (avg_rent_per_sqm * 60) / 2450.0 * 100 AS burden_60m2_pct,
    einfach_pct,
    gut_pct,
    gap_vs_avg_pct
FROM berlin_rent.districts
ORDER BY avg_rent_per_sqm;

-- ═══════════════════════════════════════════════════════════
-- ANALYTICAL QUERIES
-- ═══════════════════════════════════════════════════════════

-- Q1: What's the cheapest 60m² apartment in Berlin?
-- SELECT * FROM berlin_rent.rent_cells 
-- WHERE size_m2 = 50 AND lage = 'einfach'
-- ORDER BY rent_total LIMIT 5;

-- Q2: Which districts are affordable on median income?
-- SELECT * FROM berlin_rent.vw_district_affordability
-- WHERE burden_60m2_pct <= 30;
