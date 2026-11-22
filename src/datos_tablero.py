"""Genera una copia liviana de los contratos solo con las columnas que usa el tablero.

El tablero (dashboard/) no necesita las 60 columnas de contratos_modelo.parquet (368 MB);
con estas 12 el archivo queda en unos 28 MB, lo que hace mucho más liviana la imagen Docker.

Uso:  python src/datos_tablero.py
Salida: data/tablero/contratos_tablero.parquet
"""
from pathlib import Path

import pandas as pd

ENTRADA = Path("data/processed/contratos_modelo.parquet")
SALIDA = Path("data/tablero/contratos_tablero.parquet")

# Unión de las columnas que leen dashboard/app.py y dashboard/tabla.py.
# Si el tablero empieza a usar otra columna, hay que agregarla aquí y correr `dvc repro tablero`.
COLUMNAS = [
    "id_contrato", "nombre_entidad", "codigo_entidad", "departamento", "sector",
    "tipo_de_contrato", "fecha_de_firma", "anio_firma", "valor_del_contrato",
    "duracion_pactada_dias", "prorrogado", "dias_adicionados",
]

# Parquet guarda los datos por columna, así que columns= lee del disco solo esas 12 (no carga todo y luego filtra).
df = pd.read_parquet(ENTRADA, columns=COLUMNAS)

SALIDA.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(SALIDA, index=False)

print(f"{len(df):,} contratos, {len(COLUMNAS)} columnas -> {SALIDA} ({SALIDA.stat().st_size / 1e6:.1f} MB)")
