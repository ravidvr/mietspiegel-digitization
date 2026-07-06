#!/usr/bin/env python3
"""
CLI entry point for the Mietspiegel validation framework.

Usage:
    python -m validate.run_validations                   # validate all cities
    python -m validate.run_validations --city berlin     # validate single city
    python -m validate.run_validations --data-dir /path  # custom data directory
    python -m validate.run_validations --json            # JSON output
    python -m validate.run_validations --tolerance 0.10  # custom tolerance
    python -m validate.run_validations --gdw /path/gdw.json  # custom reference
"""
import argparse
import json
import os
import sys

# Ensure the project root is on the path
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from validate import validate_all, load_city, validate_city, format_consolidated_summary, format_report_summary
from validate.gdw_crossref import load_gdw_data


def main():
    parser = argparse.ArgumentParser(
        description="Mietspiegel Digitization — Validation Framework"
    )
    parser.add_argument(
        "--data-dir",
        default=os.path.join(_project_root, "data", "processed"),
        help="Directory containing city JSON data files (default: data/processed/)",
    )
    parser.add_argument(
        "--gdw",
        default=os.path.join(_project_root, "data", "reference", "gdw_aggregate.json"),
        help="Path to GdW aggregate reference JSON (default: data/reference/gdw_aggregate.json)",
    )
    parser.add_argument(
        "--city", "-c",
        help="Validate a single city by filename (e.g. 'berlin' or 'berlin.json')",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON report instead of formatted text",
    )
    parser.add_argument(
        "--tolerance", "-t",
        type=float,
        default=0.05,
        help="Relative tolerance for monotonicity checks (default: 0.05 = 5%)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Save report to file (JSON if --json, else .txt)",
    )

    args = parser.parse_args()

    # Validate arguments exist
    if not os.path.exists(args.gdw):
        print(f"Error: GdW reference file not found: {args.gdw}")
        sys.exit(1)
    if not os.path.exists(args.data_dir):
        print(f"Error: Data directory not found: {args.data_dir}")
        sys.exit(1)

    if args.city:
        # Single city mode
        city_name = args.city.replace(".json", "")
        city_path = os.path.join(args.data_dir, f"{city_name}.json")
        if not os.path.exists(city_path):
            print(f"Error: City file not found: {city_path}")
            sys.exit(1)

        city_data = load_city(city_path)
        gdw = load_gdw_data(args.gdw)
        report = validate_city(city_data, gdw, tolerance=args.tolerance)

        if args.json:
            output = json.dumps(report, indent=2, ensure_ascii=False)
        else:
            output = format_report_summary(report)

        print(output)

        if args.output:
            out_path = args.output
            if args.json and not out_path.endswith(".json"):
                out_path += ".json"
            elif not args.json and not out_path.endswith(".txt"):
                out_path += ".txt"
            with open(out_path, "w") as f:
                f.write(output if args.json else output)
            print(f"\nReport saved to: {out_path}")

    else:
        # Batch mode — validate all cities
        consolidated = validate_all(
            data_dir=args.data_dir,
            reference_path=args.gdw,
            tolerance=args.tolerance,
        )

        if args.json:
            output = json.dumps(consolidated, indent=2, ensure_ascii=False)
        else:
            output = format_consolidated_summary(consolidated)

        print(output)

        if args.output:
            out_path = args.output
            if args.json and not out_path.endswith(".json"):
                out_path += ".json"
            elif not args.json and not out_path.endswith(".txt"):
                out_path += ".txt"
            with open(out_path, "w") as f:
                f.write(output if args.json else output)
            print(f"\nReport saved to: {out_path}")


if __name__ == "__main__":
    main()
