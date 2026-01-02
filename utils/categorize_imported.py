#!/usr/bin/env python3
"""
Categorize all imported bank statement transactions.
This script will assign all uncategorized transactions with "Imported from bank statement" 
in their notes to the "General" category.
"""

from actual import Actual
from actual.queries import get_transactions, get_categories

# Configuration
ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"
ACTUAL_ACCOUNT_NAME = "icici"

def categorize_imported_transactions():
    """Find and categorize all imported transactions."""
    
    print("=" * 60)
    print("   CATEGORIZING IMPORTED TRANSACTIONS")
    print("=" * 60)
    
    with Actual(
        base_url=ACTUAL_SERVER_URL,
        password=ACTUAL_PASSWORD,
        file=ACTUAL_FILE
    ) as actual:
        # Get all transactions
        transactions = get_transactions(actual.session)
        
        # Get categories
        categories = get_categories(actual.session)
        
        # Find "General" category or first available category
        target_category = None
        for cat in categories:
            if cat.name in ['General', 'general', 'Usual Expenses']:
                target_category = cat
                break
        
        if not target_category and categories:
            # Use first available expense category
            for cat in categories:
                if not cat.is_income:
                    target_category = cat
                    break
        
        if not target_category:
            print("❌ No suitable category found!")
            print("   Please create a 'General' category in ActualBudget first.")
            return
        
        print(f"✓ Using category: {target_category.name}")
        
        # Find imported transactions (those with our note and no category)
        imported_count = 0
        updated_count = 0
        
        for txn in transactions:
            # Check if it's an imported transaction without category
            if (txn.notes and "Imported from bank statement" in txn.notes 
                and txn.category_id is None):
                imported_count += 1
                txn.category_id = target_category.id
                updated_count += 1
        
        if updated_count > 0:
            print(f"\n📝 Categorizing {updated_count} transactions...")
            actual.commit()
            print(f"✅ Successfully categorized {updated_count} transactions!")
        else:
            print(f"\n✓ No uncategorized imported transactions found.")
        
        print(f"\nTotal imported transactions found: {imported_count}")
        print("=" * 60)

if __name__ == "__main__":
    categorize_imported_transactions()
