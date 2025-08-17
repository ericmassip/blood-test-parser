# Blood Test Parser

A Python application that extracts blood test data from PDF documents using Google's Gemini AI and optionally updates Google Spreadsheets with the results.

The app is live in https://blood-test-parser-pqfe.vercel.app/.

<img width="1215" height="603" alt="Captura de pantalla 2025-08-17 a las 19 17 02" src="https://github.com/user-attachments/assets/ee6fa0d5-94f9-4381-a7cb-b9b406e4d300" />

## Features

- **PDF Text Extraction**: Extract blood test data from PDF documents
- **AI-Powered Parsing**: Uses Google Gemini AI to interpret and structure blood test results
- **Batch Processing**: Process single files or entire directories
- **Data Validation**: Validate extracted data against expected results
- **Google Sheets Integration**: Automatically update Google Spreadsheets with extracted data
- **Patient Matching**: Smart patient matching using name combinations
- **Error Handling**: Comprehensive error handling and logging
- **Copy-Paste Support**: Generate tab-separated values for manual data entry

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd blood_test_parser
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   export GOOGLE_API_KEY="your_gemini_api_key"
   ```

## Basic Usage

### Extract data from a single PDF:
```bash
python main.py path/to/blood_test.pdf
```

### Process multiple PDFs in a directory:
```bash
python main.py path/to/blood_tests_directory/
```

### Extract and validate results:
```bash
python main.py path/to/file.pdf --validate --validation-threshold 85.0
```

## Google Sheets Integration

### Quick Start

1. Follow the [Google Sheets Setup Guide](GOOGLE_SHEETS_SETUP.md)
2. Place your `credentials.json` file in the project directory
3. Run with spreadsheet integration:

```bash
python main.py path/to/blood_test.pdf --spreadsheet "YOUR_SPREADSHEET_ID"
```

### How It Works

The system:
1. Extracts blood test data from PDFs using AI
2. Searches for patients across ALL sheets/tabs in your spreadsheet using the "FILIACION" column
3. Matches patients by `NOMBRE + APELLIDOS` (with fallback to `APELLIDOS + NOMBRE`)
4. Automatically detects which sheet the patient is in
5. Updates the matching row in the correct sheet with blood test results
6. Provides copy-paste values for unmatched patients

## Command Line Options

```bash
python main.py [INPUT_PATH] [OPTIONS]

Arguments:
  INPUT_PATH                Path to PDF file or directory

Options:
  --api-key KEY            Google API key (or set GOOGLE_API_KEY env var)
  --output, -o FILE        Output JSON file path
  --spreadsheet, -s ID     Google Spreadsheet ID or name to update
  --credentials FILE       Path to Google credentials file (default: credentials.json)
  --validate               Enable validation against expected results
  --validation-threshold N Accuracy threshold for validation (default: 80.0)
  --validation-report FILE Path to save detailed validation report
  --verbose, -v            Enable verbose logging
  --help, -h               Show help message
```

## Examples

### Basic extraction:
```bash
python main.py blood_test.pdf --api-key "your_api_key"
```

### Extract and update spreadsheet:
```bash
python main.py blood_tests/ \
  --spreadsheet "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms" \
  --credentials "my_credentials.json"
```

### Full validation workflow:
```bash
python main.py blood_tests/ \
  --validate \
  --validation-threshold 90.0 \
  --validation-report "validation_results.json" \
  --verbose
```

## Data Structure

The extracted data follows this schema:

```json
{
  "NOMBRE": "JUAN",
  "APELLIDOS": "GARCIA RODRIGUEZ", 
  "HOSPITAL": "NEGRIN",
  "NRO_HISTORIA_CLINICA": "12345678",
  "NRO_MUESTRA": "ABC123456",
  "HEMOGLOBINA": 14.2,
  "HEMATOCRITO": 42.5,
  "VCM": 87.3,
  "ADE": 13.2,
  "PLAQUETAS": 298,
  "LEUCOCITOS": 6.8,
  "EOSINOFILOS_TOTALES": 0.12,
  "EOSINOFILOS_PORCENTAJE": 1.8,
  "GLUCOSA": 98,
  "CREATININA": 0.9,
  "ALT": 22,
  "AST": 18,
  "GGT": 28,
  "COLESTEROL": 187,
  "FERRITINA": 125,
  "VIH": 0,
  "VHA": null,
  "VHC": 0,
  "LUES": 1,
  "STRONGYLOIDES": null,
  "SARAMPION": null,
  "SCHISTOSOMA": null
}
```

## Files Generated

- **Extraction Results**: `extraction_results/extraction_results_TIMESTAMP.json`
- **Validation Reports**: `validation_reports/validation_report_TIMESTAMP.json` 
- **Log Files**: `blood_test_parser.log`

## Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Your Google Gemini API key

### Google Sheets Setup
See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for detailed instructions on:
- Creating a Google Cloud project
- Enabling APIs
- Setting up service account credentials
- Preparing your spreadsheet

## Patient Matching Logic

1. **Multi-Sheet Search**: Searches across ALL sheets/tabs in the spreadsheet
2. **Primary Match**: `NOMBRE + APELLIDOS` → Search in FILIACION column of each sheet
3. **Fallback Match**: `APELLIDOS + NOMBRE` → Search in FILIACION column of each sheet
4. **Case Insensitive**: All matching is case-insensitive
5. **Space Tolerant**: Extra spaces are ignored
6. **Sheet Detection**: Automatically identifies which sheet contains the patient
7. **Duplicate Handling**: Multiple matches (across all sheets) are flagged for manual review
8. **Missing Patient**: Unmatched patients generate copy-paste values

## Error Handling

The system handles various error scenarios:

- **Missing credentials**: Clear setup instructions provided
- **Spreadsheet access**: Permission and sharing guidance
- **Patient not found**: Copy-paste values for manual entry
- **Duplicate patients**: Warning with row numbers
- **API errors**: Detailed error logging
- **Network issues**: Graceful degradation with manual fallbacks

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify `credentials.json` exists and is valid
   - Check spreadsheet sharing with service account email

2. **Patient Not Found**:
   - Verify FILIACION column exists in spreadsheet
   - Check patient name formatting (spaces, accents, etc.)
   - Use `--verbose` flag for detailed matching logs

3. **API Rate Limits**:
   - The system handles rate limiting automatically
   - Large batches may take longer to process

4. **Column Mapping Issues**:
   - Ensure spreadsheet headers match expected column names
   - Check for typos in column headers
   - Use case-insensitive matching

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python main.py file.pdf --spreadsheet "ID" --verbose
```
