"""Construye la tabla de variables del modelo y la partición temporal (entrenamiento / validación / prueba).

Regla de oro: solo entran variables que se conocen AL FIRMAR el contrato (ver reports/hipotesis_variables.md).

Variables nuevas (sección 3 de las hipótesis):
    tasa_hist_entidad      tasa de prórroga de la entidad calculada SOLO con contratos que ya habían
                           terminado antes de la firma (sin fuga temporal), suavizada hacia la tasa global.
    tasa_hist_proveedor    lo mismo para el proveedor.
    tipo_x_tramo_precio    interacción tipo de contrato x tramo de precio base.
    supera_12_meses        duración pactada mayor a 365 días.
    cruza_vigencia         el plazo pactado termina después del 31 de diciembre del año de firma.

Uso:  python src/features.py
Salida: data/processed/features.parquet  y  data/processed/features_resumen.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ENTRADA = Path("data/processed/contratos_modelo.parquet")
OUT = Path("data/processed")
OBJETIVO = "prorrogado"

# Variables categóricas que se conocen al firmar.
CATEGORICAS = [
    "tipo_de_contrato", "modalidad_de_contratacion", "justificacion_modalidad_de", "sector",
    "orden", "rama", "entidad_centralizada", "departamento", "destino_gasto",
    "origen_de_los_recursos", "el_contrato_puede_ser_prorrogado", "es_pyme", "es_grupo",
    "habilita_pago_adelantado", "obligaci_n_ambiental", "reversion", "espostconflicto",
    "tipodocproveedor", "segmento_unspsc", "tramo_precio", "tipo_x_tramo_precio",
]
# Variables numéricas que se conocen al firmar.
NUMERICAS = [
    "log_precio_base", "duracion_pactada_dias", "supera_12_meses", "cruza_vigencia",
    "mes_firma", "dias_firma_a_inicio", "prov_antiguedad_dias",
    "proc_proveedores_invitados", "proc_respuestas_al_procedimiento",
    "proc_conteo_de_respuestas_a_ofertas", "proc_numero_de_lotes",
    "tiene_recursos_propios", "tiene_pgn", "tiene_sgp", "tiene_regalias",
    "tasa_hist_entidad", "n_hist_entidad", "tasa_hist_proveedor", "n_hist_proveedor",
]
# Columnas de apoyo (identificación y tablero); NO son entradas del modelo.
APOYO = ["id_contrato", "fecha_de_firma", "codigo_entidad", "nombre_entidad", "split"]


def tasa_historica(df, llave, prior, m):
    """Para cada contrato, cuántos contratos de la misma `llave` habían TERMINADO antes de su firma
    y qué fracción fue prorrogada. Se suaviza con m contratos "virtuales" a la tasa `prior`:
        tasa = (prorrogados_previos + m * prior) / (terminados_previos + m)
    Así una entidad con 1 contrato previo no queda con tasa 0 % o 100 %.
    """
    # 1) Historia: por llave y fecha de fin, cuántos terminaron y cuántos fueron prorrogados (acumulado).
    #    Se descartan los registros con fin anterior a la firma (0,1 %, errores de captura): si no,
    #    el propio resultado del contrato podría colarse en su historia.
    validos = df["fecha_de_fin_del_contrato"].notna() & (df["fecha_de_fin_del_contrato"] >= df["fecha_de_firma"])
    fin = (df[validos]
             .groupby([llave, "fecha_de_fin_del_contrato"], observed=True)[OBJETIVO]
             .agg(n="size", k="sum").reset_index()
             .sort_values([llave, "fecha_de_fin_del_contrato"]))
    fin["n_prev"] = fin.groupby(llave)["n"].cumsum()
    fin["k_prev"] = fin.groupby(llave)["k"].cumsum()
    fin = fin.rename(columns={"fecha_de_fin_del_contrato": "t"}).sort_values("t")

    # 2) Consulta: para cada firma, el último acumulado con fecha de fin ESTRICTAMENTE anterior.
    q = df[[llave, "fecha_de_firma"]].reset_index().sort_values("fecha_de_firma")
    r = pd.merge_asof(q, fin[[llave, "t", "n_prev", "k_prev"]], left_on="fecha_de_firma",
                      right_on="t", by=llave, direction="backward", allow_exact_matches=False)
    r = r.set_index("index").reindex(df.index)
    n_prev = r["n_prev"].fillna(0)
    k_prev = r["k_prev"].fillna(0)
    return (k_prev + m * prior) / (n_prev + m), n_prev


def main():
    p = yaml.safe_load(open("params.yaml", encoding="utf-8"))["features"]
    df = pd.read_parquet(ENTRADA)

    # --- Partición temporal: se entrena con el pasado y se evalúa con el futuro ---
    f = df["fecha_de_firma"]
    df["split"] = np.select(
        [f < pd.Timestamp(p["inicio_validacion"]), f < pd.Timestamp(p["inicio_prueba"])],
        ["train", "valid"], default="test")
    prior = df.loc[df["split"] == "train", OBJETIVO].mean()  # tasa global, solo del entrenamiento

    # --- Monto y duración ---
    df["tramo_precio"] = pd.cut(df["log_precio_base"], bins=[-np.inf, 7, 8, 9, np.inf],
                                labels=["<10M", "10M-100M", "100M-1.000M", ">1.000M"]).astype(str)
    df["tipo_x_tramo_precio"] = df["tipo_de_contrato"] + " | " + df["tramo_precio"]
    dur = df["duracion_pactada_dias"]
    df["supera_12_meses"] = (dur > 365).astype(int)
    fin_pactado = df["fecha_de_firma"] + pd.to_timedelta(dur.clip(upper=3650).fillna(0), unit="D")
    df["cruza_vigencia"] = (fin_pactado.dt.year > df["fecha_de_firma"].dt.year).astype(int)
    df["duracion_pactada_dias"] = dur.clip(upper=p["duracion_max_dias"])  # percentil 99

    # --- Otras numéricas: recortar valores absurdos ---
    df["dias_firma_a_inicio"] = df["dias_firma_a_inicio"].clip(-30, 180)
    df["prov_antiguedad_dias"] = df["prov_antiguedad_dias"].clip(lower=0)
    for c in ["proc_proveedores_invitados", "proc_respuestas_al_procedimiento",
              "proc_conteo_de_respuestas_a_ofertas", "proc_numero_de_lotes"]:
        df[c] = df[c].clip(upper=50)
    df["tiene_recursos_propios"] = (df["recursos_propios"] > 0).astype(int)
    df["tiene_pgn"] = (df["presupuesto_general_de_la_nacion_pgn"] > 0).astype(int)
    df["tiene_sgp"] = (df["sistema_general_de_participaciones"] > 0).astype(int)
    df["tiene_regalias"] = (df["sistema_general_de_regal_as"] > 0).astype(int)

    # Segmento UNSPSC (2 primeros dígitos del código de categoría): 'V1.72151800' -> '72'
    df["segmento_unspsc"] = df["codigo_de_categoria_principal"].str.extract(r"\.(\d{2})")[0].fillna("NA")

    # --- Historia sin fuga ---
    df["tasa_hist_entidad"], df["n_hist_entidad"] = tasa_historica(df, "codigo_entidad", prior, p["suavizado_m"])
    df["tasa_hist_proveedor"], df["n_hist_proveedor"] = tasa_historica(df, "codigo_proveedor", prior, p["suavizado_m"])

    for c in CATEGORICAS:
        df[c] = df[c].fillna("No Definido").astype(str)

    salida = df[APOYO + CATEGORICAS + NUMERICAS + [OBJETIVO]]
    salida.to_parquet(OUT / "features.parquet", index=False)

    resumen = {
        "filas": len(salida),
        "prior_tasa_train": round(prior, 4),
        "split": {s: {"filas": int((salida["split"] == s).sum()),
                      "tasa_prorroga": round(salida.loc[salida["split"] == s, OBJETIVO].mean(), 4)}
                  for s in ["train", "valid", "test"]},
        "n_categoricas": len(CATEGORICAS),
        "n_numericas": len(NUMERICAS),
        "contratos_con_historia_entidad": round((salida["n_hist_entidad"] > 0).mean(), 4),
    }
    json.dump(resumen, open(OUT / "features_resumen.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
