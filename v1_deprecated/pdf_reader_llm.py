import json
import re
import pymupdf
import base64
import requests
from io import BytesIO
from PIL import Image


def pdf_to_images(pdf_path, password=None):
    """
    Convert PDF pages to images for LLM processing.
    
    Args:
        pdf_path: Path to the PDF file
        password: Optional password for encrypted PDFs
    
    Returns:
        List of PIL Images, one per page
    """
    doc = pymupdf.open(pdf_path)

    if doc.is_encrypted:
        if not password or not doc.authenticate(password):
            raise RuntimeError("PDF is encrypted and requires authentication")

    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render page to image at 300 DPI for better quality
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    
    doc.close()
    return images


def image_to_base64(image):
    """Convert PIL Image to base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def extract_transactions_with_llm(image, page_num):
    """
    Use Ollama llava model to extract transactions from page image.
    
    Args:
        image: PIL Image of the PDF page
        page_num: Page number (for reference)
    
    Returns:
        Dictionary with deposits, withdrawals, and balance
    """
    img_base64 = image_to_base64(image)
    
    prompt = """Analyze this bank statement page and extract the transaction summary.

Look for a "Total:" row at the bottom of the transaction table.
Extract these exact numbers:
1. Total Deposits (credits/money in)
2. Total Withdrawals (debits/money out)
3. Final Balance

Respond ONLY with a JSON object in this exact format:
{"deposits": 0.00, "withdrawals": 0.00, "balance": 0.00}

If there are no transactions on this page (like account details page), respond with:
{"deposits": 0.00, "withdrawals": 0.00, "balance": 0.00}

Important: Remove commas from numbers. Use only the Total row, not individual transactions."""

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llava:latest',
                'prompt': prompt,
                'images': [img_base64],
                'stream': False
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '{}')
            
            # Extract JSON from response (llava might add extra text)
            json_match = re.search(r'\{[^}]*"deposits"[^}]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group(0))
                print(f"Page {page_num}: Deposits={data.get('deposits', 0):,.2f}, "
                      f"Withdrawals={data.get('withdrawals', 0):,.2f}")
                return data
            else:
                print(f"Page {page_num}: Could not parse JSON from response")
                print(f"  Raw response: {response_text[:200]}")
                return {"deposits": 0.0, "withdrawals": 0.0, "balance": 0.0}
        else:
            print(f"Page {page_num}: API error {response.status_code}")
            return {"deposits": 0.0, "withdrawals": 0.0, "balance": 0.0}
            
    except Exception as e:
        print(f"Page {page_num}: Error - {e}")
        return {"deposits": 0.0, "withdrawals": 0.0, "balance": 0.0}


def process_bank_statement(pdf_path, password=None):
    """
    Process bank statement PDF using local LLM.
    
    Args:
        pdf_path: Path to the bank statement PDF
        password: Optional PDF password
    
    Returns:
        Dictionary with summary statistics
    """
    print("Converting PDF to images...")
    images = pdf_to_images(pdf_path, password)
    
    print(f"Processing {len(images)} pages with Ollama llava...\n")
    print("=== PAGE-BY-PAGE SUMMARY ===")
    
    total_deposits = 0.0
    total_withdrawals = 0.0
    final_balance = 0.0
    starting_balance = 0.0
    
    for i, image in enumerate(images, 1):
        result = extract_transactions_with_llm(image, i)
        total_deposits += result.get('deposits', 0.0)
        total_withdrawals += result.get('withdrawals', 0.0)
        
        if result.get('balance', 0.0) > 0:
            final_balance = result.get('balance', 0.0)
            if starting_balance == 0.0 and i == 1:
                # First page balance minus first page transactions
                starting_balance = final_balance - result.get('deposits', 0.0) + result.get('withdrawals', 0.0)
    
    return {
        "starting_balance": starting_balance,
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "final_balance": final_balance
    }


def main():
    """Main function to process bank statement PDF."""
    pdf_path = "downloads/aug_2025.pdf"
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
