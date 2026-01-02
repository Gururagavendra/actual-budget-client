# ActualBudget Bank Statement Automation

This script automates the process of parsing ICICI bank statement PDFs and importing transactions into ActualBudget.

## Changes from Original Script

The original script was designed for Firefly III with email fetching capabilities. This modified version:

1. **Commented out email fetching** - The email fetcher module is disabled as PDF files are already downloaded
2. **Replaced Firefly III with ActualBudget** - Now uses `actualpy` library to connect to ActualBudget
3. **Embedded PDF parser** - Self-contained script with PDF parsing logic built-in
4. **Updated for ICICI format** - Parser specifically handles ICICI bank statement format with proper column parsing

## Prerequisites

- Python 3.10+
- ActualBudget server running (default: http://localhost:5006)
- PDF bank statements in the `downloads/` folder

## Installation

1. Install required packages:
```bash
pip install actualpy PyMuPDF
```

Or use the virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install actualpy PyMuPDF
```

## Configuration

Edit the constants at the top of `main.py`:

```python
ACTUAL_SERVER_URL = "http://localhost:5006"  # Your ActualBudget server URL
ACTUAL_PASSWORD = "your_password"  # ActualBudget server password
ACTUAL_FILE = "My Budget"  # Budget file name or sync ID
ACTUAL_ACCOUNT_NAME = "ICICI Bank"  # Account name in ActualBudget

PDF_PASSWORD = "guru2111"  # Password to open PDF statements
```

## Usage

### Process all PDFs in downloads folder:
```bash
python main.py
```

### Process a specific PDF file:
```bash
python main.py --local /path/to/statement.pdf
```

### Dry-run mode (parse only, don't post to ActualBudget):
```bash
python main.py --dry-run
```

### With custom ActualBudget settings:
```bash
python main.py \
  --server http://localhost:5006 \
  --actual-password mypass \
  --file "My Budget" \
  --account "ICICI Bank"
```

### Help:
```bash
python main.py --help
```

## Command-line Options

- `--local, -l FILE` - Process a specific PDF file
- `--password, -p PASSWORD` - PDF password (default: guru2111)
- `--dry-run, -d` - Parse PDFs but don't post to ActualBudget
- `--server, -s SERVER` - ActualBudget server URL (default: http://localhost:5006)
- `--actual-password ACTUAL_PASSWORD` - ActualBudget server password
- `--file, -f FILE` - ActualBudget file name (default: My Budget)
- `--account, -a ACCOUNT` - Account name in ActualBudget (default: ICICI Bank)

## PDF Format

The script is designed for ICICI bank statement PDFs with the following format:

```
DATE         MODE    PARTICULARS           DEPOSITS  WITHDRAWALS  BALANCE
01-07-2025           UPI/payment/details              12.00       6,57,607.05
```

## How It Works

1. **PDF Extraction**: Opens the PDF with password, extracts text content
2. **Transaction Parsing**: Parses transactions using date patterns and column detection
3. **ActualBudget Import**: Connects to ActualBudget server and creates transactions
4. **Commit**: Syncs changes to the server

## Troubleshooting

### No transactions found
- Check if the PDF format matches ICICI bank statement format
- Verify PDF password is correct
- Try `--dry-run` to see parsing output

### Cannot connect to ActualBudget
- Verify ActualBudget server is running
- Check server URL and password
- Ensure budget file name is correct

### Wrong account
- Update `ACTUAL_ACCOUNT_NAME` in the script
- Or use `--account "Account Name"` flag

## Output Example

```
============================================================
   ACTUALBUDGET BANK STATEMENT AUTOMATION
============================================================
   Server: http://localhost:5006
   Budget: My Budget
   Account: ICICI Bank
============================================================
Found 1 PDF file(s) in downloads folder

============================================================
📄 Processing: statement_JUL_2025.pdf
============================================================

================================================================================
DATE         TYPE             AMOUNT DESCRIPTION                             
================================================================================
2025-07-01   withdrawal        12.00 UPI/q589381422@ybl/t/YES BANK
2025-07-01   withdrawal       137.00 UPI/paytmqr111aihob/neals/YES BANK
...
================================================================================
Total transactions: 164

📤 Posting 164 transactions to ActualBudget...
   Account: ICICI Bank
   ✓ 2025-07-01 - UPI/q589381422@ybl/t/YES BANK - 12.00
   ✓ 2025-07-01 - UPI/paytmqr111aihob/neals/YES BANK - 137.00
...

✅ Committed 164 transactions to ActualBudget

============================================================
                 FINAL SUMMARY
============================================================
  📄 PDFs processed: 1
  ✅ Transactions posted: 164
  ❌ Transactions failed: 0
============================================================
```

## Notes

- The script automatically creates the account if it doesn't exist
- Transactions are marked with import notes
- Amounts are negative for withdrawals, positive for deposits
- The script uses ActualBudget's sync mechanism to avoid duplicates

## ActualBudget Server Setup

If you don't have ActualBudget running yet, use the provided docker-compose.yml:

```bash
docker-compose up -d
```

Then access ActualBudget at http://localhost:5006 and create your budget.
