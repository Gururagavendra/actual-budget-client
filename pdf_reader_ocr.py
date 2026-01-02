import json
import re
import pymupdf
import requests


def extract_text_from_pdf(pdf_path, password=None):
    """
    Extract text from PDF pages.
    
    Args:
        pdf_path: Path to the PDF file
        password: Optional password for encrypted PDFs
    
    Returns:
        List of text strings, one per page
    """
    doc = pymupdf.open(pdf_path)

    if doc.is_encrypted:
        if not password or not doc.authenticate(password):
            raise RuntimeError("PDF is encrypted and requires authentication")

    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pages_text.append(text)
    
    doc.close()
    return pages_text


def extract_transactions_with_llm(page_text, page_num):
    """
    Use Ollama qwen2.5 model to extract transaction totals from page text.
    
    Args:
        page_text: Extracted text from PDF page
        page_num: Page number (for reference)
    
    Returns:
        Dictionary with deposits, withdrawals, and balance
    """
    prompt = f"""You are analyzing a bank statement page. Extract the transaction summary from this page.

Look for a line that starts with "Total:" followed by three numbers:
1. Total Deposits (money in)
2. Total Withdrawals (money out)  
3. Balance

Page text:
{page_text}

Extract ONLY the Total: line numbers. Respond with valid JSON only:
{{"deposits": 0.00, "withdrawals": 0.00, "balance": 0.00}}

If no Total: line exists, respond with all zeros.
Remove commas from numbers. Example: "6,104.00" becomes 6104.00"""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'format': 'json'
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '{}')
            
            try:
                data = json.loads(response_text)
                deposits = float(data.get('deposits', 0))
                withdrawals = float(data.get('withdrawals', 0))
                balance = float(data.get('balance', 0))
                
                if deposits > 0 or withdrawals > 0:
                    print(f"Page {page_num}: Deposits={deposits:,.2f}, Withdrawals={withdrawals:,.2f}")
                
                return {
                    "deposits": deposits,
                    "withdrawals": withdrawals,
                    "balance": balance
                }
            except json.JSONDecodeError:
                print(f"Page {page_num}: JSON parse error")
                return {"deposits": 0.0, "withdrawals": 0.0, "balance": 0.0}
        else:
            print(f"Page {page_num}: API error {response.status_code}")
            return {"deposits": 0.0, "withdrawals": 0.0, "balance": 0.0}
            
    except Exception as e:
        print(f"Page {page_num}: Error - {e}")
        return {"deposits": 0.0, "withdrawals": 0.0, "balance": 0.0}


def extract_transactions_from_page_text(page_text, page_num):
    """
    Extract individual transactions from page text using regex patterns.
    Bank statement format:
    DATE | MODE | PARTICULARS | DEPOSITS | WITHDRAWALS | BALANCE
    
    Args:
        page_text: Extracted text from PDF page
        page_num: Page number (for reference)
    
    Returns:
        List of transaction dictionaries
    """
    transactions = []
    lines = page_text.split('\n')
    
    # Pattern: date at start of line (DD-MM-YYYY)
    date_pattern = re.compile(r'^(\d{2}-\d{2}-\d{4})')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if line starts with a date
        date_match = date_pattern.match(line)
        if date_match:
            date_str = date_match.group(1)
            
            # Skip B/F and Total lines
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line in ['B/F', 'Total:', ''] or 'Total:' in next_line:
                    i += 1
                    continue
            
            # Collect description and amounts from this and next few lines
            description_parts = []
            amounts_found = []
            
            # Look ahead for description and amounts (typically in next 2-6 lines)
            j = i + 1
            while j < len(lines) and j < i + 10:
                next_line = lines[j].strip()
                
                # Stop if we hit another date
                if date_pattern.match(next_line):
                    break
                
                # Stop if we hit Total or B/F or C/F
                if next_line in ['Total:', 'B/F', 'C/F', ''] or 'Total:' in next_line:
                    break
                
                # Check if line contains amounts (numbers with decimals)
                amount_matches = re.findall(r'([\d,]+\.\d{2})', next_line)
                if amount_matches:
                    # Store amounts
                    for amt in amount_matches:
                        amounts_found.append(float(amt.replace(',', '')))
                    # After finding amounts, description is complete
                    if len(amounts_found) >= 2:  # Have transaction amount + balance
                        break
                else:
                    # This is description text
                    if next_line and not next_line.isdigit() and next_line not in ['/']:
                        description_parts.append(next_line)
                
                j += 1
            
            # Parse amounts based on format
            # Format is typically: [deposit OR withdrawal], balance
            # Last amount is always balance
            # If 2 amounts: one is transaction, one is balance
            # If 3 amounts: could be deposit, withdrawal, balance OR description has number + transaction + balance
            
            deposit = 0.0
            withdrawal = 0.0
            balance = 0.0
            
            if len(amounts_found) >= 2:
                # Last amount is balance
                balance = amounts_found[-1]
                
                # Determine if previous transactions had balances to compare
                prev_balance = transactions[-1]['balance'] if transactions else 0.0
                if page_num == 1 and not transactions:
                    # First transaction on first page - check for B/F balance
                    for k in range(max(0, i-10), i):
                        if 'B/F' in lines[k]:
                            # Look for balance near B/F
                            for m in range(k, min(k+5, len(lines))):
                                bf_amounts = re.findall(r'([\d,]+\.\d{2})', lines[m])
                                if bf_amounts:
                                    prev_balance = float(bf_amounts[-1].replace(',', ''))
                                    break
                            break
                
                # Compare balance to determine deposit vs withdrawal
                transaction_amount = amounts_found[0] if len(amounts_found) >= 2 else 0.0
                
                if prev_balance > 0:
                    if balance > prev_balance:
                        # Balance increased - deposit
                        deposit = transaction_amount
                    else:
                        # Balance decreased - withdrawal
                        withdrawal = transaction_amount
                else:
                    # First transaction or no previous balance - use balance change
                    # Check all amounts to see if middle one makes sense
                    if len(amounts_found) == 2:
                        # Could be either - mark as deposit for now (will be corrected)
                        deposit = transaction_amount
            
            # Build description
            description = ' '.join(description_parts[:4])  # Limit to first 4 parts
            description = description.replace('/', ' ')  # Clean up slashes
            
            if amounts_found:  # Only add if we found amounts
                transactions.append({
                    'date': date_str,
                    'description': description[:100] if description else 'Transaction',
                    'deposit': deposit,
                    'withdrawal': withdrawal,
                    'balance': balance
                })
            
            i = j  # Jump to where we stopped looking ahead
        else:
            i += 1
    
    print(f"Page {page_num}: Extracted {len(transactions)} transactions")
    return transactions


def extract_all_transactions_from_pdf(pdf_path, password=None):
    """
    Extract ALL individual transactions from bank statement PDF using fast regex parsing.
    
    Args:
        pdf_path: Path to the bank statement PDF
        password: Optional PDF password
    
    Returns:
        Dictionary with transactions list and summary statistics
    """
    print("Extracting text from PDF...")
    pages_text = extract_text_from_pdf(pdf_path, password)
    
    print(f"Processing {len(pages_text)} pages...\n")
    
    # Extract starting balance from first page FIRST
    starting_balance = 0.0
    lines = pages_text[0].split('\n')
    for idx, line in enumerate(lines):
        if line.strip() == 'B/F' and idx + 1 < len(lines):
            for j in range(1, 5):
                if idx + j < len(lines):
                    balance_match = re.search(r'(\d{1,3}(?:,\d{3})+\.\d{2})', lines[idx + j])
                    if balance_match:
                        potential_balance = float(balance_match.group(1).replace(',', ''))
                        if potential_balance > 10000:  # Reasonable starting balance
                            starting_balance = potential_balance
                            print(f"Starting balance (B/F): ₹{starting_balance:,.2f}\n")
                            break
            if starting_balance > 0:
                break
    
    all_transactions = []
    
    for i, page_text in enumerate(pages_text, 1):
        # Use fast regex-based extraction with starting balance context
        transactions = extract_transactions_from_page_text(page_text, i)
        
        # Update previous balance for each transaction
        for txn in transactions:
            prev_balance = all_transactions[-1]['balance'] if all_transactions else starting_balance
            
            # Recalculate deposit/withdrawal based on balance change
            if prev_balance > 0 and txn['balance'] > 0:
                balance_change = txn['balance'] - prev_balance
                
                if balance_change > 0:
                    # Balance increased - deposit
                    txn['deposit'] = balance_change
                    txn['withdrawal'] = 0.0
                else:
                    # Balance decreased - withdrawal
                    txn['deposit'] = 0.0
                    txn['withdrawal'] = abs(balance_change)
            
            all_transactions.append(txn)
        
        # Get page totals using LLM (fast, only extracts Total: line)
        page_summary = extract_transactions_with_llm(page_text, i)
    
    # Calculate totals
    total_deposits = sum(t['deposit'] for t in all_transactions)
    total_withdrawals = sum(t['withdrawal'] for t in all_transactions)
    final_balance = all_transactions[-1]['balance'] if all_transactions else 0.0
    
    print(f"\n✓ Extracted {len(all_transactions)} individual transactions")
    print(f"  Total Deposits: ₹{total_deposits:,.2f}")
    print(f"  Total Withdrawals: ₹{total_withdrawals:,.2f}")
    
    return {
        "transactions": all_transactions,
        "starting_balance": starting_balance,
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "final_balance": final_balance
    }


def process_bank_statement(pdf_path, password=None):
    """
    Process bank statement PDF using OCR + LLM.
    
    Args:
        pdf_path: Path to the bank statement PDF
        password: Optional PDF password
    
    Returns:
        Dictionary with summary statistics
    """
    print("Extracting text from PDF...")
    pages_text = extract_text_from_pdf(pdf_path, password)
    
    print(f"Processing {len(pages_text)} pages with Ollama qwen2.5...\n")
    print("=== PAGE-BY-PAGE SUMMARY ===")
    
    total_deposits = 0.0
    total_withdrawals = 0.0
    final_balance = 0.0
    starting_balance = 0.0
    
    for i, page_text in enumerate(pages_text, 1):
        result = extract_transactions_with_llm(page_text, i)
        total_deposits += result.get('deposits', 0.0)
        total_withdrawals += result.get('withdrawals', 0.0)
        
        if result.get('balance', 0.0) > 0:
            final_balance = result.get('balance', 0.0)
        
        # Extract starting balance from first page (B/F line)
        if i == 1 and starting_balance == 0.0:
            # Look for B/F (brought forward) pattern - balance usually follows
            lines = page_text.split('\n')
            for idx, line in enumerate(lines):
                if line.strip() == 'B/F' and idx + 1 < len(lines):
                    # Next line or nearby should have the balance
                    for j in range(1, 5):
                        if idx + j < len(lines):
                            # Match larger balances first (6+ digits with commas)
                            balance_match = re.search(r'(\d{1,3}(?:,\d{3})+\.\d{2})', lines[idx + j])
                            if balance_match:
                                potential_balance = float(balance_match.group(1).replace(',', ''))
                                # Starting balance should be reasonably large
                                if potential_balance > 100000:
                                    starting_balance = potential_balance
                                    break
                    if starting_balance > 0:
                        break
    
    # Calculate starting balance from final balance and transactions
    if starting_balance == 0.0 and final_balance > 0:
        starting_balance = final_balance - total_deposits + total_withdrawals
    
    return {
        "starting_balance": starting_balance,
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "final_balance": final_balance
    }


def main():
    """Main function to process bank statement PDF."""
    pdf_path = "downloads/June_2025.pdf"
    password = "guru2111"
    
    result = process_bank_statement(pdf_path, password)
    
    print("\n=== FINAL SUMMARY ===")
    print(f"Starting Balance: {result['starting_balance']:,.2f}")
    print(f"Total Deposits: {result['total_deposits']:,.2f}")
    print(f"Total Withdrawals: {result['total_withdrawals']:,.2f}")
    print(f"Final Balance: {result['final_balance']:,.2f}")
    
    calculated_balance = result['starting_balance'] + result['total_deposits'] - result['total_withdrawals']
    print(f"\nVerification: {result['starting_balance']:,.2f} + {result['total_deposits']:,.2f} - "
          f"{result['total_withdrawals']:,.2f} = {calculated_balance:,.2f}")


if __name__ == "__main__":
    main()
