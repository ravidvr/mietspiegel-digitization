-- =============================================================================
-- Mietspiegel Digitization — Analytical Queries
-- =============================================================================
-- 10 production-quality SQL queries against the star schema defined in
-- bigquery_schema.sql. All queries use real German Mietspiegel data from
-- 23+ cities with official rent index tables.
--
-- Parameters marked with @param are intended as BigQuery parameterized queries
-- or Looker templated filters. Replace with literals for ad-hoc exploration.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- QUERY 1: City ranking by median rent (gut Lage, mid-size apartment)
-- -----------------------------------------------------------------------------
-- Business question: Which city has the highest official rent for
-- a "gute Wohnlage" (best location) mid-size apartment built recently?
-- This is the most common benchmark for comparing city rental markets.
-- -----------------------------------------------------------------------------

WITH newest_baujahr AS (
  SELECT
    city_slug,
    baujahr,
    ROW_NUMBER() OVER (
      PARTITION BY city_slug
      ORDER BY baujahr_start DESC NULLS LAST
    ) AS rn
  FROM `mietspiegel.fact_rent_cells`
  WHERE lage = 'gut'
    AND size_class = '60_90'
    AND baujahr_start IS NOT NULL
)
SELECT
  RANK() OVER (ORDER BY f.rent_euro_per_sqm DESC) AS rank,
  c.city_name,
  c.state_id,
  c.population,
  c.mietspiegel_year,
  f.rent_euro_per_sqm AS rent_eur_per_sqm,
  f.baujahr AS newest_build_cohort,
  ROUND(f.rent_euro_per_sqm - AVG(f.rent_euro_per_sqm) OVER (), 2) AS deviation_from_mean
FROM `mietspiegel.fact_rent_cells` f
JOIN `mietspiegel.dim_cities` c USING (city_slug)
JOIN newest_baujahr n
  ON n.city_slug = f.city_slug
 AND n.baujahr = f.baujahr
 AND n.rn = 1
WHERE f.lage = 'gut'
  AND f.size_class = '60_90'
ORDER BY rank;


-- -----------------------------------------------------------------------------
-- QUERY 2: Rent inequality — ratio of gut/einfach within each city
-- -----------------------------------------------------------------------------
-- Business question: How much more expensive is "gute Lage" vs "einfache Lage"
-- within the same city? High ratios indicate steep rent segregation.
-- -----------------------------------------------------------------------------

WITH city_rent_by_lage AS (
  SELECT
    city_slug,
    lage,
    AVG(rent_euro_per_sqm) AS avg_rent,
    PERCENTILE_CONT(rent_euro_per_sqm, 0.5) OVER (
      PARTITION BY city_slug, lage
    ) AS median_rent
  FROM `mietspiegel.fact_rent_cells`
  WHERE lage IN ('einfach', 'gut')
  GROUP BY city_slug, lage
)
SELECT
  c.city_name,
  c.state_id,
  c.population,
  ROUND(MAX(CASE WHEN lage = 'einfach' THEN avg_rent END), 2) AS einfache_lage_avg,
  ROUND(MAX(CASE WHEN lage = 'gut' THEN avg_rent END), 2) AS gute_lage_avg,
  ROUND(
    MAX(CASE WHEN lage = 'gut' THEN avg_rent END) -
    MAX(CASE WHEN lage = 'einfach' THEN avg_rent END),
    2
  ) AS absolute_spread_eur,
  ROUND(
    SAFE_DIVIDE(
      MAX(CASE WHEN lage = 'gut' THEN avg_rent END),
      MAX(CASE WHEN lage = 'einfach' THEN avg_rent END)
    ),
    3
  ) AS gut_to_einfach_ratio,
  -- Categorize inequality
  CASE
    WHEN SAFE_DIVIDE(
      MAX(CASE WHEN lage = 'gut' THEN avg_rent END),
      MAX(CASE WHEN lage = 'einfach' THEN avg_rent END)
    ) >= 1.5 THEN 'High segregation'
    WHEN SAFE_DIVIDE(
      MAX(CASE WHEN lage = 'gut' THEN avg_rent END),
      MAX(CASE WHEN lage = 'einfach' THEN avg_rent END)
    ) >= 1.3 THEN 'Moderate spread'
    ELSE 'Low spread'
  END AS inequality_tier
FROM city_rent_by_lage r
JOIN `mietspiegel.dim_cities` c USING (city_slug)
GROUP BY c.city_name, c.state_id, c.population
HAVING einfache_lage_avg IS NOT NULL
   AND gute_lage_avg IS NOT NULL
ORDER BY gut_to_einfach_ratio DESC;


-- -----------------------------------------------------------------------------
-- QUERY 3: New vs prewar premium — how much more for post-2010 vs pre-1918?
-- -----------------------------------------------------------------------------
-- Business question: What is the premium for new construction (post-2010 /
-- "Neubau") compared to prewar buildings (pre-1918 / "Altbau") across cities?
-- This measures the modernization premium in the German rental market.
-- -----------------------------------------------------------------------------

WITH new_vs_old AS (
  SELECT
    city_slug,
    lage,
    size_class,
    MAX(CASE WHEN is_newbuild THEN rent_euro_per_sqm END) AS newbuild_rent,
    MAX(CASE WHEN is_prewar THEN rent_euro_per_sqm END) AS prewar_rent
  FROM `mietspiegel.fact_rent_cells`
  WHERE (is_newbuild OR is_prewar)
    AND size_class = '60_90'  -- Standardised to mid-size
  GROUP BY city_slug, lage, size_class
)
SELECT
  c.city_name,
  c.state_id,
  l.lage,
  ROUND(l.prewar_rent, 2) AS prewar_rent_eur,
  ROUND(l.newbuild_rent, 2) AS newbuild_rent_eur,
  ROUND(l.newbuild_rent - l.prewar_rent, 2) AS absolute_premium_eur,
  ROUND(SAFE_DIVIDE(l.newbuild_rent - l.prewar_rent, l.prewar_rent) * 100, 1) AS premium_pct,
  CASE
    WHEN SAFE_DIVIDE(l.newbuild_rent - l.prewar_rent, l.prewar_rent) >= 0.40 THEN '>40% premium'
    WHEN SAFE_DIVIDE(l.newbuild_rent - l.prewar_rent, l.prewar_rent) >= 0.25 THEN '25-40% premium'
    WHEN SAFE_DIVIDE(l.newbuild_rent - l.prewar_rent, l.prewar_rent) >= 0.10 THEN '10-25% premium'
    ELSE '<10% premium'
  END AS premium_tier
FROM new_vs_old l
JOIN `mietspiegel.dim_cities` c USING (city_slug)
WHERE l.prewar_rent IS NOT NULL
  AND l.newbuild_rent IS NOT NULL
ORDER BY premium_pct DESC;


-- -----------------------------------------------------------------------------
-- QUERY 4: Size discount curve — avg % decrease per size step
-- -----------------------------------------------------------------------------
-- Business question: How much does rent per square meter drop as apartments
-- get larger? This is the "Mengenrabatt" (bulk discount) curve — critical
-- for understanding how size affects affordability.
-- -----------------------------------------------------------------------------

WITH size_curve AS (
  SELECT
    city_slug,
    lage,
    size_class,
    AVG(rent_euro_per_sqm) AS avg_rent
  FROM `mietspiegel.fact_rent_cells`
  WHERE size_class IN ('bis_40', '40_60', '60_90', 'ueber_90')
  GROUP BY city_slug, lage, size_class
),
lagged AS (
  SELECT
    city_slug,
    lage,
    size_class,
    avg_rent,
    LAG(avg_rent) OVER (PARTITION BY city_slug, lage ORDER BY size_class) AS prev_avg_rent
  FROM size_curve
)
SELECT
  c.city_name,
  c.state_id,
  l.lage,
  l.size_class,
  ROUND(l.avg_rent, 2) AS rent_eur_per_sqm,
  ROUND(l.prev_avg_rent, 2) AS prev_size_rent,
  ROUND(l.avg_rent - l.prev_avg_rent, 2) AS step_delta_eur,
  ROUND(SAFE_DIVIDE(l.avg_rent - l.prev_avg_rent, l.prev_avg_rent) * 100, 1) AS step_discount_pct,
  -- Cumulative discount from smallest to largest
  ROUND(
    FIRST_VALUE(l.avg_rent) OVER (PARTITION BY l.city_slug, l.lage ORDER BY l.size_class)
    - l.avg_rent,
    2
  ) AS cumulative_discount_from_bis_40_eur
FROM lagged l
JOIN `mietspiegel.dim_cities` c USING (city_slug)
WHERE l.prev_avg_rent IS NOT NULL
ORDER BY c.city_name, l.lage, l.size_class;


-- -----------------------------------------------------------------------------
-- QUERY 5: Most expensive Baujahr × Lage combination per city
-- -----------------------------------------------------------------------------
-- Business question: What is the single most expensive rent cell
-- (Baujahr × Lage combo) in each city, and how extreme is it?
-- -----------------------------------------------------------------------------

WITH ranked_cells AS (
  SELECT
    city_slug,
    lage,
    baujahr,
    size_class,
    rent_euro_per_sqm,
    ROW_NUMBER() OVER (
      PARTITION BY city_slug
      ORDER BY rent_euro_per_sqm DESC
    ) AS rank_in_city,
    -- How many std devs above city average
    (rent_euro_per_sqm - AVG(rent_euro_per_sqm) OVER (PARTITION BY city_slug))
      / NULLIF(STDDEV(rent_euro_per_sqm) OVER (PARTITION BY city_slug), 0) AS z_score
  FROM `mietspiegel.fact_rent_cells`
  WHERE size_class = 'bis_40'  -- Smallest flats have highest per-m² rates
)
SELECT
  c.city_name,
  c.state_id,
  c.population,
  r.lage AS top_lage,
  r.baujahr AS top_baujahr,
  ROUND(r.rent_euro_per_sqm, 2) AS max_rent_eur_per_sqm,
  ROUND(r.z_score, 2) AS city_z_score,
  ROUND(AVG(f.rent_euro_per_sqm), 2) AS city_avg_rent
FROM ranked_cells r
JOIN `mietspiegel.dim_cities` c USING (city_slug)
JOIN `mietspiegel.fact_rent_cells` f USING (city_slug)
WHERE r.rank_in_city = 1
GROUP BY c.city_name, c.state_id, c.population, r.lage, r.baujahr, r.rent_euro_per_sqm, r.z_score
ORDER BY max_rent_eur_per_sqm DESC;


-- -----------------------------------------------------------------------------
-- QUERY 6: Cross-city Baujahr coverage — which cities have which period ranges?
-- -----------------------------------------------------------------------------
-- Business question: Which cities have the most granular historical building
-- age breakdowns? And which countries share the same Baujahr taxonomy?
-- Useful for understanding data coverage and comparing cities on equal footing.
-- -----------------------------------------------------------------------------

SELECT
  c.city_name,
  c.state_id,
  c.mietspiegel_year,
  COUNT(DISTINCT f.baujahr) AS distinct_baujahr_groups,
  ARRAY_AGG(DISTINCT f.baujahr ORDER BY f.baujahr_start NULLS LAST) AS baujahr_groups,
  CASE
    WHEN COUNT(DISTINCT f.baujahr) >= 7 THEN 'Full breakdown (7-8 groups)'
    WHEN COUNT(DISTINCT f.baujahr) >= 4 THEN 'Medium breakdown (4-6 groups)'
    WHEN COUNT(DISTINCT f.baujahr) >= 2 THEN 'Minimal breakdown (2-3 groups)'
    ELSE 'Single cohort (aktuell only)'
  END AS granularity_tier,
  CASE
    WHEN MAX(f.is_prewar) THEN TRUE ELSE FALSE
  END AS has_prewar,
  CASE
    WHEN MAX(f.is_newbuild) THEN TRUE ELSE FALSE
  END AS has_newbuild,
  COUNT(DISTINCT f.size_class) AS size_classes,
  COUNT(DISTINCT f.lage) AS wohnlage_levels
FROM `mietspiegel.fact_rent_cells` f
JOIN `mietspiegel.dim_cities` c USING (city_slug)
GROUP BY c.city_name, c.state_id, c.mietspiegel_year
ORDER BY distinct_baujahr_groups DESC, c.city_name;


-- -----------------------------------------------------------------------------
-- QUERY 7: Bundesland aggregates — average rent by state
-- -----------------------------------------------------------------------------
-- Business question: How do rents compare at the Bundesland (state) level?
-- Aggregate all Mietspiegel cities within each state to produce regional
-- benchmarks.
-- -----------------------------------------------------------------------------

SELECT
  s.state_name,
  s.region,
  COUNT(DISTINCT f.city_slug) AS cities_with_data,
  ROUND(AVG(f.rent_euro_per_sqm), 2) AS avg_rent_all,
  ROUND(MIN(f.rent_euro_per_sqm), 2) AS min_rent,
  ROUND(MAX(f.rent_euro_per_sqm), 2) AS max_rent,
  ROUND(STDDEV(f.rent_euro_per_sqm), 2) AS rent_stddev,
  -- Gut Lage only
  ROUND(AVG(CASE WHEN f.lage = 'gut' THEN f.rent_euro_per_sqm END), 2) AS avg_rent_gut_lage,
  -- Einfach Lage only
  ROUND(AVG(CASE WHEN f.lage = 'einfach' THEN f.rent_euro_per_sqm END), 2) AS avg_rent_einfach_lage,
  -- Newbuild premium
  ROUND(
    SAFE_DIVIDE(
      AVG(CASE WHEN f.is_newbuild THEN f.rent_euro_per_sqm END),
      AVG(CASE WHEN f.is_prewar THEN f.rent_euro_per_sqm END)
    ),
    3
  ) AS newbuild_premium_ratio
FROM `mietspiegel.fact_rent_cells` f
JOIN `mietspiegel.dim_cities` c USING (city_slug)
JOIN `mietspiegel.dim_states` s ON c.state_id = s.state_id
GROUP BY s.state_name, s.region
HAVING cities_with_data >= 1
ORDER BY avg_rent_all DESC;


-- -----------------------------------------------------------------------------
-- QUERY 8: "Is my rent fair?" — parameterized lookup
-- -----------------------------------------------------------------------------
-- Business question: Given a specific apartment (city, Lage, Baujahr, size),
-- what does the Mietspiegel say the rent should be? Parameterized for use
-- as a rental fairness calculator.
-- Replace @param values or use as a BigQuery parameterized query.
-- -----------------------------------------------------------------------------

-- Example parameters (uncomment and replace):
-- DECLARE lookup_city STRING DEFAULT 'berlin';
-- DECLARE lookup_lage STRING DEFAULT 'mittel';
-- DECLARE lookup_baujahr STRING DEFAULT '1965-1974';
-- DECLARE lookup_size_sqm FLOAT64 DEFAULT 65;

WITH matched AS (
  SELECT
    c.city_name,
    c.state_id,
    c.mietspiegel_year,
    c.mietspiegel_type,
    f.lage,
    f.baujahr,
    f.size_class,
    f.size_label,
    f.rent_euro_per_sqm,
    -- Closest Baujahr if exact match doesn't exist
    ABS(COALESCE(f.baujahr_start, 2000) - COALESCE(f2.baujahr_start, 2000)) AS baujahr_distance
  FROM `mietspiegel.fact_rent_cells` f
  JOIN `mietspiegel.dim_cities` c USING (city_slug)
  CROSS JOIN (
    SELECT baujahr_start
    FROM `mietspiegel.fact_rent_cells`
    WHERE city_slug = @lookup_city
      AND baujahr = @lookup_baujahr
    LIMIT 1
  ) f2
  WHERE f.city_slug = @lookup_city
    AND f.lage = @lookup_lage
    AND f.size_class = CASE
      WHEN @lookup_size_sqm < 40 THEN 'bis_40'
      WHEN @lookup_size_sqm < 60 THEN '40_60'
      WHEN @lookup_size_sqm < 90 THEN '60_90'
      ELSE 'ueber_90'
    END
)
SELECT
  city_name,
  lage,
  baujahr,
  size_class,
  size_label,
  rent_euro_per_sqm AS mietspiegel_rent_eur_per_sqm,
  mietspiegel_year,
  mietspiegel_type,
  -- Compute expected monthly rent for the given size
  ROUND(rent_euro_per_sqm * @lookup_size_sqm, 2) AS expected_monthly_rent_cold_eur,
  -- Upper bound: typically 10% above Mietspiegel for "Mietpreisbremse" checks
  ROUND(rent_euro_per_sqm * @lookup_size_sqm * 1.10, 2) AS mietpreisbremse_cap_eur
FROM matched
ORDER BY baujahr_distance
LIMIT 1;


-- -----------------------------------------------------------------------------
-- QUERY 9: Year-over-year growth from historical trends (Berlin)
-- -----------------------------------------------------------------------------
-- Business question: How fast have Berlin rents grown across all three
-- Wohnlagen since 2013? Measure compound annual growth rate (CAGR)
-- and identify acceleration/deceleration periods.
-- -----------------------------------------------------------------------------

WITH berlin_timeline AS (
  SELECT
    year,
    lage,
    base_rent_per_sqm,
    LAG(base_rent_per_sqm) OVER (PARTITION BY lage ORDER BY year) AS prev_year_rent
  FROM `mietspiegel.fact_historical_trends`
  WHERE city_slug = 'berlin'
)
SELECT
  year,
  lage,
  ROUND(base_rent_per_sqm, 2) AS rent_eur_per_sqm,
  ROUND(base_rent_per_sqm - prev_year_rent, 2) AS absolute_change_eur,
  ROUND(SAFE_DIVIDE(base_rent_per_sqm - prev_year_rent, prev_year_rent) * 100, 1) AS yoy_growth_pct,
  -- Running total growth since 2013
  ROUND(
    SAFE_DIVIDE(
      base_rent_per_sqm,
      FIRST_VALUE(base_rent_per_sqm) OVER (PARTITION BY lage ORDER BY year)
    ) - 1,
    3
  ) AS cumulative_growth_since_2013,
  -- CAGR from 2013 to this year
  ROUND(
    POWER(
      SAFE_DIVIDE(
        base_rent_per_sqm,
        FIRST_VALUE(base_rent_per_sqm) OVER (PARTITION BY lage ORDER BY year)
      ),
      SAFE_DIVIDE(1, year - FIRST_VALUE(year) OVER (PARTITION BY lage ORDER BY year))
    ) - 1,
    3
  ) AS cagr_to_date
FROM berlin_timeline
WHERE prev_year_rent IS NOT NULL
ORDER BY year, lage;


-- -----------------------------------------------------------------------------
-- QUERY 10: Market premium — Immoscout market rents vs Mietspiegel official rents
-- -----------------------------------------------------------------------------
-- Business question: How much higher are actual market asking rents (Immoscout24)
-- versus the official Mietspiegel for Berlin? This gap reveals how much the
-- regulated index diverges from the free market.
-- -----------------------------------------------------------------------------

WITH immoscout_agg AS (
  SELECT
    city_slug,
    AVG(COALESCE(pi_2024, pi_2023)) AS avg_market_rent,
    MIN(COALESCE(pi_2024, pi_2023)) AS min_market_rent,
    MAX(COALESCE(pi_2024, pi_2023)) AS max_market_rent,
    STDDEV(COALESCE(pi_2024, pi_2023)) AS market_stddev,
    COUNT(*) AS grid_cells_with_data
  FROM `mietspiegel.fact_immoscout`
  WHERE pi_2024 IS NOT NULL OR pi_2023 IS NOT NULL
  GROUP BY city_slug
),
mietspiegel_agg AS (
  SELECT
    city_slug,
    AVG(rent_euro_per_sqm) AS avg_official_rent,
    AVG(CASE WHEN lage = 'mittel' THEN rent_euro_per_sqm END) AS avg_official_mittel
  FROM `mietspiegel.fact_rent_cells`
  WHERE city_slug = 'berlin'
  GROUP BY city_slug
)
SELECT
  c.city_name,
  c.state_id,
  c.mietspiegel_year,
  ROUND(m.avg_official_rent, 2) AS official_mietspiegel_avg,
  ROUND(m.avg_official_mittel, 2) AS official_mittel_lage_avg,
  ROUND(i.avg_market_rent, 2) AS market_immoscout_avg,
  ROUND(i.min_market_rent, 2) AS market_min,
  ROUND(i.max_market_rent, 2) AS market_max,
  ROUND(i.market_stddev, 2) AS market_stddev,
  i.grid_cells_with_data,
  -- Market premium over official
  ROUND(i.avg_market_rent - m.avg_official_rent, 2) AS absolute_premium_eur,
  ROUND(SAFE_DIVIDE(i.avg_market_rent - m.avg_official_rent, m.avg_official_rent) * 100, 1) AS market_premium_pct,
  -- Premium vs mittel Lage specifically
  ROUND(SAFE_DIVIDE(i.avg_market_rent - m.avg_official_mittel, m.avg_official_mittel) * 100, 1) AS market_vs_mittel_premium_pct,
  -- Interpretation
  CASE
    WHEN SAFE_DIVIDE(i.avg_market_rent - m.avg_official_rent, m.avg_official_rent) >= 0.20 THEN 'Large gap — market significantly above regulated'
    WHEN SAFE_DIVIDE(i.avg_market_rent - m.avg_official_rent, m.avg_official_rent) >= 0.05 THEN 'Moderate gap — typical divergence'
    ELSE 'Small gap — market close to index'
  END AS premium_assessment
FROM mietspiegel_agg m
JOIN immoscout_agg i USING (city_slug)
JOIN `mietspiegel.dim_cities` c USING (city_slug);
