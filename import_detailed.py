#!/usr/bin/env python3
"""
Import DETAILED individual bank transactions to ActualBudget.
Uses a hybrid approach: verified totals from LLM, individual parsing from text.
"""

import sys
import argparse
import decimal
import datetime
import re
from pathlib import Path

from actual import Actual
from actual.queries import create_transaction, get_account, create_account, get_categories

from pdf_reader_ocr import extract_text_from_pdf, process_bank_statement

# Configuration
ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"
ACTUAL_ACCOUNT_NAME = "icici"
PDF_PASSWORD = "guru2111"


def parse_individual_transactions(pages_text, starting_balance):
    """
    Parse individual transactions from PDF text pages.
    Uses balance tracking to determine deposit vs withdrawal.
    """
    all_transactions = []
    date_pattern = re.compile(r'^(\d{2}-\d{2}-\d{4})')
    
    current_balance = starting_balance
    
    for page_num, page_text in enumerate(pages_text, 1):
        lines = page_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            date_match = date_pattern.match(line)
            
            if date_match:
                date_str = date_match.group(1)
                
                # Skip B/F and Total lines
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line in ['B/F', 'C/F'] or 'Total:' in next_line:
                        i += 2
                        continue
                
                # Collect description (next 1-4 lines until we hit amounts)
                description_parts = []
                j = i + 1
                amounts = []
                
                while j < len(lines) and j < i + 10:
                    check_line = lines[j].strip()
                    
                    if date_pattern.match(check_line) or check_line in ['Total:', 'B/F', 'C/F']:
                        break
                    
                    # Find amounts
                    found_amounts = re.findall(r'([\d,]+\.\d{2})', check_line)
                    if found_amounts:
                        for amt in found_amounts:
                            amounts.append(float(amt.replace(',', '')))
                        if len(amounts) >= 2:
                            break
                    elif check_line and check_line not in ['/', '']:
                        description_parts.append(check_line)
                    
                    j += 1
                
                # Parse transaction if we have amounts
                if len(amounts) >= 2:
                    # Last amount is new balance
                    new_balance = amounts[-1]
                    balance_change = new_balance - current_balance
                    
                    if balance_change > 0:
                        deposit = balance_change
                        withdrawal = 0.0
                    else:
                        deposit = 0.0
                        withdrawal = abs(balance_change)
                    
                    description = ' '.join(description_parts[:3]).replace('/', ' ')[:100]
                    
                    all_transactions.append({
                        'date': date_str,
                        'description': description if description else 'Transaction',
                        'deposit': deposit,
                        'withdrawal': withdrawal,
                        'balance': new_balance,
                        'page': page_num
                    })
                    
                    current_balance = new_balance
                
                i = j
            else:
                i += 1
    
    return all_transactions


def parse_date(date_str: str) -> datetime.date:
    """Parse DD-MM-YYYY date string."""
    try:
        day, month, year = date_str.split('-')
        return datetime.date(int(year), int(month), int(day))
    except:
        return datetime.date.today()


def import_detailed_transactions(pdf_path: str, password: str = None, dry_run: bool = False):
    """Import individual transactions from PDF to ActualBudget."""
    
    print("=" * 80)
    print(f"   IMPORTING DETAILED TRANSACTIONS: {Path(pdf_path).name}")
    print("=" * 80)
    
    # Get verified summary first
    print("\n1. Getting verified summary...")
    summary = process_bank_statement(pdf_path, password)
    
    print(f"\n2. Parsing individual transactions...")
    pages_text = extract_text_from_pdf(pdf_path, password)
    transactions = parse_individual_transactions(pages_text, summary['starting_balance'])
    
    # Calculate totals
    calc_deposits = sum(t['deposit'] for t in transactions)
    calc_withdrawals = sum(t['withdrawal'] for t in transactions)
    
    print(f"\n📊 Summary:")
    print(f"   Starting Balance: ₹{summary['starting_balance']:,.2f}")
    print(f"   Transactions Found: {len(transactions)}")
    print(f"   Calculated Deposits: ₹{calc_deposits:,.2f}")
    print(f"   Calculated Withdrawals: ₹{calc_withdrawals:,.2f}")
    print(f"   Final Balance: ₹{summary['final_balance']:,.2f}")
    
    # Verify
    calc_final = summary['starting_balance'] + calc_deposits - calc_withdrawals
    print(f"\n   Verification: ₹{summary['starting_balance']:,.2f} + ₹{calc_deposits:,.2f} - ₹{calc_withdrawals:,.2f} = ₹{calc_final:,.2f}")
    
    if abs(calc_final - summary['final_balance']) > 1.0:
        print(f"   ⚠️  Warning: Calculated balance doesn't match statement (diff: ₹{abs(calc_final - summary['final_balance']):.2f})")
    else:
        print(f"   ✅ Balance verification passed!")
    
    if dry_run:
        print("\n🔍 DRY RUN - Not posting to ActualBudget")
        print("\nFirst 10 transactions:")
        for i, txn in enumerate(transactions[:10], 1):
            amount = txn['deposit'] if txn['deposit'] > 0 else -txn['withdrawal']
            print(f"  {i:2d}. {txn['date']} | {txn['description'][:45]:45s} | ₹{amount:10,.2f}")
        return
    
    # Import to ActualBudget
    try:
        with Actual(
            base_url=ACTUAL_SERVER_URL,
            password=ACTUAL_PASSWORD,
            file=ACTUAL_FILE
        ) as actual:
            account = get_account(actual.session, ACTUAL_ACCOUNT_NAME)
            if not account:
                print(f"\n✓ Creating account: {ACTUAL_ACCOUNT_NAME}")
                account = create_account(actual.session, ACTUAL_ACCOUNT_NAME)
            else:
                print(f"\n✓ Using existing account: {ACTUAL_ACCOUNT_NAME}")
            
            # Get categories
            categories = get_categories(actual.session)
            income_category = None
            general_category = None
            for cat in categories:
                if cat.name == "Income":
                    income_category = cat
                elif cat.name == "General":
                    general_category = cat
            
            if not income_category:
                print("❌ 'Income' category not found! Please create it in ActualBudget.")
                return
            if not general_category:
                print("❌ 'General' category not found! Please create it in ActualBudget.")
                return
            
            transactions_created = 0
            
            # Create opening balance - NO CATEGORY (it's not income, it's just starting balance)
            first_date = parse_date(transactions[0]['date']) if transactions else datetime.date.today()
            txn = create_transaction(
                actual.session,
                first_date,
                account,
                "Opening Balance",
                notes="Starting balance from bank statement",
                amount=decimal.Decimal(str(summary['starting_balance']))
            )
            # Don't set category for starting balance
            transactions_created += 1
            print(f"   ✓ Opening balance: ₹{summary['starting_balance']:,.2f}")
            
            # Create all individual transactions
            print(f"\n   Importing {len(transactions)} transactions...")
            for txn_data in transactions:
                txn_date = parse_date(txn_data['date'])
                description = txn_data['description'] or "Transaction"
                
                if txn_data['deposit'] > 0:
                    # Deposit - categorize as income
                    amount = decimal.Decimal(str(txn_data['deposit']))
                    txn = create_transaction(
                        actual.session,
                        txn_date,
                        account,
                        description,
                        notes=f"Page {txn_data['page']} | Balance: ₹{txn_data['balance']:,.2f}",
                        amount=amount
                    )
                    # Set as income
                    if income_category:
                        txn.category_id = income_category.id
                    
                elif txn_data['withdrawal'] > 0:
                    # Withdrawal - categorize as General
                    amount = decimal.Decimal(str(-txn_data['withdrawal']))
                    txn = create_transaction(
                        actual.session,
                        txn_date,
                        account,
                        description,
                        notes=f"Page {txn_data['page']} | Balance: ₹{txn_data['balance']:,.2f}",
                        amount=amount
                    )
                    # Set as General
                    if general_category:
                        txn.category_id = general_category.id
                else:
                    continue
                
                transactions_created += 1
            
            actual.commit()
            print(f"\n✅ Successfully imported {transactions_created} transactions")
            print(f"   ({len(transactions)} individual + 1 opening balance)")
            print(f"\n💡 Note: Deposits are categorized as Income")
            print(f"   Expenses are categorized as General")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description='Import detailed bank statement transactions to ActualBudget')
    parser.add_argument('pdf_file', help='Path to PDF bank statement')
    parser.add_argument('--password', '-p', default=PDF_PASSWORD, help='PDF password')
    parser.add_argument('--dry-run', '-d', action='store_true', help="Preview without importing")
    
    args = parser.parse_args()
    
    if not Path(args.pdf_file).exists():
        print(f"❌ File not found: {args.pdf_file}")
        sys.exit(1)
    
    import_detailed_transactions(args.pdf_file, password=args.password, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
