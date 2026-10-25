"""Descarga desde la API Socrata de datos.gov.co los tres conjuntos de SECOP II del proyecto.

- jbjy-vk9h  SECOP II - Contratos Electrónicos   (tabla principal, 1 fila = 1 contrato)
- p6dx-8zbt  SECOP II - Procesos de Contratación (competencia y precio base del proceso)
- qmzu-gj57  SECOP II - Proveedores Registrados  (antigüedad y tamaño del proveedor)

Por responsabilidad con los datos solo se piden columnas sin información personal:
no se descargan nombres ni documentos de personas naturales, ni cuentas bancarias.

Uso:  python src/download_secop.py
"""
import io
import os
import time
from pathlib import Path

import pandas as pd
import requests
import yaml

BASE = "https://www.datos.gov.co/resource/{id}.csv"
RAW = Path("data/raw")
# Un token de aplicación de datos.gov.co evita el límite de peticiones (opcional).
APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN")

CONTRATOS_COLS = [
    "id_contrato", "proceso_de_compra", "codigo_entidad", "nombre_entidad", "nit_entidad",
    "departamento", "ciudad", "orden", "sector", "rama", "entidad_centralizada",
    "estado_contrato", "codigo_de_categoria_principal", "tipo_de_contrato",
    "modalidad_de_contratacion", "justificacion_modalidad_de", "objeto_del_contrato",
    "fecha_de_firma", "fecha_de_inicio_del_contrato", "fecha_de_fin_del_contrato",
    "duraci_n_del_contrato", "codigo_proveedor", "tipodocproveedor", "es_grupo", "es_pyme",
    "habilita_pago_adelantado", "liquidaci_n", "obligaci_n_ambiental", "obligaciones_postconsumo",
    "reversion", "origen_de_los_recursos", "destino_gasto", "espostconflicto",
    "valor_del_contrato", "valor_de_pago_adelantado", "valor_facturado", "valor_pagado",
    "valor_pendiente_de_ejecucion", "presupuesto_general_de_la_nacion_pgn",
    "sistema_general_de_participaciones", "sistema_general_de_regal_as",
    "recursos_propios_alcald_as_gobernaciones_y_resguardos_ind_genas_",
    "recursos_de_credito", "recursos_propios", "el_contrato_puede_ser_prorrogado",
    "dias_adicionados", "ultima_actualizacion",
]

PROCESOS_COLS = [
    "id_del_portafolio", "id_del_proceso", "fecha_de_publicacion_del", "fecha_de_recepcion_de",
    "fecha_adjudicacion", "precio_base", "duracion", "unidad_de_duracion",
    "proveedores_invitados", "proveedores_con_invitacion", "visualizaciones_del",
    "proveedores_que_manifestaron", "respuestas_al_procedimiento", "conteo_de_respuestas_a_ofertas",
    "proveedores_unicos_con", "numero_de_lotes", "subtipo_de_contrato", "estado_resumen",
]

PROVEEDORES_COLS = [
    "codigo", "es_entidad", "es_grupo", "esta_activa", "fecha_creacion",
    "codigo_categoria_principal", "departamento", "municipio", "tipo_empresa", "espyme",
    "tama_o_entidad",
]


def fetch(dataset_id, columns, where=None, order=None, page_size=200_000):
    """Descarga paginada (CSV) de un conjunto Socrata; reintenta ante errores transitorios."""
    headers = {"X-App-Token": APP_TOKEN} if APP_TOKEN else {}
    frames, offset = [], 0
    while True:
        params = {"$select": ",".join(columns), "$order": order or columns[0],
                  "$limit": page_size, "$offset": offset}
        if where:
            params["$where"] = where
        for intento in range(5):
            try:
                r = requests.get(BASE.format(id=dataset_id), params=params,
                                 headers=headers, timeout=600)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                espera = 2 ** intento * 5
                print(f"  {dataset_id} offset={offset}: {e} -> reintento en {espera}s", flush=True)
                time.sleep(espera)
        else:
            raise RuntimeError(f"No se pudo descargar {dataset_id} offset={offset}")
        page = pd.read_csv(io.StringIO(r.text), dtype=str)
        frames.append(page)
        offset += len(page)
        print(f"  {dataset_id}: {offset:,} filas", flush=True)
        if len(page) < page_size:
            break
    return pd.concat(frames, ignore_index=True)


def main():
    p = yaml.safe_load(open("params.yaml", encoding="utf-8"))["download"]
    RAW.mkdir(parents=True, exist_ok=True)

    print("Contratos...")
    contratos = fetch(
        "jbjy-vk9h", CONTRATOS_COLS, order="id_contrato", page_size=p["page_size"],
        where=f"fecha_de_firma between '{p['fecha_firma_desde']}' and '{p['fecha_firma_hasta']}T23:59:59'",
    )
    contratos.to_parquet(RAW / "contratos.parquet", index=False)

    print("Procesos...")
    procesos = fetch(
        "p6dx-8zbt", PROCESOS_COLS, order="id_del_proceso", page_size=p["page_size"],
        # "Seleccionado" cubre la contratación directa, que casi nunca queda marcada adjudicado='Si'.
        where=(f"(adjudicado = 'Si' OR estado_del_procedimiento = 'Seleccionado') AND fecha_de_publicacion_del between "
               f"'{p['fecha_publicacion_proceso_desde']}' and '{p['fecha_firma_hasta']}T23:59:59'"),
    )
    procesos.to_parquet(RAW / "procesos.parquet", index=False)

    print("Proveedores...")
    proveedores = fetch("qmzu-gj57", PROVEEDORES_COLS, order="codigo", page_size=p["page_size"])
    # Solo se guardan los proveedores que aparecen en los contratos descargados.
    proveedores = proveedores[proveedores["codigo"].isin(contratos["codigo_proveedor"])]
    proveedores.to_parquet(RAW / "proveedores.parquet", index=False)

    print(f"Listo: {len(contratos):,} contratos, {len(procesos):,} procesos, "
          f"{len(proveedores):,} proveedores")


if __name__ == "__main__":
    main()
