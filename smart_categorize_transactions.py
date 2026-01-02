#!/usr/bin/env python3
"""
Smart categorization script: Apply LLM-based categorization to existing transactions.
Run this after importing statements to automatically categorize transactions.
"""

import sys
sys.path.append('.')

from actual import Actual
from actual.queries import get_transactions, get_account, get_categories
from utils.smart_categorize import categorize_transaction

ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"
ACTUAL_ACCOUNT_NAME = "icici"


def get_or_create_category(session, category_name):
    """
    Get category by name, or return None if not found.
    
    Args:
        session: Actual session
        category_name: Name of category to find
    
    Returns:
        Category object or None
    """
    categories = get_categories(session)
    for cat in categories:
        if cat.name == category_name:
            return cat
    return None


def smart_categorize_transactions(skip_categorized=True, verbose=False):
    """
    Apply smart LLM categorization to transactions.
    
    Args:
        skip_categorized: If True, skip transactions that already have a category (except 'General')
        verbose: Print detailed progress
    """
    print("=" * 70)
    print("   SMART TRANSACTION CATEGORIZATION (LLM-POWERED)")
    print("=" * 70)
    print()
    
    try:
        with Actual(
            base_url=ACTUAL_SERVER_URL,
            password=ACTUAL_PASSWORD,
            file=ACTUAL_FILE
        ) as actual:
            # Get the account
            account = get_account(actual.session, ACTUAL_ACCOUNT_NAME)
            if not account:
                print(f"❌ Account '{ACTUAL_ACCOUNT_NAME}' not found!")
                return
            
            print(f"✓ Account: {ACTUAL_ACCOUNT_NAME} (ID: {account.id})")
            
            # Get all categories for reference
            all_categories = get_categories(actual.session)
            category_map = {cat.name: cat for cat in all_categories}
            
            print(f"✓ Available categories: {', '.join(category_map.keys())}")
            print()
            
            # Get all transactions from the account
            transactions = get_transactions(actual.session, account=account)
            print(f"✓ Found {len(transactions)} transactions in account")
            print()
            
            # Filter transactions to categorize
            to_categorize = []
            for txn in transactions:
                # Skip if already has category (unless it's General)
                if skip_categorized and txn.category_id:
                    current_cat = next((cat.name for cat in all_categories if cat.id == txn.category_id), None)
                    if current_cat and current_cat != "General":
                        continue
                
                to_categorize.append(txn)
            
            print(f"📋 Transactions to categorize: {len(to_categorize)}")
            
            if len(to_categorize) == 0:
                print("\n✓ All transactions already categorized!")
                return
            
            print(f"{'─' * 70}")
            print()
            
            # Categorize each transaction
            updated_count = 0
            failed_count = 0
            
            for i, txn in enumerate(to_categorize, 1):
                # Extract transaction details
                is_deposit = txn.amount > 0
                amount = abs(txn.amount)
                particulars = txn.notes or ""
                
                # Extract description from notes (format: "Imported from bank statement\n<description>")
                description = particulars
                if "Imported from bank statement" in particulars:
                    lines = particulars.split('\n')
                    if len(lines) > 1:
                        description = lines[1]
                
                if verbose:
                    print(f"[{i}/{len(to_categorize)}] {txn.date} | ₹{amount:,.2f} | {description[:50]}")
                else:
                    # Progress indicator
                    if i % 10 == 0 or i == len(to_categorize):
                        print(f"Progress: {i}/{len(to_categorize)} transactions processed...")
                
                try:
                    # Get category from LLM
                    category_name = categorize_transaction(
                        particulars=description,
                        amount=amount,
                        is_deposit=is_deposit,
                        verbose=verbose
                    )
                    
                    # Get category object
                    category = category_map.get(category_name)
                    
                    if category:
                        # Update transaction category
                        txn.category_id = category.id
                        actual.session.add(txn)
                        updated_count += 1
                        
                        if verbose:
                            print(f"  ✓ Categorized as: {category_name}")
                    else:
                        print(f"  ⚠ Warning: Category '{category_name}' not found in Actual Budget")
                        print(f"     Please create category '{category_name}' manually")
                        failed_count += 1
                        
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    failed_count += 1
                
                if verbose:
                    print()
            
            # Commit all changes
            print()
            print(f"{'─' * 70}")
            print("\n💾 Saving changes to Actual Budget...")
            actual.commit()
            
            print()
            print("=" * 70)
            print("   CATEGORIZATION COMPLETE")
            print("=" * 70)
            print(f"✓ Successfully categorized: {updated_count} transactions")
            if failed_count > 0:
                print(f"⚠ Failed: {failed_count} transactions")
            print()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point with command-line options."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Smart categorization of transactions using LLM"
    )
    parser.add_argument(
        '--recategorize',
        action='store_true',
        help="Recategorize ALL transactions (including already categorized ones)"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Print detailed progress for each transaction"
    )
    
    args = parser.parse_args()
    
    smart_categorize_transactions(
        skip_categorized=not args.recategorize,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
