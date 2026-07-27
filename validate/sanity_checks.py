"""
Automated sanity checks for Mietspiegel city data.

Core principles tested:
  1. Rents increase with newer Baujahr (construction year) periods
  2. Rents increase with better Lage (location category): einfach < mittel < gut
  3. Rent values are internally consistent and monotonic
  4. No negative, zero, or NaN values
  5. Size relationships are sensible (smaller units typically cost more per sqm)
"""
import math
from typing import Any


def _extract_numeric_value(val: Any) -> float | None:
    """Convert a cell value to float if possible. Returns None for non-numeric."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if not math.isnan(val) else None
    return None


def _baujahr_sort_key(baujahr_label: str) -> tuple:
    """
    Convert a Baujahr label to a sortable numeric key.
    Handles common German Mietspiegel patterns:
      - "bis 1918" / "vor 1918" -> 1900
      - "1918" / "1919-1925" -> year range
      - "1949-1957" -> mid year
      - "ab 2003" / "2003-2010" / "nach 2016"
      - "2020 oder später" -> high
    """
    bj = baujahr_label.lower().strip()

    # "bis" / "vor" / "älter" / "bis einschl." = oldest
    for prefix in ["bis ", "vor ", "älter ", "bis einschl."]:
        if bj.startswith(prefix):
            year_str = bj.replace(prefix, "").strip().split()[0]
            try:
                return (0, int(year_str))
            except ValueError:
                return (0, 1900)

    # "ab " / "nach " / "seit " = from year onward
    for prefix in ["ab ", "nach ", "seit "]:
        if bj.startswith(prefix):
            year_str = bj.replace(prefix, "").strip().split()[0]
            try:
                return (3, int(year_str))
            except ValueError:
                return (3, 2100)

    # "oder später" suffix
    if "oder später" in bj:
        parts = bj.split("oder später")[0].strip()
        try:
            return (3, int(parts.split()[-1]))
        except ValueError:
            return (3, 2100)

    # "XXXX-YYYY" range
    if "-" in bj and bj.replace("-", "").strip().isdigit():
        parts = bj.split("-")
        try:
            return (1, (int(parts[0]) + int(parts[1])) // 2)
        except ValueError:
            pass

    # Single year
    if bj.isdigit():
        return (2, int(bj))

    # Unrecognized -> sort at end
    return (99, 0)


def check_baujahr_monotonicity(tables: list, lage: str | None = None,
                                 tolerance: float = 0.05) -> list:
    """
    For a given Lage (or across all if None), verify that rents
    increase (or at least do not decrease significantly) as Baujahr
    periods progress. A decrease > tolerance (fractional) is flagged.

    Returns list of violation dicts.
    """
    violations = []

    # Filter tables to the relevant Lage
    if lage:
        relevant = [t for t in tables if t.get("lage", "").lower() == lage.lower()]
    else:
        relevant = tables

    for table in relevant:
        lage_name = table.get("lage", "unknown")
        rows = sorted(table.get("rows", []), key=lambda r: _baujahr_sort_key(r.get("baujahr", "")))

        size_keys = [k for k in rows[0].keys() if k != "baujahr"] if rows else []

        for i in range(1, len(rows)):
            prev_bj = rows[i - 1]["baujahr"]
            curr_bj = rows[i]["baujahr"]

            for sk in size_keys:
                prev_val = _extract_numeric_value(rows[i - 1].get(sk))
                curr_val = _extract_numeric_value(rows[i].get(sk))

                if prev_val is None or curr_val is None:
                    continue

                # Older period should be <= newer period (rent increases with time)
                change = (curr_val - prev_val) / prev_val if prev_val > 0 else float('inf')

                if change < -tolerance:
                    violations.append({
                        "type": "baujahr_decrease",
                        "lage": lage_name,
                        "size_class": sk,
                        "from_baujahr": prev_bj,
                        "to_baujahr": curr_bj,
                        "from_value": round(prev_val, 2),
                        "to_value": round(curr_val, 2),
                        "change_pct": round(change * 100, 1),
                        "severity": "error" if abs(change) > 0.1 else "warning",
                        "message": (
                            f"[{lage_name}] Rent decreases from {prev_bj} (€{prev_val:.2f}) "
                            f"to {curr_bj} (€{curr_val:.2f}) for size class '{sk}' "
                            f"({change:+.1%}). Expected increase with newer Baujahr."
                        )
                    })

    return violations


def check_lage_monotonicity(tables: list, tolerance: float = 0.05) -> list:
    """
    Verify that for each Baujahr period and size class, the rent increases
    as Lage improves: einfach < mittel < gut.

    Returns list of violation dicts.
    """
    violations = []
    lage_order = {"einfach": 0, "mittel": 1, "gut": 2}

    # Collect all (baujahr, size_key) combos
    rows_by_lage = {}
    for table in tables:
        lage = table.get("lage", "").lower()
        if lage not in lage_order:
            continue  # Skip unrecognized Lage categories
        rows_by_lage[lage] = table.get("rows", [])

    if len(rows_by_lage) < 2:
        return violations  # Need at least 2 Lage categories to compare

    size_keys = set()
    for rows in rows_by_lage.values():
        for r in rows:
            for k in r:
                if k != "baujahr":
                    size_keys.add(k)

    # Build a lookup: (baujahr, size_key) -> {lage: value}
    index = {}
    for lage, rows in rows_by_lage.items():
        for row in rows:
            bj = row.get("baujahr", "")
            for sk in size_keys:
                val = _extract_numeric_value(row.get(sk))
                if val is not None:
                    index.setdefault((bj, sk), {})[lage] = val

    # Check monotonicity for each (baujahr, size) combo
    sorted_lages = sorted(lage_order.keys(), key=lambda l: lage_order[l])

    for (bj, sk), lage_values in index.items():
        present_lages = sorted([l for l in sorted_lages if l in lage_values],
                                key=lambda l: lage_order[l])
        for i in range(1, len(present_lages)):
            prev_lage = present_lages[i - 1]
            curr_lage = present_lages[i]
            prev_val = lage_values[prev_lage]
            curr_val = lage_values[curr_lage]

            change = (curr_val - prev_val) / prev_val if prev_val > 0 else float('inf')

            if change < -tolerance:
                violations.append({
                    "type": "lage_decrease",
                    "baujahr": bj,
                    "size_class": sk,
                    "from_lage": prev_lage,
                    "to_lage": curr_lage,
                    "from_value": round(prev_val, 2),
                    "to_value": round(curr_val, 2),
                    "change_pct": round(change * 100, 1),
                    "severity": "error" if abs(change) > 0.1 else "warning",
                    "message": (
                        f"[{bj}/{sk}] Rent decreases from '{prev_lage}' (€{prev_val:.2f}) "
                        f"to '{curr_lage}' (€{curr_val:.2f}) ({change:+.1%}). "
                        f"Expected increase with better Lage."
                    )
                })
            elif change < tolerance * 0.5:
                violations.append({
                    "type": "lage_insufficient_spread",
                    "baujahr": bj,
                    "size_class": sk,
                    "from_lage": prev_lage,
                    "to_lage": curr_lage,
                    "from_value": round(prev_val, 2),
                    "to_value": round(curr_val, 2),
                    "change_pct": round(change * 100, 1),
                    "severity": "info",
                    "message": (
                        f"[{bj}/{sk}] Small spread between '{prev_lage}' (€{prev_val:.2f}) "
                        f"and '{curr_lage}' (€{curr_val:.2f}) ({change:+.1%}). "
                        f"May be reasonable for some cities."
                    )
                })

    return violations


def check_positive_values(tables: list) -> list:
    """Check all numeric cell values are positive and non-zero."""
    issues = []
    for table in tables:
        lage = table.get("lage", "unknown")
        for ri, row in enumerate(table.get("rows", [])):
            for key, val in row.items():
                if key == "baujahr":
                    continue
                num = _extract_numeric_value(val)
                if num is not None and num <= 0:
                    issues.append({
                        "type": "non_positive_value",
                        "lage": lage,
                        "row": ri,
                        "baujahr": row.get("baujahr", "?"),
                        "field": key,
                        "value": val,
                        "severity": "error",
                        "message": (
                            f"[{lage}] Non-positive value {val} in row "
                            f"'{row.get('baujahr', '?')}', field '{key}'."
                        )
                    })
    return issues


def check_field_completeness(city_data: dict) -> list:
    """Check that no row has all-null/missing numeric fields."""
    issues = []
    for table in city_data.get("tables", []):
        lage = table.get("lage", "unknown")
        for ri, row in enumerate(table.get("rows", [])):
            non_null = sum(
                1 for k, v in row.items()
                if k != "baujahr" and _extract_numeric_value(v) is not None
            )
            if non_null == 0:
                issues.append({
                    "type": "empty_row",
                    "lage": lage,
                    "row": ri,
                    "baujahr": row.get("baujahr", "?"),
                    "severity": "error",
                    "message": (
                        f"[{lage}] Row '{row.get('baujahr', '?')}' has no numeric values."
                    )
                })
    return issues


def check_size_monotonicity(tables: list, tolerance: float = 0.05) -> list:
    """
    Check that for larger apartment sizes, the per-sqm rent is typically
    slightly lower (economy of scale). Not a strict rule — some cities
    deviate — but flag significant inversions.
    """
    violations = []
    for table in tables:
        lage = table.get("lage", "unknown")
        rows = sorted(table.get("rows", []), key=lambda r: _baujahr_sort_key(r.get("baujahr", "")))
        size_keys = [k for k in rows[0].keys() if k != "baujahr"] if rows else []

        # Try to infer size order from key names
        size_order = {}
        for k in size_keys:
            k_lower = k.lower().replace(" ", "_")
            if "unter" in k_lower or "bis" in k_lower:
                size_order[k] = 0  # small
            elif "ab" in k_lower or "über" in k_lower:
                size_order[k] = 3  # large
            else:
                size_order[k] = 1  # medium

        if len(size_order) < 2:
            continue

        for row in rows:
            bj = row.get("baujahr", "")
            prev_sk = None
            prev_val = None
            for sk in sorted(size_order, key=lambda s: size_order.get(s, 1)):
                val = _extract_numeric_value(row.get(sk))
                if val is None:
                    continue
                if prev_val is not None and prev_sk is not None:
                    change = (val - prev_val) / prev_val if prev_val > 0 else 0
                    # Larger size should cost less or same per sqm
                    if change > tolerance and size_order.get(sk, 1) > size_order.get(prev_sk, 1):
                        violations.append({
                            "type": "size_anomaly_larger_costs_more",
                            "lage": lage,
                            "baujahr": bj,
                            "from_sk": prev_sk,
                            "to_sk": sk,
                            "from_val": round(prev_val, 2),
                            "to_val": round(val, 2),
                            "change_pct": round(change * 100, 1),
                            "severity": "info",
                            "message": (
                                f"[{lage}/{bj}] Larger unit class '{sk}' costs €{val:.2f}/sqm "
                                f"vs '{prev_sk}' at €{prev_val:.2f}/sqm ({change:+.1%}). "
                                f"Unusual but not necessarily wrong."
                            )
                        })
                prev_sk = sk
                prev_val = val

    return violations


def run_all_sanity_checks(city_data: dict, tolerance: float = 0.05) -> dict:
    """Run all sanity checks on a city data dict and return consolidated results."""
    tables = city_data.get("tables", [])
    city = city_data.get("city", "Unknown")
    year = city_data.get("year", "?")

    check_results = {
        "city": city,
        "year": year,
        "status": "passed",
        "total_checks": 0,
        "errors": 0,
        "warnings": 0,
        "info": 0,
        "violations": [],
    }

    all_violations = []

    # 1. Baujahr monotonicity per Lage
    lage_names = list(set(t.get("lage", "") for t in tables))
    for lage in lage_names:
        violations = check_baujahr_monotonicity(tables, lage=lage, tolerance=tolerance)
        all_violations.extend(violations)

    # 2. Lage monotonicity (einfach < mittel < gut)
    violations = check_lage_monotonicity(tables, tolerance=tolerance)
    all_violations.extend(violations)

    # 3. Positive values
    violations = check_positive_values(tables)
    all_violations.extend(violations)

    # 4. Field completeness
    violations = check_field_completeness(city_data)
    all_violations.extend(violations)

    # 5. Size monotonicity (informational)
    violations = check_size_monotonicity(tables, tolerance=tolerance)
    all_violations.extend(violations)

    check_results["total_checks"] = len(all_violations)
    check_results["errors"] = sum(1 for v in all_violations if v.get("severity") == "error")
    check_results["warnings"] = sum(1 for v in all_violations if v.get("severity") == "warning")
    check_results["info"] = sum(1 for v in all_violations if v.get("severity") == "info")
    check_results["violations"] = all_violations

    if check_results["errors"] > 0:
        check_results["status"] = "failed"
    elif check_results["warnings"] > 0:
        check_results["status"] = "warning"
    else:
        check_results["status"] = "passed"

    return check_results
