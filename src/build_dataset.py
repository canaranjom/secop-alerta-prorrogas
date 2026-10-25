"""Cruza Contratos + Procesos + Proveedores y construye la variable objetivo `prorrogado`.

Llaves de cruce (verificadas con registros reales):
    contratos.proceso_de_compra  == procesos.id_del_portafolio   (CO1.BDOS.*)
    contratos.codigo_proveedor   == proveedores.codigo
    contratos.id_contrato        == facturas.id_contrato         (CO1.PCCNTR.*, no se usa en v1)

Uso:  python src/build_dataset.py
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAW = Path("data/raw")
OUT = Path("data/processed")

NUM_CONTRATOS = [
    "valor_del_contrato", "valor_de_pago_adelantado", "valor_facturado", "valor_pagado",
    "valor_pendiente_de_ejecucion", "presupuesto_general_de_la_nacion_pgn",
    "sistema_general_de_participaciones", "sistema_general_de_regal_as",
    "recursos_propios_alcald_as_gobernaciones_y_resguardos_ind_genas_",
    "recursos_de_credito", "recursos_propios", "dias_adicionados",
]
NUM_PROCESOS = [
    "precio_base", "duracion", "proveedores_invitados", "proveedores_con_invitacion",
    "visualizaciones_del", "proveedores_que_manifestaron", "respuestas_al_procedimiento",
    "conteo_de_respuestas_a_ofertas", "proveedores_unicos_con", "numero_de_lotes",
]
# Variables que solo se conocen DESPUÉS de firmar el contrato: no pueden ser entradas del modelo.
# valor_del_contrato se actualiza con las adiciones (si supera el precio base, la tasa de prórroga
# pasa de 2% a 36-53%); como monto del contrato se usa proc_precio_base, fijado antes de la firma.
FUGA = [
    "valor_facturado", "valor_pagado", "valor_pendiente_de_ejecucion", "estado_contrato",
    "liquidaci_n", "ultima_actualizacion", "dias_adicionados", "fecha_de_fin_del_contrato",
    "duracion_real_dias", "valor_del_contrato", "log_valor", "ratio_valor_precio_base",
]

DIAS_POR_UNIDAD = {"dia": 1, "semana": 7, "mes": 30, "año": 365, "ano": 365, "hora": 1 / 24}


def a_dias(texto):
    """'180 Dia(s)' / '6 Mes(es)' -> días. Devuelve NaN si no se reconoce."""
    if not isinstance(texto, str):
        return np.nan
    m = re.match(r"\s*([\d.,]+)\s*([A-Za-zñÑáéíóúÁÉÍÓÚ]+)", texto)
    if not m:
        return np.nan
    unidad = m.group(2).lower().replace("í", "i").replace("á", "a")
    for clave, factor in DIAS_POR_UNIDAD.items():
        if unidad.startswith(clave):
            return float(m.group(1).replace(",", ".")) * factor
    return np.nan


def main():
    corte = pd.Timestamp(yaml.safe_load(open("params.yaml", encoding="utf-8"))["build"]["fecha_corte"])
    c = pd.read_parquet(RAW / "contratos.parquet")
    pr = pd.read_parquet(RAW / "procesos.parquet")
    pv = pd.read_parquet(RAW / "proveedores.parquet")
    n0 = len(c)

    for col in NUM_CONTRATOS:
        c[col] = pd.to_numeric(c[col], errors="coerce")
    for col in ["fecha_de_firma", "fecha_de_inicio_del_contrato", "fecha_de_fin_del_contrato"]:
        c[col] = pd.to_datetime(c[col], errors="coerce")

    c = c.drop_duplicates("id_contrato")
    c = c[c["fecha_de_fin_del_contrato"].notna() & (c["fecha_de_fin_del_contrato"] <= corte)]
    c = c[c["valor_del_contrato"] > 0]

    # Objetivo: el contrato recibió una adición de tiempo (prórroga).
    c["prorrogado"] = (c["dias_adicionados"].fillna(0) > 0).astype(int)

    # Duración pactada al firmar (texto) vs duración observada (fin - inicio, incluye prórrogas).
    c["duracion_pactada_dias"] = c["duraci_n_del_contrato"].map(a_dias)
    c["duracion_real_dias"] = (c["fecha_de_fin_del_contrato"] - c["fecha_de_inicio_del_contrato"]).dt.days
    c["anio_firma"] = c["fecha_de_firma"].dt.year
    c["mes_firma"] = c["fecha_de_firma"].dt.month
    c["dias_firma_a_inicio"] = (c["fecha_de_inicio_del_contrato"] - c["fecha_de_firma"]).dt.days
    c["log_valor"] = np.log10(c["valor_del_contrato"])

    # Procesos: puede haber varias filas por portafolio (lotes); se conserva la de más respuestas.
    for col in NUM_PROCESOS:
        pr[col] = pd.to_numeric(pr[col], errors="coerce")
    pr = (pr.sort_values("respuestas_al_procedimiento", ascending=False)
            .drop_duplicates("id_del_portafolio")
            .add_prefix("proc_"))
    c = c.merge(pr, how="left", left_on="proceso_de_compra", right_on="proc_id_del_portafolio")
    c["ratio_valor_precio_base"] = c["valor_del_contrato"] / c["proc_precio_base"].where(c["proc_precio_base"] > 0)
    c["log_precio_base"] = np.log10(c["proc_precio_base"].where(c["proc_precio_base"] > 0))

    # Proveedores: antigüedad en SECOP II al momento de la firma.
    pv = pv.drop_duplicates("codigo").add_prefix("prov_")
    c = c.merge(pv, how="left", left_on="codigo_proveedor", right_on="prov_codigo")
    c["prov_antiguedad_dias"] = (c["fecha_de_firma"]
                                 - pd.to_datetime(c["prov_fecha_creacion"], errors="coerce")).dt.days

    OUT.mkdir(parents=True, exist_ok=True)
    c.to_parquet(OUT / "contratos_modelo.parquet", index=False)
    resumen = {
        "contratos_descargados": n0,
        "contratos_finales": len(c),
        "tasa_prorroga": round(c["prorrogado"].mean(), 4),
        "cruce_procesos": round(c["proc_id_del_portafolio"].notna().mean(), 4),
        "cruce_proveedores": round(c["prov_codigo"].notna().mean(), 4),
        "columnas_fuga": FUGA,
    }
    json.dump(resumen, open(OUT / "resumen.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
