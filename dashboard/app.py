
from pathlib import Path

import dash
import pandas as pd
from dash import html

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "contratos_modelo.parquet"

# Cargar únicamente las columnas necesarias
df = pd.read_parquet(
    DATA_PATH,
    columns=["prorrogado", "dias_adicionados", "codigo_entidad"],
)

total_contratos = len(df)
total_prorrogados = int(df["prorrogado"].sum())
tasa_prorroga = df["prorrogado"].mean() * 100
mediana_dias = df.loc[
    df["prorrogado"] == 1, "dias_adicionados"
].median()
entidades_100 = int(
    (df["codigo_entidad"].value_counts() >= 100).sum()
)

def formato_numero(valor):
    return f"{valor:,.0f}".replace(",", ".")

def tarjeta(titulo, valor, color="#18212E"):
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
        },
    )

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
        html.Main(
            [
                html.H1("Panorama de prórrogas"),
                html.P(
                    "Contratos SECOP II firmados en 2023–2024 "
                    "y ya terminados · Fuente: datos.gov.co",
                    style={"color": "#4A5668"},
                ),
                html.Div(
                    [
                        tarjeta(
                            "Contratos analizados",
                            formato_numero(total_contratos),
                        ),
                        tarjeta(
                            "Tasa de prórroga",
                            f"{tasa_prorroga:.1f} %".replace(".", ","),
                            "#C2410C",
                        ),
                        tarjeta(
                            "Días adicionados (mediana)",
                            formato_numero(mediana_dias),
                        ),
                        tarjeta(
                            "Entidades con ≥ 100 contratos",
                            formato_numero(entidades_100),
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": "14px",
                        "marginTop": "22px",
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

if __name__ == "__main__":
    app.run(debug=True, port=8050)
