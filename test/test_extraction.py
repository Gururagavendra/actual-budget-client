#!/usr/bin/env python3
"""Quick test of transaction extraction"""

from pdf_reader_ocr import extract_text_from_pdf

pdf_path = "pdfs/aug_2025.pdf"
password = "guru2111"

pages_text = extract_text_from_pdf(pdf_path, password)

# Print first page to see the structure
print("=== FIRST PAGE TEXT (first 100 lines) ===\n")
lines = pages_text[0].split('\n')
for i, line in enumerate(lines[:100], 1):
    print(f"{i:3d}: {line}")
