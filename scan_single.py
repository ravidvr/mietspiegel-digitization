#!/usr/bin/env python3
"""Scan all PDFs in data/raw/ for district-level (sub-city) rent tables — per-file with timeout."""
import json
import os
import re
import sys

import pdfplumber

RAW_DIR = "/Users/ruhvee/mietspiegel-digitization/data/raw"
OUTPUT_DIR = "/Users/ruhvee/mietspiegel-digitization/data/district_scan"

DISTRICT_KEYWORDS = [
    "bezirk", "stadtteil", "ortsteil", "quartier", "viertel",
    "stadtbezirk", "stadtkreis", "wohnviertel", "stadtgebiet",
    "bezirke", "stadtteile", "ortsteile"
]

def scan_single(pdf_path):
    """Scan a single PDF for district-level data."""
    filename = os.path.basename(pdf_path)
    result = {
        "filename": filename,
        "has_district_data": False,
        "total_pages": 0,
        "district_pages": [],
        "tables_found": [],
        "notes": ""
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            result["total_pages"] = total_pages
            
            district_pages = []
            
            # Phase 1: Scan all pages for district keywords
            for i in range(total_pages):
                page = pdf.pages[i]
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                
                text_lower = text.lower()
                matched_kw = None
                for kw in DISTRICT_KEYWORDS:
                    if kw in text_lower:
                        matched_kw = kw
                        break
                
                if matched_kw:
                    district_pages.append({
                        "page": i + 1,
                        "keyword": matched_kw,
                        "text": text
                    })
            
            result["district_pages"] = [(p["page"], p["keyword"]) for p in district_pages]
            
            if not district_pages:
                result["notes"] = "No district keywords found"
                return result
            
            # Phase 2: For each district page, extract tables
            for dp in district_pages:
                page_num = dp["page"]
                page = pdf.pages[page_num - 1]
                
                tables = []
                try:
                    tables = page.extract_tables()
                except Exception:
                    pass
                
                if not tables:
                    try:
                        tables = page.extract_tables({
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "snap_tolerance": 3,
                            "join_tolerance": 3,
                        })
                    except Exception:
                        pass
                
                if tables:
                    for t_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue
                        header = [str(c).strip() if c else "" for c in table[0][:10]]
                        sample = []
                        for row in table[1:8]:
                            sample.append([str(c).strip() if c else "" for c in row[:10]])
                        
                        result["has_district_data"] = True
                        result["tables_found"].append({
                            "page": page_num,
                            "table_index": t_idx,
                            "keyword": dp["keyword"],
                            "n_rows": len(table),
                            "n_cols": len(header),
                            "header": header,
                            "sample_rows": sample,
                            "method": "table"
                        })
                else:
                    # Fallback: extract relevant text lines
                    text = dp["text"]
                    lines = text.split('\n')
                    relevant = []
                    for line in lines:
                        line_lower = line.lower()
                        if any(kw in line_lower for kw in DISTRICT_KEYWORDS) or \
                           re.search(r'\d{1,2},\d{2}', line):
                            relevant.append(line.strip())
                    
                    if relevant:
                        result["has_district_data"] = True
                        result["tables_found"].append({
                            "page": page_num,
                            "table_index": 0,
                            "keyword": dp["keyword"],
                            "n_rows": len(relevant),
                            "n_cols": 0,
                            "header": [],
                            "sample_rows": [[l] for l in relevant[:10]],
                            "method": "text_lines"
                        })
    
    except Exception as e:
        result["notes"] = f"Error: {str(e)}"
    
    return result

if __name__ == "__main__":
    pdf_name = sys.argv[1]
    pdf_path = os.path.join(RAW_DIR, pdf_name)
    
    if not os.path.exists(pdf_path):
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)
    
    result = scan_single(pdf_path)
    print(json.dumps(result, ensure_ascii=False, default=str))
