"""Pantalla Evaluar contrato para el proyecto SECOP II.

Mantiene la selección de entidad visible después de buscarla.
No modifica la lógica predictiva de src/prediccion.py.
"""
from pathlib import Path
import sys

import pandas as pd
from dash import html, dcc, Input, Output, State
from dash.exceptions import PreventUpdate

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.prediccion import opciones, buscar_entidades, evaluar_contrato, _cargar


def desplegable(titulo, identificador, variable):
    return html.Div([
        html.Label(titulo, style={"fontWeight": "600", "fontSize": "13px"}),
        dcc.Dropdown(
            id=identificador,
            options=[{"label": str(v), "value": str(v)} for v in opciones(variable)],
            placeholder="Seleccionar...",
            clearable=True,
            style={"marginTop": "6px"},
        ),
    ])


def campo(titulo, identificador, tipo="text"):
    opciones_input = {"min": 0} if tipo == "number" else {}
    return html.Div([
        html.Label(titulo, style={"fontWeight": "600", "fontSize": "13px"}),

        dcc.Input(
            id=identificador,
            type=tipo,
            min=0 if tipo == "number" else None,
            debounce=True,
            style={
                "width": "100%",
                "height": "42px",
                "padding": "8px 12px",
                "fontSize": "15px",
                "lineHeight": "24px",
                "fontFamily": "Arial, sans-serif",
                "fontWeight": "500",
                "marginTop": "6px",
                "border": "1px solid #DCE2EA",
                "borderRadius": "6px",
                "boxSizing": "border-box",
                "color": "#18212E",
            },
        ),
    ])


def crear_evaluacion():
    return html.Div([
        html.H1("Evaluar contrato"),
        html.P(
            "Estima el riesgo de prórroga de un contrato público al momento de su firma.",
            style={"color": "#4A5668"},
        ),
        html.Div([
            html.H3("Información del contrato"),
            html.Div([
                html.Label("Entidad contratante", style={"fontWeight": "600"}),
                dcc.Dropdown(
                    id="eval-entidad", options=[],
                    placeholder="Escribe al menos 3 letras...",
                    searchable=True, clearable=True,
                ),
                html.Div(id="eval-entidad-confirmacion", style={
                    "fontSize": "12px", "color": "#16805D", "marginTop": "5px"
                }),
            ], style={"marginBottom": "20px"}),
            html.Div([
                desplegable("Tipo de contrato", "eval-tipo", "tipo_de_contrato"),
                desplegable("Modalidad de contratación", "eval-modalidad", "modalidad_de_contratacion"),
                desplegable("Departamento", "eval-departamento", "departamento"),
                desplegable("Orden de la entidad", "eval-orden", "orden"),
                desplegable("Sector", "eval-sector", "sector"),
                campo("Valor base del contrato (COP)", "eval-valor", "number"),
                campo("Duración pactada (días)", "eval-duracion", "number"),
                html.Div([
                    html.Label("Fecha de firma", style={"fontWeight": "600", "fontSize": "13px"}),
                    dcc.DatePickerSingle(
                        id="eval-fecha", display_format="DD/MM/YYYY",
                        placeholder="Seleccionar fecha",
                    ),
                ]),
                campo("Código del proveedor (opcional)", "eval-proveedor"),
            ], style={
                "display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(240px, 1fr))",
                "gap": "20px",
            }),
            html.Button(
                "Evaluar riesgo de prórroga", id="eval-boton", n_clicks=0,
                style={
                    "marginTop": "26px", "padding": "13px 24px",
                    "backgroundColor": "#13294B", "color": "white",
                    "border": "none", "borderRadius": "7px",
                    "fontWeight": "bold", "cursor": "pointer",
                },
            ),
            dcc.Loading(
                html.Div(id="eval-resultado", style={"marginTop": "25px"}),
                type="circle",
            ),
        ], style={
            "backgroundColor": "white", "padding": "26px", "borderRadius": "10px",
            "border": "1px solid #DCE2EA", "marginTop": "20px",
        }),
    ], style={
        "maxWidth": "1200px", "margin": "auto", "padding": "28px 24px",
        "color": "#18212E",
    })


def _fila_entidad(codigo):
    if codigo is None or str(codigo).strip() == "":
        return None
    entidades = _cargar()[2]
    codigo = str(codigo)
    if codigo not in entidades.index:
        return None
    fila = entidades.loc[codigo]
    if isinstance(fila, pd.DataFrame):
        fila = fila.iloc[0]
    return fila


def registrar_callbacks_evaluacion(app):
    @app.callback(
        Output("eval-entidad", "options"),
        Input("eval-entidad", "search_value"),
        State("eval-entidad", "value"),
    )
    def buscar_opciones_entidad(texto, seleccion):
        """Mantener la opción elegida aun cuando Dash borre search_value."""
        encontradas = []
        if texto and len(texto.strip()) >= 3:
            resultados = buscar_entidades(texto.strip(), n=20)
            encontradas = [
                {
                    "label": f"{fila['nombre_entidad']} ({fila['departamento']})",
                    "value": str(fila["codigo_entidad"]),
                }
                for _, fila in resultados.iterrows()
            ]

        if seleccion is not None:
            codigo = str(seleccion)
            if not any(op["value"] == codigo for op in encontradas):
                fila = _fila_entidad(codigo)
                if fila is not None:
                    encontradas.append({
                        "label": f"{fila['nombre_entidad']} ({fila['departamento']})",
                        "value": codigo,
                    })
        return encontradas

    @app.callback(
        Output("eval-departamento", "value"),
        Output("eval-orden", "value"),
        Output("eval-sector", "value"),
        Output("eval-entidad-confirmacion", "children"),
        Input("eval-entidad", "value"),
        prevent_initial_call=True,
    )
    def completar_entidad(codigo):
        fila = _fila_entidad(codigo)
        if fila is None:
            if not codigo:
                return None, None, None, ""
            raise PreventUpdate
        return (
            fila.get("departamento"),
            fila.get("orden"),
            fila.get("sector"),
            f"Entidad seleccionada: {fila.get('nombre_entidad')} · Código: {codigo}",
        )

    @app.callback(
        Output("eval-resultado", "children"),
        Input("eval-boton", "n_clicks"),
        State("eval-entidad", "value"),
        State("eval-tipo", "value"),
        State("eval-modalidad", "value"),
        State("eval-departamento", "value"),
        State("eval-orden", "value"),
        State("eval-sector", "value"),
        State("eval-valor", "value"),
        State("eval-duracion", "value"),
        State("eval-fecha", "date"),
        State("eval-proveedor", "value"),
        prevent_initial_call=True,
    )
    def ejecutar_evaluacion(clics, entidad, tipo, modalidad,
                            departamento, orden, sector, valor,
                            duracion, fecha, proveedor):
        if not all([tipo, modalidad, departamento, orden, sector, fecha]) \
                or valor is None or duracion is None:
            return html.P(
                "Completa los campos contractuales requeridos.",
                style={"color": "#C2410C"},
            )
        if valor <= 0 or duracion <= 0:
            return html.P(
                "El valor y la duración deben ser mayores que cero.",
                style={"color": "#C2410C"},
            )

        datos = {
            "codigo_entidad": entidad,
            "tipo_de_contrato": tipo,
            "modalidad_de_contratacion": modalidad,
            "departamento": departamento,
            "orden": orden,
            "sector": sector,
            "precio_base": float(valor),
            "duracion_pactada_dias": float(duracion),
            "fecha_de_firma": fecha,
            "codigo_proveedor": proveedor,
        }
        try:
            resultado = evaluar_contrato(datos)
        except Exception as error:
            return html.Div([
                html.H4("No fue posible evaluar el contrato"),
                html.Pre(str(error)),
            ], style={"color": "#B91C1C"})

        probabilidad = resultado["probabilidad_prorroga"] * 100
        nivel = str(resultado["nivel"]).lower()
        color = {"bajo": "#16805D", "medio": "#B7791F", "alto": "#C2410C"}.get(
            nivel, "#13294B")
        factores = resultado.get("factores", [])
        notas = resultado.get("notas", [])
        return html.Div([
            html.H2("Resultado de la evaluación"),
            html.Div(f"{probabilidad:.1f} %", style={
                "fontSize": "48px", "fontWeight": "bold", "color": color,
            }),
            html.P("Probabilidad estimada de prórroga"),
            html.H3(f"Nivel de riesgo: {nivel.upper()}", style={"color": color}),
            html.H4("Factores que aumentan el riesgo"),
            html.Ul([
                html.Li([
                    html.Strong(f"{factor['descripcion']}: "),
                    str(factor["valor"]),
                    f" (efecto {factor['efecto']:+.2f})",
                ]) for factor in factores
            ]) if factores else html.P("Sin contribuciones positivas destacadas."),
            html.H4("Observaciones"),
            html.Ul([html.Li(str(nota)) for nota in notas]) if notas else
            html.P("Sin observaciones adicionales."),
            html.P(f"Modelo: {resultado.get('modelo', 'No disponible')}", style={
                "fontSize": "12px", "color": "#64748B",
            }),
            html.P(
                "Esta estimación es una herramienta de apoyo a la decisión y no "
                "garantiza que el contrato requiera una prórroga.",
                style={"fontSize": "12px", "color": "#64748B"},
            ),
        ], style={
            "backgroundColor": "#F4F6F9", "padding": "24px", "borderRadius": "10px",
            "borderLeft": f"5px solid {color}",
        })
