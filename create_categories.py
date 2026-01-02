#!/usr/bin/env python3
"""
Create required categories in Actual Budget for smart categorization.
"""

import sys
sys.path.append('.')

from actual import Actual
from actual.queries import get_categories, create_category

ACTUAL_SERVER_URL = "http://localhost:5006"
ACTUAL_PASSWORD = "guru123"
ACTUAL_FILE = "My Finances"

# Categories needed for smart categorization
REQUIRED_CATEGORIES = [
    "Food",           # Restaurants, cafes, meals
    "Transportation", # Fuel, bus, train, uber, parking
    "Shopping",       # Amazon, Flipkart, retail stores
    "Bills",          # Electricity, water, utilities
    "Transfer",       # Person-to-person UPI payments
    "Entertainment",  # Movies, games, subscriptions
    "Health",         # Medical, pharmacy, fitness
    "Investment",     # Mutual funds, stocks, insurance
    # "General" and "Income" should already exist
]


def create_required_categories():
    """Create any missing categories in Actual Budget."""
    print("=" * 50)
    print("   CREATING REQUIRED CATEGORIES")
    print("=" * 50)

    try:
        with Actual(
            base_url=ACTUAL_SERVER_URL,
            password=ACTUAL_PASSWORD,
            file=ACTUAL_FILE
        ) as actual:
            # Get existing categories
            existing_categories = get_categories(actual.session)
            existing_names = {cat.name for cat in existing_categories}

            print(f"✓ Found {len(existing_categories)} existing categories")

            # Create missing categories
            created_count = 0
            for category_name in REQUIRED_CATEGORIES:
                if category_name not in existing_names:
                    print(f"  Creating category: {category_name}")
                    create_category(actual.session, category_name)
                    created_count += 1
                else:
                    print(f"  ✓ {category_name} already exists")

            # Commit changes
            actual.commit()

            print(f"\n✅ Created {created_count} new categories")
            print(f"Total categories: {len(existing_categories) + created_count}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_required_categories()
