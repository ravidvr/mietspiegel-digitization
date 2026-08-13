"""
GdW aggregate data model and cross-reference logic.
GdW = Gesamtverband der Wohnungswirtschaft (German Housing Association).
"""
from __future__ import annotations

import json
import os

GDW_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reference", "gdw_aggregate.json")


def load_gdw_data(path: str = GDW_PATH) -> dict:
    """Load the GdW aggregate reference data."""
    with open(path) as f:
        return json.load(f)


def state_avg(gdw: dict, state: str) -> float | None:
    """Return the GdW average net cold rent per sqm for a given Bundesland."""
    if state in gdw.get("by_state", {}):
        return gdw["by_state"][state]["net_cold_rent_per_sqm"]
    return None


def state_range(gdw: dict, state: str) -> tuple | None:
    """Return the [min, max] range for a given Bundesland."""
    if state in gdw.get("by_state", {}):
        r = gdw["by_state"][state]["range"]
        return (r[0], r[1])
    return None


def national_avg(gdw: dict) -> float:
    """Return the national average net cold rent per sqm."""
    return gdw["national_averages"]["net_cold_rent_per_sqm"]


def thresholds(gdw: dict) -> dict:
    """Return the sanity check threshold config."""
    return gdw.get("sanitiy_check_thresholds", {})


def compute_city_average(city_data: dict) -> float:
    """
    Compute the overall average rent per sqm for a city across all Lage/Baujahr/Size cells.
    Returns the mean of all non-null cell values found in all tables.
    """
    values = []
    for table in city_data.get("tables", []):
        for row in table.get("rows", []):
            for key, val in row.items():
                if key != "baujahr" and isinstance(val, (int, float)) and val > 0:
                    values.append(val)
    if not values:
        return 0.0
    return sum(values) / len(values)


def cross_reference_city(city_data: dict, gdw: dict) -> dict:
    """
    Cross-reference a city's data against GdW aggregates.
    Returns a dict with comparison results and flagging.
    """
    city = city_data.get("city", "Unknown")
    state = city_data.get("state", "Unknown")
    city_avg = compute_city_average(city_data)
    nat_avg = national_avg(gdw)
    st_avg = state_avg(gdw, state)
    st_rng = state_range(gdw, state)
    thresh = thresholds(gdw)

    results = {
        "city": city,
        "city_average_rent": round(city_avg, 2),
        "gdw_national_average": nat_avg,
        "gdw_state_average": st_avg,
        "gdw_state_range": st_rng,
        "pct_vs_national": round((city_avg - nat_avg) / nat_avg * 100, 1) if nat_avg else None,
        "pct_vs_state": round((city_avg - st_avg) / st_avg * 100, 1) if st_avg else None,
        "flags": [],
        "warnings": [],
    }

    # NOTE ON DIRECTIONALITY (recalibrated 2026-08):
    # GdW aggregate = EXISTING contracts across social/cooperative stock (€6.63/m² national).
    # Mietspiegel = NEW-LEASE reference rents (€7–20/m² in major cities).
    # New leases are structurally 20–100%+ above existing contracts, so a city being
    # ABOVE the GdW state average is EXPECTED and must NOT be flagged as an error.
    # We only flag genuine anomalies:
    #   (a) city below the GdW state range low  → new leases cheaper than existing
    #       contracts is economically implausible and suggests an extraction error;
    #   (b) implausible absolute values (outside €2–25/m²).

    # Anomaly (a): city BELOW GdW state range low (new lease < existing contract).
    if st_rng and city_avg > 0 and city_avg < st_rng[0]:
        results["flags"].append(
            f"City avg (€{city_avg:.2f}) is BELOW GdW state range low (€{st_rng[0]:.2f}). "
            f"New-lease reference rent below existing-contract stock is implausible — "
            f"verify extraction."
        )

    # Anomaly (b): implausible absolute values.
    max_plaus = thresh.get("max_rent_per_sqm_plausible", 25)
    min_plaus = thresh.get("min_rent_per_sqm_plausible", 2)
    if city_avg > max_plaus:
        results["flags"].append(
            f"City avg (€{city_avg:.2f}) exceeds plausible max (€{max_plaus:.2f}). "
            f"Values likely mis-extracted or in wrong units."
        )
    if 0 < city_avg < min_plaus:
        results["flags"].append(
            f"City avg (€{city_avg:.2f}) is below plausible min (€{min_plaus:.2f}). "
            f"Values may be incomplete or mis-extracted."
        )

    return results
