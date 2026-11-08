# Riesgo de prórroga en contratos públicos (SECOP II)

**Pregunta de negocio:** al momento de firmar un contrato público, ¿qué tan probable es que termine necesitando una
prórroga (adición de tiempo)? La respuesta sirve a órganos de control, veedurías, auditores y contadores públicos para
**priorizar qué contratos vigilar**, y a las entidades para **planear mejor los plazos**.

## Fuentes (datos.gov.co, API Socrata, actualización diaria)

Consultado el 24-oct-2026. Los seis conjuntos son publicados por Colombia Compra Eficiente y **sí se relacionan**:

| ID | Conjunto | Filas | Histórico | Grano | Uso en el proyecto |
|---|---|---:|---|---|---|
| `jbjy-vk9h` | SECOP II – Contratos Electrónicos | 5,6 M | 2015 → hoy | 1 contrato | **Tabla principal** (objetivo `dias_adicionados > 0`) |
| `p6dx-8zbt` | SECOP II – Procesos de Contratación | 9,4 M | 2015 → hoy | 1 proceso (lote) | Variables de **competencia**: precio base, ofertas, invitados |
| `qmzu-gj57` | SECOP II – Proveedores Registrados | 1,6 M | 2015 → hoy | 1 proveedor | **Perfil del proveedor**: antigüedad, pyme, tipo de empresa |
| `ibyt-yi2f` | SECOP II – Facturas | 23,0 M | 2020 → hoy | 1 factura | Ejecución financiera (tablero; es posterior a la firma → fuga para el modelo) |
| `rpmr-utcd` | SECOP Integrado (I + II) | 22,9 M | 2000 → hoy | 1 contrato (con duplicados) | Vista histórica nacional SECOP I + II para el tablero |
| `s484-c9k3` | SECOP – Convenios Interadministrativos | 88 mil | 2019 → hoy (grueso 2024+) | 1 convenio | Subconjunto de contratos entre entidades |

```
  Proveedores (codigo) ─────────────┐
                                    │ codigo_proveedor
  Procesos (id_del_portafolio) ── proceso_de_compra ── CONTRATOS (id_contrato) ── Facturas (id_contrato)
                                                            │
                                    numero_del_contrato ────┤──── id_contrato
                                    SECOP Integrado          Convenios Interadministrativos
                                    (filas origen=SECOPII)   (fuente=SECOP_II)
```

Todas las llaves se verificaron cruzando contratos reales de 2024 contra cada tabla.

### Alcance v1 de los datos
- Contratos SECOP II **firmados en 2023–2024** y **ya terminados** a la fecha de corte (`params.yaml`).
- Se excluyen columnas con datos personales (nombres/documentos de personas, cuentas bancarias).

## Reproducir

Requiere **Python 3.12** (probado con 3.12.10; ver `.python-version`). Para revisar la versión: `python --version`.
Con otras versiones pueden fallar la instalación de `requirements.txt` o la carga del modelo exportado en `models/`.

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -r requirements.txt
dvc pull             # datos y modelo desde S3 (lectura pública, sin credenciales)
jupyter notebook notebooks/
```
Para regenerar los datos desde la API: `dvc repro` (download → build → features). Opcional: `SOCRATA_APP_TOKEN`
(token gratuito de datos.gov.co) para evitar límites de la API.

Para entrenar y registrar experimentos en MLflow: `$env:MLFLOW_TRACKING_URI = "http://<IP_EC2>:8050"` y
`python src/train.py --modelo lgbm --autor <nombre>`.

## Estructura
```
params.yaml              parámetros (ventana de fechas, fecha de corte, partición, suavizado)
dvc.yaml / dvc.lock      pipeline y versión exacta de los datos
models.dvc               versión del modelo exportado (models/)
src/download_secop.py    descarga desde la API
src/build_dataset.py     cruce de tablas + variable objetivo
src/features.py          variables del modelo y partición temporal
src/train.py             entrenamiento y registro en MLflow
src/exportar_modelo.py   Model Registry y exportación del modelo
src/prediccion.py        evaluación de un contrato (página Evaluar contrato del tablero)
src/evaluar_modelo.py    figuras de evaluación del reporte
notebooks/               01 exploración de datos · 02 modelo elegido y SHAP
experimentos/            experimentos de cada integrante
reports/                 hipótesis de variables y figuras
docs/                    maqueta del prototipo (GitHub Pages)
entrega/                 reportes de las entregas y reporte de trabajo en equipo
```

**Maqueta:** https://canaranjom.github.io/secop-alerta-prorrogas/
