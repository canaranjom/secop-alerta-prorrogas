"""Evalúa un contrato nuevo con el modelo exportado (para la página "Evaluar contrato" del tablero).

Necesita los archivos de models/ (los genera src/exportar_modelo.py; con DVC: dvc pull models).

Uso desde Dash:
    from src.prediccion import evaluar_contrato, opciones, buscar_entidades

    resultado = evaluar_contrato({
        "codigo_entidad": "702305372",           # o "nombre_entidad": "ALCALDIA ..."
        "tipo_de_contrato": "Obra",
        "modalidad_de_contratacion": "Licitación pública Obra Publica",
        "precio_base": 1_850_000_000,             # pesos
        "duracion_pactada_dias": 420,             # o "duracion_meses": 14
        "departamento": "Antioquia",
        "orden": "Territorial",
        "sector": "Transporte",
        "fecha_de_firma": "2026-11-07",
        "codigo_proveedor": None,                  # opcional
    })
    # -> {"probabilidad_prorroga": 0.58, "nivel": "alto",
    #     "factores": [{"variable": ..., "descripcion": ..., "valor": ..., "efecto": +0.12}, ...], ...}

Campos que se pueden omitir: se completan con lo más frecuente en esa entidad y, si la entidad no
se encuentra, con lo más frecuente en todo el entrenamiento.

Prueba rápida:  python src/prediccion.py
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

CARPETA = Path(__file__).resolve().parent.parent / "models"

# Nombres legibles para mostrar los factores en el tablero.
DESCRIPCION = {
    "tipo_de_contrato": "Tipo de contrato", "modalidad_de_contratacion": "Modalidad de contratación",
    "justificacion_modalidad_de": "Justificación de la modalidad", "sector": "Sector",
    "orden": "Orden de la entidad", "rama": "Rama", "entidad_centralizada": "Entidad centralizada",
    "departamento": "Departamento", "destino_gasto": "Destino del gasto",
    "origen_de_los_recursos": "Origen de los recursos",
    "el_contrato_puede_ser_prorrogado": "El contrato admite prórroga", "es_pyme": "Proveedor pyme",
    "es_grupo": "Proveedor es consorcio o unión temporal", "habilita_pago_adelantado": "Pago adelantado",
    "obligaci_n_ambiental": "Obligación ambiental", "reversion": "Reversión",
    "espostconflicto": "Contrato de posconflicto", "tipodocproveedor": "Tipo de documento del proveedor",
    "segmento_unspsc": "Segmento UNSPSC", "tramo_precio": "Tramo de precio base",
    "tipo_x_tramo_precio": "Tipo de contrato y tramo de precio", "log_precio_base": "Precio base",
    "duracion_pactada_dias": "Duración pactada (días)", "supera_12_meses": "Duración mayor a 12 meses",
    "cruza_vigencia": "El plazo cruza el cierre de la vigencia fiscal", "mes_firma": "Mes de firma",
    "dias_firma_a_inicio": "Días entre firma e inicio", "prov_antiguedad_dias": "Antigüedad del proveedor (días)",
    "proc_proveedores_invitados": "Proveedores invitados", "proc_respuestas_al_procedimiento": "Respuestas al proceso",
    "proc_conteo_de_respuestas_a_ofertas": "Ofertas recibidas", "proc_numero_de_lotes": "Número de lotes",
    "tiene_recursos_propios": "Financiado con recursos propios", "tiene_pgn": "Financiado con PGN",
    "tiene_sgp": "Financiado con SGP", "tiene_regalias": "Financiado con regalías",
    "tasa_hist_entidad": "Historial de prórrogas de la entidad", "n_hist_entidad": "Contratos terminados de la entidad",
    "tasa_hist_proveedor": "Historial de prórrogas del proveedor",
    "n_hist_proveedor": "Contratos terminados del proveedor",
}
NUM_PERFIL = {"tiene_recursos_propios", "tiene_pgn", "tiene_sgp", "tiene_regalias", "dias_firma_a_inicio",
              "prov_antiguedad_dias", "proc_proveedores_invitados", "proc_respuestas_al_procedimiento",
              "proc_conteo_de_respuestas_a_ofertas", "proc_numero_de_lotes"}


@lru_cache(maxsize=1)
def _cargar():
    esquema = json.load(open(CARPETA / "esquema.json", encoding="utf-8"))
    modelo = joblib.load(CARPETA / "modelo_prorroga.joblib")
    entidades = pd.read_parquet(CARPETA / "perfil_entidad.parquet")
    entidades["codigo_entidad"] = entidades["codigo_entidad"].astype(str)
    proveedores = pd.read_parquet(CARPETA / "tasa_proveedor.parquet")
    proveedores["codigo_proveedor"] = proveedores["codigo_proveedor"].astype(str)
    return esquema, modelo, entidades.set_index("codigo_entidad"), proveedores.set_index("codigo_proveedor")


def opciones(variable):
    """Valores válidos para una lista desplegable (ordenados de más a menos frecuente)."""
    return _cargar()[0]["valores"][variable]


def buscar_entidades(texto, n=20):
    """Entidades cuyo nombre contiene el texto (para un buscador en el formulario)."""
    ent = _cargar()[2]
    r = ent[ent["nombre_entidad"].str.contains(texto, case=False, na=False, regex=False)]
    return (r.sort_values("contratos", ascending=False).head(n)
             .reset_index()[["codigo_entidad", "nombre_entidad", "departamento", "orden", "sector"]])


def _vacio(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or v == ""


def _tramo(log_precio):
    if _vacio(log_precio):
        return "nan"
    return "<10M" if log_precio <= 7 else "10M-100M" if log_precio <= 8 else "100M-1.000M" if log_precio <= 9 \
        else ">1.000M"


def construir_fila(datos):
    """Convierte lo que llega del formulario en las 40 variables que espera el modelo."""
    esquema, _, entidades, proveedores = _cargar()
    fila = dict(esquema["por_defecto"])
    prior = esquema["prior"]
    notas = []

    # Entidad: su historia y sus valores más frecuentes en lo que el formulario no pide.
    cod = datos.get("codigo_entidad")
    if _vacio(cod) and not _vacio(datos.get("nombre_entidad")):
        enc = entidades.index[entidades["nombre_entidad"].str.upper() == str(datos["nombre_entidad"]).upper()]
        cod = enc[0] if len(enc) else None
    if not _vacio(cod) and str(cod) in entidades.index:
        e = entidades.loc[str(cod)]
        for c in esquema["categoricas"] + list(NUM_PERFIL):
            if c in e.index and not _vacio(e[c]):
                fila[c] = float(e[c]) if c in NUM_PERFIL else str(e[c])
        fila["tasa_hist_entidad"], fila["n_hist_entidad"] = float(e["tasa_hist"]), float(e["n_hist"])
    else:
        fila["tasa_hist_entidad"], fila["n_hist_entidad"] = prior, 0.0
        notas.append("Entidad sin historial en SECOP II: se usa la tasa general.")

    # Lo que el usuario escribió manda sobre el perfil de la entidad.
    for c in esquema["categoricas"]:
        if not _vacio(datos.get(c)):
            fila[c] = str(datos[c])

    precio = datos.get("precio_base")
    fila["log_precio_base"] = math.log10(precio) if not _vacio(precio) and precio > 0 else np.nan
    fila["tramo_precio"] = _tramo(fila["log_precio_base"])
    fila["tipo_x_tramo_precio"] = f"{fila['tipo_de_contrato']} | {fila['tramo_precio']}"

    dur = datos.get("duracion_pactada_dias")
    if _vacio(dur) and not _vacio(datos.get("duracion_meses")):
        dur = float(datos["duracion_meses"]) * 30
    if not _vacio(dur):
        dur = float(dur)
        fila["supera_12_meses"] = int(dur > 365)
        fila["duracion_pactada_dias"] = min(dur, esquema["duracion_max_dias"])
    firma = pd.Timestamp(datos.get("fecha_de_firma") or pd.Timestamp.today().normalize())
    fila["mes_firma"] = firma.month
    dur_total = 0 if _vacio(dur) else min(dur, 3650)
    fila["cruza_vigencia"] = int((firma + pd.Timedelta(days=dur_total)).year > firma.year)

    # Proveedor (opcional).
    prov = datos.get("codigo_proveedor")
    if not _vacio(prov) and str(prov) in proveedores.index:
        p = proveedores.loc[str(prov)]
        fila["tasa_hist_proveedor"], fila["n_hist_proveedor"] = float(p["tasa_hist"]), float(p["n_hist"])
        if not _vacio(p["fecha_creacion"]):
            fila["prov_antiguedad_dias"] = max((firma - pd.Timestamp(p["fecha_creacion"])).days, 0)
    else:
        fila["tasa_hist_proveedor"], fila["n_hist_proveedor"] = prior, 0.0

    X = pd.DataFrame([fila])[esquema["categoricas"] + esquema["numericas"]]
    for c in esquema["categoricas"]:
        X[c] = X[c].astype(str)
    for c in esquema["numericas"]:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    return X, notas


def _nivel(p, bandas):
    for nombre, (lo, hi) in bandas.items():
        if lo <= p < hi or (hi == 1.0 and p == 1.0):
            return nombre
    return "alto"


def evaluar_contrato(datos, n_factores=3):
    """Probabilidad de prórroga, nivel de riesgo y factores que más la empujan hacia arriba.

    Los factores son contribuciones SHAP calculadas por el propio LightGBM (pred_contrib), en
    escala log-odds: un 'efecto' positivo sube el riesgo y uno negativo lo baja.
    """
    esquema, modelo, _, _ = _cargar()
    X, notas = construir_fila(datos)
    p = float(modelo.predict_proba(X)[0, 1])

    columnas = esquema["categoricas"] + esquema["numericas"]
    contrib = modelo[-1].predict(modelo[:-1].transform(X), pred_contrib=True)[0][:-1]  # sin el sesgo
    orden = np.argsort(-contrib)
    def legible(v):
        v = v.item() if hasattr(v, "item") else v
        return round(v, 3) if isinstance(v, float) else v

    factores = [{"variable": columnas[i], "descripcion": DESCRIPCION.get(columnas[i], columnas[i]),
                 "valor": legible(X.iloc[0, i]), "efecto": round(float(contrib[i]), 3)}
                for i in orden[:n_factores] if contrib[i] > 0]

    return {"probabilidad_prorroga": round(p, 4), "nivel": _nivel(p, esquema["bandas"]),
            "factores": factores, "notas": notas,
            "modelo": f"{esquema['modelo']['registro']} v{esquema['modelo']['version']} ({esquema['modelo']['run']})"}


if __name__ == "__main__":
    ejemplos = json.load(open(CARPETA / "ejemplos.json", encoding="utf-8"))
    for ej in ejemplos:
        r = evaluar_contrato(ej)
        print(f"\nEjemplo (prorrogado real = {ej['prorrogado_real']}, "
              f"con todas las variables: {ej['probabilidad_con_todas_las_variables']:.1%}):")
        print(f"  {ej['tipo_de_contrato']} | {ej['modalidad_de_contratacion']} | ${ej['precio_base']:,.0f} | "
              f"{ej['duracion_pactada_dias']} días | {ej['departamento']}")
        print(f"  -> probabilidad {r['probabilidad_prorroga']:.1%}, nivel {r['nivel']}")
        for f in r["factores"]:
            print(f"     + {f['descripcion']}: {f['valor']}  (efecto {f['efecto']:+.2f})")
        for n in r["notas"]:
            print(f"     nota: {n}")
