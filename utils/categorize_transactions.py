#!/usr/bin/env python3
"""
Categorize all transactions in ActualBudget account as Food.
"""

from actual import Actual
from actual.queries import get_transactions, get_account, get_categories

ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"
ACTUAL_ACCOUNT_NAME = "icici"
CATEGORY_NAME = "General"

def categorize_all_as_food():
    """Categorize all uncategorized account transactions as General."""
    
    print("=" * 60)
    print("   CATEGORIZING UNCATEGORIZED TRANSACTIONS AS GENERAL")
    print("=" * 60)
    
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
            
            print(f"✓ Found account: {ACTUAL_ACCOUNT_NAME} (ID: {account.id})")
            
            # Get Food category
            categories = get_categories(actual.session)
            food_category = None
            for cat in categories:
                if cat.name == CATEGORY_NAME:
                    food_category = cat
                    break
            
            if not food_category:
                print(f"❌ Category '{CATEGORY_NAME}' not found!")
                print("Available categories:")
                for cat in categories:
                    print(f"  - {cat.name}")
                return
            
            print(f"✓ Found category: {CATEGORY_NAME} (ID: {food_category.id})")
            
            # Get all transactions for this account
            all_transactions = get_transactions(actual.session)
            
            # Filter by account - try both 'acct' and 'account'
            account_transactions = []
            for t in all_transactions:
                if hasattr(t, 'acct') and t.acct == account.id:
                    account_transactions.append(t)
                elif hasattr(t, 'account') and t.account == account.id:
                    account_transactions.append(t)
            
            if not account_transactions:
                print(f"✓ No transactions found for account {ACTUAL_ACCOUNT_NAME}")
                return
            
            print(f"✓ Found {len(account_transactions)} transaction(s)")
            
            # Update category for all uncategorized transactions (skip income)
            print(f"\n📝 Updating categories...")
            updated_count = 0
            skipped_count = 0
            for txn in account_transactions:
                # Skip if already has a category
                if hasattr(txn, 'category_id') and txn.category_id is not None:
                    skipped_count += 1
                    continue
                
                # Set category_id for uncategorized transactions
                txn.category_id = food_category.id
                updated_count += 1
            
            # Commit changes
            actual.commit()
            print(f"✅ Successfully categorized {updated_count} transaction(s) as '{CATEGORY_NAME}'")
            print(f"   Skipped {skipped_count} transaction(s) that already have categories")
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    categorize_all_as_food()
