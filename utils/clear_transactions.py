#!/usr/bin/env python3
"""
Clear all transactions from ActualBudget account.
"""

from actual import Actual
from actual.queries import get_transactions, get_account

ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"
ACTUAL_ACCOUNT_NAME = "icici"

def clear_all_transactions():
    """Delete all transactions from the account."""
    
    print("=" * 60)
    print("   CLEARING ALL TRANSACTIONS")
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
            
            # Get all transactions for this account
            all_transactions = get_transactions(actual.session)
            print(f"✓ Total transactions in database: {len(all_transactions)}")
            
            # Debug: check first transaction attributes
            if all_transactions:
                sample = all_transactions[0]
                print(f"✓ Sample transaction attributes: {dir(sample)}")
                print(f"✓ Sample transaction account field: {getattr(sample, 'acct', 'N/A')}")
            
            # Filter by account - try both 'account' and 'acct'
            account_transactions = []
            for t in all_transactions:
                if hasattr(t, 'acct') and t.acct == account.id:
                    account_transactions.append(t)
                elif hasattr(t, 'account') and t.account == account.id:
                    account_transactions.append(t)
            
            if not account_transactions:
                print(f"✓ No transactions to delete for account {ACTUAL_ACCOUNT_NAME}")
                return
            
            print(f"\n⚠️  Found {len(account_transactions)} transaction(s) to delete for {ACTUAL_ACCOUNT_NAME}")
            
            # Confirm deletion
            response = input("\nAre you sure you want to delete ALL transactions? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cancelled")
                return
            
            # Delete each transaction
            print(f"\n🗑️  Deleting transactions...")
            for txn in account_transactions:
                actual.session.delete(txn)
            
            # Commit changes
            actual.commit()
            print(f"✅ Successfully deleted {len(account_transactions)} transaction(s)")
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clear_all_transactions()
