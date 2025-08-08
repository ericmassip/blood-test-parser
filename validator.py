"""
Blood Test Data Validator - Compare extracted data with expected results using percentage-based metrics
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating extracted data against expected data"""
    filename: str
    overall_accuracy: float
    field_accuracies: Dict[str, float]
    missing_fields: List[str]
    extra_fields: List[str]
    field_differences: Dict[str, Dict[str, Any]]
    is_valid: bool  # True if accuracy is above threshold


class BloodTestValidator:
    """Validate extracted blood test data against expected results"""
    
    def __init__(self, expected_data_dir: str = "blood_tests/json_data", accuracy_threshold: float = 80.0):
        """
        Initialise the validator
        
        Args:
            expected_data_dir: Directory containing expected JSON results
            accuracy_threshold: Minimum accuracy percentage to consider validation successful
        """
        self.expected_data_dir = Path(expected_data_dir)
        self.accuracy_threshold = accuracy_threshold
        
        if not self.expected_data_dir.exists():
            logger.warning(f"Expected data directory {expected_data_dir} does not exist")
    
    def _load_expected_data(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load expected data for a given file
        
        Args:
            filename: Name of the file (without .pdf extension)
            
        Returns:
            Expected data dictionary or None if not found
        """
        # Try different naming conventions
        possible_names = [
            f"{filename}.json",
            f"{filename.replace('.pdf', '')}.json",
            f"{Path(filename).stem}.json"
        ]
        
        for name in possible_names:
            expected_file = self.expected_data_dir / name
            if expected_file.exists():
                try:
                    with open(expected_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error loading expected data from {expected_file}: {e}")
                    return None
        
        logger.warning(f"No expected data found for {filename}")
        return None
    
    def _calculate_field_accuracy(self, expected_value: Any, actual_value: Any) -> float:
        """
        Calculate accuracy percentage for a single field
        
        Args:
            expected_value: Expected field value
            actual_value: Actual extracted field value
            
        Returns:
            Accuracy percentage (0-100)
        """
        # Handle None values
        if expected_value is None and actual_value is None:
            return 100.0
        if expected_value is None or actual_value is None:
            return 0.0
        
        # Handle string fields
        if isinstance(expected_value, str) and isinstance(actual_value, str):
            if expected_value.strip().lower() == actual_value.strip().lower():
                return 100.0
            else:
                # Use basic string similarity (could be enhanced with fuzzy matching)
                return 0.0
        
        # Handle numeric fields
        if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
            if expected_value == 0:
                return 100.0 if actual_value == 0 else 0.0
            
            # Calculate percentage difference
            diff = abs(expected_value - actual_value)
            relative_diff = (diff / abs(expected_value)) * 100
            
            # Convert to accuracy (closer values = higher accuracy)
            accuracy = max(0, 100 - relative_diff)
            return min(100.0, accuracy)
        
        # Handle boolean/integer test results (0, 1)
        if isinstance(expected_value, int) and isinstance(actual_value, int):
            return 100.0 if expected_value == actual_value else 0.0
        
        # Default case: exact match
        return 100.0 if expected_value == actual_value else 0.0
    
    def _validate_single_result(self, filename: str, extracted_data: Dict[str, Any], 
                               expected_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a single extracted result against expected data
        
        Args:
            filename: Name of the file being validated
            extracted_data: Extracted data from the parser
            expected_data: Expected data from JSON file
            
        Returns:
            ValidationResult object
        """
        field_accuracies = {}
        field_differences = {}
        
        # Get all unique field names
        all_fields = set(expected_data.keys()) | set(extracted_data.keys())
        
        # Remove 'error' field if present in extracted data
        all_fields.discard('error')
        
        for field in all_fields:
            expected_val = expected_data.get(field)
            actual_val = extracted_data.get(field)
            
            accuracy = self._calculate_field_accuracy(expected_val, actual_val)
            field_accuracies[field] = accuracy
            
            # Track differences for reporting
            if accuracy < 100.0:
                field_differences[field] = {
                    'expected': expected_val,
                    'actual': actual_val,
                    'accuracy': accuracy
                }
        
        # Calculate overall accuracy as mean of all field accuracies
        overall_accuracy = sum(field_accuracies.values()) / len(field_accuracies) if field_accuracies else 0.0
        
        # Find missing and extra fields
        expected_fields = set(expected_data.keys())
        extracted_fields = set(extracted_data.keys()) - {'error'}  # Exclude error field
        
        missing_fields = list(expected_fields - extracted_fields)
        extra_fields = list(extracted_fields - expected_fields)
        
        return ValidationResult(
            filename=filename,
            overall_accuracy=overall_accuracy,
            field_accuracies=field_accuracies,
            missing_fields=missing_fields,
            extra_fields=extra_fields,
            field_differences=field_differences,
            is_valid=overall_accuracy >= self.accuracy_threshold
        )
    
    def validate_results(self, extraction_results: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate all extraction results against expected data
        
        Args:
            extraction_results: Dictionary of extraction results from parser
            
        Returns:
            List of ValidationResult objects
        """
        validation_results = []
        
        for filename, extracted_data in extraction_results.items():
            # Skip files with extraction errors
            if "error" in extracted_data:
                logger.warning(f"Skipping validation for {filename} due to extraction error: {extracted_data['error']}")
                continue
            
            expected_data = self._load_expected_data(filename)
            if expected_data is None:
                logger.warning(f"Skipping validation for {filename} - no expected data found")
                continue
            
            result = self._validate_single_result(filename, extracted_data, expected_data)
            validation_results.append(result)
            
            logger.info(f"Validation for {filename}: {result.overall_accuracy:.1f}% accuracy")
        
        return validation_results
    
    def generate_validation_report(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate a comprehensive validation report
        
        Args:
            validation_results: List of validation results
            
        Returns:
            Dictionary containing validation report
        """
        if not validation_results:
            return {"error": "No validation results to report"}
        
        # Calculate summary statistics
        total_files = len(validation_results)
        valid_files = sum(1 for r in validation_results if r.is_valid)
        average_accuracy = sum(r.overall_accuracy for r in validation_results) / total_files
        
        # Find best and worst performing files
        best_result = max(validation_results, key=lambda r: r.overall_accuracy)
        worst_result = min(validation_results, key=lambda r: r.overall_accuracy)
        
        # Calculate per-field statistics
        all_fields = set()
        for result in validation_results:
            all_fields.update(result.field_accuracies.keys())
        
        field_stats = {}
        for field in all_fields:
            field_accuracies = [r.field_accuracies.get(field, 0) for r in validation_results 
                             if field in r.field_accuracies]
            if field_accuracies:
                field_stats[field] = {
                    'average_accuracy': sum(field_accuracies) / len(field_accuracies),
                    'min_accuracy': min(field_accuracies),
                    'max_accuracy': max(field_accuracies),
                    'total_samples': len(field_accuracies)
                }
        
        return {
            'summary': {
                'total_files': total_files,
                'valid_files': valid_files,
                'invalid_files': total_files - valid_files,
                'success_rate': (valid_files / total_files) * 100,
                'average_accuracy': average_accuracy,
                'accuracy_threshold': self.accuracy_threshold
            },
            'best_performance': {
                'filename': best_result.filename,
                'accuracy': best_result.overall_accuracy
            },
            'worst_performance': {
                'filename': worst_result.filename,
                'accuracy': worst_result.overall_accuracy
            },
            'field_statistics': field_stats,
            'detailed_results': [
                {
                    'filename': r.filename,
                    'accuracy': r.overall_accuracy,
                    'is_valid': r.is_valid,
                    'missing_fields': r.missing_fields,
                    'extra_fields': r.extra_fields,
                    'problematic_fields': [field for field, acc in r.field_accuracies.items() if acc < 80]
                }
                for r in validation_results
            ]
        }
    
    def save_validation_report(self, validation_results: List[ValidationResult], 
                             output_file: Path = None) -> None:
        """
        Save validation report to JSON file
        
        Args:
            validation_results: List of validation results
            output_file: Output file path (auto-generated if None)
        """
        if output_file is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(f"validation_reports/validation_report_{timestamp}.json")
        
        # Ensure directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        report = self.generate_validation_report(validation_results)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Validation report saved to {output_file}") 