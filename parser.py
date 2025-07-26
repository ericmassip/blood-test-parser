"""
Blood Test Parser - Extract data from blood test documents using Gemini API
"""

import os
import logging
import base64
from pathlib import Path
from typing import Union, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

from models import BloodTestData

logger = logging.getLogger(__name__)


class BloodTestParser:
    """Extract data from blood test documents using Gemini API"""
    
    def __init__(self, api_key: str = None):
        """
        Initialise the parser with Google Gemini API
        
        Args:
            api_key: Google API key. If None, will try to read from environment variable
        """
        if api_key is None:
            api_key = os.getenv('GOOGLE_API_KEY')
            
        if not api_key:
            raise ValueError("Google API key not provided. Set GOOGLE_API_KEY environment variable or pass api_key parameter.")
        
        base_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.1  # Low temperature for consistent extraction
        )
        
        self.llm = base_llm.with_structured_output(BloodTestData)
        
        self.system_instructions = self._load_system_instructions()
        
    def _load_system_instructions(self) -> str:
        """Load system instructions from file"""
        instructions_path = Path("system_instructions.txt")
        if not instructions_path.exists():
            raise FileNotFoundError("system_instructions.txt not found")
        
        with open(instructions_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def _encode_pdf_to_base64(self, pdf_path: Path) -> str:
        """
        Encode PDF file to base64 string
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Base64 encoded PDF content
        """
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
                pdf_b64 = base64.b64encode(pdf_content).decode('utf-8')
                logger.info(f"Encoded PDF {pdf_path} ({len(pdf_content)} bytes)")
                return pdf_b64
        except Exception as e:
            logger.error(f"Error encoding PDF {pdf_path}: {str(e)}")
            raise
    
    def extract_data_from_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract blood test data from a single PDF document
        
        Args:
            file_path: Path to the PDF document
            
        Returns:
            Extracted data as dictionary
        """
        logger.info(f"Processing document: {file_path}")
        
        try:
            pdf_b64 = self._encode_pdf_to_base64(file_path)
            
            # Prepare messages for LangChain
            messages = [
                SystemMessage(content=self.system_instructions)
            ]
            
            content = [
                {
                    "type": "text",
                    "text": "Please extract the blood test data from this PDF document according to the system instructions. Return the data in the specified structured format."
                },
                {
                    "type": "media",
                    "data": pdf_b64,
                    "mime_type": "application/pdf"
                }
            ]
            
            messages.append(HumanMessage(content=content))
            
            logger.info(f"Sending PDF request to Gemini API for {file_path.name}")
            logger.info(f"PDF size: {file_path.stat().st_size} bytes")
            
            # Make API call - this will return a structured BloodTestData object
            response = self.llm.invoke(messages)
            
            logger.info(f"Received structured response for {file_path.name}")
            logger.debug(f"Structured response: {response}")
            
            # Convert Pydantic model to dictionary
            extracted_data = response.model_dump()
            logger.info(f"Successfully extracted data from {file_path.name}")
            return extracted_data
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return {"error": str(e)}
    
    def process_input(self, input_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Process either a single file or directory of files
        
        Args:
            input_path: Path to file or directory
            
        Returns:
            Dictionary with results for each processed file
        """
        input_path = Path(input_path)
        results = {}
        
        if input_path.is_file():
            if input_path.suffix.lower() == '.pdf':
                results[input_path.name] = self.extract_data_from_document(input_path)
            else:
                logger.warning(f"Skipping non-PDF file: {input_path}")
                results[input_path.name] = {"error": "Not a PDF file"}
                
        elif input_path.is_dir():
            # Process all PDF files in directory
            pdf_files = list(input_path.glob('*.pdf'))
            logger.info(f"Found {len(pdf_files)} PDF files in {input_path}")
            
            for pdf_file in pdf_files:
                results[pdf_file.name] = self.extract_data_from_document(pdf_file)
                
        else:
            raise ValueError(f"Input path does not exist: {input_path}")
        
        return results 