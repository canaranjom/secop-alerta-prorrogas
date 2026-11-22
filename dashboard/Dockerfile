# Imagen del tablero Dash (Panorama + Evaluar contrato).
# Se construye desde la RAÍZ del repo, después de dvc pull data/tablero:
#     docker build -f dashboard/Dockerfile -t secop-tablero .
# Las predicciones no se calculan aquí: el tablero se las pide a la API en API_URL.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    API_URL=http://localhost:8001

RUN adduser --disabled-password --gecos '' tablero-user

WORKDIR /opt/secop

COPY dashboard/requirements.txt dashboard/requirements.txt
RUN pip install -r dashboard/requirements.txt

# Misma estructura del repo: app.py busca los datos en ../data/tablero respecto a dashboard/.
COPY data/tablero/ data/tablero/
COPY dashboard/ dashboard/
RUN chown -R tablero-user:tablero-user /opt/secop

USER tablero-user
EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/', timeout=4)"

# Correrlo como script deja dashboard/ en la ruta de Python, por eso funcionan los `from graficas import ...`.
CMD ["python", "dashboard/app.py"]
