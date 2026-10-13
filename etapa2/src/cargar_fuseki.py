"""Carga ontology.ttl e instances.ttl en el dataset de Fuseki de configuracion.py.

La carga reemplaza el contenido del dataset, así que se puede repetir.
El dataset debe existir con actualización habilitada (ver README).

Uso, desde la raíz del proyecto:
    python -m src.cargar_fuseki
"""
from pathlib import Path

import requests

import configuracion as cfg

ROOT = Path(__file__).resolve().parent.parent
CABECERAS = {"Content-Type": "text/turtle; charset=utf-8"}


def _autenticacion():
    return (cfg.USUARIO, cfg.CLAVE) if cfg.USUARIO else None


def _subir(archivo: Path, reemplazar: bool) -> None:
    metodo = requests.put if reemplazar else requests.post
    with open(archivo, "rb") as f:
        r = metodo(cfg.ENDPOINT_DATOS, params={"default": ""}, data=f,
                   headers=CABECERAS, auth=_autenticacion(), timeout=900)
    r.raise_for_status()
    print(f"cargado: {archivo.name} ({r.status_code})")


def contar_tripletas() -> int:
    r = requests.post(
        cfg.ENDPOINT_CONSULTA,
        data={"query": "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"},
        headers={"Accept": "application/sparql-results+json"},
        auth=_autenticacion(), timeout=300,
    )
    r.raise_for_status()
    return int(r.json()["results"]["bindings"][0]["n"]["value"])


def main() -> None:
    _subir(ROOT / "ontology.ttl", reemplazar=True)
    _subir(ROOT / "instances.ttl", reemplazar=False)
    print(f"tripletas en {cfg.NOMBRE_DATASET}: {contar_tripletas():,}")


if __name__ == "__main__":
    main()
