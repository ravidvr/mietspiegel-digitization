"""
Mietspiegel digitization — validation framework.
Main module: orchestrates loading city data, running sanity checks,
cross-referencing against GdW aggregates, and generating reports.
"""
import json
import os
from datetime import datetime

from . import sanity_checks
from . import gdw_crossref


def load_city(path: str) -> dict:
    """Load a single city's Mietspiegel JSON data file."""
    with open(path) as f:
        return json.load(f)


def find_city_files(data_dir: str) -> list[str]:
    """Find all city JSON data files in the processed data directory."""
    files = []
    for fname in sorted(os.listdir(data_dir)):
        if fname.endswith(".json") and not fname.startswith("_"):
            files.append(os.path.join(data_dir, fname))
    return files


def validate_city(city_data: dict, gdw: dict, tolerance: float = 0.05) -> dict:
    """
    Run full validation on a single city: sanity checks + GdW cross-ref.
    Returns a combined validation report dict.
    """
    city = city_data.get("city", "Unknown")
    year = city_data.get("year", "?")

    # Run sanity checks
    sanity = sanity_checks.run_all_sanity_checks(city_data, tolerance=tolerance)

    # Run GdW cross-reference
    crossref = gdw_crossref.cross_reference_city(city_data, gdw)

    # Combine into report
    report = {
        "city": city,
        "year": year,
        "state": city_data.get("state", ""),
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

    # Compute overall status
    total_errors = sanity["errors"] + len(crossref["flags"])
    total_warnings = sanity["warnings"] + len(crossref["warnings"])

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
            "message": f"No city JSON files found in {data_dir}",
            "reports": [],
        }

    reports = []
    for cf in city_files:
        city_data = load_city(cf)
        report = validate_city(city_data, gdw, tolerance=tolerance)
        reports.append(report)

    return {
        "status": "complete",
        "cities_validated": len(reports),
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

    lines.append("═" * 60)
    lines.append(f"MIETSPIEGEL VALIDATION REPORT")
    lines.append(f"  {consolidated['timestamp']}")
    lines.append(f"  Cities validated: {consolidated['cities_validated']}")
    lines.append("═" * 60)

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
    lines.append("─" * 60)
    lines.append(f"OVERALL: {passed} passed, {warned} warnings, {failed} failed")
    lines.append(f"  {all_flags} total flags, {all_warnings} total warnings")
    lines.append("═" * 60)

    return "\n".join(lines)
