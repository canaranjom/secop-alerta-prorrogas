
from pathlib import Path

import dash
import pandas as pd
from dash import html, dcc, Input, Output
from graficas import construir_graficas
from mapa import construir_mapa
from tabla import cargar_datos_tabla, obtener_pagina, crear_tabla

# ============================================================
# 1. CONFIGURACION Y CARGA DE DATOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "contratos_modelo.parquet"

# Una sola lectura para indicadores, filtros y graficas
df = pd.read_parquet(
    DATA_PATH,
    columns=[
        "prorrogado",
        "dias_adicionados",
        "codigo_entidad",
        "tipo_de_contrato",
        "duracion_pactada_dias",
        "anio_firma",
        "departamento",
        "sector",
    ],
)

# ============================================================
# 2. FUNCIONES AUXILIARES
# ============================================================

def formato_numero(valor):
    return f"{valor:,.0f}".replace(",", ".")


def calcular_indicadores(datos):
    total = len(datos)

    if total == 0:
        return "0", "—", "—", "0"

    tasa = datos["prorrogado"].mean() * 100

    prorrogados = datos.loc[
        datos["prorrogado"] == 1, "dias_adicionados"
    ]

    mediana = prorrogados.median()

    entidades = (
        datos["codigo_entidad"].value_counts() >= 100
    ).sum()

    return (
        formato_numero(total),
        f"{tasa:.1f} %".replace(".", ","),
        formato_numero(mediana) if pd.notna(mediana) else "—",
        formato_numero(entidades),
    )


def tarjeta(titulo, valor, color="#18212E", id_valor=None):
    return html.Div(
        [
            html.Div(
                titulo,
                style={
                    "fontSize": "13px",
                    "color": "#4A5668",
                    "fontWeight": "600",
                },
            ),
            html.Div(
                valor,
                id=id_valor,
                style={
                    "fontSize": "30px",
                    "fontWeight": "700",
                    "color": color,
                    "marginTop": "8px",
                },
            ),
        ],
        style={
            "backgroundColor": "#FFFFFF",
            "border": "1px solid #DCE2EA",
            "borderRadius": "10px",
            "padding": "18px",
            "flex": "1 1 220px",
            "minWidth": "0",
        },
    )


def estilo_grafica():
    return {
        "backgroundColor": "#FFFFFF",
        "border": "1px solid #DCE2EA",
        "borderRadius": "10px",
        "padding": "16px",
        "flex": "1 1 450px",
        "minWidth": "0",
    }


def estilo_filtro():
    return {
        "flex": "1 1 200px",
        "minWidth": "0",
    }


# ============================================================
# 3. DATOS INICIALES
# ============================================================

indicadores_iniciales = calcular_indicadores(df)

fig_tipos, fig_duracion = construir_graficas(df)

opciones_anio = [
    {"label": "2023–2024", "value": "todos"},
    {"label": "2023", "value": 2023},
    {"label": "2024", "value": 2024},
]

opciones_departamento = [
    {"label": "Todos", "value": "todos"}
] + [
    {"label": str(valor), "value": str(valor)}
    for valor in sorted(df["departamento"].unique())
]

opciones_sector = [
    {"label": "Todos", "value": "todos"}
] + [
    {"label": str(valor), "value": str(valor)}
    for valor in sorted(df["sector"].unique())
]


# ============================================================
# 4. APLICACION DASH
# ============================================================

# Datos de la tabla: carga única
df_tabla = cargar_datos_tabla()

app = dash.Dash(__name__)

app.title = "Alerta temprana de prórrogas | SECOP II"

app.layout = html.Div(
    style={
        "minHeight": "100vh",
        "backgroundColor": "#F4F6F9",
        "color": "#18212E",
        "fontFamily": "Arial, sans-serif",
    },
    children=[
        # Encabezado
        html.Header(
            [
                html.H2(
                    "Alerta temprana de prórrogas",
                    style={"margin": "0"},
                ),
                html.Div("Contratos públicos · SECOP II"),
            ],
            style={
                "backgroundColor": "#13294B",
                "color": "#FFFFFF",
                "padding": "18px 32px",
            },
        ),

        # Contenido principal
        html.Main(
            [
                html.H1("Panorama de prórrogas"),

                html.P(
                    "Contratos SECOP II firmados en 2023–2024 "
                    "y ya terminados · Fuente: datos.gov.co",
                    style={"color": "#4A5668"},
                ),

                # ============================================
                # FILTROS INTERACTIVOS
                # ============================================

                html.Div(
                    [
                        html.Div(
                            [
                                html.Label(
                                    "Año de firma",
                                    style={"fontWeight": "600"},
                                ),
                                dcc.Dropdown(
                                    id="filtro-anio",
                                    options=opciones_anio,
                                    value="todos",
                                    clearable=False,
                                ),
                            ],
                            style=estilo_filtro(),
                        ),

                        html.Div(
                            [
                                html.Label(
                                    "Departamento",
                                    style={"fontWeight": "600"},
                                ),
                                dcc.Dropdown(
                                    id="filtro-departamento",
                                    options=opciones_departamento,
                                    value="todos",
                                    clearable=False,
                                    searchable=True,
                                ),
                            ],
                            style=estilo_filtro(),
                        ),

                        html.Div(
                            [
                                html.Label(
                                    "Sector",
                                    style={"fontWeight": "600"},
                                ),
                                dcc.Dropdown(
                                    id="filtro-sector",
                                    options=opciones_sector,
                                    value="todos",
                                    clearable=False,
                                    searchable=True,
                                ),
                            ],
                            style=estilo_filtro(),
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": "14px",
                        "marginTop": "20px",
                        "marginBottom": "20px",
                    },
                ),

                # ============================================
                # CUATRO INDICADORES
                # ============================================

                html.Div(
                    [
                        tarjeta(
                            "Contratos analizados",
                            indicadores_iniciales[0],
                            id_valor="kpi-contratos",
                        ),

                        tarjeta(
                            "Tasa de prórroga",
                            indicadores_iniciales[1],
                            color="#C2410C",
                            id_valor="kpi-tasa",
                        ),

                        tarjeta(
                            "Días adicionados (mediana)",
                            indicadores_iniciales[2],
                            id_valor="kpi-mediana",
                        ),

                        tarjeta(
                            "Entidades con ≥ 100 contratos",
                            indicadores_iniciales[3],
                            id_valor="kpi-entidades",
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": "14px",
                        "marginTop": "22px",
                    },
                ),

                # ============================================
                # GRAFICAS DESCRIPTIVAS
                # ============================================

                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "Tasa de prórroga por tipo de contrato"
                                ),

                                dcc.Graph(
                                    id="grafica-tipos",
                                    figure=fig_tipos,
                                    config={"displayModeBar": False},
                                ),
                            ],
                            style=estilo_grafica(),
                        ),

                        html.Div(
                            [
                                html.H3(
                                    "Tasa de prórroga por duración pactada"
                                ),

                                dcc.Graph(
                                    id="grafica-duracion",
                                    figure=fig_duracion,
                                    config={"displayModeBar": False},
                                ),
                            ],
                            style=estilo_grafica(),
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": "14px",
                        "marginTop": "20px",
                    },
                ),
                
                # MAPA DE PRORROGAS POR DEPARTAMENTO
                html.Div(
                    [
                        html.H3(
                            "Tasa de prórroga por departamento"
                        ),
                        dcc.Graph(
                            id="mapa-colombia",
                            figure=construir_mapa(df),
                            config={"displayModeBar": False},
                        ),
                        html.P(
                            "Fuente: SECOP II. Los contratos sin "
                            "departamento definido no se representan "
                            "en el mapa.",
                            style={
                                "color": "#4A5668",
                                "fontSize": "12px",
                            },
                        ),
                    ],
                    style={
                        "backgroundColor": "#FFFFFF",
                        "border": "1px solid #DCE2EA",
                        "borderRadius": "10px",
                        "padding": "16px",
                        "marginTop": "20px",
                    },
                ),
                html.Div(
                    [
                        html.H3("Consulta histórica de contratos"),
                        html.P(
                            "Explora los contratos SECOP II según los "
                            "filtros seleccionados. Los resultados de "
                            "prórroga son históricos, no predicciones.",
                            style={
                                "color": "#4A5668",
                                "fontSize": "13px",
                            },
                        ),
                        crear_tabla(),
                    ],
                    style={
                        "backgroundColor": "#FFFFFF",
                        "border": "1px solid #DCE2EA",
                        "borderRadius": "10px",
                        "padding": "16px",
                        "marginTop": "20px",
                    },
                ),
            ],
            style={
                "maxWidth": "1200px",
                "margin": "auto",
                "padding": "28px 24px",
            },
        ),
    ],
)


# ============================================================
# 5. CALLBACK: ACTUALIZACION CON LOS FILTROS
# ============================================================

@app.callback(
    Output("kpi-contratos", "children"),
    Output("kpi-tasa", "children"),
    Output("kpi-mediana", "children"),
    Output("kpi-entidades", "children"),
    Output("grafica-tipos", "figure"),
    Output("grafica-duracion", "figure"),
    Output("mapa-colombia", "figure"),
    Input("filtro-anio", "value"),
    Input("filtro-departamento", "value"),
    Input("filtro-sector", "value"),
)
def actualizar_panorama(anio, departamento, sector):

    datos = df

    # Filtro por año de firma
    if anio != "todos":
        datos = datos[
            datos["anio_firma"] == anio
        ]

    # Filtro por departamento
    if departamento != "todos":
        datos = datos[
            datos["departamento"] == departamento
        ]

    # Filtro por sector
    if sector != "todos":
        datos = datos[
            datos["sector"] == sector
        ]

    # Indicadores del subconjunto filtrado
    indicadores = calcular_indicadores(datos)

    # Evitar fallos cuando no hay registros
    if datos.empty:
        figura_vacia_tipos = {
            "data": [],
            "layout": {
                "annotations": [
                    {
                        "text": "No hay datos para los filtros seleccionados",
                        "showarrow": False,
                        "xref": "paper",
                        "yref": "paper",
                        "x": 0.5,
                        "y": 0.5,
                    }
                ]
            },
        }

        figura_vacia_duracion = {
            "data": [],
            "layout": {
                "annotations": [
                    {
                        "text": "No hay datos para los filtros seleccionados",
                        "showarrow": False,
                        "xref": "paper",
                        "yref": "paper",
                        "x": 0.5,
                        "y": 0.5,
                    }
                ]
            },
        }

        return (
            *indicadores,
            figura_vacia_tipos,
            figura_vacia_duracion,
            construir_mapa(datos),
        )
    # Reconstruir graficas con los datos filtrados
    figuras = construir_graficas(datos)
    figura_mapa = construir_mapa(datos)

    return (
        *indicadores,
        figuras[0],
        figuras[1],
        figura_mapa,
    )

# ============================================================
# 6. EJECUCION LOCAL
# ============================================================

@app.callback(
    Output("tabla-contratos", "data"),
    Output("tabla-contratos", "page_count"),
    Input("tabla-contratos", "page_current"),
    Input("tabla-contratos", "page_size"),
    Input("tabla-contratos", "sort_by"),
    Input("filtro-anio", "value"),
    Input("filtro-departamento", "value"),
    Input("filtro-sector", "value"),
)
def actualizar_tabla(
    pagina, tamano, ordenamiento,
    anio, departamento, sector
):
    datos = df_tabla

    if anio != "todos":
        datos = datos[datos["anio_firma"] == anio]

    if departamento != "todos":
        datos = datos[
            datos["departamento"] == departamento
        ]

    if sector != "todos":
        datos = datos[datos["sector"] == sector]

    if ordenamiento:
        columna = ordenamiento[0]["column_id"]
        ascendente = (
            ordenamiento[0]["direction"] == "asc"
        )

        datos = datos.sort_values(
            columna,
            ascending=ascendente,
            na_position="last",
        )

    if datos.empty:
        return [], 0

    total_paginas = (
        len(datos) + tamano - 1
    ) // tamano

    pagina = min(pagina or 0, total_paginas - 1)

    registros = obtener_pagina(
        datos,
        pagina=pagina,
        tamano=tamano,
    )

    return registros, total_paginas


if __name__ == "__main__":
    app.run(debug=True, port=8050)
