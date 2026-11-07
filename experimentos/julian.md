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

## 5. Registro de resultados (llénalo tú)

| # | Run en MLflow | Qué cambié | valid_auc | valid_precision_top10 | valid_brier | ¿Mejor que la línea base? |
|---|---|---|---|---|---|---|
| 0 | linea-base-logistica (Camilo) | Referencia, m = 20 | 0,737 | 0,409 | 0,102 | — |
| 1 | m05-logistica-julian | m = 5 | | | | |
| 2 | m50-logistica-julian | m = 50 | | | | |
| 3 | m100-logistica-julian | m = 100 | | | | |
| 4 | balanced-logistica-julian | class_weight = balanced | | | | |
| 5 | rf-depth06-julian | RF, max_depth = 6 | | | | |
| 6 | rf-depth10-julian | RF, max_depth = 10 | | | | |
| 7 | rf-depth14-julian | RF, max_depth = 14 | | | | |
| 8 | rf-depth20-julian | RF, max_depth = 20 | | | | |

## 6. Conclusiones (para el reporte)

Escribe 2 o 3 frases por experimento: qué esperabas, qué pasó y qué decisión se toma.

- **Experimento 1 (m):**
- **Experimento 2 (balanceo):**
- **Experimento 3 (profundidad):**

---

## 7. Guardar tu trabajo en el repositorio

Cuando llenes la tabla (y cada vez que avances), guarda **solo este archivo**:

```powershell
git add experimentos/julian.md
git commit -m "Resultados de experimentos de Julián"
git pull
git push
```

Si `git push` pide usuario, inicia sesión con tu cuenta de GitHub (Camilo debe haberte agregado como
colaborador). Si algo sale en rojo, copia el mensaje y envíalo al grupo antes de intentar otra cosa.

## Referencias

- Cestnik, B. (1990). Estimating probabilities: A crucial task in machine learning. *Proceedings of ECAI*, 147–149.
- Micci-Barreca, D. (2001). A preprocessing scheme for high-cardinality categorical attributes in classification
  and prediction problems. *ACM SIGKDD Explorations Newsletter, 3*(1), 27–32.
