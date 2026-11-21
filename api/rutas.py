"""Las cinco rutas del contrato. Cada una solo traduce HTTP <-> funciones de src/prediccion.py:
la lógica del modelo no se duplica aquí."""
import logging
import math

from fastapi import APIRouter, HTTPException, Query

from api import esquemas
from api.config import NOMBRE, VERSION_API
from src.prediccion import _cargar, buscar_entidades, evaluar_contrato, opciones

log = logging.getLogger("api")
router = APIRouter()

CAMPOS_ENTIDAD = ("nombre_entidad", "departamento", "orden", "sector")


def _limpio(valor):
    """NaN no es válido en JSON: se devuelve como null."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    return valor


def version_modelo():
    m = _cargar()[0]["modelo"]
    return f"{m['registro']} v{m['version']} ({m['run']})"


@router.get("/health", response_model=esquemas.Salud, tags=["estado"])
def salud():
    """La API está viva y el modelo está cargado."""
    return {"nombre": NOMBRE, "version_api": VERSION_API, "version_modelo": version_modelo()}


@router.get("/opciones/{variable}", response_model=esquemas.Opciones, tags=["formulario"])
def ver_opciones(variable: str):
    """Valores de una lista desplegable, de más a menos frecuente."""
    if variable not in esquemas.VARIABLES_OPCIONES:
        raise HTTPException(status_code=404,
                            detail=f"Variable '{variable}' no disponible; use una de {list(esquemas.VARIABLES_OPCIONES)}")
    return {"variable": variable, "valores": [str(v) for v in opciones(variable)]}


@router.get("/entidades", response_model=list[esquemas.Entidad], tags=["formulario"])
def buscar(q: str = Query(min_length=3, description="Parte del nombre de la entidad"),
           n: int = Query(20, ge=1, le=50, description="Máximo de resultados")):
    """Entidades cuyo nombre contiene el texto, de más a menos contratos."""
    encontradas = buscar_entidades(q.strip(), n=n)
    return [{k: _limpio(v) for k, v in fila.items()} for fila in encontradas.to_dict("records")]


@router.get("/entidades/{codigo}", response_model=esquemas.Entidad, tags=["formulario"])
def ver_entidad(codigo: str):
    """Una entidad por su código."""
    entidades = _cargar()[2]
    if codigo not in entidades.index:
        raise HTTPException(status_code=404, detail=f"No existe la entidad con código {codigo}")
    fila = entidades.loc[codigo]
    return {"codigo_entidad": codigo, **{c: _limpio(fila.get(c)) for c in CAMPOS_ENTIDAD}}


@router.post("/evaluar", response_model=esquemas.Resultado, tags=["modelo"])
def evaluar(contrato: esquemas.ContratoEntrada):
    """Probabilidad de prórroga, nivel de riesgo y factores que más la suben."""
    datos = contrato.model_dump()
    datos["fecha_de_firma"] = contrato.fecha_de_firma.isoformat()
    resultado = evaluar_contrato(datos)
    for factor in resultado["factores"]:
        factor["valor"] = _limpio(factor["valor"])
    log.info("evaluar: %s | %s | %.0f días -> %.3f (%s)", contrato.tipo_de_contrato, contrato.departamento,
             contrato.duracion_pactada_dias, resultado["probabilidad_prorroga"], resultado["nivel"])
    return resultado
