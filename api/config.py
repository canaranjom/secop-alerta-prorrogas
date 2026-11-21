"""Configuración de la API. Lo que cambia entre ambientes se lee de variables de entorno."""
import os

NOMBRE = "API alerta de prórrogas SECOP"
VERSION_API = "1.0.0"
PREFIJO = "/api/v1"                          # si el contrato cambia, se publica /api/v2
NIVEL_LOG = os.getenv("NIVEL_LOG", "INFO")   # DEBUG para ver más detalle
