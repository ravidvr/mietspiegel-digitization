#!/usr/bin/env python3
"""Scan all PDFs in data/raw/ for district-level (sub-city) rent tables."""
import json
import os
import re

import pdfplumber

RAW_DIR = "/Users/ruhvee/mietspiegel-digitization/data/raw"

# Keywords that indicate district-level data
DISTRICT_KEYWORDS = [
    "bezirk", "stadtteil", "ortsteil", "quartier", "viertel",
    "stadtbezirk", "stadtkreis", "wohnviertel", "stadtgebiet",
    "bezirke", "stadtteile", "ortsteile"
]

def extract_text_from_pdf(pdf_path, max_pages=None):
    """Extract text per page from PDF."""
    pages_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            limit = min(total, max_pages) if max_pages else total
            for i in range(limit):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                pages_text.append((i+1, text))
    except Exception as e:
        print(f"  ERROR opening {pdf_path}: {e}")
    return pages_text

def find_district_pages(pages_text):
    """Find pages that mention district keywords."""
    district_pages = []
    for page_num, text in pages_text:
        text_lower = text.lower()
        for kw in DISTRICT_KEYWORDS:
            if kw in text_lower:
                district_pages.append((page_num, kw, text))
                break
    return district_pages

def extract_tables_from_page(pdf_path, page_num):
    """Extract tables from a specific page."""
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num <= len(pdf.pages):
                page = pdf.pages[page_num - 1]
                # Try default table extraction
                tables = page.extract_tables()
                # Also try with explicit settings for borderless tables
                if not tables:
                    tables = page.extract_tables({
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "snap_tolerance": 3,
                        "join_tolerance": 3,
                    })
    except Exception as e:
        print(f"  ERROR extracting tables from page {page_num}: {e}")
    return tables

def get_table_summary(table, max_rows=5, max_cols=8):
    """Summarize a table: columns and first N rows."""
    if not table:
        return None
    # Get header (first row)
    header = [str(c).strip() if c else "" for c in table[0][:max_cols]]
    # Get sample rows
    sample = []
    for row in table[1:max_rows+1]:
        sample.append([str(c).strip() if c else "" for c in row[:max_cols]])
    return {
        "n_rows": len(table),
        "n_cols": len(header),
        "header": header,
        "sample_rows": sample,
    }

def scan_pdf(pdf_path):
    """Scan a single PDF for district-level data."""
    filename = os.path.basename(pdf_path)
    print(f"\n{'='*60}")
    print(f"Scanning: {filename}")
    print(f"{'='*60}")
    
    result = {
        "filename": filename,
        "has_district_data": False,
        "district_pages": [],
        "tables_found": [],
        "notes": ""
    }
    
    # Extract all text
    pages_text = extract_text_from_pdf(pdf_path)
    if not pages_text:
        result["notes"] = "Could not extract text (may be scanned/image PDF)"
        return result
    
    result["total_pages"] = len(pages_text)
    
    # Find pages mentioning district keywords
    district_pages = find_district_pages(pages_text)
    
    if not district_pages:
        result["notes"] = "No district keywords (Bezirk/Stadtteil/Ortsteil/etc.) found in text"
        # Still check for tables just in case
        return result
    
    print(f"  Found district keywords on {len(district_pages)} pages")
    
    # For each district page, try to extract tables
    for page_num, keyword, text in district_pages:
        print(f"  Page {page_num}: keyword='{keyword}'")
        
        # Extract tables from this page
        tables = extract_tables_from_page(pdf_path, page_num)
        
        if tables:
            for t_idx, table in enumerate(tables):
                summary = get_table_summary(table)
                if summary and summary["n_rows"] > 1:
                    result["has_district_data"] = True
                    result["tables_found"].append({
                        "page": page_num,
                        "table_index": t_idx,
                        "keyword_matched": keyword,
                        "summary": summary
                    })
                    print(f"    Table {t_idx}: {summary['n_rows']} rows, {summary['n_cols']} cols")
                    print(f"    Header: {summary['header']}")
                    if summary["sample_rows"]:
                        print(f"    First row: {summary['sample_rows'][0]}")
        else:
            # No tables extracted - check text content for district-like patterns
            # Look for lines with district names followed by numbers (rent values)
            lines = text.split('\n')
            district_lines = []
            for line in lines:
                line_lower = line.lower()
                # Check if line has a district keyword or looks like data
                if any(kw in line_lower for kw in DISTRICT_KEYWORDS) or \
                   re.search(r'\d{1,2},\d{2}', line):
                    district_lines.append(line.strip())
            
            if district_lines:
                result["has_district_data"] = True
                result["tables_found"].append({
                    "page": page_num,
                    "table_index": 0,
                    "keyword_matched": keyword,
                    "summary": {
                        "n_rows": len(district_lines),
                        "n_cols": 0,
                        "header": [],
                        "sample_rows": [[l] for l in district_lines[:10]],
                        "extraction_method": "text_lines"
                    }
                })
                print(f"    Text-based extraction: {len(district_lines)} relevant lines")
                for dl in district_lines[:3]:
                    print(f"      > {dl}")
    
    # If we still haven't found tables but have district keywords,
    # look at the text more carefully
    if not result["tables_found"]:
        for page_num, keyword, text in district_pages:
            lines = text.split('\n')
            relevant = []
            for line in lines:
                if any(kw in line.lower() for kw in DISTRICT_KEYWORDS):
                    relevant.append(line.strip())
            if relevant:
                result["has_district_data"] = True
                result["tables_found"].append({
                    "page": page_num,
                    "table_index": 0,
                    "keyword_matched": keyword,
                    "summary": {
                        "n_rows": len(relevant),
                        "n_cols": 0,
                        "header": [],
                        "sample_rows": [[l] for l in relevant[:10]],
                        "extraction_method": "text_lines_fallback"
                    }
                })
    
    if not result["tables_found"]:
        result["notes"] = f"District keywords found on {len(district_pages)} pages but no tables/data extracted"
    
    return result

def main():
    pdfs = sorted([f for f in os.listdir(RAW_DIR) if f.lower().endswith('.pdf')])
    print(f"Found {len(pdfs)} PDFs to scan")
    
    all_results = []
    for pdf in pdfs:
        pdf_path = os.path.join(RAW_DIR, pdf)
        result = scan_pdf(pdf_path)
        all_results.append(result)
    
    # Summary
    print(f"\n\n{'#'*60}")
    print("SUMMARY REPORT")
    print(f"{'#'*60}")
    
    has_district = [r for r in all_results if r["has_district_data"]]
    no_district = [r for r in all_results if not r["has_district_data"]]
    
    print(f"\nPDFs WITH district-level data: {len(has_district)}/{len(all_results)}")
    for r in has_district:
        print(f"  ✓ {r['filename']}")
        for t in r["tables_found"]:
            s = t["summary"]
            print(f"    Page {t['page']}: {s['n_rows']} rows, {s['n_cols']} cols, method={s.get('extraction_method','table')}")
            if s["header"]:
                print(f"      Header: {s['header']}")
            if s["sample_rows"]:
                print(f"      Sample: {s['sample_rows'][0]}")
    
    print(f"\nPDFs WITHOUT district-level data: {len(no_district)}/{len(all_results)}")
    for r in no_district:
        print(f"  ✗ {r['filename']}: {r.get('notes','no district keywords')}")
    
    # Save full results as JSON
    output_path = "/Users/ruhvee/mietspiegel-digitization/data/district_scan_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nFull results saved to: {output_path}")

if __name__ == "__main__":
    main()
