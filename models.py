"""
Blood Test Data Models - Pydantic schemas for blood test data extraction
"""

from typing import Optional
from pydantic import BaseModel, Field


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