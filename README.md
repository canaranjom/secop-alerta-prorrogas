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

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -r requirements.txt
dvc repro            # download -> build
jupyter notebook notebooks/01_exploracion_secop.ipynb
```
Opcional: `SOCRATA_APP_TOKEN` (token gratuito de datos.gov.co) para evitar límites de la API.

## Estructura
```
params.yaml            parámetros (ventana de fechas, fecha de corte)
dvc.yaml / dvc.lock    pipeline y versión exacta de los datos
src/download_secop.py  descarga desde la API
src/build_dataset.py   cruce de tablas + variable objetivo
notebooks/             exploración de datos
reports/figures/       gráficas de la exploración
docs/                  maqueta del prototipo (GitHub Pages)
entrega/               reporte de la Entrega 1
```

**Maqueta:** https://canaranjom.github.io/secop-alerta-prorrogas/
