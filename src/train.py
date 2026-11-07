"""Entrena un modelo de prórroga y registra el experimento en MLflow (servidor en la EC2).

Un solo script para todo el equipo: la línea base, los experimentos de Julián y los modelos finales.

Antes de correrlo (PowerShell, con el .venv activo):
    $env:MLFLOW_TRACKING_URI = "http://<IP_EC2>:8050"

Ejemplos:
    python src/train.py --modelo logistica --autor Camilo
    python src/train.py --modelo logistica --autor Julian --param C=0.1
    python src/train.py --modelo rf   --autor Julian --param n_estimators=200 --param max_depth=12
    python src/train.py --modelo lgbm --autor Julian --param num_leaves=63 --param learning_rate=0.05

Métricas (en validación y en prueba):
    auc              capacidad de ordenar: qué tan seguido un prorrogado queda por encima de uno no prorrogado.
    ap               average precision (área bajo la curva precisión-exhaustividad); más exigente con clases desbalanceadas.
    brier, log_loss  calidad de la probabilidad (más bajo es mejor).
    precision_top10  de los 10 % de contratos con más riesgo (los que el tablero marcaría en alerta), cuántos se prorrogaron.
    recall_top10     de todos los prorrogados, qué fracción cae en ese 10 % de alerta.
    lift_top10       cuántas veces mejor que escoger contratos al azar.
"""
import argparse
import ast
import os
import sys
import time

import mlflow
import numpy as np
import pandas as pd
import yaml
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

sys.path.insert(0, os.path.dirname(__file__))
from features import CATEGORICAS, NUMERICAS, OBJETIVO  # noqa: E402

DATOS = "data/processed/features.parquet"
EXPERIMENTO = "secop-prorrogas"
SEMILLA = 42

# Hiperparámetros por defecto de cada modelo (se pueden cambiar con --param clave=valor).
DEFAULTS = {
    "logistica": {"C": 1.0, "class_weight": None, "max_iter": 300},
    "rf": {"n_estimators": 200, "max_depth": 14, "min_samples_leaf": 50, "max_features": "sqrt",
           "class_weight": None},
    "lgbm": {"n_estimators": 600, "learning_rate": 0.05, "num_leaves": 63, "min_child_samples": 100,
             "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "reg_lambda": 1.0},
}
# Fracción del conjunto de entrenamiento que se usa por defecto (para que corra en minutos).
MUESTRA_DEFAULT = {"logistica": 0.5, "rf": 0.3, "lgbm": 1.0}


def construir_modelo(nombre, hp):
    if nombre == "logistica":
        prep = ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=200), CATEGORICAS),
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("esc", StandardScaler())]), NUMERICAS),
        ])
        return Pipeline([("prep", prep), ("clf", LogisticRegression(random_state=SEMILLA, **hp))]), {}

    # Modelos de árboles: las categorías se codifican como enteros (no necesitan one-hot ni escalar).
    prep = ColumnTransformer([
        ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1,
                               encoded_missing_value=-1), CATEGORICAS),
        ("num", SimpleImputer(strategy="median"), NUMERICAS),
    ])
    if nombre == "rf":
        clf = RandomForestClassifier(random_state=SEMILLA, n_jobs=-1, **hp)
        return Pipeline([("prep", prep), ("clf", clf)]), {}
    if nombre == "lgbm":
        from lightgbm import LGBMClassifier
        clf = LGBMClassifier(random_state=SEMILLA, n_jobs=-1, verbose=-1, **hp)
        # Las primeras columnas (las categóricas) se tratan como categorías nativas de LightGBM.
        return Pipeline([("prep", prep), ("clf", clf)]), {"clf__categorical_feature": list(range(len(CATEGORICAS)))}
    raise ValueError(f"Modelo desconocido: {nombre}")


def metricas(y, p, prefijo):
    k = int(len(p) * 0.10)
    top = np.argsort(-p)[:k]
    prec_top = y[top].mean()
    return {
        f"{prefijo}_auc": roc_auc_score(y, p),
        f"{prefijo}_ap": average_precision_score(y, p),
        f"{prefijo}_brier": brier_score_loss(y, p),
        f"{prefijo}_log_loss": log_loss(y, p),
        f"{prefijo}_precision_top10": prec_top,
        f"{prefijo}_recall_top10": y[top].sum() / y.sum(),
        f"{prefijo}_lift_top10": prec_top / y.mean(),
    }


def leer_param(texto):
    clave, valor = texto.split("=", 1)
    try:
        valor = ast.literal_eval(valor)      # números, None, True/False
    except (ValueError, SyntaxError):
        pass                                 # texto, por ejemplo "sqrt" o "balanced"
    return clave, valor


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", required=True, choices=list(DEFAULTS))
    ap.add_argument("--autor", required=True, help="Nombre de quien corre el experimento (queda en MLflow)")
    ap.add_argument("--param", action="append", default=[], help="Hiperparámetro clave=valor (repetible)")
    ap.add_argument("--muestra", type=float, default=None, help="Fracción del entrenamiento a usar (0-1)")
    ap.add_argument("--nombre", default=None, help="Nombre del run (opcional)")
    ap.add_argument("--nota", default="", help="Qué se quiere probar con este run (queda en MLflow)")
    args = ap.parse_args()

    if not os.environ.get("MLFLOW_TRACKING_URI"):
        sys.exit('Falta la dirección de MLflow. En PowerShell:  $env:MLFLOW_TRACKING_URI = "http://<IP_EC2>:8050"')

    hp = dict(DEFAULTS[args.modelo])
    hp.update(dict(leer_param(t) for t in args.param))
    muestra = args.muestra if args.muestra is not None else MUESTRA_DEFAULT[args.modelo]

    df = pd.read_parquet(DATOS)
    train = df[df["split"] == "train"]
    if muestra < 1:
        train = train.sample(frac=muestra, random_state=SEMILLA)
    valid, test = df[df["split"] == "valid"], df[df["split"] == "test"]
    X = lambda d: d[CATEGORICAS + NUMERICAS]  # noqa: E731

    modelo, fit_kw = construir_modelo(args.modelo, hp)

    mlflow.set_experiment(EXPERIMENTO)
    nombre = args.nombre or f"{args.modelo}-{args.autor.lower()}"
    with mlflow.start_run(run_name=nombre):
        mlflow.set_tags({"autor": args.autor, "modelo": args.modelo, "nota": args.nota})
        # También se registran los parámetros de las variables (params.yaml), p. ej. suavizado_m.
        p_feat = yaml.safe_load(open("params.yaml", encoding="utf-8"))["features"]
        mlflow.log_params({**hp, **{f"feat_{k}": v for k, v in p_feat.items()},
                           "modelo": args.modelo, "muestra_train": muestra,
                           "filas_train": len(train), "n_variables": len(CATEGORICAS) + len(NUMERICAS)})

        print(f"Entrenando {args.modelo} con {len(train):,} contratos y {hp} ...")
        t0 = time.time()
        modelo.fit(X(train), train[OBJETIVO], **fit_kw)
        segundos = time.time() - t0

        res = {"segundos_entrenamiento": segundos}
        for nombre_split, d in [("valid", valid), ("test", test)]:
            res.update(metricas(d[OBJETIVO].to_numpy(), modelo.predict_proba(X(d))[:, 1], nombre_split))
        mlflow.log_metrics(res)
        # cloudpickle: el formato por defecto de MLflow 3 (skops) rechaza tipos de numpy/LightGBM.
        mlflow.sklearn.log_model(modelo, name="modelo", input_example=X(valid).head(5),
                                 serialization_format="cloudpickle")

        print(f"\nListo en {segundos:.0f} s. Resultados:")
        for k, v in res.items():
            print(f"  {k:28s} {v:.4f}")
        print(f"\nVer en MLflow: {os.environ['MLFLOW_TRACKING_URI']}  (experimento '{EXPERIMENTO}', run '{nombre}')")


if __name__ == "__main__":
    main()
