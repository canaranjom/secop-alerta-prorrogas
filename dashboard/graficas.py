

import pandas as pd
import plotly.express as px


def construir_graficas(df):
    # Gráfica 1: tipos con al menos 500 contratos
    tipos = (
        df.groupby("tipo_de_contrato")["prorrogado"]
        .agg(contratos="size", tasa="mean")
        .reset_index()
    )

    tipos = tipos[tipos["contratos"] >= 500].copy()
    tipos["tasa"] = tipos["tasa"] * 100
    tipos = tipos.sort_values("tasa", ascending=True)

    fig_tipos = px.bar(
        tipos,
        x="tasa",
        y="tipo_de_contrato",
        orientation="h",
        text="tasa",
        labels={
            "tasa": "Tasa de prórroga (%)",
            "tipo_de_contrato": "",
        },
        color_discrete_sequence=["#1F5FAF"],
    )

    fig_tipos.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )

    fig_tipos.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=55, t=20, b=30),
        showlegend=False,
        xaxis_range=[0, 55],
    )

    # Gráfica 2: duración pactada
    duracion = df[
        df["duracion_pactada_dias"].notna()
        & (df["duracion_pactada_dias"] > 0)
        & (df["duracion_pactada_dias"] <= 3650)
    ].copy()

    limites = [0, 30, 90, 180, 270, 365, 730, 3650]
    etiquetas = [
        "≤1 mes",
        "1–3 meses",
        "3–6 meses",
        "6–9 meses",
        "9–12 meses",
        "1–2 años",
        "2–10 años",
    ]

    duracion["rango"] = pd.cut(
        duracion["duracion_pactada_dias"],
        bins=limites,
        labels=etiquetas,
        include_lowest=False,
    )

    tasas = (
        duracion.groupby("rango", observed=True)["prorrogado"]
        .agg(contratos="size", tasa="mean")
        .reset_index()
    )
    tasas["tasa"] = tasas["tasa"] * 100

    fig_duracion = px.bar(
        tasas,
        x="rango",
        y="tasa",
        text="tasa",
        labels={
            "rango": "Duración pactada",
            "tasa": "Tasa de prórroga (%)",
        },
        color_discrete_sequence=["#C2410C"],
    )

    fig_duracion.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )

    fig_duracion.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=20, t=20, b=55),
        showlegend=False,
    )

    return fig_tipos, fig_duracion
