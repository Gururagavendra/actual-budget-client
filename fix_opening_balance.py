#!/usr/bin/env python3
"""
Fix the opening balance transaction to use Starting Balances category.
"""

import sys
sys.path.append('.')

from actual import Actual
from actual.queries import get_transactions, get_account, get_categories

ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"
ACTUAL_ACCOUNT_NAME = "icici"


def fix_opening_balance_category():
    """Update opening balance transaction to use Starting Balances category."""
    print("=" * 60)
    print("   FIXING OPENING BALANCE CATEGORY")
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

            # Get Starting Balances category
            categories = get_categories(actual.session)
            starting_balance_category = None
            for cat in categories:
                if cat.name == "Starting Balances":
                    starting_balance_category = cat
                    break

            if not starting_balance_category:
                print("❌ 'Starting Balances' category not found!")
                return

            print(f"✓ Found Starting Balances category (ID: {starting_balance_category.id})")

            # Get all transactions
            transactions = get_transactions(actual.session, account=account)

            # Find opening balance transaction
            opening_balance_txn = None
            for txn in transactions:
                if txn.notes and "Starting balance from bank statement" in txn.notes:
                    opening_balance_txn = txn
                    break

            if not opening_balance_txn:
                print("❌ Opening balance transaction not found!")
                return

            print(f"✓ Found opening balance transaction")
            print(f"   Date: {opening_balance_txn.date}")
            print(f"   Amount: ₹{opening_balance_txn.amount:,.2f}")

            # Update category
            opening_balance_txn.category_id = starting_balance_category.id
            actual.session.add(opening_balance_txn)
            actual.commit()

            print(f"\n✅ Opening balance categorized as 'Starting Balances'")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    fix_opening_balance_category()
