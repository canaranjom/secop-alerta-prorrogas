"""Pantalla Evaluar contrato para el proyecto SECOP II.

Consulta las predicciones y los datos del formulario mediante FastAPI.
Mantiene la selección de entidad visible después de buscarla.
"""

import os
import requests

from dash import html, dcc, Input, Output, State
from dash.exceptions import PreventUpdate

API_URL = os.getenv("API_URL", "http://127.0.0.1:8001").rstrip("/")
API = f"{API_URL}/api/v1"


def api_get(ruta, **params):
    """Consulta la API y devuelve su respuesta JSON."""
    respuesta = requests.get(
        f"{API}{ruta}",
        params=params,
        timeout=30
    )
    respuesta.raise_for_status()
    return respuesta.json()


def opciones_seguras(variable):
    """Obtiene opciones de la API sin impedir el arranque de Dash."""
    try:
        return api_get(f"/opciones/{variable}")["valores"]
    except (requests.RequestException, KeyError, ValueError, TypeError):
        return []


def desplegable(titulo, identificador, variable):
    return html.Div([
        html.Label(titulo, style={"fontWeight": "600", "fontSize": "13px"}),
        dcc.Dropdown(
            id=identificador,
            options=[],
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

        html.Div(
            id="eval-api-aviso",
            children=(
                "Servicio de predicción no disponible temporalmente. "
                "No es posible buscar entidades ni evaluar contratos. "
                "Puedes continuar utilizando Panorama."
            ),
            style={"display": "none"},
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
    """Obtiene una entidad desde la API usando su código."""
    if codigo is None or str(codigo).strip() == "":
        return None

    try:
        return api_get(f"/entidades/{str(codigo).strip()}")
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            return None
        raise


def registrar_callbacks_evaluacion(app):


    @app.callback(
        Output("eval-tipo", "options"),
        Output("eval-modalidad", "options"),
        Output("eval-departamento", "options"),
        Output("eval-orden", "options"),
        Output("eval-sector", "options"),
        Output("eval-api-aviso", "style"),
        Input("navegacion", "value"),
        State("eval-tipo", "options"),
        State("eval-modalidad", "options"),
        State("eval-departamento", "options"),
        State("eval-orden", "options"),
        State("eval-sector", "options"),
    )

    def cargar_opciones_evaluacion(pantalla, *opciones_actuales):
        """Actualiza opciones y muestra el estado de FastAPI."""
        if pantalla != "evaluar":
            raise PreventUpdate

        variables = [
            "tipo_de_contrato",
            "modalidad_de_contratacion",
            "departamento",
            "orden",
            "sector",
        ]

        estilo_aviso = {
            "backgroundColor": "#FFF4E5",
            "color": "#8A4B08",
            "border": "1px solid #F1CD93",
            "borderRadius": "6px",
            "padding": "12px 16px",
            "marginTop": "16px",
            "marginBottom": "16px",
            "fontSize": "13px",
        }

        try:
            api_get("/health")
            api_disponible = True
        except (requests.RequestException, KeyError, ValueError, TypeError):
            api_disponible = False

        resultados = []

        for variable, anteriores in zip(variables, opciones_actuales):
            if not api_disponible:
                resultados.append(anteriores or [])
                continue

            try:
                valores = api_get(f"/opciones/{variable}")["valores"]
                nuevas = [
                    {"label": str(v), "value": str(v)}
                    for v in valores
                ]
                resultados.append(nuevas)
            except (requests.RequestException, KeyError, ValueError, TypeError):
                resultados.append(anteriores or [])

        if api_disponible:
            estilo_aviso = {"display": "none"}

        return (*resultados, estilo_aviso)

    @app.callback(
        Output("eval-entidad", "options"),
        Input("eval-entidad", "search_value"),
        State("eval-entidad", "value"),
    )

    def buscar_opciones_entidad(texto, seleccion):
        """Busca entidades y conserva la selección ante fallos de API."""
        encontradas = []

        if texto and len(texto.strip()) >= 3:
            try:
                resultados = api_get("/entidades", q=texto.strip(), n=20)
                encontradas = [
                    {
                        "label": f"{fila['nombre_entidad']} ({fila['departamento']})",
                        "value": str(fila["codigo_entidad"]),
                    }
                    for fila in resultados
                ]
            except (requests.RequestException, KeyError, ValueError, TypeError):
                pass

        if seleccion is not None:
            codigo = str(seleccion)
            if not any(op["value"] == codigo for op in encontradas):
                try:
                    fila = _fila_entidad(codigo)
                    if fila is not None:
                        encontradas.append({
                            "label": f"{fila['nombre_entidad']} ({fila['departamento']})",
                            "value": codigo,
                        })
                except (requests.RequestException, KeyError, ValueError, TypeError):
                    raise PreventUpdate

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
        try:
            fila = _fila_entidad(codigo)
        except (requests.RequestException, KeyError, ValueError, TypeError):
            raise PreventUpdate
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
            respuesta = requests.post(
                f"{API}/evaluar",
                json=datos,
                timeout=30
            )
            respuesta.raise_for_status()
            resultado = respuesta.json()

        except requests.Timeout:
            return html.P(
                "La API tardó demasiado en responder. Intenta nuevamente.",
                style={"color": "#B91C1C"}
            )

        except requests.ConnectionError:
            return html.P(
                "No fue posible conectar con el servicio de predicción. "
                "Verifica que la API esté disponible.",
                style={"color": "#B91C1C"}
            )

        except requests.HTTPError as error:
            return html.P(
                "No fue posible evaluar el contrato. "
                f"El servicio respondió con el código "
                f"{error.response.status_code if error.response is not None else 'desconocido'}.",
                style={"color": "#B91C1C"}
            )

        except (ValueError, KeyError, TypeError):
            return html.P(
                "La respuesta del servicio de predicción no tiene el formato esperado.",
                style={"color": "#B91C1C"}
            )

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
