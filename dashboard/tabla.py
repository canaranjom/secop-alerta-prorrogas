
from pathlib import Path

import pandas as pd
from dash import dash_table


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "contratos_modelo.parquet"

COLUMNAS = [
    "id_contrato",
    "nombre_entidad",
    "departamento",
    "tipo_de_contrato",
    "fecha_de_firma",
    "valor_del_contrato",
    "duracion_pactada_dias",
    "prorrogado",
    "dias_adicionados",
    "anio_firma",
    "sector",
]

COLUMNAS_VISIBLES = [
    {"name": "ID contrato", "id": "id_contrato"},
    {"name": "Entidad", "id": "nombre_entidad"},
    {"name": "Departamento", "id": "departamento"},
    {"name": "Tipo de contrato", "id": "tipo_de_contrato"},
    {"name": "Fecha firma", "id": "fecha_de_firma"},
    {"name": "Valor (COP)", "id": "valor_del_contrato"},
    {"name": "Duración (días)", "id": "duracion_pactada_dias"},
    {"name": "Prórroga", "id": "prorrogado"},
    {"name": "Días adicionados", "id": "dias_adicionados"},
]


def cargar_datos_tabla():
    return pd.read_parquet(DATA_PATH, columns=COLUMNAS)


def obtener_pagina(datos, pagina=0, tamano=10):
    inicio = pagina * tamano
    fin = inicio + tamano

    resultado = datos.iloc[inicio:fin].copy()

    resultado["fecha_de_firma"] = (
        pd.to_datetime(resultado["fecha_de_firma"])
        .dt.strftime("%Y-%m-%d")
    )

    resultado["valor_del_contrato"] = (
        resultado["valor_del_contrato"]
        .map(lambda x: f"${x:,.0f}".replace(",", ".")
             if pd.notna(x) else "—")
    )

    resultado["duracion_pactada_dias"] = (
        resultado["duracion_pactada_dias"]
        .map(lambda x: f"{x:,.0f}".replace(",", ".")
             if pd.notna(x) else "—")
    )

    resultado["prorrogado"] = (
        resultado["prorrogado"]
        .map({1: "Sí", 0: "No"})
    )

    return resultado[
        [col["id"] for col in COLUMNAS_VISIBLES]
    ].to_dict("records")


def crear_tabla():
    return dash_table.DataTable(
        id="tabla-contratos",
        columns=COLUMNAS_VISIBLES,
        data=[],
        page_action="custom",
        page_current=0,
        page_size=10,
        page_count=0,
        sort_action="custom",
        sort_mode="single",
        sort_by=[],
        style_table={
            "overflowX": "auto",
        },
        style_header={
            "backgroundColor": "#13294B",
            "color": "white",
            "fontWeight": "bold",
            "padding": "12px",
            "textAlign": "left",
        },
        style_cell={
            "padding": "10px",
            "fontFamily": "Arial, sans-serif",
            "fontSize": "12px",
            "textAlign": "left",
            "minWidth": "110px",
            "maxWidth": "280px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
        style_data={
            "backgroundColor": "#FFFFFF",
            "color": "#18212E",
        },
        style_data_conditional=[
            {
                "if": {
                    "filter_query": '{prorrogado} = "Sí"',
                    "column_id": "prorrogado",
                },
                "color": "#C2410C",
                "fontWeight": "bold",
            }
        ],
    )
