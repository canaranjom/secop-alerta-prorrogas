"""Punto de entrada de la API.

Desde la raíz del repo (necesita models/, que se trae con `dvc pull models`):
    uvicorn api.main:app --port 8001 --reload
Documentación interactiva: http://localhost:8001/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from api.config import NIVEL_LOG, NOMBRE, PREFIJO, VERSION_API
from api.rutas import router, version_modelo
from src.prediccion import _cargar

logging.basicConfig(level=NIVEL_LOG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Se carga el modelo UNA vez al arrancar: si falta models/, la API falla aquí (visible en los logs
    # del contenedor) y no en la primera petición de un usuario.
    _cargar()
    log.info("Modelo cargado: %s", version_modelo())
    yield


app = FastAPI(
    title=NOMBRE,
    version=VERSION_API,
    description="Probabilidad de que un contrato SECOP II sea prorrogado. Contrato completo en api/CONTRATO.md.",
    lifespan=ciclo_de_vida,
)
app.include_router(router, prefix=PREFIJO)


@app.get("/", include_in_schema=False)
def inicio():
    return HTMLResponse(f"<h2>{NOMBRE}</h2><p>Documentación: <a href='/docs'>/docs</a></p>")
