
from pathlib import Path
import json

from shapely.geometry import shape, mapping

BASE = Path(__file__).resolve().parent

ORIGEN = (
    BASE / "assets" / "geo"
    / "colombia_departamentos.geojson"
)

DESTINO = (
    BASE / "assets" / "geo"
    / "colombia_departamentos_simplificado.geojson"
)

with open(ORIGEN, encoding="utf-8") as archivo:
    geojson = json.load(archivo)

nuevas_features = []

for feature in geojson["features"]:
    propiedades = feature.get("properties", {})

    codigo = str(
        propiedades.get("cod_depart") or ""
    ).strip()

    nombre = str(
        propiedades.get("departamen") or ""
    ).strip()

    # Excluir registro geográfico sin identificación
    if not codigo or not nombre:
        continue

    geometria = shape(feature["geometry"])

    # Simplificación aproximada a 0,005 grados.
    # Se conserva la topología de cada geometría.
    simplificada = geometria.simplify(
        tolerance=0.005,
        preserve_topology=True,
    )

    nueva_feature = {
        "type": "Feature",
        "properties": propiedades,
        "geometry": mapping(simplificada),
    }

    nuevas_features.append(nueva_feature)

resultado = {
    "type": "FeatureCollection",
    "features": nuevas_features,
}

with open(DESTINO, "w", encoding="utf-8") as archivo:
    json.dump(
        resultado,
        archivo,
        ensure_ascii=False,
        separators=(",", ":"),
    )

original_mb = ORIGEN.stat().st_size / (1024 * 1024)
nuevo_mb = DESTINO.stat().st_size / (1024 * 1024)

print(f"Tamaño original: {original_mb:.2f} MB")
print(f"Tamaño simplificado: {nuevo_mb:.2f} MB")
print(f"Geometrías: {len(nuevas_features)}")
print(
    f"Reducción: {(1 - nuevo_mb/original_mb)*100:.1f}%"
)
