#!/usr/bin/env python3
"""
Test detailed transaction extraction on all PDFs in pdfs/ folder.
"""

import os
from pathlib import Path
from import_detailed import parse_individual_transactions
from pdf_reader_ocr import extract_text_from_pdf, process_bank_statement

PDF_PASSWORD = "guru2111"
PDFS_DIR = "pdfs"

def test_all_pdfs():
    """Test all PDFs in pdfs directory."""
    pdf_files = sorted(Path(PDFS_DIR).glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in pdfs/ directory")
        return
    
    print("=" * 100)
    print(f"   TESTING {len(pdf_files)} BANK STATEMENT PDFs")
    print("=" * 100)
    
    results = []
    
    for pdf_path in pdf_files:
        print(f"\n{'='*100}")
        print(f"📄 {pdf_path.name}")
        print('='*100)
        
        try:
            # Get verified summary
            summary = process_bank_statement(str(pdf_path), PDF_PASSWORD)
            
            # Parse individual transactions
            pages_text = extract_text_from_pdf(str(pdf_path), PDF_PASSWORD)
            transactions = parse_individual_transactions(pages_text, summary['starting_balance'])
            
            # Calculate totals
            calc_deposits = sum(t['deposit'] for t in transactions)
            calc_withdrawals = sum(t['withdrawal'] for t in transactions)
            calc_final = summary['starting_balance'] + calc_deposits - calc_withdrawals
            
            # Verify
            balance_diff = abs(calc_final - summary['final_balance'])
            passed = balance_diff < 1.0
            
            result = {
                'file': pdf_path.name,
                'starting': summary['starting_balance'],
                'transactions': len(transactions),
                'deposits': calc_deposits,
                'withdrawals': calc_withdrawals,
                'final': summary['final_balance'],
                'calculated': calc_final,
                'diff': balance_diff,
                'passed': passed
            }
            results.append(result)
            
            print(f"\n📊 Results:")
            print(f"   Starting Balance:       ₹{result['starting']:>12,.2f}")
            print(f"   Transactions Extracted: {result['transactions']:>5}")
            print(f"   Deposits:               ₹{result['deposits']:>12,.2f}")
            print(f"   Withdrawals:            ₹{result['withdrawals']:>12,.2f}")
            print(f"   Expected Final:         ₹{result['final']:>12,.2f}")
            print(f"   Calculated Final:       ₹{result['calculated']:>12,.2f}")
            print(f"   Difference:             ₹{result['diff']:>12,.2f}")
            
            if passed:
                print(f"   ✅ PASSED - Balance verification successful!")
            else:
                print(f"   ❌ FAILED - Balance mismatch (diff: ₹{balance_diff:.2f})")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'file': pdf_path.name,
                'passed': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 100)
    print("   FINAL SUMMARY")
    print("=" * 100)
    print(f"\n{'File':<20} {'Txns':>6} {'Deposits':>15} {'Withdrawals':>15} {'Status':>10}")
    print("-" * 100)
    
    passed_count = 0
    for r in results:
        if 'error' in r:
            print(f"{r['file']:<20} {'ERROR':>6} {'':>15} {'':>15} {'❌ FAILED':>10}")
        else:
            status = "✅ PASSED" if r['passed'] else "❌ FAILED"
            print(f"{r['file']:<20} {r['transactions']:>6} ₹{r['deposits']:>13,.2f} ₹{r['withdrawals']:>13,.2f} {status:>10}")
            if r['passed']:
                passed_count += 1
    
    print("-" * 100)
    print(f"\nTotal: {passed_count}/{len(results)} PDFs passed verification")
    
    if passed_count == len(results):
        print("\n🎉 ALL TESTS PASSED! The detailed extraction method is working correctly.")
    else:
        print(f"\n⚠️  {len(results) - passed_count} PDF(s) failed verification. Please review.")


if __name__ == "__main__":
    test_all_pdfs()
