# Manual de instalación — Alerta de prórrogas SECOP II

Este manual explica cómo instalar y poner en marcha la solución completa: el **tablero** (Dash) y la **API del
modelo** (FastAPI), cada uno en su contenedor Docker. Se describen dos opciones:

- **Opción A — Servidor en AWS (EC2):** es el despliegue usado por el equipo.
- **Opción B — Computador local:** para probar o desarrollar.

Repositorio: https://github.com/canaranjom/secop-alerta-prorrogas

---

## 1. Cómo está armada la solución

```
                     ┌──────────────── Servidor (EC2 o PC) ────────────────┐
  Navegador ──8050──▶│  tablero (Dash)  ──http://api:8001──▶  api (FastAPI) │
                     │  datos livianos                       modelo LightGBM│
  Otros sistemas ─8001──────────────────────────────────────▶               │
                     └─────────────────────────────────────────────────────┘
                              ▲  dvc pull (lectura pública, sin credenciales)
                     Bucket S3: secop-alerta-prorrogas-dvc-cn
```

| Componente | Puerto | Imagen | Qué contiene |
|---|---|---|---|
| API del modelo | 8001 | `secop-api` | `api/`, `src/prediccion.py` y el modelo exportado (`models/`) |
| Tablero | 8050 | `secop-tablero` | `dashboard/` y los datos livianos (`data/tablero/`, 28 MB) |

- El tablero **no carga el modelo**: le pide cada predicción a la API por HTTP. La dirección de la API se le pasa
  con la variable de entorno `API_URL`.
- `docker-compose.yml` (en la raíz del repo) construye y levanta los dos contenedores con un solo comando, en una
  red interna donde el tablero encuentra la API por el nombre `api`.
- El modelo y los datos **no están en Git**: se versionan con DVC y se descargan del bucket S3 del proyecto, que es
  de lectura pública.

---

## 2. Opción A — Instalación en AWS (EC2)

### 2.1 Requisitos

- Una cuenta de AWS (el equipo usó AWS Academy, región `us-east-1`).
- Un par de llaves (`.pem`) para entrar por SSH.

### 2.2 Crear la instancia

En la consola de AWS: **EC2 → Instancias → Lanzar instancias**, con esta configuración:

| Campo | Valor |
|---|---|
| Nombre | `secop-app` |
| Imagen (AMI) | Ubuntu Server 24.04 LTS |
| Tipo de instancia | `t2.medium` (2 vCPU, 4 GB). Con `t2.micro` la construcción de las imágenes se queda sin memoria. |
| Par de llaves | el suyo |
| Almacenamiento | 20 GB gp3 |
| Grupo de seguridad | nuevo, con las reglas de entrada de la tabla siguiente |

| Tipo | Puerto | Origen | Para qué |
|---|---|---|---|
| SSH | 22 | 0.0.0.0/0 (o solo su IP) | administrar la máquina |
| TCP personalizado | 8050 | 0.0.0.0/0 | tablero |
| TCP personalizado | 8001 | 0.0.0.0/0 | API (documentación y uso desde otros sistemas) |

Cuando la instancia esté en **En ejecución**, copie su **Dirección IPv4 pública**.

### 2.3 Entrar por SSH

Desde PowerShell (Windows) o una terminal (Mac/Linux):

```bash
ssh -i "ruta/a/su-llave.pem" -o ServerAliveInterval=60 ubuntu@<IP_PUBLICA>
```

`ServerAliveInterval` evita que la conexión se corte cuando se queda quieta.

### 2.4 Instalar Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit
```

El script oficial instala Docker y el plugin `docker compose`. `usermod` permite usar Docker sin `sudo`; el
cambio solo aplica al volver a entrar, por eso el `exit`. Vuelva a conectarse por SSH y verifique:

```bash
docker --version && docker compose version
```

Versiones probadas: Docker 29.10 y Docker Compose v5.8.

### 2.5 Descargar el código, el modelo y los datos

```bash
git clone https://github.com/canaranjom/secop-alerta-prorrogas.git
cd secop-alerta-prorrogas

sudo apt-get update && sudo apt-get install -y python3-venv
python3 -m venv ~/dvc-env
~/dvc-env/bin/pip install "dvc[s3]==3.67.1"

~/dvc-env/bin/dvc pull models.dvc tablero
```

- DVC se instala en un ambiente aparte porque Ubuntu 24.04 no permite instalar paquetes con `pip` sobre el Python
  del sistema.
- `dvc pull models.dvc tablero` baja solo lo que necesitan los contenedores: el modelo (`models/`) y los datos
  livianos del tablero (`data/tablero/contratos_tablero.parquet`). No pide credenciales.
- Al final debe decir algo como `7 files fetched`.

### 2.6 Construir y levantar los contenedores

```bash
docker compose up -d --build
```

- `--build` construye las dos imágenes (la primera vez tarda unos 3 a 5 minutos).
- `-d` deja los contenedores corriendo en segundo plano: siguen funcionando aunque se cierre la sesión SSH.
- El tablero arranca solo cuando la API ya responde (`depends_on` con `service_healthy` en el compose).
- Los contenedores tienen `restart: unless-stopped`: si la instancia se reinicia, vuelven a arrancar solos.

### 2.7 Verificar

```bash
docker ps
```

Deben aparecer los dos contenedores con estado `Up ... (healthy)`. Luego, desde el navegador de su computador:

| Qué | Dirección |
|---|---|
| Tablero | `http://<IP_PUBLICA>:8050` |
| Documentación interactiva de la API | `http://<IP_PUBLICA>:8001/docs` |
| Estado de la API | `http://<IP_PUBLICA>:8001/api/v1/health` |

Prueba rápida de una predicción desde la terminal:

```bash
curl -X POST http://localhost:8001/api/v1/evaluar -H "Content-Type: application/json" -d '{
  "codigo_entidad": "702547704", "tipo_de_contrato": "Prestación de servicios",
  "modalidad_de_contratacion": "Contratación directa", "departamento": "Distrito Capital de Bogotá",
  "orden": "Nacional", "sector": "defensa", "precio_base": 14872002,
  "duracion_pactada_dias": 270, "fecha_de_firma": "2024-10-15"}'
```

Respuesta esperada: `"probabilidad_prorroga": 0.5141`, `"nivel": "alto"` y tres factores.

---

## 3. Opción B — Instalación en un computador local

Requisitos: **Git**, **Docker Desktop** (encendido) y **Python 3.12** (solo para DVC).

```powershell
git clone https://github.com/canaranjom/secop-alerta-prorrogas.git
cd secop-alerta-prorrogas

python -m venv .venv
.venv\Scripts\Activate.ps1            # Mac/Linux: source .venv/bin/activate
pip install "dvc[s3]==3.67.1"
dvc pull models.dvc tablero

docker compose up -d --build
```

Luego abra `http://localhost:8050` (tablero) y `http://localhost:8001/docs` (API).

Si PowerShell no deja activar el ambiente ("ejecución de scripts deshabilitada"), ejecute una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y repita.

### Sin Docker (para desarrollo)

Con el ambiente completo del proyecto (`pip install -r requirements.txt`), en dos terminales desde la raíz del repo:

```powershell
uvicorn api.main:app --port 8001      # terminal 1: API
python dashboard/app.py               # terminal 2: tablero (busca la API en localhost:8001)
```

---

## 4. Configuración

| Variable | Contenedor | Valor por defecto | Para qué |
|---|---|---|---|
| `API_URL` | tablero | `http://localhost:8001` (en el compose: `http://api:8001`) | dirección de la API |
| `PORT` | tablero | `8050` | puerto del tablero |
| `DEBUG` | tablero | apagado | `DEBUG=1` activa el modo de depuración de Dash (no usar en el servidor) |

Para cambiar una variable, edite la sección `environment:` del servicio en `docker-compose.yml` y ejecute de nuevo
`docker compose up -d`.

---

## 5. Operación del día a día

| Tarea | Comando (desde la carpeta del repo) |
|---|---|
| Ver el estado | `docker ps` |
| Ver los registros | `docker compose logs -f tablero` o `docker compose logs -f api` |
| Actualizar a la última versión del código | `git pull && docker compose up -d --build` |
| Actualizar el modelo o los datos | `~/dvc-env/bin/dvc pull models.dvc tablero && docker compose up -d --build` |
| Detener la solución | `docker compose down` |
| Volver a levantarla | `docker compose up -d` |

**Apagar y encender la instancia (AWS):** use **Detener** (Stop), no **Terminar** (Terminate), que borra la
máquina. Al encenderla de nuevo, los contenedores arrancan solos, pero **la IP pública cambia**: tome la nueva en
la consola de EC2. Para una IP fija se puede asociar una IP elástica.

---

## 6. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El navegador no abre `:8050` o `:8001` | El puerto no está abierto en el grupo de seguridad, o la IP cambió | Revise las reglas de entrada (sección 2.2) y la IP actual en la consola |
| `permission denied ... docker.sock` | El usuario aún no está en el grupo `docker` | Salga con `exit` y vuelva a entrar por SSH |
| `dvc pull` falla con `does not exist as an output` | Se nombró una carpeta en lugar del objetivo DVC | Use exactamente `dvc pull models.dvc tablero` |
| La construcción falla con `COPY failed: ... models` o `data/tablero` | Falta el `dvc pull` | Ejecute el paso 2.5 y repita `docker compose up -d --build` |
| `docker ps` muestra `unhealthy` en la API | El modelo no cargó | `docker compose logs api` para ver el error |
| El tablero abre pero "Evaluar contrato" no responde | El tablero no alcanza la API | Verifique `docker ps` (API `healthy`) y que `API_URL` sea `http://api:8001` |
| La construcción se queda sin memoria | Instancia muy pequeña | Use `t2.medium` o superior |
