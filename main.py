#!/usr/bin/env python3
"""
Blood Test Parser - Extract data from blood test documents using Gemini API
"""

import os
import json
import logging
import argparse
from pathlib import Path
from typing import Union, List, Dict, Any, Optional
from datetime import datetime
import base64

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

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

# Define the structured output schema using Pydantic
class BloodTestData(BaseModel):
    """Blood test data extraction schema"""
    NOMBRE: Optional[str] = Field(None, description="Nombre del paciente")
    APELLIDOS: Optional[str] = Field(None, description="Apellidos del paciente (combinar primer y segundo apellido si están separados)")
    HOSPITAL: Optional[str] = Field(None, description="Nombre del hospital - debe ser uno de: NEGRIN, INSULAR, FUERTEVENTURA, LANZAROTE")
    NRO_HISTORIA_CLINICA: Optional[str] = Field(None, description="Número de historia clínica como string")
    NRO_MUESTRA: Optional[str] = Field(None, description="Número de muestra como string")
    HEMOGLOBINA: Optional[float] = Field(None, description="Nivel de hemoglobina en g/dl")
    HEMATOCRITO: Optional[float] = Field(None, description="Porcentaje de hematocrito")
    VCM: Optional[float] = Field(None, description="Volumen corpuscular medio en fl")
    ADE: Optional[float] = Field(None, description="Amplitud de distribución eritrocitaria (RDW) en porcentaje")
    PLAQUETAS: Optional[float] = Field(None, description="Recuento de plaquetas en 10^3/µL")
    LEUCOCITOS: Optional[float] = Field(None, description="Recuento de leucocitos en 10^3/µL")
    EOSINOFILOS_TOTALES: Optional[float] = Field(None, description="Eosinófilos totales en 10^3/µL")
    EOSINOFILOS_PORCENTAJE: Optional[float] = Field(None, description="Porcentaje de eosinófilos")
    GLUCOSA: Optional[float] = Field(None, description="Nivel de glucosa en mg/dl")
    CREATININA: Optional[float] = Field(None, description="Nivel de creatinina en mg/dl")
    ALT: Optional[float] = Field(None, description="Alanina aminotransferasa (ALT o GPT) en U/L")
    AST: Optional[float] = Field(None, description="Aspartato aminotransferasa (AST o GOT) en U/L")
    GGT: Optional[float] = Field(None, description="Gamma glutamil transferasa en U/L")
    COLESTEROL: Optional[float] = Field(None, description="Nivel de colesterol en mg/dL")
    FERRITINA: Optional[float] = Field(None, description="Nivel de ferritina en ng/mL")
    VIH: Optional[int] = Field(None, description="Resultado del test VIH: 1 para Positivo, 0 para Negativo, null si no se encuentra")
    VHA: Optional[int] = Field(None, description="Resultado del test Hepatitis A: 1 para Positivo, 0 para Negativo, null si no se encuentra")
    VHC: Optional[int] = Field(None, description="Resultado del test Hepatitis C: 1 para Positivo, 0 para Negativo, null si no se encuentra")
    LUES: Optional[int] = Field(None, description="Resultado del test Treponema pallidum (Sífilis): 1 para Positivo, 0 para Negativo, null si no se encuentra")
    STRONGYLOIDES: Optional[int] = Field(None, description="Resultado del test Strongyloides: 1 para Positivo, 0 para Negativo, null si no se encuentra")
    SARAMPION: Optional[int] = Field(None, description="Resultado del test Sarampión: 1 para Positivo, 0 para Negativo, null si no se encuentra")
    SCHISTOSOMA: Optional[int] = Field(None, description="Resultado del test Schistosoma: 1 para Positivo, 0 para Negativo, null si no se encuentra")
    HEMOGLOBINOPATIA: Optional[int] = Field(None, description="Resultado de hemoglobinopatía como número: 0=No, 1=DREPANOCITOSIS, 2=A-TALASEMIA, 3=B-TALASEMIA MINOR, 4=RASGO HB S, 5=RASGO HB C, 6=PERSISTENCIA HB F, 7=homocigosis HbC, 8=portador Hb de HOPE, 9=Indice Metzner <13")

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

def save_results(results: Dict[str, Any], output_file: Path = None) -> None:
    """Save results to JSON file"""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(f"extraction_results_{timestamp}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to {output_file}")

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
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        blood_parser = BloodTestParser(api_key=args.api_key)
        results = blood_parser.process_input(args.input_path)
        
        output_path = Path(args.output) if args.output else None
        save_results(results, output_path)
        
        total_files = len(results)
        successful = sum(1 for result in results.values() if "error" not in result)
        failed = total_files - successful
        
        print(f"\nProcessing complete!")
        print(f"Total files: {total_files}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print("\nFailed files:")
            for filename, result in results.items():
                if "error" in result:
                    print(f"  - {filename}: {result['error']}")
    
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
