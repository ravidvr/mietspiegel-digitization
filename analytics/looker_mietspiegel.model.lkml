# =============================================================================
# LookML Model: Mietspiegel Digitization
# =============================================================================
# Looker model for German Mietspiegel (rent index) analytics.
# Connects to BigQuery dataset `mietspiegel`.
#
# Explores:
#   rent_cells         — Core rent table (city × Lage × Baujahr × Size)
#   cities             — City metadata
#   immoscout          — Berlin Immoscout24 market rent grid
#   historical_trends  — Berlin YoY Mietspiegel editions (2013–2023)
#   berlin_districts   — Berlin 12 Bezirke Wohnlage distribution
#
# Project: https://github.com/ravidvr/mietspiegel-digitization
# =============================================================================

connection: "bigquery_mietspiegel"

# Include all views from the views directory
include: "/views/*.view.lkml"
include: "/dashboards/*.dashboard.lkml"

# =============================================================================
# DATAGROUP: Default datagroup for persistent derived tables
# =============================================================================
datagroup: mietspiegel_default {
  sql_trigger: SELECT MAX(updated_at) FROM dim_cities ;;
  max_cache_age: "24 hours"
}

# =============================================================================
# EXPLORE: rent_cells — Core analytical explore
# =============================================================================
explore: rent_cells {
  label: "Mietspiegel Rent Cells"
  description: "Official Mietspiegel rent values: one row per city × Wohnlage × Baujahr × Apartment size class."
  group_label: "Mietspiegel"

  view_name: fact_rent_cells

  # ── Joins ──
  join: dim_cities {
    type: left_outer
    relationship: many_to_one
    sql_on: ${fact_rent_cells.city_slug} = ${dim_cities.city_slug} ;;
  }

  join: dim_states {
    type: left_outer
    relationship: many_to_one
    sql_on: ${dim_cities.state_id} = ${dim_states.state_id} ;;
  }

  # ── Always-join for city context ──
  always_join: [dim_cities]

  # ── Symmetric aggregates ──
  symmetric_aggregates: yes

  # ── Fields hidden from explore but available for joins ──
  hidden: yes
}

# =============================================================================
# EXPLORE: cities — City metadata explore
# =============================================================================
explore: cities {
  label: "Cities"
  description: "German cities with Mietspiegel rent data: population, location, rent index metadata."
  group_label: "Mietspiegel"

  view_name: dim_cities

  join: dim_states {
    type: left_outer
    relationship: many_to_one
    sql_on: ${dim_cities.state_id} = ${dim_states.state_id} ;;
  }

  join: fact_rent_cells {
    type: left_outer
    relationship: one_to_many
    sql_on: ${dim_cities.city_slug} = ${fact_rent_cells.city_slug} ;;
  }

  symmetric_aggregates: yes
}

# =============================================================================
# EXPLORE: immoscout — Berlin market rent grid
# =============================================================================
explore: immoscout {
  label: "Immoscout24 Market Rents"
  description: "Berlin 1km² grid cell market asking rents from Immoscout24 (RWI-GEO-REDX PUF v16). Compare actual market prices against official Mietspiegel."
  group_label: "Berlin"

  view_name: fact_immoscout

  join: dim_cities {
    type: left_outer
    relationship: many_to_one
    sql_on: ${fact_immoscout.city_slug} = ${dim_cities.city_slug} ;;
  }

  always_join: [dim_cities]
  symmetric_aggregates: yes
}

# =============================================================================
# EXPLORE: historical_trends — Berlin rent history by Wohnlage
# =============================================================================
explore: historical_trends {
  label: "Historical Rent Trends"
  description: "Berlin Mietspiegel editions 2013–2023: base rent per Wohnlage, year-over-year growth, and long-term trajectories."
  group_label: "Berlin"

  view_name: fact_historical_trends

  join: dim_cities {
    type: left_outer
    relationship: many_to_one
    sql_on: ${fact_historical_trends.city_slug} = ${dim_cities.city_slug} ;;
  }

  always_join: [dim_cities]
  symmetric_aggregates: yes
}

# =============================================================================
# EXPLORE: berlin_districts — Bezirk-level Wohnlage distribution
# =============================================================================
explore: berlin_districts {
  label: "Berlin Districts"
  description: "Berlin 12 Bezirke: Wohnlage address distribution from 400K WFS points, estimated average rents per district."
  group_label: "Berlin"

  view_name: fact_berlin_districts

  symmetric_aggregates: yes
}

# =============================================================================
# VIEW: dim_states — Bundesländer lookup
# =============================================================================
view: dim_states {
  sql_table_name: `mietspiegel.dim_states` ;;

  dimension: state_id {
    type: string
    sql: ${TABLE}.state_id ;;
    primary_key: yes
    label: "State ID (ISO)"
    description: "ISO 3166-2:DE two-letter state code (DE-BE, DE-BY, ...)"
  }

  dimension: state_name {
    type: string
    sql: ${TABLE}.state_name ;;
    label: "Bundesland"
  }

  dimension: capital {
    type: string
    sql: ${TABLE}.capital ;;
    label: "Capital"
  }

  dimension: region {
    type: string
    sql: ${TABLE}.region ;;
    label: "Macro-Region"
    group_label: "Geography"
  }

  dimension: population_2022 {
    type: number
    sql: ${TABLE}.population_2022 ;;
    label: "Population (2022)"
    group_label: "Demographics"
  }

  dimension: area_km2 {
    type: number
    value_format_name: decimal_2
    sql: ${TABLE}.area_km2 ;;
    label: "Area (km²)"
    group_label: "Geography"
  }

  measure: count {
    type: count
    label: "Number of States"
  }

  measure: total_population {
    type: sum
    sql: ${population_2022} ;;
    label: "Total Population (2022)"
    value_format_name: decimal_0
  }

  measure: avg_population {
    type: average
    sql: ${population_2022} ;;
    label: "Avg Population per State"
    value_format_name: decimal_0
  }

  measure: total_area {
    type: sum
    sql: ${area_km2} ;;
    label: "Total Area (km²)"
    value_format_name: decimal_0
  }
}

# =============================================================================
# VIEW: dim_cities — City metadata
# =============================================================================
view: dim_cities {
  sql_table_name: `mietspiegel.dim_cities` ;;

  dimension: city_slug {
    type: string
    sql: ${TABLE}.city_slug ;;
    primary_key: yes
    label: "City Slug"
    description: "URL-safe city identifier (berlin, frankfurt-am-main)"
  }

  dimension: city_name {
    type: string
    sql: ${TABLE}.city_name ;;
    label: "City"
  }

  dimension: state_id {
    type: string
    sql: ${TABLE}.state_id ;;
    label: "State ID"
  }

  # ── Geography ──
  dimension_group: location {
    type: location
    sql_latitude: ${TABLE}.lat ;;
    sql_longitude: ${TABLE}.lng ;;
    group_label: "Geography"
  }

  dimension: lat {
    type: number
    sql: ${TABLE}.lat ;;
    hidden: yes
  }

  dimension: lng {
    type: number
    sql: ${TABLE}.lng ;;
    hidden: yes
  }

  # ── Demographics ──
  dimension: population {
    type: number
    value_format_name: decimal_0
    sql: ${TABLE}.population ;;
    label: "Population"
    group_label: "Demographics"
  }

  dimension: population_tier {
    type: tier
    sql: ${population} ;;
    tiers: [250000, 500000, 1000000, 2000000]
    style: integer
    label: "City Size Tier"
    group_label: "Demographics"
  }

  # ── Mietspiegel metadata ──
  dimension: mietspiegel_year {
    type: number
    sql: ${TABLE}.mietspiegel_year ;;
    label: "Mietspiegel Edition Year"
    group_label: "Mietspiegel Info"
  }

  dimension: mietspiegel_type {
    type: string
    sql: ${TABLE}.mietspiegel_type ;;
    label: "Mietspiegel Type"
    group_label: "Mietspiegel Info"
  }

  dimension: has_rent_data {
    type: yesno
    sql: ${TABLE}.has_rent_data ;;
    label: "Has Rent Data"
    group_label: "Mietspiegel Info"
    description: "FALSE if the city has metadata but no rent table (e.g. Chemnitz)"
  }

  # ── Measures ──
  measure: count {
    type: count
    label: "Cities"
  }

  measure: total_population {
    type: sum
    sql: ${population} ;;
    label: "Total Population (all cities)"
    value_format_name: decimal_0
  }

  measure: avg_population {
    type: average
    sql: ${population} ;;
    label: "Avg Population per City"
    value_format_name: decimal_0
  }
}

# =============================================================================
# VIEW: fact_rent_cells — Core rent fact table
# =============================================================================
view: fact_rent_cells {
  sql_table_name: `mietspiegel.fact_rent_cells` ;;

  dimension: rent_cell_id {
    type: string
    sql: ${TABLE}.rent_cell_id ;;
    primary_key: yes
    hidden: yes
  }

  dimension: city_slug {
    type: string
    sql: ${TABLE}.city_slug ;;
    label: "City Slug"
  }

  # ── Core dimensions ──
  dimension: lage {
    type: string
    sql: ${TABLE}.lage ;;
    label: "Wohnlage"
    description: "Residential location quality tier: einfach (simple), mittel (medium), gut (good)"
    group_label: "Apartment Attributes"
    suggest_explore: rent_cells
    suggest_dimension: rent_cells.lage
  }

  dimension: baujahr {
    type: string
    sql: ${TABLE}.baujahr ;;
    label: "Baujahr (Building Age)"
    description: "Building construction period (Baujahrgruppe)"
    group_label: "Apartment Attributes"
  }

  dimension: baujahr_start {
    type: number
    sql: ${TABLE}.baujahr_start ;;
    label: "Baujahr Start Year"
    group_label: "Apartment Attributes"
  }

  dimension: baujahr_end {
    type: number
    sql: ${TABLE}.baujahr_end ;;
    label: "Baujahr End Year"
    group_label: "Apartment Attributes"
  }

  dimension: size_class {
    type: string
    sql: ${TABLE}.size_class ;;
    label: "Size Class Key"
    description: "Machine key: bis_40, 40_60, 60_90, ueber_90"
    group_label: "Apartment Attributes"
  }

  dimension: size_label {
    type: string
    sql: ${TABLE}.size_label ;;
    label: "Apartment Size"
    description: "Display label: bis 40 m², 40-60 m², 60-90 m², über 90 m²"
    group_label: "Apartment Attributes"
  }

  # ── Boolean flags ──
  dimension: is_aktuell {
    type: yesno
    sql: ${TABLE}.is_aktuell ;;
    label: "Single Cohort (aktuell)"
    description: "TRUE if the city has only one unified Baujahr group"
    group_label: "Apartment Attributes"
  }

  dimension: is_prewar {
    type: yesno
    sql: ${TABLE}.is_prewar ;;
    label: "Pre-war (pre-1945)"
    group_label: "Apartment Attributes"
  }

  dimension: is_postwar {
    type: yesno
    sql: ${TABLE}.is_postwar ;;
    label: "Post-war (1945-1990)"
    group_label: "Apartment Attributes"
  }

  dimension: is_newbuild {
    type: yesno
    sql: ${TABLE}.is_newbuild ;;
    label: "New Build (post-2010)"
    group_label: "Apartment Attributes"
  }

  # ── Building era tier ──
  dimension: building_era {
    type: string
    sql:
      CASE
        WHEN ${is_prewar} THEN 'Prewar (<1945)'
        WHEN ${baujahr_start} >= 1945 AND ${baujahr_start} < 1991 THEN 'Postwar (1945-1990)'
        WHEN ${baujahr_start} >= 1991 AND ${baujahr_start} < 2011 THEN 'Reunification (1991-2010)'
        WHEN ${baujahr_start} >= 2011 THEN 'New Build (2011+)'
        ELSE 'Unknown/aktuell'
      END ;;
    label: "Building Era"
    group_label: "Apartment Attributes"
  }

  # ── Value (the core metric) ──
  dimension: rent_euro_per_sqm {
    type: number
    value_format_name: decimal_2
    sql: ${TABLE}.rent_euro_per_sqm ;;
    label: "Rent (€/m²)"
    description: "Nettokaltmiete in Euros per square meter — net cold rent"
  }

  dimension: mietspiegel_year {
    type: number
    sql: ${TABLE}.mietspiegel_year ;;
    label: "Edition Year"
    group_label: "Mietspiegel Info"
  }

  # ── Param filter for size_sqm lookup ──
  filter: size_sqm_filter {
    type: number
    label: "Apartment Size (m²)"
    description: "Enter actual apartment size in square meters for rent lookup"
    suggestable: true
  }

  # ── Measures ──
  measure: count {
    type: count
    label: "Rent Cells"
    description: "Total number of rent cells in the dataset"
  }

  measure: avg_rent {
    type: average
    sql: ${rent_euro_per_sqm} ;;
    label: "Average Rent (€/m²)"
    value_format_name: decimal_2
    description: "Mean Nettokaltmiete across all selected rent cells"
  }

  measure: median_rent {
    type: median
    sql: ${rent_euro_per_sqm} ;;
    label: "Median Rent (€/m²)"
    value_format_name: decimal_2
    description: "Median Nettokaltmiete — more robust to skewed distributions"
  }

  measure: min_rent {
    type: min
    sql: ${rent_euro_per_sqm} ;;
    label: "Minimum Rent (€/m²)"
    value_format_name: decimal_2
  }

  measure: max_rent {
    type: max
    sql: ${rent_euro_per_sqm} ;;
    label: "Maximum Rent (€/m²)"
    value_format_name: decimal_2
  }

  measure: rent_spread {
    type: number
    sql: ${max_rent} - ${min_rent} ;;
    label: "Rent Spread (€/m²)"
    value_format_name: decimal_2
    description: "Difference between max and min rent in selection"
  }

  measure: rent_stddev {
    type: number
    sql: STDDEV(${rent_euro_per_sqm}) ;;
    label: "Rent Std Dev"
    value_format_name: decimal_2
    description: "Standard deviation of rent within the current selection"
  }

  measure: p25_rent {
    type: percentile
    sql: ${rent_euro_per_sqm} ;;
    percentile: 25
    label: "25th Percentile Rent"
    value_format_name: decimal_2
  }

  measure: p75_rent {
    type: percentile
    sql: ${rent_euro_per_sqm} ;;
    percentile: 75
    label: "75th Percentile Rent"
    value_format_name: decimal_2
  }

  measure: percentile_90_rent {
    type: percentile
    sql: ${rent_euro_per_sqm} ;;
    percentile: 90
    label: "90th Percentile Rent"
    value_format_name: decimal_2
  }

  # ── Pre-built analytical measures ──

  measure: gut_lage_avg {
    type: average
    sql: ${rent_euro_per_sqm} ;;
    filters: [lage: "gut"]
    label: "Avg Rent — Gute Lage"
    value_format_name: decimal_2
  }

  measure: mittel_lage_avg {
    type: average
    sql: ${rent_euro_per_sqm} ;;
    filters: [lage: "mittel"]
    label: "Avg Rent — Mittlere Lage"
    value_format_name: decimal_2
  }

  measure: einfach_lage_avg {
    type: average
    sql: ${rent_euro_per_sqm} ;;
    filters: [lage: "einfach"]
    label: "Avg Rent — Einfache Lage"
    value_format_name: decimal_2
  }

  measure: gut_to_einfach_ratio {
    type: number
    sql: SAFE_DIVIDE(${gut_lage_avg}, NULLIF(${einfach_lage_avg}, 0)) ;;
    label: "Gut/Einfach Ratio"
    value_format_name: decimal_3
    description: "Ratio of gute to einfache Wohnlage average rent — measures rent inequality within city. Values > 1.5 indicate high segregation."
  }

  measure: size_discount_pct {
    type: number
    sql:
      SAFE_DIVIDE(
        ${TABLE}.rent_euro_per_sqm - (
          SELECT AVG(rent_euro_per_sqm)
          FROM `mietspiegel.fact_rent_cells` f2
          WHERE f2.city_slug = ${TABLE}.city_slug
            AND f2.lage = ${TABLE}.lage
            AND f2.size_class = 'ueber_90'
        ),
        ${TABLE}.rent_euro_per_sqm
      ) * 100 ;;
    label: "Size Discount (%)"
    value_format_name: decimal_1
    description: "Percentage discount from current size class to >90 m² (same city/Lage/Baujahr). Positive = larger apartments are cheaper per m²."
  }

  measure: newbuild_premium_pct {
    type: number
    sql:
      SAFE_DIVIDE(
        AVG(CASE WHEN ${is_newbuild} THEN ${rent_euro_per_sqm} END)
        - AVG(CASE WHEN ${is_prewar} THEN ${rent_euro_per_sqm} END),
        NULLIF(AVG(CASE WHEN ${is_prewar} THEN ${rent_euro_per_sqm} END), 0)
      ) * 100 ;;
    label: "New Build Premium (%)"
    value_format_name: decimal_1
    description: "Percentage by which post-2010 builds exceed pre-1918 rents"
  }

  # ── Cities count ──
  measure: distinct_cities {
    type: count_distinct
    sql: ${city_slug} ;;
    label: "Distinct Cities"
  }

  # ── Parameterised fields ──
  parameter: comparison_city {
    type: unquoted
    allowed_value: {
      label: "Berlin"
      value: "'berlin'"
    }
    allowed_value: {
      label: "München"
      value: "'muenchen'"
    }
    allowed_value: {
      label: "Hamburg"
      value: "'hamburg'"
    }
    allowed_value: {
      label: "Köln"
      value: "'koeln'"
    }
    allowed_value: {
      label: "Frankfurt am Main"
      value: "'frankfurt'"
    }
    allowed_value: {
      label: "Stuttgart"
      value: "'stuttgart'"
    }
    allowed_value: {
      label: "Düsseldorf"
      value: "'duesseldorf'"
    }
    allowed_value: {
      label: "Leipzig"
      value: "'leipzig'"
    }
    allowed_value: {
      label: "Dresden"
      value: "'dresden'"
    }
    allowed_value: {
      label: "Bremen"
      value: "'bremen'"
    }
    label: "Comparison City"
    description: "Select a city to use as comparison benchmark"
  }
}

# =============================================================================
# VIEW: fact_immoscout — Berlin market rent grid
# =============================================================================
view: fact_immoscout {
  sql_table_name: `mietspiegel.fact_immoscout` ;;

  dimension: grid_id {
    type: string
    sql: ${TABLE}.grid_id ;;
    primary_key: yes
    label: "Grid Cell ID"
    description: "RWI-GEO-REDX 1km² grid identifier"
  }

  dimension: city_slug {
    type: string
    sql: ${TABLE}.city_slug ;;
    hidden: yes
  }

  dimension_group: location {
    type: location
    sql_latitude: ${TABLE}.lat ;;
    sql_longitude: ${TABLE}.lng ;;
    group_label: "Geography"
  }

  dimension: plz {
    type: string
    sql: ${TABLE}.plz ;;
    label: "Postal Code (PLZ)"
    group_label: "Geography"
  }

  # ── Yearly price indices ──
  dimension: pi_2008 { type: number; sql: ${TABLE}.pi_2008 ;; group_label: "2008"; hidden: yes }
  dimension: pi_2013 { type: number; sql: ${TABLE}.pi_2013 ;; group_label: "2013"; hidden: yes }
  dimension: pi_2018 { type: number; sql: ${TABLE}.pi_2018 ;; group_label: "2018"; hidden: yes }
  dimension: pi_2023 { type: number; sql: ${TABLE}.pi_2023 ;; group_label: "2023"; hidden: yes }
  dimension: pi_2024 { type: number; sql: ${TABLE}.pi_2024 ;; group_label: "2024"; hidden: yes }
  dimension: pi_2025 { type: number; sql: ${TABLE}.pi_2025 ;; group_label: "2025"; hidden: yes }

  dimension: n_2008 { type: number; sql: ${TABLE}.n_2008 ;; hidden: yes }
  dimension: n_2013 { type: number; sql: ${TABLE}.n_2013 ;; hidden: yes }
  dimension: n_2018 { type: number; sql: ${TABLE}.n_2018 ;; hidden: yes }
  dimension: n_2023 { type: number; sql: ${TABLE}.n_2023 ;; hidden: yes }
  dimension: n_2024 { type: number; sql: ${TABLE}.n_2024 ;; hidden: yes }
  dimension: n_2025 { type: number; sql: ${TABLE}.n_2025 ;; hidden: yes }

  # ── Latest available rent ──
  dimension: latest_market_rent {
    type: number
    value_format_name: decimal_2
    sql: COALESCE(${TABLE}.pi_2025, ${TABLE}.pi_2024, ${TABLE}.pi_2023) ;;
    label: "Latest Market Rent (€/m²)"
    description: "Most recent available Immoscout24 asking rent index"
    group_label: "Rent"
  }

  dimension: change_pct {
    type: number
    value_format_name: decimal_1
    sql: ${TABLE}.change_pct ;;
    label: "Price Change (%)"
    description: "Long-term % change from earliest to latest available year"
    group_label: "Rent"
  }

  # ── Measures ──
  measure: count {
    type: count
    label: "Grid Cells"
  }

  measure: avg_market_rent {
    type: average
    sql: ${latest_market_rent} ;;
    label: "Avg Market Rent (€/m²)"
    value_format_name: decimal_2
  }

  measure: median_market_rent {
    type: median
    sql: ${latest_market_rent} ;;
    label: "Median Market Rent (€/m²)"
    value_format_name: decimal_2
  }

  measure: p25_rent {
    type: percentile
    sql: ${latest_market_rent} ;;
    percentile: 25
    label: "25th Percentile Market Rent"
    value_format_name: decimal_2
  }

  measure: p75_rent {
    type: percentile
    sql: ${latest_market_rent} ;;
    percentile: 75
    label: "75th Percentile Market Rent"
    value_format_name: decimal_2
  }

  measure: avg_change_pct {
    type: average
    sql: ${change_pct} ;;
    label: "Avg Long-Term Change (%)"
    value_format_name: decimal_1
  }
}

# =============================================================================
# VIEW: fact_historical_trends — Berlin rent history
# =============================================================================
view: fact_historical_trends {
  sql_table_name: `mietspiegel.fact_historical_trends` ;;

  dimension: city_slug {
    type: string
    sql: ${TABLE}.city_slug ;;
    label: "City Slug"
  }

  # ── Time dimension ──
  dimension_group: edition {
    type: time
    timeframes: [raw, date, year]
    sql: MAKE_DATE(${TABLE}.year, 1, 1) ;;
    label: "Edition Date"
    description: "Year of Mietspiegel publication"
  }

  dimension: year {
    type: number
    sql: ${TABLE}.year ;;
    label: "Year"
    group_label: "Time"
  }

  dimension: lage {
    type: string
    sql: ${TABLE}.lage ;;
    label: "Wohnlage"
  }

  dimension: base_rent_per_sqm {
    type: number
    value_format_name: decimal_2
    sql: ${TABLE}.base_rent_per_sqm ;;
    label: "Base Rent (€/m²)"
    description: "Reference rent for mittlere Lage, 60-90m², 1965-1974 Baujahr"
  }

  dimension: baujahr_cohort {
    type: string
    sql: ${TABLE}.baujahr_cohort ;;
    label: "Reference Baujahr Cohort"
  }

  # ── Measures ──
  measure: count {
    type: count
    label: "Data Points"
  }

  measure: latest_rent {
    type: number
    sql: ${base_rent_per_sqm} ;;
    filters: [year: "2023"]
    label: "2023 Base Rent (€/m²)"
    value_format_name: decimal_2
  }

  measure: earliest_rent {
    type: number
    sql: ${base_rent_per_sqm} ;;
    filters: [year: "2013"]
    label: "2013 Base Rent (€/m²)"
    value_format_name: decimal_2
  }

  measure: total_growth_pct {
    type: number
    sql: SAFE_DIVIDE(${latest_rent} - ${earliest_rent}, ${earliest_rent}) * 100 ;;
    label: "10-Year Growth (2013→2023, %)"
    value_format_name: decimal_1
    description: "Total percentage growth in base rent from 2013 to 2023"
  }

  measure: avg_yoy_growth_pct {
    type: number
    sql: (POWER(SAFE_DIVIDE(${latest_rent}, NULLIF(${earliest_rent}, 0)), 0.1) - 1) * 100 ;;
    label: "Avg Annual Growth (CAGR, %)"
    value_format_name: decimal_1
  }
}

# =============================================================================
# VIEW: fact_berlin_districts — Bezirk-level data
# =============================================================================
view: fact_berlin_districts {
  sql_table_name: `mietspiegel.fact_berlin_districts` ;;

  dimension: bezirk_name {
    type: string
    sql: ${TABLE}.bezirk_name ;;
    primary_key: yes
    label: "Bezirk"
    description: "Berlin district name"
  }

  dimension: wohnlage_einfach {
    type: number
    sql: ${TABLE}.wohnlage_einfach ;;
    label: "Einfache Wohnlage (addresses)"
    group_label: "Wohnlage Distribution"
  }

  dimension: wohnlage_mittel {
    type: number
    sql: ${TABLE}.wohnlage_mittel ;;
    label: "Mittlere Wohnlage (addresses)"
    group_label: "Wohnlage Distribution"
  }

  dimension: wohnlage_gut {
    type: number
    sql: ${TABLE}.wohnlage_gut ;;
    label: "Gute Wohnlage (addresses)"
    group_label: "Wohnlage Distribution"
  }

  dimension: total_addresses {
    type: number
    sql: ${TABLE}.total_addresses ;;
    label: "Total Addresses"
    group_label: "Wohnlage Distribution"
  }

  dimension: einfach_pct {
    type: number
    value_format_name: decimal_1
    sql: ${TABLE}.einfach_pct * 100 ;;
    label: "% Einfache Wohnlage"
    group_label: "Wohnlage Distribution"
  }

  dimension: mittel_pct {
    type: number
    value_format_name: decimal_1
    sql: ${TABLE}.mittel_pct * 100 ;;
    label: "% Mittlere Wohnlage"
    group_label: "Wohnlage Distribution"
  }

  dimension: gut_pct {
    type: number
    value_format_name: decimal_1
    sql: ${TABLE}.gut_pct * 100 ;;
    label: "% Gute Wohnlage"
    group_label: "Wohnlage Distribution"
  }

  dimension: estimated_rent {
    type: number
    value_format_name: decimal_2
    sql: ${TABLE}.estimated_rent ;;
    label: "Estimated Avg Rent (€/m²)"
    group_label: "Rent"
  }

  # ── Dominant Wohnlage ──
  dimension: dominant_wohnlage {
    type: string
    sql:
      CASE
        WHEN ${einfach_pct} >= ${mittel_pct} AND ${einfach_pct} >= ${gut_pct} THEN 'Einfach'
        WHEN ${mittel_pct} >= ${einfach_pct} AND ${mittel_pct} >= ${gut_pct} THEN 'Mittel'
        ELSE 'Gut'
      END ;;
    label: "Dominant Wohnlage"
    group_label: "Wohnlage Distribution"
  }

  # ── Measures ──
  measure: count {
    type: count
    label: "Districts"
  }

  measure: total_addresses_berlin {
    type: sum
    sql: ${total_addresses} ;;
    label: "Total Addresses (Berlin)"
    value_format_name: decimal_0
  }

  measure: avg_estimated_rent {
    type: average
    sql: ${estimated_rent} ;;
    label: "Avg Estimated Rent (€/m²)"
    value_format_name: decimal_2
  }

  measure: avg_einfach_pct {
    type: average
    sql: ${einfach_pct} ;;
    label: "Avg % Einfache Wohnlage"
    value_format_name: decimal_1
  }

  measure: avg_mittel_pct {
    type: average
    sql: ${mittel_pct} ;;
    label: "Avg % Mittlere Wohnlage"
    value_format_name: decimal_1
  }

  measure: avg_gut_pct {
    type: average
    sql: ${gut_pct} ;;
    label: "Avg % Gute Wohnlage"
    value_format_name: decimal_1
  }
}
