"""Pruebas de la API contra el contrato. Desde la raíz del repo:  python -m pytest api/tests -q"""
import pytest
from fastapi.testclient import TestClient

from api.esquemas import EJEMPLO
from api.main import app


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:        # el "with" ejecuta el arranque (carga del modelo)
        yield c


def test_health(cliente):
    r = cliente.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["version_modelo"].startswith("secop-prorroga")


def test_opciones(cliente):
    r = cliente.get("/api/v1/opciones/orden")
    assert r.status_code == 200
    assert "Territorial" in r.json()["valores"]
    assert cliente.get("/api/v1/opciones/precio_base").status_code == 404


def test_buscar_entidades(cliente):
    r = cliente.get("/api/v1/entidades", params={"q": "medell", "n": 2})
    assert r.status_code == 200 and len(r.json()) == 2
    assert cliente.get("/api/v1/entidades", params={"q": "me"}).status_code == 422


def test_ver_entidad(cliente):
    assert cliente.get("/api/v1/entidades/702547704").status_code == 200
    assert cliente.get("/api/v1/entidades/no-existe").status_code == 404


def test_evaluar_ejemplo(cliente):
    r = cliente.post("/api/v1/evaluar", json=EJEMPLO)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["nivel"] == "alto"
    assert cuerpo["probabilidad_prorroga"] == pytest.approx(0.5141, abs=1e-3)
    assert 1 <= len(cuerpo["factores"]) <= 3


@pytest.mark.parametrize("cambio", [{"precio_base": 0}, {"fecha_de_firma": "15/10/2024"},
                                    {"departamento": "Narnia"}])
def test_evaluar_rechaza_datos_malos(cliente, cambio):
    assert cliente.post("/api/v1/evaluar", json={**EJEMPLO, **cambio}).status_code == 422
