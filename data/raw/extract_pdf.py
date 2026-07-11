import fitz
doc = fitz.open("/Users/ruhvee/mietspiegel-digitization/data/raw/duesseldorf-mietspiegel-2024.pdf")
print(f"Pages: {len(doc)}")
for i, page in enumerate(doc):
    print(f"\n=== PAGE {i+1} ===")
    text = page.get_text()
    print(text)
doc.close()
