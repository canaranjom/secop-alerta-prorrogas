
from functools import lru_cache

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from geografia import cargar_geografia, normalizar_nombre


@lru_cache(maxsize=1)
def obtener_geografia():
    # Cargar GeoJSON y equivalencias una sola vez
    return cargar_geografia()


def construir_mapa(datos):
    geojson, equivalencias = obtener_geografia()

    # Agrupar primero: de millones de registros
    # a un maximo de 34 categorias
    resumen = (
        datos.groupby("departamento")["prorrogado"]
        .agg(contratos="size", tasa="mean")
        .reset_index()
    )

    # Homologar solamente los nombres agrupados
    resumen["codigo_geo"] = (
        resumen["departamento"]
        .map(normalizar_nombre)
        .map(equivalencias)
    )

    # No Definido permanece en indicadores,
    # pero no tiene representacion geografica
    resumen = resumen.dropna(
        subset=["codigo_geo"]
    ).copy()

    if resumen.empty:
        figura = go.Figure()
        figura.add_annotation(
            text="No hay datos geograficos disponibles",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        figura.update_layout(
            height=520,
            template="plotly_white",
        )
        return figura

    resumen["tasa"] *= 100

    figura = px.choropleth(
        resumen,
        geojson=geojson,
        locations="codigo_geo",
        featureidkey="properties.cod_depart",
        color="tasa",
        hover_name="departamento",
        hover_data={
            "codigo_geo": False,
            "contratos": True,
            "tasa": ":.2f",
        },
        color_continuous_scale="Blues",
        labels={
            "tasa": "Tasa de prórroga (%)",
            "contratos": "Contratos",
        },
    )

    figura.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showland=False,
    )

    figura.update_layout(
        template="plotly_white",
        height=520,
        margin=dict(l=0, r=0, t=10, b=0),
        coloraxis_colorbar=dict(
            title="Tasa (%)",
            thickness=14,
            len=0.65,
        ),
    )

    return figura
