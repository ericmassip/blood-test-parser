#!/usr/bin/env python3
"""
Pytest tests for multi-sheet search functionality
This script mocks the Google Sheets API to test the search logic
"""

import pytest
from unittest.mock import Mock
from google_sheets_service import GoogleSheetsService


@pytest.fixture
def mock_sheet_data():
    """Mock sheet data for testing"""
    return {
        '2024': [
            ['NOMBRE', 'APELLIDOS', 'FILIACION', 'Hb (g/dl) 12-18', 'Hto (%) 36-50'],
            ['JUAN', 'GARCIA LOPEZ', 'JUAN GARCIA LOPEZ', '', ''],
            ['MARIA', 'RODRIGUEZ SANCHEZ', 'MARIA RODRIGUEZ SANCHEZ', '', ''],
            ['PEDRO', 'MARTINEZ GARCIA', 'PEDRO MARTINEZ GARCIA', '', '']
        ],
        '2023': [
            ['NOMBRE', 'APELLIDOS', 'FILIACION', 'Hb (g/dl) 12-18', 'Hto (%) 36-50'],
            ['ANA', 'LOPEZ MARTINEZ', 'ANA LOPEZ MARTINEZ', '', ''],
            ['CARLOS', 'SANCHEZ RUIZ', 'CARLOS SANCHEZ RUIZ', '', ''],
            ['LUCIA', 'FERNANDEZ TORRES', 'LUCIA FERNANDEZ TORRES', '', '']
        ],
        'Pending': [
            ['NOMBRE', 'APELLIDOS', 'FILIACION', 'Hb (g/dl) 12-18', 'Hto (%) 36-50'],
            ['MIGUEL', 'TORRES LOPEZ', 'MIGUEL TORRES LOPEZ', '', ''],
            ['SOFIA', 'RUIZ MARTINEZ', 'SOFIA RUIZ MARTINEZ', '', '']
        ],
        'Archive': [
            ['NOMBRE', 'APELLIDOS', 'FILIACION', 'Hb (g/dl) 12-18', 'Hto (%) 36-50'],
            ['JOSE', 'GARCIA RODRIGUEZ', 'JOSE GARCIA RODRIGUEZ', '', ''],
            ['ELENA', 'MARTINEZ LOPEZ', 'ELENA MARTINEZ LOPEZ', '', '']
        ]
    }


@pytest.fixture
def mock_sheets():
    """Mock sheets metadata for testing"""
    return [
        {'properties': {'title': '2024'}},
        {'properties': {'title': '2023'}},
        {'properties': {'title': 'Pending'}},
        {'properties': {'title': 'Archive'}}
    ]


@pytest.fixture
def mock_sheets_service(mock_sheets, mock_sheet_data):
    """Create a mock Google Sheets service for testing"""
    service = GoogleSheetsService.__new__(GoogleSheetsService)
    service.service = Mock()
    service.credentials_file = "mock_credentials.json"
    
    # Mock the get_spreadsheet_sheets method
    def mock_get_sheets(spreadsheet_name):
        return mock_sheets
    
    # Mock the get_spreadsheet_data method
    def mock_get_data(spreadsheet_name, sheet_name=None, range_name='A:Z'):
        if sheet_name and sheet_name in mock_sheet_data:
            return mock_sheet_data[sheet_name]
        elif not sheet_name:
            # Return first sheet data if no sheet specified
            return mock_sheet_data['2024']
        else:
            return []
    
    service.get_spreadsheet_sheets = mock_get_sheets
    service.get_spreadsheet_data = mock_get_data
    
    return service


@pytest.fixture
def duplicate_sheets_service(mock_sheets):
    """Create a mock service with duplicate patient data"""
    service = GoogleSheetsService.__new__(GoogleSheetsService)
    service.service = Mock()
    service.credentials_file = "mock_credentials.json"
    
    # Mock data with duplicates
    duplicate_data = {
        '2024': [
            ['NOMBRE', 'APELLIDOS', 'FILIACION', 'Hb (g/dl) 12-18'],
            ['DUPLICATE', 'PATIENT', 'DUPLICATE PATIENT', '']
        ],
        '2023': [
            ['NOMBRE', 'APELLIDOS', 'FILIACION', 'Hb (g/dl) 12-18'],
            ['DUPLICATE', 'PATIENT', 'DUPLICATE PATIENT', '']
        ],
        'Pending': [
            ['NOMBRE', 'APELLIDOS', 'FILIACION', 'Hb (g/dl) 12-18']
        ],
        'Archive': [
            ['NOMBRE', 'APELLIDOS', 'FILIACION', 'Hb (g/dl) 12-18']
        ]
    }
    
    service.get_spreadsheet_sheets = lambda spreadsheet_name: mock_sheets
    service.get_spreadsheet_data = lambda spreadsheet_name, sheet_name=None, range_name='A:Z': duplicate_data.get(sheet_name, [])
    
    return service

@pytest.mark.parametrize("nombre,apellidos,expected_found", [
    ("JUAN", "GARCIA LOPEZ", True),      # Should find in 2024 sheet
    ("CARLOS", "SANCHEZ RUIZ", True),    # Should find in 2023 sheet  
    ("MIGUEL", "TORRES LOPEZ", True),    # Should find in Pending sheet
    ("ELENA", "MARTINEZ LOPEZ", True),   # Should find in Archive sheet
    ("UNKNOWN", "PATIENT", False),       # Should not find anywhere
    ("GARCIA LOPEZ", "JUAN", True),      # Test fallback search (reverse name)
])
def test_multi_sheet_patient_search(mock_sheets_service, nombre, apellidos, expected_found):
    """Test patient search across multiple sheets"""
    row_number, sheet_name, status_message = mock_sheets_service.find_patient_row(
        "test_spreadsheet", nombre, apellidos
    )
    
    if expected_found:
        assert row_number is not None, f"Expected to find patient {nombre} {apellidos}"
        assert sheet_name is not None, f"Expected sheet name for patient {nombre} {apellidos}"
        assert "found" in status_message.lower(), f"Unexpected status: {status_message}"
    else:
        assert row_number is None, f"Should not find patient {nombre} {apellidos}"
        assert sheet_name is None, f"Should not return sheet name for unfound patient"
        assert "not found" in status_message.lower(), f"Unexpected status: {status_message}"


def test_patient_found_in_specific_sheets(mock_sheets_service):
    """Test that patients are found in their expected sheets"""
    test_cases = [
        ("JUAN", "GARCIA LOPEZ", "2024"),
        ("CARLOS", "SANCHEZ RUIZ", "2023"),
        ("MIGUEL", "TORRES LOPEZ", "Pending"),
        ("ELENA", "MARTINEZ LOPEZ", "Archive"),
    ]
    
    for nombre, apellidos, expected_sheet in test_cases:
        row_number, sheet_name, status_message = mock_sheets_service.find_patient_row(
            "test_spreadsheet", nombre, apellidos
        )
        
        assert sheet_name == expected_sheet, f"Patient {nombre} {apellidos} should be in sheet '{expected_sheet}', found in '{sheet_name}'"
        assert row_number is not None, f"Should have row number for {nombre} {apellidos}"


def test_fallback_name_search(mock_sheets_service):
    """Test that reverse name order works as fallback"""
    # Test with reversed name order
    row_number, sheet_name, status_message = mock_sheets_service.find_patient_row(
        "test_spreadsheet", "GARCIA LOPEZ", "JUAN"
    )
    
    assert row_number is not None, "Should find patient with reversed name order"
    assert sheet_name == "2024", "Should find patient in correct sheet"
    assert "found" in status_message.lower(), f"Unexpected status: {status_message}"

def test_duplicate_detection(duplicate_sheets_service):
    """Test duplicate patient detection across sheets"""
    row_number, sheet_name, status_message = duplicate_sheets_service.find_patient_row(
        "test_spreadsheet", "DUPLICATE", "PATIENT"
    )
    
    # Should detect duplicates and return None for both row and sheet
    assert row_number is None, "Should not return row number for duplicate patients"
    assert sheet_name is None, "Should not return sheet name for duplicate patients"
    assert "Multiple patients" in status_message, f"Should detect duplicates, got: {status_message}"


def test_empty_spreadsheet(mock_sheets):
    """Test behavior with empty spreadsheet"""
    service = GoogleSheetsService.__new__(GoogleSheetsService)
    service.service = Mock()
    service.credentials_file = "mock_credentials.json"
    
    # Mock empty spreadsheet
    service.get_spreadsheet_sheets = lambda spreadsheet_name: []
    
    row_number, sheet_name, status_message = service.find_patient_row(
        "test_spreadsheet", "ANY", "PATIENT"
    )
    
    assert row_number is None
    assert sheet_name is None
    assert "No sheets found" in status_message


def test_sheet_without_filiacion_column(mock_sheets):
    """Test behavior when sheet doesn't have FILIACION column"""
    service = GoogleSheetsService.__new__(GoogleSheetsService)
    service.service = Mock()
    service.credentials_file = "mock_credentials.json"
    
    # Mock sheet without FILIACION column
    service.get_spreadsheet_sheets = lambda spreadsheet_name: mock_sheets
    service.get_spreadsheet_data = lambda spreadsheet_name, sheet_name=None, range_name='A:Z': [
        ['NOMBRE', 'APELLIDOS', 'OTHER_COLUMN'],  # No FILIACION column
        ['JUAN', 'GARCIA', 'some_data']
    ]
    
    row_number, sheet_name, status_message = service.find_patient_row(
        "test_spreadsheet", "JUAN", "GARCIA"
    )
    
    assert row_number is None
    assert sheet_name is None
    assert "not found" in status_message.lower()


class TestGoogleSheetsService:
    """Test class for Google Sheets service methods"""
    
    def test_column_index_to_letter(self):
        """Test column index to letter conversion"""
        service = GoogleSheetsService.__new__(GoogleSheetsService)
        
        # Test basic conversions
        assert service._column_index_to_letter(0) == 'A'
        assert service._column_index_to_letter(1) == 'B'
        assert service._column_index_to_letter(25) == 'Z'
        assert service._column_index_to_letter(26) == 'AA'
        assert service._column_index_to_letter(27) == 'AB'
    
    def test_get_spreadsheet_id(self):
        """Test spreadsheet ID extraction"""
        service = GoogleSheetsService.__new__(GoogleSheetsService)
        
        # Test with what looks like an ID
        long_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        assert service._get_spreadsheet_id(long_id) == long_id
        
        # Test with short string (treated as name)
        short_name = "MySheet"
        assert service._get_spreadsheet_id(short_name) == short_name 