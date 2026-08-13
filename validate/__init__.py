"""
Mietspiegel digitization — validation framework.
Main module: orchestrates loading city data, running sanity checks,
cross-referencing against GdW aggregates, and generating reports.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List

from . import gdw_crossref, sanity_checks

SCHEMA_KEYS_A = {"city", "state", "year", "tables"}       # Standard Mietspiegel table schema
MATRIX_KEYS = {"lage_categories", "bauperiods", "size_groups", "values"}  # Matrix format
INDEX_FILES = {"mietspiegel_katalog.json", "stadt-index.json", "cities.json"}


def _is_skip_file(fname: str) -> bool:
    """Return True for non-data files that should be skipped."""
    if not fname.endswith(".json"):
        return True
    if fname.startswith("."):
        return True  # .gitkeep etc.
    fname_lower = fname.lower()
    if any(fname_lower == idx for idx in INDEX_FILES):
        return True
    if "katalog" in fname_lower or "index" in fname_lower:
        return True
    return False


def detect_schema(data: dict) -> str:
    """Detect the schema type of a city data file."""
    if "tables" in data and isinstance(data.get("tables"), list) and len(data["tables"]) > 0:
        return "tables"
    if "matrix" in data and isinstance(data.get("matrix"), dict):
        return "matrix"
    if "current_edition" in data:
        return "metadata_only"
    if "cities" in data or "meta" in data:
        return "catalog"
    return "unknown"


def normalize_city_data(data: dict) -> dict | None:
    """
    Normalize a city data file to the standard validation format.
    Returns None if the data cannot be normalized (no rent tables).
    """
    schema = detect_schema(data)

    if schema == "catalog":
        return None  # Skip index/catalog files

    if schema == "metadata_only":
        return None  # No rent tables to validate

    if schema == "unknown":
        return None

    if schema == "tables":
        return {
            "city": data.get("city", "Unknown"),
            "year": data.get("year", 0),
            "state": data.get("state", ""),
            "tables": data.get("tables", []),
            "source_url": data.get("source_url", ""),
        }

    if schema == "matrix":
        return normalize_matrix_schema(data)

    return None


def normalize_matrix_schema(data: dict) -> dict | None:
    """
    Normalize the 'matrix' format (e.g. dresden-extended.json) to the
    standard tables format.

    Matrix format:
      city: { name, slug, state, ... }
      matrix: { lage_categories: [...], bauperiods: [...],
                size_groups: [...], values: {lage_key: {periode_key: {size_key: val}}} }
    """
    city_info = data.get("city", {})
    if isinstance(city_info, dict):
        city_name = city_info.get("name", city_info.get("display", "Unknown"))
        state = city_info.get("state", "")
    else:
        city_name = str(city_info)
        state = data.get("city_state", "")

    matrix = data.get("matrix", {})
    lage_cats = matrix.get("lage_categories", [])
    bauperiods = matrix.get("bauperiods", [])
    size_groups = matrix.get("size_groups", [])
    values = matrix.get("values", {})
    year = data.get("year", 0)

    supported_lages = ["einfach", "mittel", "gut"]
    tables = []
    for lc in lage_cats:
        lc_key = lc.get("key", lc) if isinstance(lc, dict) else lc
        lc_label = lc.get("label", lc_key) if isinstance(lc, dict) else lc_key
        lc_lower = str(lc_key).lower()

        # Skip unsupported Lage
        if lc_lower not in supported_lages:
            continue

        rows = []
        for bp in bauperiods:
            bp_key = bp.get("key", bp) if isinstance(bp, dict) else bp
            bp_label = bp.get("label", bp_key) if isinstance(bp, dict) else bp_key
            row = {"baujahr": str(bp_label)}

            for sg in size_groups:
                sg_key = sg.get("key", sg) if isinstance(sg, dict) else sg
                sg_label = sg.get("label", sg_key) if isinstance(sg, dict) else sg_key

                val = values.get(str(lc_key), {}).get(str(bp_key), {}).get(str(sg_key))
                if val is not None:
                    col_key = str(sg_label).replace(" ", "_").lower()
                    row[col_key] = float(val)

            rows.append(row)

        if rows:
            tables.append({"lage": lc_lower, "lage_label": lc_label, "rows": rows})

    if not tables:
        return None

    return {
        "city": city_name,
        "year": year,
        "state": state,
        "tables": tables,
        "source_url": data.get("source_url", data.get("meta", {}).get("source_url", "")),
    }


def load_city(path: str) -> dict:
    """Load and normalize a single city's Mietspiegel data file."""
    with open(path) as f:
        raw = json.load(f)
    city_data = normalize_city_data(raw)
    if city_data is None:
        raise ValueError(f"File {path} does not contain Mietspiegel rent tables")
    return city_data


def find_city_files(data_dir: str) -> list[str]:
    """Find all city data files in the processed data directory."""
    files = []
    for fname in sorted(os.listdir(data_dir)):
        if _is_skip_file(fname):
            continue
        fpath = os.path.join(data_dir, fname)
        if not os.path.isfile(fpath):
            continue
        # Try to load — skip files that don't normalize to rent data
        try:
            with open(fpath) as f:
                raw = json.load(f)
            if normalize_city_data(raw) is not None:
                files.append(fpath)
            else:
                pass  # skip silently
        except (json.JSONDecodeError, ValueError):
            pass  # skip invalid files
    return files


def validate_city(city_data: dict, gdw: dict, tolerance: float = 0.05) -> dict:
    """
    Run full validation on a single city: sanity checks + GdW cross-ref.
    Returns a combined validation report dict.
    """
    city = city_data.get("city", "Unknown")
    year = city_data.get("year", "?")
    state = city_data.get("state", "")
    tables = city_data.get("tables", [])

    # Run sanity checks
    sanity = sanity_checks.run_all_sanity_checks(city_data, tolerance=tolerance)

    # Run GdW cross-reference
    crossref = gdw_crossref.cross_reference_city(city_data, gdw)

    # Combine into report
    report = {
        "city": city,
        "year": year,
        "state": state,
        "tables_count": len(tables),
        "rows_count": sum(len(t.get("rows", [])) for t in tables),
        "lage_categories": [t.get("lage", "?") for t in tables],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "overall_status": "passed",
        "sanity_checks": sanity,
        "gdw_crossref": {
            "city_average_rent": crossref["city_average_rent"],
            "gdw_national_average": crossref["gdw_national_average"],
            "gdw_state_average": crossref["gdw_state_average"],
            "pct_vs_national": crossref["pct_vs_national"],
            "pct_vs_state": crossref["pct_vs_state"],
            "flags": crossref["flags"],
            "warnings": crossref["warnings"],
        },
        "summary": {
            "total_flags": 0,
            "total_warnings": 0,
        },
    }

    # Compute overall status.
    # GdW cross-ref flags now only fire on GENUINE anomalies (recalibrated 2026-08):
    #   - city BELOW GdW state range low (new lease < existing contract, implausible)
    #   - implausible absolute values (< €2 or > €25/m²)
    # Being ABOVE the GdW state average is expected (new-lease > existing-contract) and
    # no longer produces any flag. These genuine anomalies surface as warnings, not errors.
    total_errors = sanity["errors"]
    total_warnings = sanity["warnings"] + len(crossref["flags"]) + len(crossref["warnings"])

    report["summary"]["total_flags"] = total_errors
    report["summary"]["total_warnings"] = total_warnings

    if total_errors > 0:
        report["overall_status"] = "failed"
    elif total_warnings > 0:
        report["overall_status"] = "warning"

    return report


def validate_all(data_dir: str, reference_path: str = "auto",
                 tolerance: float = 0.05) -> dict:
    """
    Run validation on all city data files found in data_dir.
    Returns a consolidated validation report.
    """
    if reference_path is None or reference_path == "auto":
        reference_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "data", "reference", "gdw_aggregate.json")
        )

    gdw = gdw_crossref.load_gdw_data(reference_path)
    city_files = find_city_files(data_dir)

    if not city_files:
        return {
            "status": "no_data",
            "message": f"No city Mietspiegel tables found in {data_dir}",
            "reports": [],
        }

    reports = []
    errors = []
    for cf in city_files:
        try:
            city_data = load_city(cf)
            report = validate_city(city_data, gdw, tolerance=tolerance)
            reports.append(report)
        except Exception as e:
            errors.append({"file": cf, "error": str(e)})

    return {
        "status": "complete",
        "cities_validated": len(reports),
        "error_count": len(errors),
        "errors": errors,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reports": reports,
    }


def format_report_summary(report: dict) -> str:
    """Format a validation report as a human-readable string."""
    lines = []
    city = report["city"]
    status = report["overall_status"]
    status_icon = {"passed": "✓", "warning": "⚠", "failed": "✗"}.get(status, "?")

    lines.append(f"{status_icon} {city} ({report.get('year', '?')}) — {status.upper()}")
    lines.append(f"   Tables: {report.get('tables_count', 0)} lage categories, "
                 f"{report.get('rows_count', 0)} total rows")

    # GdW cross-ref highlights
    cref = report.get("gdw_crossref", {})
    avg = cref.get("city_average_rent", "?")
    nat = cref.get("gdw_national_average", "?")
    st_avg = cref.get("gdw_state_average", "N/A")
    pct_st = cref.get("pct_vs_state")
    pct_nat = cref.get("pct_vs_national")

    lines.append(f"   Average rent: €{avg}/sqm")
    if st_avg:
        lines.append(f"   vs GdW state avg: €{st_avg}/sqm ({pct_st:+.1f}%)")
    lines.append(f"   vs GdW national avg: €{nat}/sqm ({pct_nat:+.1f}%)")

    if cref.get("flags"):
        lines.append(f"   ⚑ Flags ({len(cref['flags'])}):")
        for f in cref["flags"]:
            lines.append(f"      ✗ {f}")

    if cref.get("warnings"):
        for w in cref["warnings"]:
            lines.append(f"      ⚠ {w}")

    # Sanity check violations
    sc = report.get("sanity_checks", {})
    if sc.get("errors", 0) > 0 or sc.get("warnings", 0) > 0:
        lines.append(f"   Sanity checks: {sc.get('errors', 0)} errors, {sc.get('warnings', 0)} warnings")
        for v in sc.get("violations", []):
            if v.get("severity") in ("error", "warning"):
                icon = "✗" if v["severity"] == "error" else "⚠"
                lines.append(f"      {icon} {v['message']}")

    return "\n".join(lines)


def format_consolidated_summary(consolidated: dict) -> str:
    """Format the full validation run as a human-readable summary."""
    lines = []
    status = consolidated["status"]

    if status == "no_data":
        lines.append("No city data files to validate.")
        lines.append(f"  {consolidated['message']}")
        return "\n".join(lines)

    lines.append("═" * 70)
    lines.append("MIETSPIEGEL VALIDATION REPORT")
    lines.append(f"  Run: {consolidated['timestamp']}")
    lines.append(f"  Cities validated: {consolidated['cities_validated']}")
    if consolidated.get("error_count", 0) > 0:
        lines.append(f"  Files skipped (parse errors): {consolidated['error_count']}")
    lines.append("═" * 70)

    all_flags = 0
    all_warnings = 0
    passed = failed = warned = 0

    for report in consolidated["reports"]:
        lines.append("")
        lines.append(format_report_summary(report))

        s = report["overall_status"]
        if s == "failed":
            failed += 1
        elif s == "warning":
            warned += 1
        else:
            passed += 1
        all_flags += report["summary"]["total_flags"]
        all_warnings += report["summary"]["total_warnings"]

    lines.append("")
    lines.append("─" * 70)
    lines.append(f"OVERALL: {passed} passed, {warned} warnings, {failed} failed")
    lines.append(f"  {all_flags} total flags, {all_warnings} total warnings")
    if consolidated.get("error_count", 0) > 0:
        lines.append(f"  {consolidated['error_count']} files with parse errors (see --json for details)")
    lines.append("═" * 70)

    return "\n".join(lines)
