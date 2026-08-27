#!/usr/bin/env python3
"""
Berlin Rent Data → BigQuery Upload Script
==========================================
Uploads CSV exports to BigQuery Sandbox (free tier).

PREREQUISITES:
  pip install google-cloud-bigquery
  gcloud auth application-default login
  gcloud config set project YOUR_PROJECT_ID

Or use the BigQuery web console:
  1. Go to https://console.cloud.google.com/bigquery
  2. Create dataset: berlin_rent
  3. Create tables from CSV uploads in exports/

Usage:
  python3 scripts/upload_to_bigquery.py --project=YOUR_PROJECT_ID
"""

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"

TABLES = {
    "berlin_rent.mietspiegel_2024": {
        "file": "berlin_mietspiegel_2024.csv",
        "schema": [
            ("lage", "STRING"),
            ("baujahr", "STRING"),
            ("bis_40", "FLOAT"),
            ("_40_60", "FLOAT"),
            ("_60_90", "FLOAT"),
            ("ueber_90", "FLOAT"),
        ]
    },
    "berlin_rent.rent_cells": {
        "file": "berlin_rent_cells.csv",
        "schema": [
            ("city", "STRING"),
            ("lage", "STRING"),
            ("baujahr", "STRING"),
            ("size_class", "STRING"),
            ("size_m2", "INTEGER"),
            ("rent_per_sqm", "FLOAT"),
            ("rent_total", "FLOAT"),
            ("year", "INTEGER"),
        ],
        "partition": "year",
        "cluster": ["lage", "baujahr"],
    },
    "berlin_rent.districts": {
        "file": "berlin_districts.csv",
        "schema": [
            ("district", "STRING"),
            ("avg_rent_per_sqm", "FLOAT"),
            ("einfach_pct", "FLOAT"),
            ("mittel_pct", "FLOAT"),
            ("gut_pct", "FLOAT"),
            ("total_addresses", "INTEGER"),
            ("gap_vs_avg_pct", "FLOAT"),
        ]
    },
    "berlin_rent.historical_trend": {
        "file": "berlin_historical_trend.csv",
        "schema": [
            ("city", "STRING"),
            ("year", "INTEGER"),
            ("base_rent_per_sqm", "FLOAT"),
            ("mietspiegel_type", "STRING"),
            ("period", "STRING"),
        ],
        "partition": "year",
    },
    "berlin_rent.mietpreisbremse_analysis": {
        "file": "berlin_mietpreisbremse_analysis.csv",
        "schema": [
            ("metric", "STRING"),
            ("value", "FLOAT"),
            ("unit", "STRING"),
        ]
    },
}


def upload_via_bq_cli(project_id: str) -> bool:
    """Upload using bq command-line tool (fastest)."""
    import subprocess
    
    # Create dataset
    subprocess.run(
        ["bq", "mk", "--dataset", f"{project_id}:berlin_rent"],
        capture_output=True
    )
    
    for table_id, config in TABLES.items():
        csv_path = EXPORTS / config["file"]
        if not csv_path.exists():
            print(f"⚠️  Missing: {csv_path}")
            continue
        
        full_table = f"{project_id}:{table_id}"
        cmd = [
            "bq", "load",
            "--source_format=CSV",
            "--skip_leading_rows=1",
            "--replace",
            full_table,
            str(csv_path),
        ]
        
        # Add schema
        schema_str = ",".join(f"{name}:{dtype}" for name, dtype in config["schema"])
        cmd.append(schema_str)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            lines = sum(1 for _ in open(csv_path)) - 1
            print(f"✓ {table_id} — {lines} rows")
        else:
            print(f"✗ {table_id}: {result.stderr[:200]}")
    
    return True


def upload_via_python_sdk(project_id: str) -> bool:
    """Upload using google-cloud-bigquery Python SDK."""
    from google.cloud import bigquery
    
    client = bigquery.Client(project=project_id)
    
    # Create dataset
    dataset_id = f"{project_id}.berlin_rent"
    try:
        client.get_dataset(dataset_id)
        print(f"Dataset {dataset_id} exists")
    except Exception:
        client.create_dataset(dataset_id)
        print(f"Created dataset {dataset_id}")
    
    for table_id, config in TABLES.items():
        csv_path = EXPORTS / config["file"]
        if not csv_path.exists():
            print(f"⚠️  Missing: {csv_path}")
            continue
        
        full_table = f"{project_id}.{table_id}"
        
        # Build schema
        schema = [
            bigquery.SchemaField(name, dtype)
            for name, dtype in config["schema"]
        ]
        
        # Load job config
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            skip_leading_rows=1,
            source_format=bigquery.SourceFormat.CSV,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        
        # Optional partitioning/clustering
        if "partition" in config:
            job_config.time_partitioning = bigquery.TimePartitioning(
                field=config["partition"]
            )
        if "cluster" in config:
            job_config.clustering_fields = config["cluster"]
        
        with open(csv_path, "rb") as f:
            job = client.load_table_from_file(f, full_table, job_config=job_config)
        job.result()
        
        table = client.get_table(full_table)
        print(f"✓ {table_id} — {table.num_rows} rows")
    
    return True


def print_console_instructions():
    """Print manual BigQuery web console upload instructions."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  BIGQUERY WEB CONSOLE UPLOAD INSTRUCTIONS                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Go to https://console.cloud.google.com/bigquery          ║
║  2. Create a new project (or use existing)                   ║
║  3. In the Explorer, click "Create Dataset"                  ║
║     Dataset ID: berlin_rent                                  ║
║     Location: europe-west3 (Frankfurt)                       ║
║                                                              ║
║  4. For each CSV file in exports/, click "Create Table":     ║
║     Source: Upload > select the CSV file                     ║
║     Table name: see below                                     ║
║     Schema: Auto-detect (or use berlin_bigquery_schema.sql)  ║
║                                                              ║
║  Files to upload:                                            ║
║""")
    for table_id, config in TABLES.items():
        f = config["file"]
        path = EXPORTS / f
        rows = sum(1 for _ in open(path)) - 1 if path.exists() else 0
        print(f"║    {f:<45s} → {table_id:<30s} ({rows} rows) ║")
    print("""║                                                              ║
║  5. After upload, open berlin_bigquery_schema.sql             ║
║     and run the CREATE VIEW statements to create the          ║
║     analytical views (vw_affordable, vw_district_*, etc.)    ║
║                                                              ║
║  6. Connect Tableau Public to your BigQuery dataset           ║
║     File > New > Google BigQuery > select project/dataset    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload Berlin rent data to BigQuery")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--method", choices=["bq", "sdk", "console"], default="console",
                       help="Upload method: bq (CLI), sdk (Python), console (print instructions)")
    args = parser.parse_args()
    
    if args.method == "console":
        print_console_instructions()
    elif args.method == "bq":
        upload_via_bq_cli(args.project)
    elif args.method == "sdk":
        try:
            upload_via_python_sdk(args.project)
        except ImportError:
            print("google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery")
            print_console_instructions()
