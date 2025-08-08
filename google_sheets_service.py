"""
Google Sheets Service - Handle Google Sheets integration for blood test results
"""

import os
import logging
import locale
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Service for interacting with Google Sheets"""
    
    # Column mapping from JSON keys to spreadsheet columns (in order)
    COLUMN_MAPPING = {
        'HEMOGLOBINA': 'Hb (g/dl) 12-18',
        'HEMATOCRITO': 'Hto (%) 36-50', 
        'VCM': 'VCM (fl) (70-98)',
        'ADE': 'ADE (>16,5)',
        'PLAQUETAS': 'Plaquetas (x10^3/µL) 100-450',
        'LEUCOCITOS': 'Leucos (x10^3/µL) 5-12',
        'EOSINOFILOS_TOTALES': 'Eo. Totales (mayor o = 450)',
        'EOSINOFILOS_PORCENTAJE': 'Eo (%) (mayor o = a 5)',
        'GLUCOSA': 'Glu. (mg/dl) 60-110',
        'CREATININA': 'Creatinina (mg/dl)',
        'ALT': 'ALT (U/L) >45',
        'AST': 'AST (U/L) >37',
        'GGT': 'GGT (U/L) > 55',
        'COLESTEROL': 'Col. T (100-200)',
        'FERRITINA': 'Ferritina (15-120)',
        'VIH': 'VIH',
        'VHC': 'VHC',
        'VHA': 'VHA',
        'LUES': 'Lues',
        'STRONGYLOIDES': 'STRONGYLOIDES',
        'SARAMPION': 'SARAMPIÓN',
        'SCHISTOSOMA': 'SEROL SCHISTOSOMA'
    }
    
    def __init__(self, credentials_file: str = 'credentials.json'):
        """
        Initialize Google Sheets service
        
        Args:
            credentials_file: Path to service account credentials JSON file
        """
        self.credentials_file = credentials_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using service account"""
        try:
            if not os.path.exists(self.credentials_file):
                raise FileNotFoundError(
                    f"Credentials file not found: {self.credentials_file}\n"
                    f"Please download your service account key from Google Cloud Console and save it as '{self.credentials_file}'"
                )
            
            # Define the required scopes
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            
            # Create credentials from service account file
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=scopes
            )
            
            # Build the service
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Successfully authenticated with Google Sheets API")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets API: {str(e)}")
            raise
    
    def get_spreadsheet_sheets(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Get all sheets/tabs in a spreadsheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet (from URL)
            
        Returns:
            List of sheet information dictionaries
        """
        try:
            validated_id = self._get_spreadsheet_id(spreadsheet_id)
            
            result = self.service.spreadsheets().get(
                spreadsheetId=validated_id,
                fields='sheets.properties'
            ).execute()
            
            sheets = result.get('sheets', [])
            logger.info(f"Found {len(sheets)} sheets in spreadsheet")
            return sheets
            
        except HttpError as e:
            logger.error(f"Error getting sheets: {str(e)}")
            raise
    
    def get_spreadsheet_data(self, spreadsheet_id: str, sheet_name: str = None, range_name: str = None) -> List[List[Any]]:
        """
        Get data from a Google Spreadsheet
        
        Args:
            spreadsheet_id: ID of the spreadsheet (from URL)
            sheet_name: Name of the specific sheet/tab (if None, uses default)
            range_name: Range to read (if None, auto-detects based on headers)
            
        Returns:
            List of rows, where each row is a list of cell values
        """
        try:
            # Validate the spreadsheet ID
            validated_id = self._get_spreadsheet_id(spreadsheet_id)
            
            # If no range specified, auto-detect based on headers
            if range_name is None:
                range_name = self._detect_data_range(validated_id, sheet_name)
            
            # Build range string with sheet name if provided
            if sheet_name:
                full_range = f"'{sheet_name}'!{range_name}"
            else:
                full_range = range_name
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=validated_id,
                range=full_range
            ).execute()
            
            values = result.get('values', [])
            sheet_info = f" from sheet '{sheet_name}'" if sheet_name else ""
            logger.info(f"Retrieved {len(values)} rows{sheet_info} (range: {range_name})")
            return values
            
        except HttpError as e:
            logger.error(f"Error reading spreadsheet{f' sheet {sheet_name}' if sheet_name else ''}: {str(e)}")
            raise
    
    def _detect_data_range(self, spreadsheet_id: str, sheet_name: str = None) -> str:
        """
        Detect the data range by finding the last column with a non-empty header
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the specific sheet/tab
            
        Returns:
            Range string (e.g., 'A:AC' for columns A through AC)
        """
        try:
            # First, get a large range to find headers (up to column ZZ = 702 columns)
            if sheet_name:
                header_range = f"'{sheet_name}'!1:1"
            else:
                header_range = "1:1"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=header_range,
                majorDimension='ROWS'
            ).execute()
            
            values = result.get('values', [])
            if not values or not values[0]:
                logger.warning("No headers found, using default range A:Z")
                return 'A:Z'
            
            headers = values[0]
            
            # Find the last non-empty header
            last_col_index = 0
            for i, header in enumerate(headers):
                if header and str(header).strip():  # Non-empty header
                    last_col_index = i
            
            # Convert index to column letter
            last_col_letter = self._column_index_to_letter(last_col_index)
            
            # Return range from A to the last column with data
            range_str = f"A:{last_col_letter}"
            logger.debug(f"Auto-detected range: {range_str} (found {last_col_index + 1} columns with headers)")
            return range_str
            
        except Exception as e:
            logger.warning(f"Error detecting range, using default A:Z: {str(e)}")
            return 'A:Z'
    
    def _get_spreadsheet_id(self, spreadsheet_id: str) -> str:
        """
        Validate and return spreadsheet ID
        
        Args:
            spreadsheet_id: ID of the spreadsheet (from URL)
            
        Returns:
            Spreadsheet ID
            
        Note:
            We cannot use spreadsheet names because:
            1. Google Sheets API only accepts IDs, not names
            2. Names are not unique (multiple sheets can have same name)
            3. Names can change, breaking references
            4. Converting names to IDs would require Drive API and complex search logic
        """
        # If it looks like a spreadsheet ID (long alphanumeric string), return as-is
        if len(spreadsheet_id) > 20 and spreadsheet_id.replace('_', '').replace('-', '').isalnum():
            return spreadsheet_id
        
        # Warn if user might have provided a name instead of ID
        logger.warning(f"'{spreadsheet_id}' doesn't look like a spreadsheet ID. Please use the ID from your Google Sheets URL.")
        return spreadsheet_id
    
    def find_patient_row(self, spreadsheet_id: str, nombre: str, apellidos: str) -> Tuple[Optional[int], Optional[str], str]:
        """
        Find patient row in spreadsheet by searching across all sheets
        
        Args:
            spreadsheet_id: ID of the spreadsheet (from URL)
            nombre: Patient's first name
            apellidos: Patient's last name
            
        Returns:
            Tuple of (row_number, sheet_name, status_message)
            row_number and sheet_name are None if not found or if there are duplicates
        """
        try:
            # Get all sheets in the spreadsheet
            sheets = self.get_spreadsheet_sheets(spreadsheet_id)
            
            if not sheets:
                return None, None, "No sheets found in spreadsheet"
            
            # Create full name combinations to search for
            full_name_1 = f"{nombre} {apellidos}".lower().strip()
            full_name_2 = f"{apellidos} {nombre}".lower().strip()
            
            logger.info(f"Searching for patient: '{full_name_1}' or '{full_name_2}' across {len(sheets)} sheets")
            
            # Search across all sheets
            all_matches = []  # List of (sheet_name, row_number) tuples
            
            for sheet in sheets:
                sheet_name = sheet['properties']['title']
                logger.debug(f"Searching in sheet: '{sheet_name}'")
                
                try:
                    # Get data from this sheet
                    data = self.get_spreadsheet_data(spreadsheet_id, sheet_name)
                    
                    if not data:
                        logger.debug(f"Sheet '{sheet_name}' is empty, skipping")
                        continue
                    
                    # Find FILIACION column in this sheet
                    header_row = data[0] if data else []
                    filiacion_col = None
                    
                    for i, cell in enumerate(header_row):
                        if cell and 'FILIACION' in str(cell).upper():
                            filiacion_col = i
                            break
                    
                    if filiacion_col is None:
                        logger.debug(f"No FILIACION column found in sheet '{sheet_name}', skipping")
                        continue
                    
                    # Search for patient in this sheet
                    for row_index, row in enumerate(data[1:], start=2):  # Start from row 2 (skip header)
                        if len(row) > filiacion_col:
                            filiacion_value = str(row[filiacion_col]).lower().strip()
                            
                            if filiacion_value == full_name_1 or filiacion_value == full_name_2:
                                all_matches.append((sheet_name, row_index))
                                logger.info(f"Found patient in sheet '{sheet_name}' at row {row_index}")
                
                except Exception as e:
                    logger.warning(f"Error searching sheet '{sheet_name}': {str(e)}")
                    continue
            
            # Handle results
            if len(all_matches) == 0:
                return None, None, f"Patient not found in any sheet: {full_name_1}"
            elif len(all_matches) == 1:
                sheet_name, row_number = all_matches[0]
                logger.info(f"Found patient in sheet '{sheet_name}' at row {row_number}")
                return row_number, sheet_name, f"Patient found in sheet '{sheet_name}' at row {row_number}"
            else:
                # Multiple matches found
                match_details = [f"'{sheet}' row {row}" for sheet, row in all_matches]
                return None, None, f"Multiple patients found with same name: {full_name_1} (locations: {', '.join(match_details)})"
        
        except Exception as e:
            logger.error(f"Error finding patient: {str(e)}")
            return None, None, f"Error searching for patient: {str(e)}"
    
    def update_patient_data(self, spreadsheet_id: str, sheet_name: str, row_number: int, blood_test_data: Dict[str, Any]) -> bool:
        """
        Update patient row with blood test data
        
        Args:
            spreadsheet_id: ID of the spreadsheet (from URL)
            sheet_name: Name of the specific sheet/tab
            row_number: Row number to update (1-based)
            blood_test_data: Dictionary with blood test results
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get spreadsheet data to find column positions
            data = self.get_spreadsheet_data(spreadsheet_id, sheet_name)
            
            if not data:
                logger.error(f"Cannot update: sheet '{sheet_name}' is empty")
                return False
            
            header_row = data[0]
            
            # Create updates list
            updates = []
            
            for json_key, spreadsheet_column in self.COLUMN_MAPPING.items():
                # Find column index for this field
                col_index = None
                for i, header in enumerate(header_row):
                    if header and spreadsheet_column.lower() in str(header).lower():
                        col_index = i
                        break
                
                if col_index is not None and json_key in blood_test_data:
                    value = blood_test_data[json_key]
                    if value is not None:
                        # Apply custom transformations for specific fields
                        if json_key == 'EOSINOFILOS_TOTALES' and isinstance(value, (int, float)):
                            value = value * 1000  # Convert format for spreadsheet
                        
                        # Convert column index to letter (A, B, C, etc.)
                        col_letter = self._column_index_to_letter(col_index)
                        cell_range = f"'{sheet_name}'!{col_letter}{row_number}"
                        
                        # Preserve original data type (don't convert everything to string)
                        updates.append({
                            'range': cell_range,
                            'values': [[value]]  # Keep original type (int, float, etc.)
                        })
            
            if not updates:
                logger.warning("No data to update")
                return False
            
            # Perform batch update
            validated_id = self._get_spreadsheet_id(spreadsheet_id)
            
            batch_update_request = {
                'valueInputOption': 'USER_ENTERED',  # Let Google Sheets interpret the data type
                'data': updates
            }
            
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=validated_id,
                body=batch_update_request
            ).execute()
            
            updated_cells = result.get('totalUpdatedCells', 0)
            logger.info(f"Successfully updated {updated_cells} cells in sheet '{sheet_name}' row {row_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating spreadsheet sheet '{sheet_name}': {str(e)}")
            return False
    
    def _column_index_to_letter(self, index: int) -> str:
        """Convert column index (0-based) to letter (A, B, C, etc.)"""
        result = ""
        while index >= 0:
            result = chr(index % 26 + ord('A')) + result
            index = index // 26 - 1
        return result
    
    def print_copy_paste_values(self, blood_test_data: Dict[str, Any], nombre: str, apellidos: str):
        """
        Print values in tab-separated format for easy copy-paste to spreadsheet
        
        Args:
            blood_test_data: Dictionary with blood test results
            nombre: Patient's first name
            apellidos: Patient's last name
        """
        print(f"\n{'='*60}")
        print(f"COPY-PASTE VALUES FOR PATIENT: {nombre} {apellidos}")
        print(f"{'='*60}")
        print("Values in order (tab-separated for easy copy-paste):")
        print()
        
        values = []
        headers = []
        
        for json_key, spreadsheet_column in self.COLUMN_MAPPING.items():
            headers.append(spreadsheet_column)
            value = blood_test_data.get(json_key)
            if value is not None:
                # Apply the same transformation as in update_patient_data
                if json_key == 'EOSINOFILOS_TOTALES' and isinstance(value, (int, float)):
                    value = value * 1000  # Convert format for spreadsheet
                
                # Format numbers using Spanish locale (comma as decimal separator)
                if isinstance(value, (int, float)):
                    formatted_value = self._format_number_spanish(value)
                    values.append(formatted_value)
                else:
                    values.append(str(value))
            else:
                values.append("")
        
        # Print headers for reference
        print("Headers:")
        print("\t".join(headers))
        print()
        
        # Print values ready to copy
        print("Values to copy:")
        print("\t".join(values))
        print(f"\n{'='*60}")
    
    def _format_number_spanish(self, value: float) -> str:
        """
        Format a number using Spanish locale (comma as decimal separator)
        
        Args:
            value: Numeric value to format
            
        Returns:
            Formatted string with Spanish number format
        """
        try:
            # Try to set Spanish locale temporarily
            original_locale = locale.getlocale(locale.LC_NUMERIC)
            
            # Try different Spanish locale variations
            spanish_locales = ['es_ES.UTF-8', 'es_ES', 'es', 'Spanish_Spain', 'Spanish']
            
            for loc in spanish_locales:
                try:
                    locale.setlocale(locale.LC_NUMERIC, loc)
                    formatted = locale.format_string("%.10g", value).rstrip('0').rstrip('.')
                    locale.setlocale(locale.LC_NUMERIC, original_locale)  # Restore original
                    return formatted
                except locale.Error:
                    continue
            
            # Fallback: manual formatting with comma as decimal separator
            if isinstance(value, float):
                # Format with appropriate decimal places, then replace . with ,
                if value == int(value):  # No decimal part needed
                    return str(int(value))
                else:
                    # Remove trailing zeros and format
                    formatted = f"{value:.10g}".replace('.', ',')
                    return formatted
            else:
                return str(value)
                
        except Exception as e:
            logger.debug(f"Error formatting number {value}: {e}")
            # Final fallback: just replace . with ,
            return str(value).replace('.', ',')
        
        finally:
            # Ensure we restore the original locale
            try:
                locale.setlocale(locale.LC_NUMERIC, original_locale)
            except:
                pass
        print(f"COPY-PASTE VALUES FOR PATIENT: {nombre} {apellidos}")
        print(f"{'='*60}")
        print("Values in order (tab-separated for easy copy-paste):")
        print()
        
        values = []
        headers = []
        
        for json_key, spreadsheet_column in self.COLUMN_MAPPING.items():
            headers.append(spreadsheet_column)
            value = blood_test_data.get(json_key)
            if value is not None:
                # Apply the same transformation as in update_patient_data
                if json_key == 'EOSINOFILOS_TOTALES' and isinstance(value, (int, float)):
                    value = value * 1000  # Convert format for spreadsheet
                
                # Format numbers using Spanish locale (comma as decimal separator)
                if isinstance(value, (int, float)):
                    formatted_value = self._format_number_spanish(value)
                    values.append(formatted_value)
                else:
                    values.append(str(value))
            else:
                values.append("")
        
        # Print headers for reference
        print("Headers:")
        print("\t".join(headers))
        print()
        
        # Print values ready to copy
        print("Values to copy:")
        print("\t".join(values))
        print(f"\n{'='*60}") 