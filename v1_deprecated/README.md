# Deprecated Code - V1

This folder contains previous iterations of the PDF bank statement parser that were replaced by more robust solutions.

## Files

### pdf_reader.py
- **Approach**: Used `pymupdf4llm` for table extraction with manual regex parsing
- **Issues**: 
  - Failed on inconsistent PDF table formats
  - Page 1 had different structure (compressed table)
  - Required complex regex patterns for different formats
  - Brittle and hard to maintain
- **Deprecated**: 2026-01-01

### pdf_reder_backup.py
- **Approach**: Early backup of PDF reader
- **Issues**: Incomplete implementation
- **Deprecated**: 2026-01-01

### pdf_reader_llm.py
- **Approach**: Used Ollama `llava:latest` vision model to read PDF images
- **Issues**:
  - llava struggled with precise number extraction
  - Incorrect totals extracted
  - Vision models not reliable for structured data
- **Deprecated**: 2026-01-01

## Current Solution

**File**: `pdf_reader_ocr.py` (in parent directory)

**Approach**: 
- Uses PyMuPDF's built-in text extraction
- Passes extracted text to Ollama `qwen2.5:7b` for intelligent parsing
- LLM finds "Total:" rows and extracts structured data

**Benefits**:
- ✅ 100% accuracy across all test PDFs (6/6 passed)
- ✅ Handles any PDF format/layout variations
- ✅ Uses local Ollama (no API costs)
- ✅ Fast and reliable
- ✅ Easy to maintain

## Test Results

All 6 bank statement PDFs (May-Nov 2025) passed with perfect verification.
