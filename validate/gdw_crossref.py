"""
GdW aggregate data model and cross-reference logic.
GdW = Gesamtverband der Wohnungswirtschaft (German Housing Association).
"""
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

    # Flag 1: City significantly above state average
    max_pct = thresh.get("pct_above_gdw_state_avg_max", 50.0)
    if st_avg and results["pct_vs_state"] is not None:
        if results["pct_vs_state"] > max_pct:
            results["flags"].append(
                f"City avg (€{city_avg:.2f}) is {results['pct_vs_state']:+.1f}% above GdW state avg "
                f"(€{st_avg:.2f}) — exceeds {max_pct}% threshold. Flag for review."
            )
        elif results["pct_vs_state"] > max_pct * 0.7:
            results["warnings"].append(
                f"City avg (€{city_avg:.2f}) is {results['pct_vs_state']:+.1f}% above GdW state avg "
                f"(€{st_avg:.2f}) — approaching threshold ({max_pct}%)."
            )

    # Flag 2: City below state range low
    if st_rng and city_avg < st_rng[0]:
        results["flags"].append(
            f"City avg (€{city_avg:.2f}) is below GdW state range low (€{st_rng[0]:.2f}). "
            f"Unusually low — verify extraction."
        )

    # Flag 3: City above state range high
    if st_rng and city_avg > st_rng[1]:
        results["flags"].append(
            f"City avg (€{city_avg:.2f}) is above GdW state range high (€{st_rng[1]:.2f}). "
            f"Unusually high — verify against local market data."
        )

    # Flag 4: City below national average by significant margin
    min_pct = thresh.get("pct_below_gdw_state_avg_min", -30.0)
    if st_avg and results["pct_vs_state"] is not None:
        if results["pct_vs_state"] < min_pct:
            results["flags"].append(
                f"City avg (€{city_avg:.2f}) is {results['pct_vs_state']:+.1f}% below GdW state avg "
                f"(€{st_avg:.2f}) — below {min_pct}% threshold. Possible extraction issue."
            )

    # Flag 5: Implausible absolute values
    max_plaus = thresh.get("max_rent_per_sqm_plausible", 25)
    min_plaus = thresh.get("min_rent_per_sqm_plausible", 2)
    if city_avg > max_plaus:
        results["flags"].append(
            f"City avg (€{city_avg:.2f}) exceeds plausible max (€{max_plaus:.2f}). "
            f"Values likely mis-extracted or in wrong units."
        )
    if city_avg < min_plaus and city_avg > 0:
        results["flags"].append(
            f"City avg (€{city_avg:.2f}) is below plausible min (€{min_plaus:.2f}). "
            f"Values may be incomplete or mis-extracted."
        )

    return results
