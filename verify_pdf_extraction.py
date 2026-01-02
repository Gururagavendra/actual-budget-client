#!/usr/bin/env python3
"""
Verification module for PDF extraction accuracy.
Checks if extracted transactions match the PDF summary totals.
"""

import decimal


class PDFExtractionVerificationError(Exception):
    """Raised when PDF extraction verification fails."""
    pass


def verify_pdf_extraction_is_correct(summary, transactions, tolerance=1.0):
    """
    Verify that extracted transactions match the PDF summary.

    Args:
        summary: Dictionary with starting_balance, total_deposits, total_withdrawals, final_balance
        transactions: List of transaction dictionaries with deposit, withdrawal, balance
        tolerance: Maximum allowed difference in balance calculation (default ₹1.00)

    Raises:
        PDFExtractionVerificationError: If verification fails

    Returns:
        dict: Verification results with details
    """
    # Calculate totals from individual transactions
    calc_deposits = sum(t['deposit'] for t in transactions)
    calc_withdrawals = sum(t['withdrawal'] for t in transactions)

    # Calculate final balance from individual transactions
    calc_final = summary['starting_balance'] + calc_deposits - calc_withdrawals

    # Check balance verification
    balance_diff = abs(calc_final - summary['final_balance'])

    # Check deposit total verification
    deposit_diff = abs(calc_deposits - summary['total_deposits'])

    # Check withdrawal total verification
    withdrawal_diff = abs(calc_withdrawals - summary['total_withdrawals'])

    verification_results = {
        'balance_diff': balance_diff,
        'deposit_diff': deposit_diff,
        'withdrawal_diff': withdrawal_diff,
        'calc_deposits': calc_deposits,
        'calc_withdrawals': calc_withdrawals,
        'calc_final': calc_final,
        'passed': balance_diff <= tolerance and deposit_diff <= tolerance and withdrawal_diff <= tolerance
    }

    if not verification_results['passed']:
        error_msg = "PDF extraction verification failed:\n"
        error_msg += f"  Balance mismatch: Expected ₹{summary['final_balance']:,.2f}, Calculated ₹{calc_final:,.2f} (diff: ₹{balance_diff:.2f})\n"
        error_msg += f"  Deposits mismatch: Expected ₹{summary['total_deposits']:,.2f}, Calculated ₹{calc_deposits:,.2f} (diff: ₹{deposit_diff:.2f})\n"
        error_msg += f"  Withdrawals mismatch: Expected ₹{summary['total_withdrawals']:,.2f}, Calculated ₹{calc_withdrawals:,.2f} (diff: ₹{withdrawal_diff:.2f})\n"
        error_msg += f"\n  This indicates the PDF extraction may be incorrect. Please verify the PDF manually."

        raise PDFExtractionVerificationError(error_msg)

    return verification_results


def print_verification_results(summary, transactions, verification_results):
    """
    Print detailed verification results.

    Args:
        summary: PDF summary dictionary
        transactions: List of transactions
        verification_results: Results from verify_pdf_extraction_is_correct
    """
    print("\n🔍 PDF Extraction Verification:")
    print(f"   Starting Balance:       ₹{summary['starting_balance']:>12,.2f}")
    print(f"   Transactions Extracted: {len(transactions):>5}")
    print(f"   Deposits (PDF):         ₹{summary['total_deposits']:>12,.2f}")
    print(f"   Deposits (Calculated):  ₹{verification_results['calc_deposits']:>12,.2f}")
    print(f"   Withdrawals (PDF):      ₹{summary['total_withdrawals']:>12,.2f}")
    print(f"   Withdrawals (Calculated): ₹{verification_results['calc_withdrawals']:>12,.2f}")
    print(f"   Final Balance (PDF):    ₹{summary['final_balance']:>12,.2f}")
    print(f"   Final Balance (Calc):   ₹{verification_results['calc_final']:>12,.2f}")

    if verification_results['passed']:
        print("   ✅ VERIFICATION PASSED - Extraction appears correct")
    else:
        print("   ❌ VERIFICATION FAILED - Extraction may be incorrect")
        print(f"      Balance diff: ₹{verification_results['balance_diff']:.2f}")
        print(f"      Deposits diff: ₹{verification_results['deposit_diff']:.2f}")
        print(f"      Withdrawals diff: ₹{verification_results['withdrawal_diff']:.2f}")