"""Esquemas (Pydantic) de lo que entra y sale de la API. Son el contrato de api/CONTRATO.md escrito en código:
FastAPI los usa para validar las peticiones (422 si algo no cumple) y para generar la documentación en /docs."""
from datetime import date
from typing import Optional, Union

from pydantic import BaseModel, Field, model_validator

from src.prediccion import opciones

# Variables con lista desplegable en el tablero (las únicas que acepta /opciones/{variable}).
VARIABLES_OPCIONES = ("tipo_de_contrato", "modalidad_de_contratacion", "departamento", "orden", "sector")

EJEMPLO = {
    "codigo_entidad": "702547704",
    "tipo_de_contrato": "Prestación de servicios",
    "modalidad_de_contratacion": "Contratación directa",
    "departamento": "Distrito Capital de Bogotá",
    "orden": "Nacional",
    "sector": "defensa",
    "precio_base": 14872002,
    "duracion_pactada_dias": 270,
    "fecha_de_firma": "2024-10-15",
    "codigo_proveedor": None,
}


class Salud(BaseModel):
    nombre: str
    version_api: str
    version_modelo: str


class Opciones(BaseModel):
    variable: str
    valores: list[str]


class Entidad(BaseModel):
    codigo_entidad: str
    nombre_entidad: Optional[str] = None
    departamento: Optional[str] = None
    orden: Optional[str] = None
    sector: Optional[str] = None


class ContratoEntrada(BaseModel):
    """Lo que envía el formulario Evaluar contrato."""
    tipo_de_contrato: str
    modalidad_de_contratacion: str
    departamento: str
    orden: str
    sector: str
    precio_base: float = Field(gt=0, description="Precio base en pesos")
    duracion_pactada_dias: float = Field(gt=0, description="Plazo pactado en días")
    fecha_de_firma: date = Field(description="Formato AAAA-MM-DD")
    codigo_entidad: Optional[str] = None
    codigo_proveedor: Optional[str] = None

    model_config = {"json_schema_extra": {"examples": [EJEMPLO]}}

    @model_validator(mode="after")
    def valores_conocidos(self):
        """Las categorías deben ser de las que el modelo vio al entrenar (las mismas de /opciones)."""
        for variable in VARIABLES_OPCIONES:
            valor = getattr(self, variable)
            if valor not in {str(v) for v in opciones(variable)}:
                raise ValueError(f"{variable} = '{valor}' no es un valor conocido por el modelo; "
                                 f"ver /api/v1/opciones/{variable}")
        return self


class Factor(BaseModel):
    variable: str
    descripcion: str
    valor: Union[int, float, str, None]
    efecto: float = Field(description="Contribución SHAP en log-odds; positivo sube el riesgo")


class Resultado(BaseModel):
    probabilidad_prorroga: float = Field(ge=0, le=1)
    nivel: str = Field(description="bajo, medio o alto")
    factores: list[Factor]
    notas: list[str]
    modelo: str
