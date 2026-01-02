import os
import json
from pdf_reader_ocr import process_bank_statement


def test_all_pdfs():
    """Test all PDFs in the pdf folder."""
    pdf_folder = "pdf"
    password = "guru2111"
    
    # Get all PDF files
    pdf_files = sorted([f for f in os.listdir(pdf_folder) if f.endswith('.pdf')])
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    print("=" * 80)
    
    results = []
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        print(f"\n{'='*80}")
        print(f"PROCESSING: {pdf_file}")
        print(f"{'='*80}")
        
        try:
            result = process_bank_statement(pdf_path, password)
            
            # Verify calculation
            calculated = result['starting_balance'] + result['total_deposits'] - result['total_withdrawals']
            verification_pass = abs(calculated - result['final_balance']) < 0.01
            
            results.append({
                'file': pdf_file,
                'starting_balance': result['starting_balance'],
                'total_deposits': result['total_deposits'],
                'total_withdrawals': result['total_withdrawals'],
                'final_balance': result['final_balance'],
                'calculated_balance': calculated,
                'verification': '✅ PASS' if verification_pass else '❌ FAIL',
                'error': None
            })
            
            print(f"\n{'='*80}")
            print(f"RESULT: {pdf_file}")
            print(f"{'='*80}")
            print(f"Starting Balance:    {result['starting_balance']:>15,.2f}")
            print(f"Total Deposits:      {result['total_deposits']:>15,.2f}")
            print(f"Total Withdrawals:   {result['total_withdrawals']:>15,.2f}")
            print(f"Final Balance:       {result['final_balance']:>15,.2f}")
            print(f"Calculated Balance:  {calculated:>15,.2f}")
            print(f"Verification:        {results[-1]['verification']}")
            
        except Exception as e:
            print(f"\n❌ ERROR processing {pdf_file}: {e}")
            results.append({
                'file': pdf_file,
                'error': str(e),
                'verification': '❌ ERROR'
            })
    
    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY OF ALL TESTS")
    print(f"{'='*80}\n")
    
    print(f"{'File':<20} {'Starting':<15} {'Deposits':<15} {'Withdrawals':<15} {'Final':<15} {'Status':<10}")
    print("-" * 100)
    
    for r in results:
        if r['error']:
            print(f"{r['file']:<20} {'ERROR':<15} {'ERROR':<15} {'ERROR':<15} {'ERROR':<15} {r['verification']:<10}")
        else:
            print(f"{r['file']:<20} {r['starting_balance']:>14,.2f} {r['total_deposits']:>14,.2f} "
                  f"{r['total_withdrawals']:>14,.2f} {r['final_balance']:>14,.2f} {r['verification']:<10}")
    
    # Count results
    passed = sum(1 for r in results if r['verification'] == '✅ PASS')
    failed = sum(1 for r in results if '❌' in r['verification'])
    
    print("-" * 100)
    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED! 🎉")
    else:
        print(f"\n⚠️  {failed} test(s) failed")
    
    return results


if __name__ == "__main__":
    test_all_pdfs()
