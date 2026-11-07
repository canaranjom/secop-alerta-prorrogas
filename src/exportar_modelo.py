"""Exporta el modelo elegido desde MLflow para que el tablero (página Evaluar contrato) lo use sin servidor.

Qué hace:
    1. Busca el run elegido en el experimento 'secop-prorrogas' (por defecto, 'lgbm-base').
    2. Lo registra en el Model Registry de MLflow como 'secop-prorroga' (alias 'candidato').
    3. Guarda en models/ todo lo que necesita src/prediccion.py:
         modelo_prorroga.joblib   el pipeline completo (preparación + LightGBM)
         perfil_entidad.parquet   por entidad: nombre, tasa histórica de prórroga y sus valores más
                                  frecuentes en las demás variables (para completar el formulario)
         tasa_proveedor.parquet   por proveedor: tasa histórica de prórroga y fecha de creación
         esquema.json             valores válidos de cada lista, valores por defecto, bandas y métricas
         ejemplos.json            contratos reales de prueba (uno por banda) para probar el tablero

La historia de entidades y proveedores se calcula con TODOS los contratos terminados hasta la fecha
de corte (un contrato nuevo se firma hoy, así que toda esa historia ya es conocida). Se usa la misma
fórmula suavizada de src/features.py.

Uso (PowerShell, con el .venv activo):
    $env:MLFLOW_TRACKING_URI = "http://<IP_EC2>:8050"
    python src/exportar_modelo.py                       # exporta y registra lgbm-base
    python src/exportar_modelo.py --run lgbm-base --sin-registro
"""
import argparse
import json
import os
import sys
from pathlib import Path

import joblib
import mlflow
import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from features import CATEGORICAS, NUMERICAS, OBJETIVO  # noqa: E402

EXPERIMENTO = "secop-prorrogas"
NOMBRE_REGISTRO = "secop-prorroga"
SALIDA = Path("models")
BANDAS = {"bajo": [0.0, 0.25], "medio": [0.25, 0.50], "alto": [0.50, 1.0]}

# Lo que el usuario escribe en el formulario de la maqueta (docs/index.html).
CAMPOS_FORMULARIO = ["codigo_entidad", "tipo_de_contrato", "modalidad_de_contratacion", "precio_base",
                     "duracion_pactada_dias", "departamento", "orden", "sector", "fecha_de_firma"]
# Variables que se completan con lo más frecuente en la entidad cuando el formulario no las pide.
DE_LA_ENTIDAD = ["justificacion_modalidad_de", "rama", "entidad_centralizada", "destino_gasto",
                 "origen_de_los_recursos", "el_contrato_puede_ser_prorrogado", "es_pyme", "es_grupo",
                 "habilita_pago_adelantado", "obligaci_n_ambiental", "reversion", "espostconflicto",
                 "tipodocproveedor", "segmento_unspsc", "departamento", "orden", "sector",
                 "tiene_recursos_propios", "tiene_pgn", "tiene_sgp", "tiene_regalias",
                 "dias_firma_a_inicio", "prov_antiguedad_dias", "proc_proveedores_invitados",
                 "proc_respuestas_al_procedimiento", "proc_conteo_de_respuestas_a_ofertas",
                 "proc_numero_de_lotes"]


def buscar_run(client, nombre):
    exp = client.get_experiment_by_name(EXPERIMENTO)
    runs = client.search_runs([exp.experiment_id], filter_string=f"attributes.run_name = '{nombre}'",
                              order_by=["attributes.start_time DESC"], max_results=1)
    if not runs:
        sys.exit(f"No encontré el run '{nombre}' en el experimento '{EXPERIMENTO}'.")
    return runs[0]


def historia_actual(m, llave, prior, suavizado):
    """Tasa de prórroga suavizada con todos los contratos terminados (misma fórmula de features.py)."""
    validos = m["fecha_de_fin_del_contrato"].notna() & (m["fecha_de_fin_del_contrato"] >= m["fecha_de_firma"])
    g = m[validos].groupby(llave, observed=True)[OBJETIVO].agg(n_hist="size", k="sum")
    g["tasa_hist"] = (g["k"] + suavizado * prior) / (g["n_hist"] + suavizado)
    return g.drop(columns="k")


def mas_frecuente(s):
    v = s.mode(dropna=True)
    return v.iloc[0] if len(v) else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="lgbm-base", help="Nombre del run de MLflow a exportar")
    ap.add_argument("--sin-registro", action="store_true", help="No registrar en el Model Registry")
    args = ap.parse_args()
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        sys.exit('Falta la dirección de MLflow. En PowerShell:  $env:MLFLOW_TRACKING_URI = "http://<IP_EC2>:8050"')

    p = yaml.safe_load(open("params.yaml", encoding="utf-8"))["features"]
    resumen = json.load(open("data/processed/features_resumen.json", encoding="utf-8"))
    prior, suavizado = resumen["prior_tasa_train"], p["suavizado_m"]
    SALIDA.mkdir(exist_ok=True)

    # --- 1. Modelo desde MLflow ---
    client = mlflow.MlflowClient()
    run = buscar_run(client, args.run)
    uri = f"runs:/{run.info.run_id}/modelo"
    print(f"Descargando {args.run} ({run.info.run_id}) ...")
    modelo = mlflow.sklearn.load_model(uri)
    joblib.dump(modelo, SALIDA / "modelo_prorroga.joblib", compress=3)

    version = None
    if not args.sin_registro:
        mv = mlflow.register_model(uri, NOMBRE_REGISTRO)
        client.set_registered_model_alias(NOMBRE_REGISTRO, "candidato", mv.version)
        client.set_model_version_tag(NOMBRE_REGISTRO, mv.version, "run", args.run)
        version = mv.version
        print(f"Registrado como '{NOMBRE_REGISTRO}' versión {version} (alias 'candidato').")

    # --- 2. Historia de entidades y proveedores ---
    print("Calculando la historia de entidades y proveedores ...")
    m = pd.read_parquet("data/processed/contratos_modelo.parquet",
                        columns=["codigo_entidad", "codigo_proveedor", "fecha_de_firma",
                                 "fecha_de_fin_del_contrato", "prov_fecha_creacion", OBJETIVO])
    f = pd.read_parquet("data/processed/features.parquet")

    perfil = f.sort_values("fecha_de_firma").groupby("codigo_entidad").agg(
        nombre_entidad=("nombre_entidad", "last"), contratos=("id_contrato", "size"),
        **{c: (c, mas_frecuente) for c in DE_LA_ENTIDAD})
    perfil = perfil.join(historia_actual(m, "codigo_entidad", prior, suavizado), how="left")
    perfil["n_hist"] = perfil["n_hist"].fillna(0).astype(int)
    perfil["tasa_hist"] = perfil["tasa_hist"].fillna(prior)
    perfil.reset_index().to_parquet(SALIDA / "perfil_entidad.parquet", index=False)

    prov = historia_actual(m, "codigo_proveedor", prior, suavizado)
    fecha_creacion = pd.to_datetime(m.groupby("codigo_proveedor")["prov_fecha_creacion"].first(), errors="coerce")
    prov = prov.join(fecha_creacion.rename("fecha_creacion"), how="left")
    prov.reset_index().to_parquet(SALIDA / "tasa_proveedor.parquet", index=False)

    # --- 3. Esquema: listas válidas, valores por defecto y métricas ---
    train = f[f["split"] == "train"]
    esquema = {
        "modelo": {"run": args.run, "run_id": run.info.run_id, "registro": NOMBRE_REGISTRO,
                   "version": version, "metricas": {k: round(v, 4) for k, v in run.data.metrics.items()}},
        "campos_formulario": CAMPOS_FORMULARIO,
        "categoricas": CATEGORICAS,
        "numericas": NUMERICAS,
        "valores": {c: train[c].value_counts().index.tolist() for c in CATEGORICAS},
        "por_defecto": {**{c: train[c].mode().iloc[0] for c in CATEGORICAS},
                        **{c: float(train[c].median()) for c in NUMERICAS}},
        "prior": prior,
        "suavizado_m": suavizado,
        "duracion_max_dias": p["duracion_max_dias"],
        "bandas": BANDAS,
    }
    json.dump(esquema, open(SALIDA / "esquema.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2,
              default=str)

    # --- 4. Ejemplos reales de prueba, uno por banda ---
    test = f[f["split"] == "test"].sample(20000, random_state=42)
    test = test.assign(probabilidad=modelo.predict_proba(test[CATEGORICAS + NUMERICAS])[:, 1])
    precio = 10 ** test["log_precio_base"]
    test = test.assign(precio_base=precio.round(0), fecha_de_firma=test["fecha_de_firma"].dt.strftime("%Y-%m-%d"))
    ejemplos = []
    for banda, (lo, hi) in BANDAS.items():
        cand = test[(test["probabilidad"] >= lo) & (test["probabilidad"] < hi) & test["precio_base"].notna()]
        if len(cand):
            fila = cand.iloc[0]
            # La probabilidad con las 40 variables reales; en el tablero puede variar un poco porque
            # las variables que no pide el formulario se completan con el perfil de la entidad.
            ejemplos.append({"banda_con_todas_las_variables": banda,
                             "probabilidad_con_todas_las_variables": round(float(fila["probabilidad"]), 3),
                             "prorrogado_real": int(fila[OBJETIVO]),
                             **{c: (None if pd.isna(fila[c]) else fila[c]) for c in CAMPOS_FORMULARIO}})
    json.dump(ejemplos, open(SALIDA / "ejemplos.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2,
              default=str)

    print("\nArchivos en models/:")
    for a in sorted(SALIDA.iterdir()):
        print(f"  {a.name:28s} {a.stat().st_size / 1e6:7.1f} MB")
    print("\nPrueba rápida:  python src/prediccion.py")


if __name__ == "__main__":
    main()
