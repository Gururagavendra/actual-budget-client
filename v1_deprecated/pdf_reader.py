import json
import re
import pymupdf.layout
import pymupdf4llm


def pdf_to_json(pdf_path, password=None):
    """
    Convert a PDF file to JSON format with table extraction.
    
    Args:
        pdf_path: Path to the PDF file
        password: Optional password for encrypted PDFs
    
    Returns:
        JSON string containing extracted PDF data
    """
    doc = pymupdf.open(pdf_path)

    if doc.is_encrypted:
        if not password or not doc.authenticate(password):
            raise RuntimeError("PDF is encrypted and requires authentication")

    return pymupdf4llm.to_json(doc)


def extract_payment_tables(response):
    """
    Extract payment transaction tables from parsed PDF response.
    Handles both standard table format and compressed page 1 format.
    
    Args:
        response: Parsed JSON response from PDF
    
    Returns:
        List of dictionaries containing page number and filtered transaction rows
    """
    header = ["DATE", "MODE", "PARTICULARS", "DEPOSITS", "WITHDRAWALS", "BALANCE"]
    extracted = []
    
    for page in response["pages"]:
        for block in page.get("boxes", []):
            if block.get("boxclass") == "table":
                rows = block.get('table', {}).get("extract", [])
                
                # Check for standard format (header row exists)
                header_found = False
                for i, row in enumerate(rows):
                    if row == header:
                        header_found = True
                        table_data = rows[i+1:]
                        table_data_filtered = []
                        
                        for r in table_data:
                            if len(r) >= 6:
                                # Match date at start (may have additional text after)
                                has_date = r[0] and re.match(r'^\d{2}-\d{2}-\d{4}', str(r[0]))
                                has_deposit = r[3] and str(r[3]).strip() != ''
                                has_withdrawal = r[4] and str(r[4]).strip() != ''
                                has_balance = r[5] and str(r[5]).strip() != ''
                                
                                if has_date and (has_deposit or has_withdrawal or has_balance):
                                    table_data_filtered.append(r)
                        
                        if table_data_filtered:
                            extracted.append({
                                "page_number": page["page_number"],
                                "table_rows": table_data_filtered
                            })
                        break
                
                # Handle page 1 format - look for Total: row to extract page totals
                if not header_found:
                    for row in rows:
                        if row and len(row) > 0 and row[0] and "Total:" in str(row[0]):
                            # Parse Total: line - format is "Total:\ndeposits\nwithdrawals\nbalance"
                            parts = str(row[0]).split('\n')
                            if len(parts) >= 4:
                                try:
                                    deposits = parts[1].strip()
                                    withdrawals = parts[2].strip()
                                    balance = parts[3].strip()
                                    
                                    # Create a synthetic row representing page 1's transactions
                                    extracted.append({
                                        "page_number": page["page_number"],
                                        "table_rows": [[
                                            "01-08-2025",  # Representative date
                                            "VARIOUS",
                                            "Page 1 transactions (summary)",
                                            deposits,
                                            withdrawals,
                                            balance
                                        ]]
                                    })
                                except Exception as e:
                                    pass
                            break
    
    return extracted


def calculate_transaction(extracted, verbose=False):
    """
    Calculate total deposits, withdrawals, and balances from extracted tables.
    
    Args:
        extracted: List of extracted table data
        verbose: If True, print page-by-page summary
    
    Returns:
        Dictionary with total_deposits, total_withdrawals, total_remaining, starting_value
    """
    total_deposits = 0.0
    total_withdrawals = 0.0
    starting_value = 0.0
    final_balance = 0.0
    
    if verbose:
        print("\n=== PAGE-BY-PAGE SUMMARY ===")
    
    for table in extracted:
        page_deposits = 0.0
        page_withdrawals = 0.0
        
        for row in table["table_rows"]:
            if len(row) >= 6:
                deposits_str = row[3] if row[3] and row[3] != "" else "0"
                withdrawals_str = row[4] if row[4] and row[4] != "" else "0"
                balance_str = row[5] if row[5] and row[5] != "" else "0"
                
                deposits = float(deposits_str.replace(',', ''))
                withdrawals = float(withdrawals_str.replace(',', ''))
                balance = float(balance_str.replace(',', ''))
                
                page_deposits += deposits
                page_withdrawals += withdrawals
                total_deposits += deposits
                total_withdrawals += withdrawals
                final_balance = balance
        
        if verbose:
            print(f"Page {table['page_number']}: Deposits={page_deposits:,.2f}, Withdrawals={page_withdrawals:,.2f}")
    
    # Calculate starting balance by reversing the first transaction
    if extracted and extracted[0]["table_rows"]:
        first_row = extracted[0]["table_rows"][0]
        if len(first_row) >= 6 and first_row[5]:
            first_balance = float(first_row[5].replace(',', ''))
            first_deposits = float((first_row[3] if first_row[3] and first_row[3] != "" else "0").replace(',', ''))
            first_withdrawals = float((first_row[4] if first_row[4] and first_row[4] != "" else "0").replace(',', ''))
            starting_value = first_balance - first_deposits + first_withdrawals
    
    return {
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "total_remaining": final_balance,
        "starting_value": starting_value
    }


def main():
    """Main function to process bank statement PDF and display summary."""
    pdf_path = "downloads/aug_2025.pdf"
    password = "guru2111"
    
    res_json = pdf_to_json(pdf_path, password)
    response = json.loads(res_json)

    extracted = extract_payment_tables(response)
    result = calculate_transaction(extracted, verbose=True)
    
    print("\n=== FINAL SUMMARY ===")
    print(f"Starting Balance: {result['starting_value']:,.2f}")
    print(f"Total Deposits: {result['total_deposits']:,.2f}")
    print(f"Total Withdrawals: {result['total_withdrawals']:,.2f}")
    print(f"Final Balance: {result['total_remaining']:,.2f}")
    print(f"\nVerification: {result['starting_value']:,.2f} + {result['total_deposits']:,.2f} - {result['total_withdrawals']:,.2f} = {result['starting_value'] + result['total_deposits'] - result['total_withdrawals']:,.2f}")


if __name__ == "__main__":
    main()