#!/usr/bin/env python3
"""
Import bank statement transactions to ActualBudget using LLM-based extraction.
"""

import sys
import argparse
import decimal
import datetime
from pathlib import Path

# ActualBudget API
from actual import Actual
from actual.queries import create_transaction, get_account, create_account, get_categories

# PDF extraction using LLM
from pdf_reader_ocr import extract_all_transactions_from_pdf

# Configuration
ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"
ACTUAL_ACCOUNT_NAME = "icici"
PDF_PASSWORD = "guru2111"


def parse_date(date_str: str) -> datetime.date:
    """Parse DD-MM-YYYY date string."""
    try:
        day, month, year = date_str.split('-')
        return datetime.date(int(year), int(month), int(day))
    except:
        return datetime.date.today()


def import_to_actualbudget(pdf_path: str, password: str = None, dry_run: bool = False):
    """Import individual transactions from PDF to ActualBudget."""
    
    print("=" * 80)
    print(f"   IMPORTING TO ACTUALBUDGET: {Path(pdf_path).name}")
    print("=" * 80)
    
    # Extract all individual transactions using LLM
    result = extract_all_transactions_from_pdf(pdf_path, password)
    
    transactions = result['transactions']
    
    print(f"\n📊 Summary:")
    print(f"   Starting Balance: ₹{result['starting_balance']:,.2f}")
    print(f"   Total Deposits:   ₹{result['total_deposits']:,.2f}")
    print(f"   Total Withdrawals: ₹{result['total_withdrawals']:,.2f}")
    print(f"   Final Balance:    ₹{result['final_balance']:,.2f}")
    print(f"   Total Transactions: {len(transactions)}")
    
    if dry_run:
        print("\n🔍 DRY RUN - Not posting to ActualBudget")
        print("\nFirst 5 transactions:")
        for i, txn in enumerate(transactions[:5], 1):
            amount = txn['deposit'] if txn['deposit'] > 0 else -txn['withdrawal']
            print(f"  {i}. {txn['date']} | {txn['description'][:40]} | ₹{amount:,.2f}")
        return
    
    # Import to ActualBudget
    try:
        with Actual(
            base_url=ACTUAL_SERVER_URL,
            password=ACTUAL_PASSWORD,
            file=ACTUAL_FILE
        ) as actual:
            # Get or create account
            account = get_account(actual.session, ACTUAL_ACCOUNT_NAME)
            if not account:
                print(f"✓ Creating account: {ACTUAL_ACCOUNT_NAME}")
                account = create_account(actual.session, ACTUAL_ACCOUNT_NAME)
            else:
                print(f"✓ Using existing account: {ACTUAL_ACCOUNT_NAME}")
            
            transactions_created = 0
            
            # Create opening balance transaction
            if result['starting_balance'] > 0:
                first_date = parse_date(transactions[0]['date']) if transactions else datetime.date.today()
                
                txn = create_transaction(
                    actual.session,
                    first_date,
                    account,
                    "Opening Balance",
                    notes="Starting balance from bank statement",
                    amount=decimal.Decimal(str(result['starting_balance']))
                )
                transactions_created += 1
                print(f"\n   ✓ Opening balance: ₹{result['starting_balance']:,.2f} on {first_date}")
            
            # Create individual transactions
            print(f"\n   Importing {len(transactions)} transactions...")
            for txn_data in transactions:
                txn_date = parse_date(txn_data['date'])
                description = txn_data['description'][:100] or "Transaction"
                
                # Determine amount (positive for deposits, negative for withdrawals)
                if txn_data['deposit'] > 0:
                    amount = decimal.Decimal(str(txn_data['deposit']))
                elif txn_data['withdrawal'] > 0:
                    amount = decimal.Decimal(str(-txn_data['withdrawal']))
                else:
                    continue  # Skip zero-amount transactions
                
                txn = create_transaction(
                    actual.session,
                    txn_date,
                    account,
                    description,
                    notes=f"Page {txn_data['page']} | Balance: ₹{txn_data['balance']:,.2f}",
                    amount=amount
                )
                transactions_created += 1
            
            # Commit
            actual.commit()
            print(f"\n✅ Successfully imported {transactions_created} transactions")
            print(f"   ({len(transactions)} statement entries + 1 opening balance)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description='Import bank statement to ActualBudget using LLM')
    parser.add_argument('pdf_file', help='Path to PDF bank statement')
    parser.add_argument('--password', '-p', default=PDF_PASSWORD, help='PDF password')
    parser.add_argument('--dry-run', '-d', action='store_true', help="Don't post to ActualBudget")
    
    args = parser.parse_args()
    
    if not Path(args.pdf_file).exists():
        print(f"❌ File not found: {args.pdf_file}")
        sys.exit(1)
    
    import_to_actualbudget(args.pdf_file, password=args.password, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
