# Imagen de la API del modelo de prórrogas SECOP II.
# Se construye desde la RAÍZ del repo (necesita api/, src/ y models/), después de `dvc pull models`:
#     docker build -f api/Dockerfile -t secop-api .
#     docker run --rm -p 8001:8001 secop-api
# Qué archivos entran al contexto lo define api/Dockerfile.dockerignore.

# Misma versión de Python del proyecto (.python-version), en su variante liviana.
FROM python:3.12-slim

# Python sin archivos .pyc y con los logs saliendo de inmediato (para `docker logs`).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# LightGBM necesita la librería de OpenMP (libgomp1), que la imagen slim no trae.
# No hace falta build-essential: todas las dependencias se instalan como wheels ya compiladas.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios: si alguien vulnera la API, no queda como root dentro del contenedor.
RUN adduser --disabled-password --gecos '' api-user

WORKDIR /opt/secop

# 1) Primero solo las dependencias: esta capa queda en caché y no se reinstala cada vez que cambia el código.
COPY api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt

# 2) Después el código y el modelo (cambian más seguido).
COPY src/prediccion.py src/prediccion.py
COPY models/ models/
COPY api/ api/
RUN chown -R api-user:api-user /opt/secop

USER api-user
EXPOSE 8001

# Docker revisa cada 30 s que la API responda; `docker ps` muestra healthy/unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/v1/health', timeout=4)"

# 0.0.0.0 = escuchar en todas las interfaces, no solo dentro del contenedor.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
