# Contrato de la API — Alerta de prórrogas SECOP II

Versión 1.0 · Este documento es el acuerdo entre la **API** (que sirve el modelo) y el **tablero** (que la consume).
Mientras ambos lados respeten este contrato, cada uno puede cambiar por dentro sin romper al otro.

```
  Tablero (Dash)  ──HTTP + JSON──▶  API (FastAPI)  ──▶  modelo + models/
     cliente        ◀──respuesta──     servidor
```

- **Dirección base:** la lee el tablero de la variable de entorno `API_URL`
  (en local `http://localhost:8001`; en AWS, `http://<IP_EC2>:8001`).
- **Prefijo de versión:** todas las rutas empiezan por `/api/v1`.
- **Formato:** JSON en UTF-8. Los nombres de los campos son los mismos de `src/prediccion.py`.
- **Documentación interactiva:** con la API corriendo, `http://<API_URL>/docs` (la genera FastAPI).

## Resumen de rutas

| Método | Ruta | Para qué | Reemplaza en el tablero |
|---|---|---|---|
| GET | `/api/v1/health` | Saber si la API está viva y qué modelo sirve | — |
| GET | `/api/v1/opciones/{variable}` | Valores de un desplegable | `opciones(variable)` |
| GET | `/api/v1/entidades?q=texto&n=20` | Buscador de entidades | `buscar_entidades(texto)` |
| GET | `/api/v1/entidades/{codigo}` | Una entidad por su código | `_cargar()[2]` |
| POST | `/api/v1/evaluar` | Probabilidad de prórroga de un contrato | `evaluar_contrato(datos)` |

`GET` se usa para **consultar** (los datos van en la URL y no hay cuerpo). `POST` se usa para **enviar datos a
procesar** (van en el cuerpo, en JSON).

## Códigos de respuesta

| Código | Significa | Cuándo |
|---|---|---|
| 200 | Todo bien | Respuesta normal |
| 404 | No existe | Variable de desplegable o código de entidad desconocidos |
| 422 | Datos mal formados | Falta un campo obligatorio, un número ≤ 0, fecha inválida, búsqueda de menos de 3 letras |
| 500 | Error interno | Falla inesperada de la API (no debería pasar) |

En los errores la respuesta trae un campo `detail` con la explicación.

---

## GET `/api/v1/health`

Respuesta `200`:

```json
{
  "nombre": "API alerta de prórrogas SECOP",
  "version_api": "1.0.0",
  "version_modelo": "secop-prorroga v1 (lgbm-base)"
}
```

## GET `/api/v1/opciones/{variable}`

`variable` es una de: `tipo_de_contrato`, `modalidad_de_contratacion`, `departamento`, `orden`, `sector`.

Ejemplo: `GET /api/v1/opciones/orden` → `200`

```json
{
  "variable": "orden",
  "valores": ["Territorial", "Nacional", "Corporación Autónoma", "No Definido"]
}
```

Los valores vienen ordenados de más a menos frecuente. Variable no permitida → `404`.

## GET `/api/v1/entidades?q=texto&n=20`

| Parámetro | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `q` | texto | sí | mínimo 3 caracteres; busca dentro del nombre, sin distinguir mayúsculas |
| `n` | entero | no | máximo de resultados, por defecto 20, entre 1 y 50 |

Ejemplo: `GET /api/v1/entidades?q=medell&n=2` → `200`

```json
[
  {"codigo_entidad": "700774011", "nombre_entidad": "INSTITUTO DE DEPORTES Y RECREACION DE MEDELLIN",
   "departamento": "Antioquia", "orden": "Territorial", "sector": "deportes"},
  {"codigo_entidad": "704683010", "nombre_entidad": "BIBLIOTECA PUBLICA PILOTO DE MEDELLIN PARA AMERICA LATINA",
   "departamento": "Antioquia", "orden": "Territorial", "sector": "Cultura"}
]
```

Sin coincidencias → `200` con lista vacía `[]`.

## GET `/api/v1/entidades/{codigo}`

Devuelve una sola entidad con los mismos campos de la búsqueda. Código desconocido → `404`.

## POST `/api/v1/evaluar`

Cuerpo de la petición:

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `tipo_de_contrato` | texto | sí | uno de `/opciones/tipo_de_contrato` |
| `modalidad_de_contratacion` | texto | sí | uno de `/opciones/modalidad_de_contratacion` |
| `departamento` | texto | sí | uno de `/opciones/departamento` |
| `orden` | texto | sí | uno de `/opciones/orden` |
| `sector` | texto | sí | uno de `/opciones/sector` |
| `precio_base` | número | sí | en pesos, mayor que 0 |
| `duracion_pactada_dias` | número | sí | mayor que 0 |
| `fecha_de_firma` | texto | sí | formato `AAAA-MM-DD` |
| `codigo_entidad` | texto | no | si se envía, se usa el historial de la entidad |
| `codigo_proveedor` | texto | no | si se envía, se usa el historial del proveedor |

Ejemplo (tercer contrato de `models/ejemplos.json`, que en la realidad sí se prorrogó):

```json
{
  "codigo_entidad": "702547704",
  "tipo_de_contrato": "Prestación de servicios",
  "modalidad_de_contratacion": "Contratación directa",
  "departamento": "Distrito Capital de Bogotá",
  "orden": "Nacional",
  "sector": "defensa",
  "precio_base": 14872002,
  "duracion_pactada_dias": 270,
  "fecha_de_firma": "2024-10-15",
  "codigo_proveedor": null
}
```

Respuesta `200` (resultado real del modelo v1):

```json
{
  "probabilidad_prorroga": 0.5141,
  "nivel": "alto",
  "factores": [
    {"variable": "duracion_pactada_dias", "descripcion": "Duración pactada (días)", "valor": 270.0, "efecto": 1.319},
    {"variable": "departamento", "descripcion": "Departamento", "valor": "Distrito Capital de Bogotá", "efecto": 0.565},
    {"variable": "mes_firma", "descripcion": "Mes de firma", "valor": 10, "efecto": 0.459}
  ],
  "notas": [],
  "modelo": "secop-prorroga v1 (lgbm-base)"
}
```

| Campo de salida | Significado |
|---|---|
| `probabilidad_prorroga` | Entre 0 y 1 |
| `nivel` | `bajo` (< 0,25), `medio` (0,25–0,50) o `alto` (≥ 0,50) |
| `factores` | Hasta 3 variables que más **suben** el riesgo; `efecto` en log-odds (contribución SHAP de LightGBM) |
| `notas` | Avisos, por ejemplo "Entidad sin historial en SECOP II: se usa la tasa general." |
| `modelo` | Nombre y versión del modelo en el Model Registry de MLflow |

Falta un obligatorio o un número ≤ 0 → `422`.

---

## Cómo cambia el tablero

Antes (llamada directa al modelo):

```python
from src.prediccion import evaluar_contrato
resultado = evaluar_contrato(datos)
```

Después (llamada a la API):

```python
import os
import requests

API_URL = os.getenv("API_URL", "http://localhost:8001")

resultado = requests.post(f"{API_URL}/api/v1/evaluar", json=datos, timeout=30)
resultado.raise_for_status()          # lanza error si la API respondió 4xx/5xx
resultado = resultado.json()          # mismo diccionario que devolvía evaluar_contrato
```

El diccionario `datos` que ya arma `dashboard/evaluacion.py` es exactamente el cuerpo de `POST /evaluar`, y la
respuesta tiene las mismas llaves que antes, así que el resto del código del tablero no cambia. Las otras tres
llamadas siguen el mismo patrón con `requests.get(...)`. Con este cambio el tablero deja de importar `src/` y de
leer `models/`.

## Decisiones de diseño

- **`/api/v1` en la ruta:** si la entrada cambia, se publica `/api/v2` sin romper el tablero.
- **Un contrato por llamada:** el formulario evalúa uno a la vez. Si luego se necesita puntuar en lote, se agrega
  `/api/v1/evaluar/lote` sin tocar esta ruta.
- **Obligatorios iguales a los del formulario:** `prediccion.py` tolera campos vacíos, pero exigirlos en la API
  da errores claros (422) en vez de predicciones con valores rellenados sin que el usuario lo sepa.
- **Desplegables desde la API:** así los valores siempre coinciden con lo que el modelo conoce.
