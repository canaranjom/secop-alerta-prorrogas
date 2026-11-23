# Experimentos de Julián · Entrega 2

**Responsable:** Julián David Castañeda Plazas
**Para qué sirve:** cada experimento responde una pregunta concreta sobre el modelo. Los resultados quedan en MLflow
(en la EC2 del equipo) con tu nombre, y aquí anotas lo que probaste y lo que concluyes. Esto es tu aporte técnico
visible: runs en MLflow con autor "Julian" y commits en el repositorio.

> No necesitas programar. El script `src/train.py` ya hace todo; tú solo cambias parámetros desde la terminal.

---

## 0. Preparar tu computador (una sola vez, ~20 minutos)

Abre **PowerShell** (en Mac, la app *Terminal*) y ejecuta una línea a la vez.

```powershell
# 1. Descargar el repositorio
cd $HOME\Documents
git clone https://github.com/canaranjom/secop-alerta-prorrogas.git
cd secop-alerta-prorrogas

# 2. Crear y activar el ambiente virtual (una "caja" con las librerías del proyecto)
python -m venv .venv
.venv\Scripts\Activate.ps1          # Mac: source .venv/bin/activate
pip install -r requirements.txt     # tarda unos minutos

# 3. Descargar los datos desde S3 (no pide credenciales; el bucket es de lectura pública)
dvc pull
```

- Si `Activate.ps1` da un error rojo de "ejecución de scripts deshabilitada", escribe primero
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y repite.
- Sabes que el ambiente está activo porque la línea empieza con `(.venv)`.
- Al final de `dvc pull` debes tener el archivo `data/processed/features.parquet`.

**Cada vez que abras una terminal nueva** para trabajar:

```powershell
cd $HOME\Documents\secop-alerta-prorrogas
.venv\Scripts\Activate.ps1
$env:MLFLOW_TRACKING_URI = "http://<IP_QUE_TE_ENVÍA_CAMILO>:8050"   # Mac: export MLFLOW_TRACKING_URI=...
```

La última línea le dice al script a qué servidor de MLflow enviar los resultados. La IP cambia cada vez que se
reinicia la máquina en AWS: pídesela a Camilo por WhatsApp.

---

## 1. Conceptos mínimos para leer los resultados

| Métrica en MLflow | Qué significa | ¿Mejor alto o bajo? |
|---|---|---|
| `valid_auc` | Si tomo al azar un contrato prorrogado y uno no prorrogado, qué tan seguido el modelo le da más riesgo al prorrogado. 0,5 = moneda al aire; 1 = perfecto. | Alto |
| `valid_precision_top10` | De los 10 % de contratos que el tablero pondría **en alerta**, qué fracción de verdad se prorrogó. | Alto |
| `valid_lift_top10` | Cuántas veces mejor que escoger contratos al azar. | Alto |
| `valid_brier` | Qué tan "creíbles" son las probabilidades (si dice 30 %, ¿se prorroga ~30 %?). | Bajo |

- **Compara siempre con las métricas `valid_`** (validación). Las `test_` son el examen final: se miran solo al
  escoger el modelo definitivo, para no hacer trampa.
- **Referencia (línea base de Camilo):** regresión logística, `valid_auc = 0,737`, `valid_precision_top10 = 0,409`.

---

## 2. Experimento 1 · ¿Cuánto suavizar la tasa histórica de la entidad? (valor de m)

**La pregunta.** La variable más importante del modelo es la tasa histórica de prórroga de cada entidad. Una
entidad con pocos contratos previos tendría una tasa poco confiable (1 de 1 = 100 %), así que se le suman
**m contratos "imaginarios"** con la tasa promedio del país:

```
tasa = (prorrogados previos + m × 0,128) / (terminados previos + m)
```

Es la técnica *m-estimate* (Cestnik, 1990) usada para variables con muchas categorías (Micci-Barreca, 2001).
Con m pequeño se confía más en la historia de cada entidad; con m grande, más en el promedio del país. Hoy
usamos m = 20, pero **nadie ha probado si es el mejor valor**. Eso lo decides tú.

**Pasos** (repetir para m = 5, 50 y 100; m = 20 ya está corrido por Camilo):

1. Abre `params.yaml` en VS Code o el Bloc de notas, busca `suavizado_m: 20` y cambia el 20 por el valor a
   probar (por ejemplo `5`). Guarda.
2. Recalcula las variables con el nuevo m (tarda ~20 segundos):
   ```powershell
   dvc repro features
   ```
3. Entrena el modelo y envíalo a MLflow (tarda ~1 minuto):
   ```powershell
   python src/train.py --modelo logistica --autor Julian --muestra 1 --nombre m05-logistica-julian --nota "Experimento 1: suavizado m=5"
   ```
   Cambia `m05` y `m=5` según el valor que estés probando.
4. Anota el resultado en la tabla de la sección 5.

**Al terminar los tres valores, deja todo como estaba** (esto es importante para no cambiar el modelo de los
demás sin acordarlo):

```powershell
git checkout params.yaml dvc.lock
dvc checkout
```

**Cómo verlo en MLflow:** entra a `http://<IP>:8050` → experimento **secop-prorrogas** → marca las casillas de
tus cuatro runs (incluido `linea-base-logistica`, que es m = 20) → botón **Compare**. En la gráfica, pon
`feat_suavizado_m` en el eje X y `valid_auc` en el eje Y. **Toma pantallazo**: va al reporte.

---

## 3. Experimento 2 · ¿Conviene "darle más peso" a los contratos prorrogados?

**La pregunta.** Solo el 12 % de los contratos se prorroga. Algunos modelos tienden a "ignorar" la clase
minoritaria. La opción `class_weight=balanced` le dice al modelo que un error en un prorrogado cuenta tanto como
todos los errores de los no prorrogados. ¿Mejora la alerta, o solo distorsiona las probabilidades?

```powershell
python src/train.py --modelo logistica --autor Julian --muestra 1 --param class_weight=balanced --nombre balanced-logistica-julian --nota "Experimento 2: class_weight balanced"
```

**Qué mirar:** compara con `linea-base-logistica`. Probablemente el `valid_auc` casi no cambie, pero el
`valid_brier` empeore (las probabilidades quedan infladas). Si es así, la conclusión es: *balancear no ayuda a
ordenar los contratos y daña la interpretación de la probabilidad que muestra el tablero*.

---

## 4. Experimento 3 · Profundidad de los árboles en Random Forest

**La pregunta.** Igual que en el Taller 4 con `mlflow-diab.py`: un bosque aleatorio con árboles muy poco
profundos no alcanza a aprender (subajuste); con árboles muy profundos memoriza el entrenamiento (sobreajuste).
¿Cuál es el punto medio para nuestro problema?

```powershell
python src/train.py --modelo rf --autor Julian --param max_depth=6  --nombre rf-depth06-julian --nota "Experimento 3: max_depth=6"
python src/train.py --modelo rf --autor Julian --param max_depth=10 --nombre rf-depth10-julian --nota "Experimento 3: max_depth=10"
python src/train.py --modelo rf --autor Julian --param max_depth=14 --nombre rf-depth14-julian --nota "Experimento 3: max_depth=14"
python src/train.py --modelo rf --autor Julian --param max_depth=20 --nombre rf-depth20-julian --nota "Experimento 3: max_depth=20"
```

Cada uno tarda varios minutos (usa el 30 % del entrenamiento para no demorar tanto). **Qué mirar:** en MLflow,
compara los cuatro con `max_depth` en el eje X y `valid_auc` en el eje Y. Esperamos que suba y luego se aplane o
baje. Toma pantallazo.

---

## 5. Registro de resultados

Runs ejecutados en el servidor MLflow de la EC2 del equipo, en el experimento `secop-prorrogas`. Todas las cifras son de **validación** correspondientes al periodo de tiempo de abril a junio de 2024; 183.052 contratos; tasa de prórroga 12,96 %. Los runs de regresión logística usan el 100 % del entrenamiento (1.117.593 contratos) y los de Random Forest el 30 % (335.278), igual que sus referencias.

| # | Run en MLflow | Qué cambié | valid_auc | valid_precision_top10 | valid_brier | ¿Mejor que la línea base? |
|---|---|---|---|---|---|---|
| 0 | linea-base-logistica (Camilo) | Referencia: logística, m = 20 | 0,7366 | 0,4085 | 0,1016 | — |
| 1 | m05-logistica-julian | m = 5 | 0,7356 | 0,4073 | 0,1017 | No (prácticamente igual) |
| 2 | m50-logistica-julian | m = 50 | 0,7363 | 0,4079 | 0,1016 | No (prácticamente igual) |
| 3 | m100-logistica-julian | m = 100 | 0,7354 | 0,4064 | 0,1018 | No (prácticamente igual) |
| 4 | balanced-logistica-julian | class_weight = balanced | 0,7373 | 0,3747 | 0,2221 | No: peor alerta y probabilidades infladas |
| 5 | rf-depth06-julian | RF, max_depth = 6 | 0,7633 | 0,4214 | 0,1053 | Sí en AUC y alerta; Brier algo peor |
| 6 | rf-depth10-julian | RF, max_depth = 10 | 0,7789 | 0,4587 | 0,1001 | Sí |
| 7 | rf-depth14-julian | RF, max_depth = 14 | 0,7881 | 0,4733 | 0,0980 | Sí |
| 8 | rf-depth20-julian | RF, max_depth = 20 | 0,7983 | 0,4752 | 0,0967 | Sí (mejor de la serie) |
| 9 | rf-depthNone-julian *(extra)* | RF, sin límite de profundidad | 0,7978 | 0,4751 | 0,0968 | Sí (igual a max_depth = 20) |

Soportes: pantallazos de las comparaciones en MLflow (IP del servidor visible) para cada experimento.

## 6. Conclusiones

- **Experimento 1. Suavizado m de la tasa histórica de la entidad:** se esperaba un equilibrio entre ruido (m pequeño) y pérdida de la señal propia de cada entidad (m grande), según el *m-estimate* (Cestnik, 1990; Micci-Barreca, 2001). El máximo se obtuvo en m = 20, pero toda la variación entre m = 5 y m = 100 fue de 0,0012 en AUC y 0,003 en precisión del 10 % en alerta; la variable es robusta al suavizado porque el 86,3 % de los contratos pertenece a entidades con historia previa. **Decisión: mantener m = 20.**
- **Experimento 2. Balanceo de clases:** se esperaba que el AUC no cambiara y que las probabilidades se inflaran, como reportan van den Goorbergh et al. (2022). Ambas cosas se cumplieron (AUC 0,7373 frente a 0,7366; Brier de 0,102 a 0,222) y, además, la precisión en el 10 % en alerta cayó 3,4 puntos: el AUC promedia todo el ranking y oculta lo que pasa en la parte alta, que es la que usa el tablero. **Decisión: mantener `class_weight = None`**; si se requiere alertar más contratos, se ajusta el umbral y no los pesos.
- **Experimento 3. Profundidad del Random Forest:** se esperaba subajuste con árboles poco profundos y una meseta o sobreajuste con árboles muy profundos. El AUC subió de 0,763 (profundidad 6) a 0,798 (profundidad 20) y se aplanó: sin límite de profundidad dio 0,798, porque `min_samples_leaf = 50` detiene el crecimiento de los árboles, y la diferencia (0,0005) es menor que el error de muestreo del AUC (Hanley y McNeil, 1982). La precisión del 10 % en alerta ya casi no mejora después de 14 (+0,002 de 14 a 20). **Decisión: profundidad entre 14 y 20; no conviene quitar el límite**, porque no mejora y produce un modelo más pesado para la API.

**Observaciones adicionales**

- La profundidad de los árboles fue el factor con más impacto con 3,5 puntos de AUC; el suavizado y el balanceo no mejoraron el modelo. Incluso el Random Forest más simple (profundidad 6) supera a la regresión logística, porque los árboles capturan interacciones entre variables, como la del tipo de contrato con el monto identificada en la Entrega 1.
- Reproducibilidad: `rf-depth14-julian` usa la misma configuración que `rf-base` y reprodujo sus resultados en prueba (AUC 0,82 y AP 0,42) en otro computador, con el mismo código, datos versionados con DVC y semilla.
- Prudencia con las ganancias pequeñas: en el conjunto de prueba (julio a diciembre de 2024) el AUC del Random Forest se mantiene en aproximadamente 0,82 desde profundidad 10, y la precisión en el 10 % baja levemente de 10 a 20. 
La tasa de prórroga en prueba (10,2 %) es menor que en validación (13,0 %), lo que puede reflejar contratos de fines de 2024 aún abiertos al corte por lo cual se deja la recomendación de revisar este aspecto antes de escoger el modelo final.

### Referencias de esta sección

- Cestnik, B. (1990). Estimating probabilities: A crucial task in machine learning. *Proceedings of ECAI*, 147–149.
- Hanley, J. A. y McNeil, B. J. (1982). The meaning and use of the area under a receiver operating characteristic (ROC) curve. *Radiology, 143*(1), 29–36.
- Micci-Barreca, D. (2001). A preprocessing scheme for high-cardinality categorical attributes in classification and prediction problems. *ACM SIGKDD Explorations Newsletter, 3*(1), 27–32.
- van den Goorbergh, R., van Smeden, M., Timmerman, D. y Van Calster, B. (2022). The harm of class imbalance corrections for risk prediction models: Illustration and simulation using logistic regression. *Journal of the American Medical Informatics Association, 29*(9), 1525–1534.

---

# Entrega 3 · Ronda v2 sobre el modelo final (LightGBM)

**Pregunta:** ¿cuánto conviene regularizar LightGBM? La referencia es `lgbm-base`, el modelo registrado como `secop-prorroga` v1 (`min_child_samples = 100`, `colsample_bytree = 0,8`, semilla 42; AUC de validación 0,815).
**Servidor:** MLflow en la EC2 del equipo (3.88.171.144:8050), experimento `secop-prorrogas`, 22 de noviembre de 2026. Todos los runs usan el 100 % del entrenamiento (1.117.593 contratos). Las cifras son de **validación** (abril a junio de 2024), que es el conjunto con el que se decide; prueba solo se reporta.

## 7. Experimentos

- **Experimento 4. Mínimo de contratos por hoja (`min_child_samples`):** 25 (menos regularización) y 400 (más regularización), frente a 100 en la base. Un valor bajo permite hojas muy específicas y riesgo de sobreajuste; uno alto puede causar subajuste (documentación de LightGBM, *Parameters Tuning*).
- **Experimento 5. Fracción de variables por árbol (`colsample_bytree`):** 0,5 y 1,0, frente a 0,8 en la base. Submuestrear variables en cada árbol es la idea del *random subspace method* (Ho, 1998) y la documentación de LightGBM lo recomienda para controlar el sobreajuste.
- **Experimento 6 (agregado). Variabilidad por la semilla:** las cuatro variantes cayeron en precisión del 10 % en alerta en la misma dirección, sin importar si regularizaban más o menos. Para saber si esa caída era real o azar del entrenamiento (`subsample` y `colsample_bytree` son aleatorios), se repitió `lgbm-base` con las semillas 42, 1, 7, 123 y 2026. Para esto se agregó la opción `--semilla` a `src/train.py`; por defecto vale 42, de modo que los runs anteriores no cambian.

## 8. Registro de resultados

**Experimentos 4 y 5**

| # | Run en MLflow | Qué cambié | valid_auc | valid_precision_top10 | valid_ap | valid_brier |
|---|---|---|---|---|---|---|
| 0 | lgbm-base (Camilo) | Referencia | 0,8150 | 0,4839 | 0,4400 | 0,0916 |
| 10 | lgbm-mcs25-julian | min_child_samples = 25 | 0,8159 | 0,4712 | 0,4322 | 0,0920 |
| 11 | lgbm-mcs400-julian | min_child_samples = 400 | 0,8148 | 0,4670 | 0,4402 | 0,0915 |
| 12 | lgbm-col05-julian | colsample_bytree = 0,5 | 0,8212 | 0,4718 | 0,4239 | 0,0920 |
| 13 | lgbm-col10-julian | colsample_bytree = 1,0 | 0,8139 | 0,4745 | 0,4260 | 0,0923 |

**Experimento 6: `lgbm-base` con cinco semillas**

| # | Run en MLflow | Semilla | valid_auc | valid_precision_top10 | valid_ap | valid_brier | test_auc | test_precision_top10 |
|---|---|---|---|---|---|---|---|---|
| 14 | lgbm-base-s42-julian | 42 (control) | 0,8150 | 0,4839 | 0,4400 | 0,0916 | 0,8245 | 0,4200 |
| 15 | lgbm-base-s1-julian | 1 | 0,8188 | 0,4728 | 0,4300 | 0,0920 | 0,8279 | 0,4337 |
| 16 | lgbm-base-s7-julian | 7 | 0,8158 | 0,4687 | 0,4208 | 0,0924 | 0,8246 | 0,4196 |
| 17 | lgbm-base-s123-julian | 123 | 0,8143 | 0,4693 | 0,4229 | 0,0925 | 0,8284 | 0,4236 |
| 18 | lgbm-base-s2026-julian | 2026 | 0,8211 | 0,4883 | 0,4419 | 0,0909 | 0,8284 | 0,4234 |
| | **Media ± desviación estándar** | | **0,8170 ± 0,0029** | **0,4766 ± 0,0089** | **0,4311 ± 0,0096** | **0,0919 ± 0,0007** | **0,8268 ± 0,0020** | **0,4241 ± 0,0057** |

**Variantes frente a la banda de la base** (z = (variante − media) / desviación estándar)

| Variante | z en valid_auc | z en valid_precision_top10 |
|---|---|---|
| mcs25 | −0,4 | −0,6 |
| mcs400 | −0,8 | −1,1 |
| col05 | +1,5 | −0,5 |
| col10 | −1,1 | −0,2 |

Soportes: pantallazos de las comparaciones en MLflow con la IP del servidor visible, en `entrega/pantallazos/` (`julian_exp4_*.png`, `julian_exp5_*.png` y `julian_exp6_*.png`). Orden de las columnas en las tablas de MLflow: Exp. 4 = 100, 25, 400; Exp. 5 = 0,8, 0,5, 1,0; Exp. 6 = semillas 1, 7, 123, 2026, 42.

## 9. Conclusiones

- **Control de reproducibilidad:** con la semilla 42, el run en un Mac (`lgbm-base-s42-julian`) reprodujo **exactamente** las métricas de `lgbm-base`, entrenado en otro computador con Windows. El mismo código, los mismos datos versionados con DVC y la misma semilla dan el mismo modelo.
- **Experimentos 4 y 5:** comparadas con un solo run de la base, todas las variantes parecían peores en precisión del 10 % en alerta (entre −0,9 y −1,7 puntos), y `col05` parecía mejor en AUC (+0,006). **Comparadas con la variación por semilla, ninguna diferencia supera 1,5 desviaciones estándar**: no se distinguen del azar del entrenamiento. La semilla 42 resultó la segunda corrida más alta de las cinco en precisión del 10 %, lo que hacía ver peores a las variantes.
- **Experimento 6. Variabilidad por semilla:** con exactamente la misma configuración, la precisión del 10 % en alerta varió entre 0,4687 (semilla 7) y 0,4883 (semilla 2026), un rango de 2 puntos, y el AUC entre 0,8143 y 0,8211. En cambio, el Brier casi no cambió (0,0909 a 0,0925): la calidad de las probabilidades es estable, mientras que la parte alta de la lista, la que el tablero pone en alerta, es la más sensible al azar del entrenamiento. Por eso cualquier comparación sobre esa métrica debe hacerse con varias semillas.
- **Hallazgo:** el modelo es **robusto a la regularización** en el rango probado (`min_child_samples` de 25 a 400; `colsample_bytree` de 0,5 a 1,0). No depende de un ajuste fino de estos parámetros, lo que conviene para un modelo que se reentrenará periódicamente.
- **Decisión: se mantiene `lgbm-base` (`secop-prorroga` v1) como modelo desplegado.** Ninguna alternativa justifica el cambio, y la v1 ya está desplegada y es reproducible.
- **Desempeño reportado con su margen:** en prueba (julio a diciembre de 2024), AUC 0,827 ± 0,002 y precisión del 10 % en alerta 0,424 ± 0,006, es decir, unas 4,2 veces la tasa general de prórroga del periodo (10,2 %).
- **Lección aprendida:** el error de muestreo de la precisión del 10 % en validación (unos 18.300 contratos) es de aproximadamente ±0,004, pero la variación real entre semillas es de ±0,009, más del doble. En este problema, comparar runs únicos con diferencias de un punto en esa métrica no es confiable; las comparaciones deben hacerse con varias semillas (Bouthillier et al., 2021; Dietterich, 1998).

### Referencias de esta sección

- Bouthillier, X., Delaunay, P., Bronzi, M., Trofimov, A., Nichyporuk, B., Szeto, J., … Vincent, P. (2021). Accounting for variance in machine learning benchmarks. *Proceedings of Machine Learning and Systems, 3* (MLSys 2021).
- Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning algorithms. *Neural Computation, 10*(7), 1895–1923.
- Ho, T. K. (1998). The random subspace method for constructing decision forests. *IEEE Transactions on Pattern Analysis and Machine Intelligence, 20*(8), 832–844.
- Microsoft. (2026). *LightGBM documentation: Parameters tuning* (versión 4.7.0). https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html
