#!/usr/bin/env python3
"""
Düsseldorf Mietspiegel extraction script.
Extract tables from the Düsseldorf Mietspiegel PDF and map to unified schema.
"""

import json
import sys
import os
import camelot
import pdfplumber
from pathlib import Path

PROJECT_ROOT = Path("/Users/ruhvee/mietspiegel-digitization")
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

def extract_with_camelot(pdf_path):
    """Try to extract tables using camelot-py."""
    print(f"Extracting with camelot-py from: {pdf_path}")
    
    # Try lattice mode first (for tables with borders)
    try:
        tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="lattice")
        if len(tables) > 0:
            print(f"  Lattice mode: {len(tables)} tables found")
            return tables
    except Exception as e:
        print(f"  Lattice mode failed: {e}")
    
    # Try stream mode (for tables without borders)
    try:
        tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="stream")
        if len(tables) > 0:
            print(f"  Stream mode: {len(tables)} tables found")
            return tables
    except Exception as e:
        print(f"  Stream mode failed: {e}")
    
    return None

def extract_with_pdfplumber(pdf_path):
    """Fallback: extract text and tables using pdfplumber."""
    print(f"Extracting with pdfplumber from: {pdf_path}")
    tables_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for j, table in enumerate(tables):
                print(f"  Page {i+1}, Table {j+1}: {len(table)} rows")
                tables_data.append({
                    "page": i + 1,
                    "table_index": j,
                    "rows": table
                })
    return tables_data

def map_to_schema(tables, source_url, pdf_filename):
    """
    Map extracted tables to the unified schema.
    
    Expected columns for Düsseldorf Mietspiegel table:
    - Baujahr (construction year period)
    - Wohnlage categories (einfach, mittel, gut)
    - Size categories (m²)
    - Rent values in €/m²
    """
    
    schema = {
        "city": "Duesseldorf",
        "city_display": "Düsseldorf",
        "state": "Nordrhein-Westfalen",
        "year": 2025,
        "type": "qualifizierter Mietspiegel",
        "lage_categories": [],
        "tables": [],
        "source_url": source_url,
        "source_pdf": pdf_filename,
        "extraction_date": "2026-07-06"
    }
    
    # TODO: Add actual extraction logic based on table structure
    # This will need manual inspection of the PDF first
    
    return schema

def main():
    pdf_path = None
    source_url = ""
    pdf_filename = ""
    
    # Check for PDF in raw directory
    for f in sorted(RAW_DIR.iterdir()):
        if f.suffix.lower() == ".pdf" and "duesseldorf" in f.name.lower():
            pdf_path = f
            pdf_filename = f.name
            break
    
    if not pdf_path:
        print("No Düsseldorf Mietspiegel PDF found in data/raw/")
        print("Place the PDF in:", RAW_DIR)
        print("Expected filename pattern: *duesseldorf*.pdf")
        sys.exit(1)
    
    print(f"Processing: {pdf_path}")
    
    # Extract with camelot
    camelot_tables = extract_with_camelot(pdf_path)
    
    # Print table previews
    if camelot_tables:
        for i, table in enumerate(camelot_tables):
            print(f"\n--- Table {i+1} ---")
            print(table.df.to_string())
    
    # Also extract with pdfplumber for comparison
    pdfplumber_tables = extract_with_pdfplumber(pdf_path)
    
    # Map to schema
    schema = map_to_schema(camelot_tables, source_url, pdf_filename)
    
    # Save
    output_path = PROCESSED_DIR / "duesseldorf.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {output_path}")

if __name__ == "__main__":
    main()
