#!/usr/bin/env python3
"""
Blood Test Parser - Extract data from blood test documents using Gemini API
"""

import json
import logging
import argparse
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv

from parser import BloodTestParser
from validator import BloodTestValidator
from google_sheets_service import GoogleSheetsService

def setup_logging() -> logging.Logger:
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('blood_test_parser.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Load environment variables from .env for local runs
load_dotenv()

def save_results(results: Dict[str, Any], output_file: Path = None) -> None:
    """Save results to JSON file"""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(f"extraction_results/extraction_results_{timestamp}.json")
    
    # Ensure directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to {output_file}")

def print_validation_summary(validation_results):
    """Print a summary of validation results"""
    if not validation_results:
        print("\nNo validation results available.")
        return
    
    total_files = len(validation_results)
    valid_files = sum(1 for r in validation_results if r.is_valid)
    average_accuracy = sum(r.overall_accuracy for r in validation_results) / total_files
    
    print(f"\n{'='*50}")
    print("VALIDATION SUMMARY")
    print(f"{'='*50}")
    print(f"Total files validated: {total_files}")
    print(f"Files passing threshold: {valid_files}")
    print(f"Files failing threshold: {total_files - valid_files}")
    print(f"Average accuracy: {average_accuracy:.1f}%")
    print(f"Success rate: {(valid_files / total_files) * 100:.1f}%")
    
    print(f"\n{'Results by file:'}")
    print(f"{'-'*50}")
    for result in validation_results:
        status = "✓ PASS" if result.is_valid else "✗ FAIL"
        print(f"{result.filename:<30} {result.overall_accuracy:>6.1f}% {status}")
        
        if result.missing_fields:
            print(f"  Missing fields: {', '.join(result.missing_fields)}")
        if result.extra_fields:
            print(f"  Extra fields: {', '.join(result.extra_fields)}")
        
        # Show problematic fields (accuracy < 80%)
        problematic = [field for field, acc in result.field_accuracies.items() if acc < 80]
        if problematic:
            print(f"  Low accuracy fields: {', '.join(problematic)}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Extract blood test data using Gemini API")
    parser.add_argument(
        "input_path",
        help="Path to PDF file or directory containing PDF files"
    )
    parser.add_argument(
        "--api-key",
        help="Google API key (can also be set via GOOGLE_API_KEY environment variable)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file path"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Enable validation against expected results in json_data folder"
    )
    parser.add_argument(
        "--validation-threshold",
        type=float,
        default=80.0,
        help="Accuracy threshold for validation (default: 80.0)"
    )
    parser.add_argument(
        "--validation-report",
        help="Path to save detailed validation report"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--spreadsheet",
        "-s",
        help="Google Spreadsheet ID to update with results (get from spreadsheet URL)"
    )
    parser.add_argument(
        "--credentials",
        default="credentials.json",
        help="Path to Google service account credentials file (default: credentials.json)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        blood_parser = BloodTestParser(api_key=args.api_key)
        results = blood_parser.process_input(args.input_path)
        
        output_path = Path(args.output) if args.output else None
        save_results(results, output_path)
        
        # Calculate basic extraction statistics
        total_files = len(results)
        successful = sum(1 for result in results.values() if "error" not in result)
        failed = total_files - successful
        
        print(f"\nExtraction complete!")
        print(f"Total files: {total_files}")
        print(f"Successful extractions: {successful}")
        print(f"Failed extractions: {failed}")
        
        if failed > 0:
            print("\nFailed files:")
            for filename, result in results.items():
                if "error" in result:
                    print(f"  - {filename}: {result['error']}")
        
        # Update Google Spreadsheet if requested
        if args.spreadsheet:
            print(f"\n{'='*50}")
            print("UPDATING GOOGLE SPREADSHEET")
            print(f"{'='*50}")
            
            try:
                sheets_service = GoogleSheetsService(credentials_file=args.credentials)
                
                for filename, result in results.items():
                    if "error" in result:
                        logger.warning(f"Skipping {filename} due to extraction error")
                        continue
                    
                    # Check if we have patient name information
                    nombre = result.get('NOMBRE')
                    apellidos = result.get('APELLIDOS')
                    
                    if not nombre or not apellidos:
                        logger.warning(f"Skipping {filename}: Missing patient name information (NOMBRE: {nombre}, APELLIDOS: {apellidos})")
                        sheets_service.print_copy_paste_values(result, nombre or "UNKNOWN", apellidos or "UNKNOWN")
                        continue
                    
                    print(f"\nProcessing {filename} - Patient: {nombre} {apellidos}")
                    
                    # Find patient row
                    row_number, sheet_name, status_message = sheets_service.find_patient_row(
                        args.spreadsheet, nombre, apellidos
                    )
                    
                    print(f"  Status: {status_message}")
                    
                    if row_number is not None and sheet_name is not None:
                        # Update the spreadsheet
                        success = sheets_service.update_patient_data(
                            args.spreadsheet, sheet_name, row_number, result
                        )
                        
                        if success:
                            print(f"  ✓ Successfully updated sheet '{sheet_name}' row {row_number}")
                        else:
                            print(f"  ✗ Failed to update spreadsheet")
                            sheets_service.print_copy_paste_values(result, nombre, apellidos)
                    else:
                        # Patient not found or multiple matches - print copy-paste values
                        sheets_service.print_copy_paste_values(result, nombre, apellidos)
                
                print(f"\nSpreadsheet update process completed!")
                
            except FileNotFoundError as e:
                logger.error(f"Google Sheets setup error: {str(e)}")
                print(f"\nTo use Google Sheets integration:")
                print(f"1. Go to Google Cloud Console (console.cloud.google.com)")
                print(f"2. Create a new project or select an existing one")
                print(f"3. Enable the Google Sheets API")
                print(f"4. Create a service account and download the JSON key file")
                print(f"5. Share your Google Spreadsheet with the service account email")
                print(f"6. Save the key file as 'credentials.json' in this directory")
                return 1
                
            except Exception as e:
                logger.error(f"Error updating Google Spreadsheet: {str(e)}")
                print(f"\nFailed to update spreadsheet. Printing copy-paste values for manual entry:")
                
                # Print copy-paste values for all successful extractions
                try:
                    sheets_service = GoogleSheetsService(credentials_file=args.credentials)
                    for filename, result in results.items():
                        if "error" not in result:
                            nombre = result.get('NOMBRE', 'UNKNOWN')
                            apellidos = result.get('APELLIDOS', 'UNKNOWN')
                            sheets_service.print_copy_paste_values(result, nombre, apellidos)
                except:
                    # If we can't create sheets service, just print the raw data
                    for filename, result in results.items():
                        if "error" not in result:
                            print(f"\n{filename}: {json.dumps(result, indent=2)}")
        
        # Perform validation if requested
        if args.validate:
            print(f"\n{'='*50}")
            print("STARTING VALIDATION")
            print(f"{'='*50}")
            
            validator = BloodTestValidator(accuracy_threshold=args.validation_threshold)
            validation_results = validator.validate_results(results)
            
            if validation_results:
                print_validation_summary(validation_results)
                
                # Save detailed validation report if requested
                if args.validation_report:
                    report_path = Path(args.validation_report)
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_path = Path(f"validation_reports/validation_report_{timestamp}.json")
                
                validator.save_validation_report(validation_results, report_path)
                print(f"\nDetailed validation report saved to: {report_path}")
            else:
                print("\nNo files could be validated (missing expected data or extraction errors)")
    
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
