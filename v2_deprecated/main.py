#!/usr/bin/env python3
"""
ActualBudget Bank Statement Automation - Main Orchestrator
Parses PDF bank statements and imports transactions to ActualBudget

Usage:
    python main.py              # Process PDFs in downloads folder
    python main.py --local FILE # Process a local PDF file
    python main.py --dry-run    # Parse PDFs but don't post to ActualBudget
"""

import sys
import argparse
import decimal
import datetime
import re
from pathlib import Path

# PDF parsing
import fitz  # PyMuPDF

# ActualBudget API
from actual import Actual
from actual.queries import create_transaction, get_accounts, get_account, create_account, get_categories, create_category

# ============================================================================
# CONFIGURATION - Update these values for your setup
# ============================================================================
ACTUAL_SERVER_URL = "http://localhost:5006"  # ActualBudget server URL
ACTUAL_PASSWORD = "guru123"  # ActualBudget server password
ACTUAL_FILE = "My Finances"  # Budget file name or sync ID
ACTUAL_ACCOUNT_NAME = "icici"  # Account name in ActualBudget

PDF_PASSWORD = "guru2111"  # Password to open PDF statements
DOWNLOADS_DIR = Path(__file__).parent / "downloads"

# ============================================================================
# EMAIL FETCHER - COMMENTED OUT (using local files instead)
# ============================================================================
# from email_fetcher import fetch_and_download_statements
# def fetch_emails():
#     """Fetch and download bank statements from email"""
#     return fetch_and_download_statements()

# ============================================================================
# PDF SCANNER - Embedded for self-contained script
# ============================================================================

def extract_transactions_from_pdf(pdf_path: str, password: str = None) -> dict:
    """
    Extract transactions from ICICI bank statement PDF using column positions.
    
    Args:
        pdf_path: Path to the PDF file
        password: Password to open the PDF
    
    Returns:
        Dict with keys: 'transactions' (list), 'opening_balance' (float or None), 'opening_date' (date or None)
    """
    import re
    
    transactions = []
    opening_balance = None
    opening_date = None
    
    # Column x-position boundaries (determined from PDF analysis)
    # DEPOSITS column: x ~365-415 (header at 372, actual amounts at 368-392)
    # WITHDRAWALS column: x ~440-520 (header at 431, amounts at 455-495)
    # BALANCE column: x ~520+ (amounts around 522-527)
    # Note: Header area has values at x=419 which we want to exclude from deposits
    COL_DEPOSITS_START = 365
    COL_DEPOSITS_END = 415
    COL_WITHDRAWALS_START = 440
    COL_WITHDRAWALS_END = 520
    COL_BALANCE_START = 520
    
    amount_pattern = re.compile(r'^[\d,]+\.\d{2}$')
    date_pattern = re.compile(r'^(\d{2}-\d{2}-\d{4})')
    
    try:
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            if password:
                doc.authenticate(password)
            else:
                raise ValueError("PDF is encrypted but no password provided")
        
        # Process each page (typically 6 pages for transactions)
        for page_num in range(min(len(doc), 7)):
            page = doc[page_num]
            blocks = page.get_text('dict')['blocks']
            
            # First pass: collect all amounts with their positions and y-coordinates
            page_data = []  # List of (y_pos, x_pos, text, type)
            total_line_y = None  # Track y-position of "Total:" line to skip it
            
            for block in blocks:
                if 'lines' not in block:
                    continue
                for line in block['lines']:
                    y_pos = line['bbox'][1]  # y coordinate
                    
                    for span in line['spans']:
                        text = span['text'].strip()
                        x0 = span['bbox'][0]
                        
                        # Check for "Total:" - mark this y position to skip
                        if text == 'Total:':
                            total_line_y = y_pos
                            continue
                        
                        # Skip items on the Total line
                        if total_line_y and abs(y_pos - total_line_y) < 2:
                            continue
                        
                        # Check for date
                        date_match = date_pattern.match(text)
                        if date_match:
                            page_data.append((y_pos, x0, date_match.group(1), 'date'))
                        
                        # Check for B/F (opening balance marker)
                        if text == 'B/F':
                            page_data.append((y_pos, x0, text, 'bf'))
                        
                        # Check for amounts
                        if amount_pattern.match(text):
                            amount_val = float(text.replace(',', ''))
                            
                            if COL_DEPOSITS_START <= x0 < COL_DEPOSITS_END:
                                page_data.append((y_pos, x0, amount_val, 'deposit'))
                            elif COL_WITHDRAWALS_START <= x0 < COL_WITHDRAWALS_END:
                                page_data.append((y_pos, x0, amount_val, 'withdrawal'))
                            elif x0 >= COL_BALANCE_START:
                                page_data.append((y_pos, x0, amount_val, 'balance'))
                        
                        # Check for description text in PARTICULARS column
                        if 143 <= x0 < 365 and len(text) > 5:
                            page_data.append((y_pos, x0, text, 'desc'))
            
            # Sort by y position
            page_data.sort(key=lambda x: x[0])
            
            # Now parse the sorted data
            current_date = None
            current_desc_parts = []
            current_deposit = 0
            current_withdrawal = 0
            is_bf_entry = False
            
            for i, (y_pos, x_pos, value, item_type) in enumerate(page_data):
                if item_type == 'date':
                    # Save previous transaction if exists
                    if current_date and (current_deposit > 0 or current_withdrawal > 0) and not is_bf_entry:
                        desc = ' '.join(current_desc_parts)[:100]
                        if current_deposit > 0:
                            transactions.append({
                                'date': current_date,
                                'description': desc or 'Deposit',
                                'type': 'deposit',
                                'amount': current_deposit
                            })
                        elif current_withdrawal > 0:
                            transactions.append({
                                'date': current_date,
                                'description': desc or 'Withdrawal',
                                'type': 'withdrawal',
                                'amount': current_withdrawal
                            })
                    
                    # Parse new date
                    try:
                        parts = value.split('-')
                        current_date = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                    except:
                        current_date = None
                    current_desc_parts = []
                    current_deposit = 0
                    current_withdrawal = 0
                    is_bf_entry = False
                    
                elif item_type == 'bf':
                    is_bf_entry = True
                    
                elif item_type == 'deposit':
                    if is_bf_entry and opening_balance is None:
                        # This is actually the balance after B/F
                        pass
                    elif value > 0:
                        current_deposit = value
                        
                elif item_type == 'withdrawal':
                    if value > 0:
                        current_withdrawal = value
                        
                elif item_type == 'balance':
                    if is_bf_entry and opening_balance is None and current_date:
                        opening_balance = value
                        opening_date = current_date
                        print(f"📊 Opening Balance detected: ₹{opening_balance:,.2f} on {opening_date}")
                        
                elif item_type == 'desc':
                    current_desc_parts.append(value)
            
            # Don't forget last transaction on page
            if current_date and (current_deposit > 0 or current_withdrawal > 0) and not is_bf_entry:
                desc = ' '.join(current_desc_parts)[:100]
                if current_deposit > 0:
                    transactions.append({
                        'date': current_date,
                        'description': desc or 'Deposit',
                        'type': 'deposit',
                        'amount': current_deposit
                    })
                elif current_withdrawal > 0:
                    transactions.append({
                        'date': current_date,
                        'description': desc or 'Withdrawal',
                        'type': 'withdrawal',
                        'amount': current_withdrawal
                    })
        
        doc.close()
        
    except Exception as e:
        print(f"Error extracting transactions: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return {
        'transactions': transactions,
        'opening_balance': opening_balance,
        'opening_date': opening_date
    }


def display_transactions(transactions: list):
    """Display extracted transactions in a table format."""
    if not transactions:
        print("No transactions found")
        return
    
    print(f"\n{'='*80}")
    print(f"{'DATE':<12} {'TYPE':<10} {'AMOUNT':>12} {'DESCRIPTION':<40}")
    print(f"{'='*80}")
    
    for txn in transactions:
        date_str = txn['date'].strftime('%Y-%m-%d') if isinstance(txn['date'], datetime.date) else str(txn['date'])
        print(f"{date_str:<12} {txn['type']:<10} {txn['amount']:>12,.2f} {txn['description'][:40]:<40}")
    
    print(f"{'='*80}")
    print(f"Total transactions: {len(transactions)}")


# ============================================================================
# ACTUALBUDGET INTEGRATION
# ============================================================================

def set_starting_balance(actual_session, account, balance: float, date: datetime.date):
    """
    Set the starting balance for an account.
    
    Args:
        actual_session: Actual session
        account: Account object
        balance: Balance amount
        date: Date for the starting balance
    """
    from actual.queries import create_transaction
    import decimal
    
    # Create a starting balance transaction
    txn = create_transaction(
        actual_session,
        date,
        account,
        "",  # No payee
        notes="Starting Balance (from statement)",
        amount=decimal.Decimal(str(balance))
    )
    txn.starting_balance_flag = 1
    print(f"   ✓ Starting balance set: ₹{balance:,.2f} on {date}")
    return txn

def transform_for_actualbudget(transaction: dict) -> dict:
    """
    Transform parsed PDF transaction to ActualBudget format.
    
    Args:
        transaction: Dict with keys: date, description, type, amount
    
    Returns:
        Dict ready for ActualBudget API
    """
    # ActualBudget uses negative amounts for expenses, positive for income
    amount = transaction['amount']
    if transaction['type'] == 'withdrawal':
        amount = -abs(amount)
    else:
        amount = abs(amount)
    
    return {
        'date': transaction['date'],
        'payee_name': transaction['description'],
        'notes': f"Imported from bank statement",
        'amount': decimal.Decimal(str(amount))
    }


def post_to_actualbudget(transactions: list, opening_balance: float = None, opening_date: datetime.date = None, dry_run: bool = False) -> tuple:
    """
    Post transactions to ActualBudget.
    
    Args:
        transactions: List of transformed transaction dicts
        opening_balance: Opening balance amount (optional)
        opening_date: Date for opening balance (optional)
        dry_run: If True, don't actually post
    
    Returns:
        Tuple of (success_count, fail_count)
    """
    if dry_run:
        print("\n🔍 DRY RUN - Not posting to ActualBudget")
        return len(transactions), 0
    
    success_count = 0
    fail_count = 0
    
    try:
        with Actual(
            base_url=ACTUAL_SERVER_URL,
            password=ACTUAL_PASSWORD,
            file=ACTUAL_FILE
        ) as actual:
            # Get or create the account
            account = get_account(actual.session, ACTUAL_ACCOUNT_NAME)
            if not account:
                print(f"Creating new account: {ACTUAL_ACCOUNT_NAME}")
                account = create_account(actual.session, ACTUAL_ACCOUNT_NAME)
            
            # Set opening balance if provided
            # Import opening balance as a deposit transaction so it appears in the correct date order
            if opening_balance is not None and opening_date is not None:
                print(f"\n💰 Opening balance detected: ₹{opening_balance:,.2f} on {opening_date}")
                print(f"   Importing as a deposit transaction...")
                
                # Add opening balance as the first transaction
                opening_txn = {
                    'date': opening_date,
                    'description': 'Opening Balance (B/F)',
                    'type': 'deposit',
                    'amount': opening_balance
                }
                transactions.insert(0, opening_txn)
                print(f"   ✓ Added opening balance transaction")
            
            # Get or create a default category for imported transactions
            categories = get_categories(actual.session)
            import_category = None
            
            # Look for "General" or "Usual Expenses" category
            for cat in categories:
                if cat.name in ['General', 'Usual Expenses', 'general']:
                    import_category = cat
                    break
            
            if not import_category:
                print(f"⚠️ No default category found. Transactions will be uncategorized.")
                print(f"   Please categorize them manually in ActualBudget.")
            else:
                print(f"   Using category: {import_category.name}")
            
            print(f"\n📤 Posting {len(transactions)} transactions to ActualBudget...")
            print(f"   Account: {ACTUAL_ACCOUNT_NAME}")
            
            for txn in transactions:
                try:
                    actual_txn = transform_for_actualbudget(txn)
                    t = create_transaction(
                        actual.session,
                        actual_txn['date'],
                        account,
                        actual_txn['payee_name'],
                        notes=actual_txn['notes'],
                        amount=actual_txn['amount']
                    )
                    # Assign category if available
                    if import_category:
                        t.category_id = import_category.id
                    
                    success_count += 1
                    print(f"   ✓ {txn['date']} - {txn['description'][:30]} - {txn['amount']:.2f}")
                except Exception as e:
                    fail_count += 1
                    print(f"   ✗ Failed: {txn['description'][:30]} - {e}")
            
            # Commit all changes
            actual.commit()
            print(f"\n✅ Committed {success_count} transactions to ActualBudget")
            
    except Exception as e:
        print(f"❌ Error connecting to ActualBudget: {e}")
        return 0, len(transactions)
    
    return success_count, fail_count


def process_pdf(pdf_path: str, password: str = None, dry_run: bool = False) -> tuple:
    """
    Process a single PDF and optionally post transactions to ActualBudget.
    
    Args:
        pdf_path: Path to the PDF file
        password: PDF password (optional)
        dry_run: If True, don't post to ActualBudget, just show transactions
    
    Returns:
        Tuple of (success_count, fail_count)
    """
    print(f"\n{'='*60}")
    print(f"📄 Processing: {Path(pdf_path).name}")
    print(f"{'='*60}")
    
    # Step 1: Extract transactions from PDF
    try:
        result = extract_transactions_from_pdf(str(pdf_path), password=password)
        transactions = result['transactions']
        opening_balance = result['opening_balance']
        opening_date = result['opening_date']
    except Exception as e:
        print(f"❌ Error parsing PDF: {e}")
        return 0, 1
    
    if not transactions:
        print("⚠️ No transactions found in PDF")
        # Still set opening balance if available
        if opening_balance and opening_date and not dry_run:
            print(f"\n💰 But found opening balance: ₹{opening_balance:,.2f}")
            return post_to_actualbudget([], opening_balance, opening_date, dry_run)
        return 0, 0
    
    # Display extracted transactions
    display_transactions(transactions)
    
    # Step 2: Post to ActualBudget
    return post_to_actualbudget(transactions, opening_balance, opening_date, dry_run=dry_run)


def process_downloads_folder(password: str = None, dry_run: bool = False) -> dict:
    """
    Process all PDFs in the downloads folder.
    
    Args:
        password: PDF password
        dry_run: If True, don't post to ActualBudget
    
    Returns:
        Summary dict
    """
    total_success = 0
    total_fail = 0
    pdfs_processed = 0
    
    # Find all PDF files in downloads folder
    pdf_files = list(DOWNLOADS_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"⚠️ No PDF files found in {DOWNLOADS_DIR}")
        return {
            'pdfs_processed': 0,
            'transactions_posted': 0,
            'transactions_failed': 0
        }
    
    print(f"Found {len(pdf_files)} PDF file(s) in downloads folder")
    
    for pdf_file in pdf_files:
        success, fail = process_pdf(str(pdf_file), password=password, dry_run=dry_run)
        total_success += success
        total_fail += fail
        pdfs_processed += 1
    
    return {
        'pdfs_processed': pdfs_processed,
        'transactions_posted': total_success,
        'transactions_failed': total_fail
    }


def main():
    global ACTUAL_SERVER_URL, ACTUAL_PASSWORD, ACTUAL_FILE, ACTUAL_ACCOUNT_NAME
    
    parser = argparse.ArgumentParser(
        description='ActualBudget Bank Statement Automation'
    )
    parser.add_argument(
        '--local', '-l',
        metavar='FILE',
        help='Process a local PDF file instead of scanning downloads folder'
    )
    parser.add_argument(
        '--password', '-p',
        default=PDF_PASSWORD,
        help=f'PDF password (default: {PDF_PASSWORD})'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help="Parse PDFs but don't post to ActualBudget"
    )
    parser.add_argument(
        '--server', '-s',
        default=ACTUAL_SERVER_URL,
        help=f'ActualBudget server URL (default: {ACTUAL_SERVER_URL})'
    )
    parser.add_argument(
        '--actual-password',
        default=ACTUAL_PASSWORD,
        help='ActualBudget server password'
    )
    parser.add_argument(
        '--file', '-f',
        default=ACTUAL_FILE,
        help=f'ActualBudget file name (default: {ACTUAL_FILE})'
    )
    parser.add_argument(
        '--account', '-a',
        default=ACTUAL_ACCOUNT_NAME,
        help=f'Account name in ActualBudget (default: {ACTUAL_ACCOUNT_NAME})'
    )
    
    args = parser.parse_args()
    
    # Update config from args
    ACTUAL_SERVER_URL = args.server
    ACTUAL_PASSWORD = args.actual_password
    ACTUAL_FILE = args.file
    ACTUAL_ACCOUNT_NAME = args.account
    
    print("=" * 60)
    print("   ACTUALBUDGET BANK STATEMENT AUTOMATION")
    print("=" * 60)
    print(f"   Server: {ACTUAL_SERVER_URL}")
    print(f"   Budget: {ACTUAL_FILE}")
    print(f"   Account: {ACTUAL_ACCOUNT_NAME}")
    print("=" * 60)
    
    # Get password from args
    password = args.password
    
    if args.local:
        # Process single local file
        if not Path(args.local).exists():
            print(f"❌ File not found: {args.local}")
            sys.exit(1)
        
        success, fail = process_pdf(args.local, password=password, dry_run=args.dry_run)
        
        print("\n" + "=" * 60)
        print("                 FINAL SUMMARY")
        print("=" * 60)
        print(f"  ✅ Transactions posted: {success}")
        print(f"  ❌ Transactions failed: {fail}")
        print("=" * 60)
        
    else:
        # Process all PDFs in downloads folder
        # ============================================================
        # EMAIL FETCHING - COMMENTED OUT
        # ============================================================
        # downloads = fetch_and_download_statements()
        # if not downloads:
        #     print("\n✨ No new PDFs to process!")
        #     return
        # ============================================================
        
        summary = process_downloads_folder(password=password, dry_run=args.dry_run)
        
        print("\n" + "=" * 60)
        print("                 FINAL SUMMARY")
        print("=" * 60)
        print(f"  📄 PDFs processed: {summary['pdfs_processed']}")
        print(f"  ✅ Transactions posted: {summary['transactions_posted']}")
        print(f"  ❌ Transactions failed: {summary['transactions_failed']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
