# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Blood Test Parser application that extracts structured data from Spanish medical PDF documents using Google's Gemini AI. The system processes blood test PDFs, validates results, and integrates with Google Spreadsheets for data management.

## Key Commands

### Development Environment
```bash
# Install dependencies
uv sync

# Run the application
python main.py path/to/file.pdf --api-key "your_key"
python main.py blood_tests/ --spreadsheet "SPREADSHEET_ID"

# Environment setup
export GOOGLE_API_KEY="your_gemini_api_key"
```

### Testing and Validation
```bash
# Extract and validate data
python main.py blood_tests/ --validate --validation-threshold 85.0

# Generate validation report
python main.py blood_tests/ --validate --validation-report "validation_results.json"

# Enable verbose logging for debugging
python main.py file.pdf --verbose
```

### Google Sheets Integration
```bash
# Update spreadsheet with results
python main.py blood_tests/ --spreadsheet "SPREADSHEET_ID" --credentials "credentials.json"
```

## Code Architecture

### Core Components

1. **BloodTestParser** (`parser.py`):
   - Uses LangChain with Google Gemini 2.5-flash model
   - Processes PDF documents via base64 encoding
   - Returns structured Pydantic models defined in `models.py`
   - Loads extraction instructions from `system_instructions.txt`

2. **BloodTestData Model** (`models.py`):
   - Pydantic schema defining 38+ medical parameters
   - Handles Spanish medical terminology and units
   - Maps to specific JSON keys for consistency

3. **BloodTestValidator** (`validator.py`):
   - Compares extracted data against expected results in `blood_tests/json_data/`
   - Calculates field-level and overall accuracy percentages
   - Supports configurable accuracy thresholds
   - Generates detailed validation reports

4. **GoogleSheetsService** (`google_sheets_service.py`):
   - Authenticates via service account credentials
   - Multi-sheet patient search across spreadsheet tabs
   - Smart patient matching using name combinations
   - Column mapping for medical parameters
   - Spanish locale number formatting for copy-paste functionality

### Data Flow

1. **Input Processing**: PDFs → Base64 encoding → Gemini API
2. **Extraction**: System instructions + PDF → Structured BloodTestData
3. **Validation**: Compare against expected JSON files → Accuracy metrics
4. **Output**: JSON results + Google Sheets updates + Copy-paste values

### Key Features

- **Multi-sheet Search**: Searches for patients across all spreadsheet tabs using FILIACION column
- **Smart Patient Matching**: Tries both "NOMBRE APELLIDOS" and "APELLIDOS NOMBRE" patterns
- **Spanish Medical Format**: Handles Spanish number formats (comma as decimal separator)
- **Batch Processing**: Processes entire directories of PDF files
- **Error Handling**: Graceful fallbacks with copy-paste values for failed operations

## File Structure

```
blood_tests/           # Source PDF files
  json_data/          # Expected results for validation
extraction_results/   # Generated extraction outputs
validation_reports/   # Validation analysis results
credentials.json      # Google service account key (not in git)
system_instructions.txt # Spanish extraction prompts for Gemini
```

## Google Sheets Integration

The system expects spreadsheets with:
- FILIACION column containing patient names
- Specific column headers matching medical parameters
- Multiple sheets/tabs supported for patient organization

Patient matching logic:
1. Search all sheets for FILIACION column
2. Try "NOMBRE APELLIDOS" and "APELLIDOS NOMBRE" combinations
3. Case-insensitive matching with space tolerance
4. Handle duplicates and missing patients gracefully

## Dependencies

- **AI/ML**: `langchain-google-genai`, `google-generativeai`
- **Google APIs**: `google-api-python-client`, `google-auth`
- **Data**: `pydantic` for schemas, `python-dotenv` for config
- **Testing**: `pytest` for validation testing

## Validation System

The validator uses percentage-based accuracy metrics:
- Field-level accuracy for each medical parameter
- Overall accuracy as mean of all field accuracies
- Configurable threshold (default 80%) for pass/fail
- Detailed reports with field differences and statistics