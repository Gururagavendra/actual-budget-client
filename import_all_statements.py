#!/usr/bin/env python3
"""
Import all bank statement PDFs to ActualBudget in chronological order.
"""

import sys
from pathlib import Path
from import_detailed import import_detailed_transactions

PDF_PASSWORD = "guru2111"
PDFS_DIR = "pdfs"

# Order: May -> June -> Aug -> Sep -> Oct -> Nov
PDF_ORDER = [
    "may_2025.pdf",
    "June_2025.pdf",
    "aug_2025.pdf",
    "sep_2025.pdf",
    "oct_2025.pdf",
    "Nov_2025.pdf"
]

def import_all_pdfs():
    """Import all PDFs in chronological order."""
    
    print("=" * 100)
    print("   IMPORTING ALL BANK STATEMENTS TO ACTUALBUDGET")
    print("=" * 100)
    
    pdfs_path = Path(PDFS_DIR)
    
    # Check all files exist
    missing = []
    for filename in PDF_ORDER:
        if not (pdfs_path / filename).exists():
            missing.append(filename)
    
    if missing:
        print(f"❌ Missing PDF files: {', '.join(missing)}")
        sys.exit(1)
    
    print(f"\n📁 Found all {len(PDF_ORDER)} PDFs")
    print("\n⚠️  This will import:")
    for i, filename in enumerate(PDF_ORDER, 1):
        print(f"   {i}. {filename}")
    
    response = input("\nProceed with import? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    # Import each PDF
    success_count = 0
    for i, filename in enumerate(PDF_ORDER, 1):
        pdf_path = pdfs_path / filename
        print(f"\n{'='*100}")
        print(f"[{i}/{len(PDF_ORDER)}] Processing {filename}...")
        print('='*100)
        
        try:
            import_detailed_transactions(str(pdf_path), password=PDF_PASSWORD, dry_run=False)
            success_count += 1
        except Exception as e:
            print(f"❌ Error importing {filename}: {e}")
            import traceback
            traceback.print_exc()
            
            response = input("\nContinue with remaining PDFs? (yes/no): ")
            if response.lower() != 'yes':
                break
    
    # Summary
    print("\n" + "=" * 100)
    print("   IMPORT SUMMARY")
    print("=" * 100)
    print(f"Successfully imported: {success_count}/{len(PDF_ORDER)} PDFs")
    
    if success_count == len(PDF_ORDER):
        print("\n🎉 All statements imported successfully!")
    else:
        print(f"\n⚠️  {len(PDF_ORDER) - success_count} PDF(s) failed to import")


if __name__ == "__main__":
    import_all_pdfs()
