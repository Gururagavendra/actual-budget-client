#!/usr/bin/env python3
"""
Check categorization results of imported transactions.
"""

import sys
sys.path.append('.')

from actual import Actual
from actual.queries import get_transactions, get_account, get_categories

ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"
ACTUAL_ACCOUNT_NAME = "icici"


def check_categorization():
    """Check how transactions are categorized."""
    print("=" * 80)
    print("   TRANSACTION CATEGORIZATION RESULTS")
    print("=" * 80)

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

            # Get categories
            categories = get_categories(actual.session)
            category_map = {cat.id: cat.name for cat in categories}

            # Get transactions
            transactions = get_transactions(actual.session, account=account)

            # Count by category
            category_counts = {}
            sample_transactions = []

            for txn in transactions:
                cat_name = category_map.get(txn.category_id, "Uncategorized")
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

                # Collect some sample transactions
                if len(sample_transactions) < 10:
                    # Debug: print transaction attributes
                    if len(sample_transactions) == 0:
                        print(f"Transaction attributes: {dir(txn)}")
                    sample_transactions.append({
                        'date': txn.date,
                        'description': str(txn)[:50],  # Fallback
                        'amount': txn.amount,
                        'category': cat_name
                    })

            print(f"✓ Found {len(transactions)} transactions")
            print()

            print("📊 Category Distribution:")
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {cat:15s}: {count:3d} transactions")

            print()
            print("📋 Sample Transactions:")
            print("-" * 80)
            for i, txn in enumerate(sample_transactions, 1):
                amount_str = f"₹{abs(txn['amount']):,.2f}"
                if txn['amount'] < 0:
                    amount_str = f"-{amount_str}"
                print(f"{i:2d}. {txn['date']} | {txn['description'][:40]:40s} | {amount_str:12s} | {txn['category']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_categorization()
