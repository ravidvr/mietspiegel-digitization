#!/usr/bin/env python3
"""
Berlin Rent → BigQuery → Looker Studio — Complete Pipeline
===========================================================
One command deploys all Berlin data to BigQuery and prints
the Looker Studio connection URL.

PREREQUISITE (one-time):
    gcloud auth login dvrravi@gmail.com

USAGE:
    python3 scripts/deploy_berlin.py --project=YOUR_GCP_PROJECT_ID
    
    If you don't have a GCP project:
    1. Go to https://console.cloud.google.com/projectcreate
    2. Create a project (free — BigQuery Sandbox needs no billing)
    3. Run this script with --project=PROJECT_ID

Then open Looker Studio:
    https://lookerstudio.google.com/
    → Create → Data Source → BigQuery
    → Select project → dataset: berlin_rent → table: rent_cells
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"

TABLES = {
    "rent_cells": {
        "file": "berlin_rent_cells.csv",
        "schema": "city:STRING,lage:STRING,baujahr:STRING,size_class:STRING,size_m2:INTEGER,rent_per_sqm:FLOAT,rent_total:FLOAT,year:INTEGER",
        "partition": "year",
    },
    "districts": {
        "file": "berlin_districts.csv",
        "schema": "district:STRING,avg_rent_per_sqm:FLOAT,einfach_pct:FLOAT,mittel_pct:FLOAT,gut_pct:FLOAT,total_addresses:INTEGER,gap_vs_avg_pct:FLOAT",
    },
    "mietspiegel_2024": {
        "file": "berlin_mietspiegel_2024.csv",
        "schema": "lage:STRING,baujahr:STRING,bis_40:FLOAT,_40_60:FLOAT,_60_90:FLOAT,ueber_90:FLOAT",
    },
}

VIEWS_SQL = """
CREATE OR REPLACE VIEW berlin_rent.vw_affordable AS
SELECT *, rent_total / 2450.0 * 100 AS burden_pct,
  CASE WHEN rent_total <= 735 THEN 'YES' ELSE 'NO' END AS affordable_30pct
FROM berlin_rent.rent_cells WHERE year = 2024 ORDER BY rent_total;

CREATE OR REPLACE VIEW berlin_rent.vw_district_affordability AS
SELECT *, avg_rent_per_sqm * 60 AS rent_60m2,
  (avg_rent_per_sqm * 60) / 2450.0 * 100 AS burden_60m2_pct
FROM berlin_rent.districts ORDER BY avg_rent_per_sqm;
"""


def run(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(f"  ✗ {r.stderr[:200]}")
    else:
        print(f"  ✓ {r.stdout.strip()[:100]}")
    return r


def deploy(project_id: str):
    dataset = f"{project_id}:berlin_rent"
    
    # 1. Check auth
    print("1. Checking gcloud auth...")
    r = run("gcloud auth list --format='value(account)'")
    if r.returncode != 0 or not r.stdout.strip():
        print("\n❌ Not authenticated. Run: gcloud auth login dvrravi@gmail.com")
        sys.exit(1)
    print(f"   Authenticated as: {r.stdout.strip()}")
    
    # 2. Create dataset
    print(f"\n2. Creating dataset {dataset}...")
    run(f"bq mk --dataset --location=europe-west3 {dataset}")
    
    # 3. Load tables
    for table_name, config in TABLES.items():
        csv_path = EXPORTS / config["file"]
        if not csv_path.exists():
            print(f"   ⚠️  Missing: {csv_path}")
            continue
        
        full_table = f"{dataset}.{table_name}"
        rows = sum(1 for _ in open(csv_path)) - 1
        print(f"\n3. Loading {table_name} ({rows} rows)...")
        
        cmd = [
            "bq", "load",
            "--source_format=CSV",
            "--skip_leading_rows=1",
            "--replace",
            full_table,
            str(csv_path),
            config["schema"],
        ]
        if "partition" in config:
            cmd.insert(3, f"--time_partitioning_field={config['partition']}")
        
        run(" ".join(cmd))
    
    # 4. Create views
    print("\n4. Creating analytical views...")
    for stmt in VIEWS_SQL.strip().split(";\n"):
        stmt = stmt.strip()
        if stmt:
            run(f"bq query --use_legacy_sql=false '{stmt}'")
    
    # 5. Success + Looker Studio link
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ✓ Berlin rent data deployed to BigQuery!                   ║
╠══════════════════════════════════════════════════════════════╣
║  Dataset: {dataset:<45s} ║
║  Tables:  {str(len(TABLES)):<49s} ║
║  Views:   2 (vw_affordable, vw_district_affordability)      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  LOOKER STUDIO:                                              ║
║  1. Open https://lookerstudio.google.com/                    ║
║  2. Create → Data Source → BigQuery                         ║
║  3. Select: {project_id} → berlin_rent → rent_cells         ║
║  4. Build your dashboard                                    ║
║                                                              ║
║  Direct link:                                                ║
║  https://lookerstudio.google.com/datasources/create?        ║
║    connectorId=bigQuery                                      ║
║                                                              ║
║  KEY CHARTS TO BUILD:                                        ║
║  • Bar chart: district vs avg_rent_per_sqm                  ║
║  • Stacked bar: Wohnlage % by district                      ║
║  • Table: Mietspiegel 2024 with conditional formatting      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy Berlin rent data to BigQuery")
    parser.add_argument("--project", required=True, help="GCP project ID")
    args = parser.parse_args()
    deploy(args.project)
