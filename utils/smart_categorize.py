"""
Smart transaction categorization using hybrid approach:
1. Parse transaction PARTICULARS to extract structured fields
2. Send description + receiver_name to LLM for intelligent categorization
3. No keyword maintenance required - LLM understands context
"""

import json
import requests


# Predefined category list for Actual Budget
CATEGORIES = [
    "Food",           # Restaurants, cafes, meals, groceries
    "Transportation", # Fuel, bus, train, uber, ola, parking, toll
    "Shopping",       # Amazon, Flipkart, clothing, electronics
    "Bills",          # Electricity, water, recharge, utilities
    "Transfer",       # Person-to-person UPI payments
    "Entertainment",  # Movies, games, subscriptions
    "Health",         # Medical, pharmacy, fitness
    "Investment",     # Mutual funds, stocks, insurance
    "General"         # Fallback for unclassified
]


def parse_upi_particulars(particulars: str) -> dict:
    """
    Parse UPI transaction format: payment_mode/receiver_name/receiver_id/description/receiver_bank
    
    Example: "UPI/Mohan Sing/paytmqr5jwkvc@/chapati/YES BANK"
    Returns: {'mode': 'UPI', 'receiver_name': 'Mohan Sing', 'description': 'chapati', ...}
    
    Args:
        particulars: Transaction PARTICULARS field from bank statement
    
    Returns:
        Dictionary with parsed fields, or None if not UPI format
    """
    parts = particulars.split('/')
    
    if len(parts) >= 5 and parts[0] == 'UPI':
        return {
            'mode': parts[0],
            'receiver_name': parts[1].strip(),
            'receiver_id': parts[2].strip(),
            'description': parts[3].strip(),
            'bank': parts[4].strip() if len(parts) > 4 else '',
            'full_text': particulars
        }
    
    # Return basic structure for non-UPI transactions
    return {
        'mode': 'OTHER',
        'receiver_name': '',
        'receiver_id': '',
        'description': particulars,
        'bank': '',
        'full_text': particulars
    }


def categorize_with_llm(description: str, receiver_name: str, amount: float, is_deposit: bool) -> str:
    """
    Use Ollama qwen2.5 model to categorize transaction based on description.
    
    Args:
        description: Transaction description field (e.g., "chapati", "breakfast")
        receiver_name: Receiver/merchant name (e.g., "Mohan Sing", "MADURA CAF")
        amount: Transaction amount (for context)
        is_deposit: True if money coming in (Income), False if going out
    
    Returns:
        Category name from CATEGORIES list
    """
    # If it's a deposit, automatically categorize as Income
    if is_deposit:
        return "Income"
    
    # Combine description and receiver name for context
    context = f"{description} - {receiver_name}".strip(" -")
    
    prompt = f"""You are a financial assistant categorizing bank transactions.

Transaction details:
- Description: {description}
- Merchant/Receiver: {receiver_name}
- Amount: ₹{amount:,.2f}

Categorize this transaction into ONE of these categories:
{json.dumps(CATEGORIES, indent=2)}

Rules:
- Food: Restaurants, cafes, food delivery, groceries, meals (breakfast/lunch/dinner)
- Transportation: Fuel, petrol, bus, train, metro, uber, ola, rapido, parking, toll
- Shopping: Online shopping (Amazon, Flipkart), retail stores, clothing, electronics
- Bills: Electricity, water, gas, mobile recharge, internet, utilities
- Transfer: Person-to-person payments (names without merchant context)
- Entertainment: Movies, games, streaming services, sports, events
- Health: Hospitals, pharmacies, doctors, gym, fitness
- Investment: Mutual funds, stocks, insurance premiums, savings
- General: Anything that doesn't fit above categories

Respond with ONLY the category name, nothing else. No explanation.

Example:
Description: "chapati", Merchant: "Mohan Sing" → Food
Description: "petrol", Merchant: "HP PETROL PUMP" → Transportation
Description: "", Merchant: "Yanamala A" → Transfer
"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False
            },
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            category = result.get('response', 'General').strip()
            
            # Validate category is in our list
            if category in CATEGORIES:
                return category
            
            # Try to find partial match (LLM might add extra text)
            for valid_cat in CATEGORIES:
                if valid_cat.lower() in category.lower():
                    return valid_cat
            
            print(f"Warning: LLM returned invalid category '{category}', using General")
            return "General"
        else:
            print(f"LLM API error {response.status_code}, using General")
            return "General"
            
    except Exception as e:
        print(f"Error calling LLM: {e}, using General")
        return "General"


def categorize_transaction(particulars: str, amount: float, is_deposit: bool, verbose: bool = False) -> str:
    """
    Main function: Parse transaction and categorize using LLM.
    
    Args:
        particulars: Transaction PARTICULARS/description field
        amount: Transaction amount
        is_deposit: True if deposit (money in), False if withdrawal
        verbose: Print debug information
    
    Returns:
        Category name
    """
    # Parse transaction format
    parsed = parse_upi_particulars(particulars)
    
    if verbose:
        print(f"\nParsed: {json.dumps(parsed, indent=2)}")
    
    # Get LLM categorization
    category = categorize_with_llm(
        description=parsed['description'],
        receiver_name=parsed['receiver_name'],
        amount=amount,
        is_deposit=is_deposit
    )
    
    if verbose:
        print(f"Category: {category}")
    
    return category


dpdef extract_description_with_llm(description: str, receiver_name: str, amount: float, is_deposit: bool) -> str:
    """
    Use Ollama qwen2.5 model to extract a short, human-readable description from transaction details.
    
    Args:
        description: Transaction description field (e.g., "chapati", "breakfast")
        receiver_name: Receiver/merchant name (e.g., "Mohan Sing", "MADURA CAF")
        amount: Transaction amount (for context)
        is_deposit: True if money coming in (Income), False if going out
    
    Returns:
        Short description string (1-3 words) like "snacks", "coffee", "breakfast", "train ticket", etc.
    """
    prompt = f"""You are a financial assistant extracting short, human-readable descriptions from bank transactions.

Transaction details:
- Description: {description}
- Merchant/Receiver: {receiver_name}
- Amount: ₹{amount:,.2f}
- Type: {'Deposit' if is_deposit else 'Withdrawal'}

Extract a short, meaningful description (1-3 words) that describes what this transaction is for.
Examples:
- "snacks", "coffee", "breakfast", "lunch", "dinner"
- "train ticket", "metro", "bus", "petrol"
- "groceries", "shopping", "clothing"
- "mobile recharge", "electricity bill"
- "salary", "refund", "transfer"

If it's a person-to-person transfer, use the receiver name or "transfer".
If it's unclear, use a generic term based on the merchant name.

Respond with ONLY the short description (1-3 words), nothing else. No explanation, no quotes, no punctuation.
"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False
            },
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            extracted_desc = result.get('response', '').strip()
            
            # Clean up the response - remove quotes, extra whitespace, newlines
            extracted_desc = extracted_desc.strip('"\'')
            extracted_desc = ' '.join(extracted_desc.split())
            
            # Limit to reasonable length (max 50 chars)
            if extracted_desc:
                return extracted_desc[:50]
            else:
                return ""
        else:
            return ""
            
    except Exception as e:
        return ""


def extract_transaction_description(particulars: str, amount: float, is_deposit: bool, verbose: bool = False) -> str:
    """
    Main function: Parse transaction and extract human-readable description using LLM.
    
    Args:
        particulars: Transaction PARTICULARS/description field
        amount: Transaction amount
        is_deposit: True if deposit (money in), False if withdrawal
        verbose: Print debug information
    
    Returns:
        Short description string (1-3 words)
    """
    # Parse transaction format
    parsed = parse_upi_particulars(particulars)
    
    if verbose:
        print(f"\nParsed: {json.dumps(parsed, indent=2)}")
    
    # Get LLM description extraction
    extracted_desc = extract_description_with_llm(
        description=parsed['description'],
        receiver_name=parsed['receiver_name'],
        amount=amount,
        is_deposit=is_deposit
    )
    
    if verbose:
        print(f"Extracted Description: {extracted_desc}")
    
    return extracted_desc


def test_categorization():
    """Test the categorization with sample transactions."""
    test_cases = [
        ("UPI/Saravanan/paytmqr6b1nv5@/breakfast/YES BANK", 150.0, False),
        ("UPI/AL TAJ RES/paytmqr6ieh4q@/dinner/YES BANK", 450.0, False),
        ("UPI/MADURA CAF/maduracafeandj/t/TAMILNAD M", 180.0, False),
        ("UPI/YANAMALA A/aravindy1605-1/UPI/ICICI Bank", 500.0, False),
        ("UPI/HP PETROL/hppetrol@paytm/petrol/HDFC", 2000.0, False),
        ("SALARY CREDIT", 50000.0, True),
    ]
    
    print("=== TESTING TRANSACTION CATEGORIZATION ===\n")
    
    for particulars, amount, is_deposit in test_cases:
        print(f"Transaction: {particulars}")
        print(f"Amount: ₹{amount:,.2f} ({'Deposit' if is_deposit else 'Withdrawal'})")
        
        category = categorize_transaction(particulars, amount, is_deposit, verbose=True)
        
        print(f"✓ Final Category: {category}")
        print("-" * 60)


if __name__ == "__main__":
    test_categorization()
