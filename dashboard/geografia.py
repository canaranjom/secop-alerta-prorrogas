
from pathlib import Path
import json
import unicodedata

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
GEO_PATH = (
    BASE_DIR / "dashboard" / "assets" / "geo"
    / "colombia_departamentos_simplificado.geojson"
)


def normalizar_nombre(nombre):
    texto = unicodedata.normalize("NFKD", str(nombre))
    texto = "".join(
        c for c in texto if not unicodedata.combining(c)
    )
    return texto.upper().strip()


def cargar_geografia():
    with open(GEO_PATH, encoding="utf-8") as archivo:
        geojson = json.load(archivo)

    # Excluir geometrías sin código o nombre válido
    geojson["features"] = [
        feature
        for feature in geojson["features"]
        if str(
            feature["properties"].get("cod_depart") or ""
        ).strip()
        and str(
            feature["properties"].get("departamen") or ""
        ).strip()
    ]

    # Corregir la etiqueta de Bogota sin cambiar su codigo
    for feature in geojson["features"]:
        if feature["properties"]["cod_depart"] == "11":
            feature["properties"]["departamen"] = "BOGOTÁ D.C."

    equivalencias = {}

    for feature in geojson["features"]:
        propiedades = feature["properties"]
        nombre = normalizar_nombre(propiedades["departamen"])
        codigo = propiedades["cod_depart"]
        equivalencias[nombre] = codigo

    # Diferencias entre SECOP y el GeoJSON
    equivalencias["DISTRITO CAPITAL DE BOGOTA"] = "11"
    equivalencias[
        "SAN ANDRES, PROVIDENCIA Y SANTA CATALINA"
    ] = "88"

    # Ajustar la orientación de los anillos para Plotly.
    # No modifica el archivo GeoJSON original.
    for feature in geojson["features"]:
        geometria = feature["geometry"]
        tipo = geometria["type"]

        if tipo == "Polygon":
            for anillo in geometria["coordinates"]:
                anillo.reverse()

        elif tipo == "MultiPolygon":
            for poligono in geometria["coordinates"]:
                for anillo in poligono:
                    anillo.reverse()


    return geojson, equivalencias


def agregar_codigo_geografico(datos, equivalencias):
    resultado = datos.copy()

    resultado["codigo_geo"] = (
        resultado["departamento"]
        .map(normalizar_nombre)
        .map(equivalencias)
    )

    return resultado


if __name__ == "__main__":
    geojson, equivalencias = cargar_geografia()

    datos = pd.read_parquet(
        BASE_DIR / "data" / "processed"
        / "contratos_modelo.parquet",
        columns=["departamento"],
    )

    datos = agregar_codigo_geografico(datos, equivalencias)

    no_definidos = datos["departamento"].eq("No Definido")
    sin_codigo = datos["codigo_geo"].isna()

    print("Geometrias validas:", len(geojson["features"]))
    print("Total contratos:", len(datos))
    print("Contratos con codigo:", datos["codigo_geo"].notna().sum())
    print("Contratos No Definido:", no_definidos.sum())
    print(
        "Contratos sin homologacion inesperada:",
        (sin_codigo & ~no_definidos).sum()
    )
    print(
        "Categorias sin homologar:",
        datos.loc[sin_codigo & ~no_definidos, "departamento"]
        .unique().tolist()
    )
