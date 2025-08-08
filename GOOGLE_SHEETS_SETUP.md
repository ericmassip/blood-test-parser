# Google Sheets Integration Setup Guide

This guide will help you set up Google Sheets integration for the blood test parser to automatically update spreadsheets with extracted results.

## Prerequisites

1. A Google account
2. Access to Google Cloud Console
3. A Google Spreadsheet with patient data

## Step-by-Step Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note down your project ID

### 2. Enable Google Sheets API

1. In Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google Sheets API"
3. Click on it and press "Enable"

### 3. Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details:
   - Name: `blood-test-parser-service`
   - Description: `Service account for blood test parser spreadsheet integration`
4. Click "Create and Continue"
5. Skip role assignment (click "Continue")
6. Click "Done"

### 4. Generate Service Account Key

1. In the Credentials page, find your service account
2. Click on the service account email
3. Go to the "Keys" tab
4. Click "Add Key" > "Create new key"
5. Select "JSON" format
6. Click "Create"
7. The JSON file will download automatically
8. **Rename this file to `credentials.json`** and place it in your project directory

### 5. Prepare Your Google Spreadsheet

1. Open your Google Spreadsheet
2. Make sure it has a column named "FILIACION" containing patient full names
3. Make sure it has columns matching the blood test parameters (see column mapping below)
4. **Important**: Share the spreadsheet with your service account:
   - Click "Share" in your spreadsheet
   - Add the service account email (found in the credentials.json file under "client_email")
   - Give it "Editor" permissions

### 6. Column Mapping

The system maps these JSON fields to spreadsheet columns:

| JSON Field | Spreadsheet Column |
|------------|-------------------|
| HEMOGLOBINA | Hb (g/dl) 12-18 |
| HEMATOCRITO | Hto (%) 36-50 |
| VCM | VCM (fl) (70-98) |
| ADE | ADE (>16,5) |
| PLAQUETAS | Plaquetas (x10^3/µL) 100-450 |
| LEUCOCITOS | Leucos (x10^3/µL) 5-12 |
| EOSINOFILOS_TOTALES | Eo. Totales (mayor o = 450) |
| EOSINOFILOS_PORCENTAJE | Eo (%) (mayor o = a 5) |
| GLUCOSA | Glu. (mg/dl) 60-110 |
| CREATININA | Creatinina (mg/dl) |
| ALT | ALT (U/L) >45 |
| AST | AST (U/L) >37 |
| GGT | GGT (U/L) > 55 |
| COLESTEROL | Col. T (100-200) |
| FERRITINA | Ferritina (15-120) |
| VIH | VIH |
| VHC | VHC |
| VHA | VHA |
| LUES | Lues |
| STRONGYLOIDES | STRONGYLOIDES |
| SARAMPION | SARAMPIÓN |
| SCHISTOSOMA | SEROL SCHISTOSOMA |

**Note**: The column headers in your spreadsheet should contain these exact texts (case-insensitive matching).

### Multi-Sheet Support

The system automatically searches across **ALL sheets/tabs** in your spreadsheet:

- **Example**: If you have sheets named "2024", "2023", "Pending", etc., the system will search all of them
- **Automatic Detection**: When a patient is found, the system remembers which sheet they're in
- **Smart Updates**: Data is updated in the correct sheet where the patient was found
- **Cross-Sheet Duplicates**: If the same patient appears in multiple sheets, you'll be notified

Example output:
```
Processing sample.pdf - Patient: JUAN GARCIA
  Status: Patient found in sheet '2024' at row 45
  ✓ Successfully updated sheet '2024' row 45
```

## Usage

### Install Dependencies

First, install the new dependencies:

```bash
uv sync
```

### Basic Usage

Run the parser with Google Sheets integration:

```bash
python main.py path/to/blood_test.pdf --spreadsheet "YOUR_SPREADSHEET_ID_OR_NAME"
```

### Finding Your Spreadsheet ID

You can use either:
1. **Spreadsheet ID**: Found in the URL of your Google Spreadsheet
   - URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
   - Use the `SPREADSHEET_ID` part
2. **Spreadsheet Name**: The system will attempt to use it as an ID

### Complete Example

```bash
python main.py /path/to/blood_tests/ \
  --spreadsheet "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms" \
  --credentials "my_credentials.json" \
  --api-key "your_gemini_api_key"
```

## How It Works

1. **Multi-Sheet Search**: The system searches across ALL sheets/tabs in your spreadsheet
2. **Patient Matching**: For each sheet, it searches for patients by matching `NOMBRE + APELLIDOS` against the "FILIACION" column
3. **Fallback Search**: If not found, it tries `APELLIDOS + NOMBRE`
4. **Sheet Detection**: When a patient is found, the system notes which sheet they're in
5. **Duplicate Handling**: If multiple patients have the same name (across all sheets), it logs the issue and provides copy-paste values
6. **Missing Patients**: If a patient is not found in any sheet, it provides copy-paste values for manual entry
7. **Data Update**: Successfully matched patients have their blood test data automatically updated in the correct sheet

## Troubleshooting

### Common Issues

1. **"Credentials file not found"**
   - Make sure `credentials.json` is in the correct location
   - Check the file permissions

2. **"Permission denied" or "Spreadsheet not found"**
   - Ensure you've shared the spreadsheet with the service account email
   - Check that the spreadsheet ID is correct

3. **"FILIACION column not found"**
   - Make sure your spreadsheet has a column containing "FILIACION" in the header
   - Check for spelling errors

4. **"Patient not found"**
   - Verify that patient names in the FILIACION column match the extracted NOMBRE + APELLIDOS
   - Names are matched case-insensitively
   - Extra spaces are ignored

### Debug Mode

Run with verbose logging to see detailed information:

```bash
python main.py path/to/file.pdf --spreadsheet "ID" --verbose
```

## Security Notes

- Keep your `credentials.json` file secure and never commit it to version control
- The service account only has access to spreadsheets you explicitly share with it
- Consider rotating service account keys periodically

## Example credentials.json Structure

Your credentials file should look like this (with your actual values):

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "blood-test-parser-service@your-project-id.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
``` 