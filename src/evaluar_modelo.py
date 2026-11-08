"""Figuras y tablas de evaluación del modelo elegido, para el reporte y para MLflow.

Genera en reports/figures/ (y sube al run elegido de MLflow, en la carpeta 'evaluacion/'):
    11_comparacion_modelos.png   métricas de validación de todos los runs del experimento
    12_calibracion.png           curva de calibración en validación y prueba (probabilidad dicha vs. real)
    13_shap_importancia.png      importancia global de las variables (promedio de |SHAP|)
    14_shap_numericas.png        dirección del efecto de las variables numéricas (beeswarm SHAP)
    comparacion_modelos.csv      tabla de métricas de todos los runs
    calibracion.csv              tabla de la curva de calibración
    shap_importancia.csv         importancia global de cada variable
    shap_categorias.csv          para cada variable categórica, qué categorías suben o bajan el riesgo

Los valores SHAP los calcula el propio LightGBM (pred_contrib=True): para cada contrato reparten la
predicción (en log-odds) entre las 40 variables. Se usa una muestra de validación.

Uso (PowerShell, con el .venv activo):
    $env:MLFLOW_TRACKING_URI = "http://<IP_EC2>:8050"
    python src/evaluar_modelo.py                    # run lgbm-base
    python src/evaluar_modelo.py --sin-mlflow       # solo genera los archivos locales
"""
import argparse
import os
import sys
from pathlib import Path

import joblib
import matplotlib
import mlflow
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from features import CATEGORICAS, NUMERICAS, OBJETIVO  # noqa: E402
from prediccion import DESCRIPCION  # noqa: E402

EXPERIMENTO = "secop-prorrogas"
SALIDA = Path("reports/figures")
MUESTRA_SHAP = 30000
SEMILLA = 42
AZUL, NARANJA, GRIS = "#1F5FAF", "#C2410C", "#8A94A6"


def comparar_runs(client):
    exp = client.get_experiment_by_name(EXPERIMENTO)
    filas = []
    for r in client.search_runs([exp.experiment_id], order_by=["attributes.start_time ASC"]):
        m = r.data.metrics
        filas.append({"run": r.info.run_name, "autor": r.data.tags.get("autor"),
                      "modelo": r.data.tags.get("modelo"),
                      **{k: m.get(k) for k in ["valid_auc", "valid_ap", "valid_brier", "valid_precision_top10",
                                               "valid_lift_top10", "test_auc", "test_ap",
                                               "test_precision_top10", "segundos_entrenamiento"]}})
    tabla = pd.DataFrame(filas).dropna(subset=["valid_auc"]).sort_values("valid_auc")
    tabla.to_csv(SALIDA / "comparacion_modelos.csv", index=False)

    fig, ejes = plt.subplots(1, 3, figsize=(13, 0.45 * len(tabla) + 1.6), sharey=True)
    for ax, (col, titulo) in zip(ejes, [("valid_auc", "AUC"), ("valid_ap", "Average precision"),
                                       ("valid_precision_top10", "Precisión en el 10 % de mayor riesgo")]):
        colores = [AZUL if "lgbm" in str(mo) else NARANJA if mo == "rf" else GRIS for mo in tabla["modelo"]]
        ax.barh(tabla["run"], tabla[col], color=colores)
        for y, v in enumerate(tabla[col]):
            ax.text(v, y, f" {v:.3f}", va="center", fontsize=9)
        ax.set_title(titulo, fontsize=11)
        ax.set_xlim(0, tabla[col].max() * 1.18)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Comparación de modelos en validación (abr–jun 2024)", fontsize=12)
    fig.tight_layout()
    fig.savefig(SALIDA / "11_comparacion_modelos.png", dpi=150)
    plt.close(fig)
    return tabla


def calibracion(modelo, df):
    cortes = [0, .05, .1, .15, .25, .35, .5, .7, 1]
    fig, ax = plt.subplots(figsize=(6, 5.5))
    ax.plot([0, 1], [0, 1], ls="--", color=GRIS, lw=1, label="Calibración perfecta")
    filas = []
    for split, color in [("valid", AZUL), ("test", NARANJA)]:
        d = df[df["split"] == split]
        p = modelo.predict_proba(d[CATEGORICAS + NUMERICAS])[:, 1]
        g = (pd.DataFrame({"p": p, "y": d[OBJETIVO].to_numpy(), "tramo": pd.cut(p, cortes)})
               .groupby("tramo", observed=True).agg(contratos=("y", "size"), predicho=("p", "mean"),
                                                    real=("y", "mean")).reset_index())
        g.insert(0, "split", split)
        filas.append(g)
        ax.plot(g["predicho"], g["real"], marker="o", color=color,
                label=f"{'Validación' if split == 'valid' else 'Prueba'} (Brier {np.mean((p - d[OBJETIVO]) ** 2):.3f})")
    for corte in (0.25, 0.5):
        ax.axvline(corte, color=GRIS, lw=0.6, ls=":")
    ax.text(0.125, 0.93, "bajo", ha="center", color=GRIS)
    ax.text(0.375, 0.93, "medio", ha="center", color=GRIS)
    ax.text(0.75, 0.93, "alto", ha="center", color=GRIS)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Probabilidad de prórroga que da el modelo",
           ylabel="Fracción de contratos que se prorrogaron")
    ax.set_title("Calibración de LightGBM", fontsize=12)
    ax.legend(loc="lower right", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SALIDA / "12_calibracion.png", dpi=150)
    plt.close(fig)
    tabla = pd.concat(filas)
    tabla["tramo"] = tabla["tramo"].astype(str)
    tabla.to_csv(SALIDA / "calibracion.csv", index=False)
    return tabla


def shap_global(modelo, df):
    import shap

    d = df[df["split"] == "valid"].sample(MUESTRA_SHAP, random_state=SEMILLA)
    X = d[CATEGORICAS + NUMERICAS]
    contrib = modelo[-1].predict(modelo[:-1].transform(X), pred_contrib=True)[:, :-1]
    columnas = CATEGORICAS + NUMERICAS

    imp = (pd.DataFrame({"variable": columnas, "descripcion": [DESCRIPCION.get(c, c) for c in columnas],
                         "tipo": ["categórica"] * len(CATEGORICAS) + ["numérica"] * len(NUMERICAS),
                         "shap_medio_abs": np.abs(contrib).mean(axis=0)})
             .sort_values("shap_medio_abs", ascending=False))
    imp["porcentaje"] = imp["shap_medio_abs"] / imp["shap_medio_abs"].sum()
    imp.to_csv(SALIDA / "shap_importancia.csv", index=False)

    top = imp.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top["descripcion"], top["shap_medio_abs"],
            color=[AZUL if t == "numérica" else NARANJA for t in top["tipo"]])
    for y, (v, pct) in enumerate(zip(top["shap_medio_abs"], top["porcentaje"])):
        ax.text(v, y, f" {pct:.0%}", va="center", fontsize=9)
    ax.set_xlabel("Promedio de |SHAP| (log-odds)")
    ax.set_title("Variables que más pesan en la predicción (15 de 40)", fontsize=12)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=AZUL), plt.Rectangle((0, 0), 1, 1, color=NARANJA)],
              labels=["Numérica", "Categórica"], loc="lower right", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(SALIDA / "13_shap_importancia.png", dpi=150)
    plt.close(fig)

    # Dirección del efecto en las numéricas: color = valor de la variable (rojo alto, azul bajo).
    idx_num = [columnas.index(c) for c in NUMERICAS]
    orden = imp[imp["tipo"] == "numérica"]["variable"].head(12).tolist()
    sel = [NUMERICAS.index(c) for c in orden]
    plt.figure()
    shap.summary_plot(contrib[:, idx_num][:, sel], X[NUMERICAS].iloc[:, sel].astype(float),
                      feature_names=[DESCRIPCION.get(c, c) for c in orden], show=False, max_display=12,
                      plot_size=(9, 6))
    plt.title("Efecto de las variables numéricas (rojo = valor alto)", fontsize=12)
    plt.tight_layout()
    plt.savefig(SALIDA / "14_shap_numericas.png", dpi=150)
    plt.close("all")

    # Categóricas: efecto promedio de cada categoría (positivo = sube el riesgo).
    filas = []
    for i, c in enumerate(CATEGORICAS):
        g = pd.DataFrame({"categoria": X[c].to_numpy(), "shap": contrib[:, i]}).groupby("categoria")["shap"]
        res = g.agg(["size", "mean"]).rename(columns={"size": "contratos", "mean": "shap_medio"})
        res = res[res["contratos"] >= 100].reset_index()
        res.insert(0, "variable", c)
        filas.append(res)
    cat = pd.concat(filas).sort_values(["variable", "shap_medio"], ascending=[True, False])
    cat.to_csv(SALIDA / "shap_categorias.csv", index=False)
    return imp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="lgbm-base", help="Run de MLflow donde se suben las figuras")
    ap.add_argument("--sin-mlflow", action="store_true", help="No subir nada a MLflow")
    args = ap.parse_args()
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        sys.exit('Falta la dirección de MLflow. En PowerShell:  $env:MLFLOW_TRACKING_URI = "http://<IP_EC2>:8050"')
    SALIDA.mkdir(parents=True, exist_ok=True)

    client = mlflow.MlflowClient()
    modelo = joblib.load("models/modelo_prorroga.joblib")
    df = pd.read_parquet("data/processed/features.parquet")

    print("1/3 Comparación de modelos ...")
    tabla = comparar_runs(client)
    print(tabla[["run", "valid_auc", "valid_ap", "valid_precision_top10"]].round(3).to_string(index=False))
    print("\n2/3 Calibración ...")
    print(calibracion(modelo, df).round(3).to_string(index=False))
    print("\n3/3 SHAP (muestra de validación) ...")
    imp = shap_global(modelo, df)
    print(imp.head(15)[["descripcion", "shap_medio_abs", "porcentaje"]].round(3).to_string(index=False))

    archivos = ["11_comparacion_modelos.png", "12_calibracion.png", "13_shap_importancia.png",
                "14_shap_numericas.png", "comparacion_modelos.csv", "calibracion.csv",
                "shap_importancia.csv", "shap_categorias.csv"]
    if not args.sin_mlflow:
        exp = client.get_experiment_by_name(EXPERIMENTO)
        run = client.search_runs([exp.experiment_id], filter_string=f"attributes.run_name = '{args.run}'",
                                 order_by=["attributes.start_time DESC"], max_results=1)[0]
        for a in archivos:
            client.log_artifact(run.info.run_id, str(SALIDA / a), artifact_path="evaluacion")
        print(f"\nSubido a MLflow: run '{args.run}' -> Artifacts -> evaluacion/")
    print("Archivos en reports/figures/: " + ", ".join(archivos))


if __name__ == "__main__":
    main()
