"""Ejecuta las consultas de consultas/*.rq contra Fuseki y guarda los resultados.

Escribe un CSV por consulta en resultados/ y un resumen en resultados/resultados.md.

Uso, desde la raíz del proyecto:
    python -m src.ejecutar_consultas
"""
import csv
from pathlib import Path

import requests

import configuracion as cfg

ROOT = Path(__file__).resolve().parent.parent
CARPETA_CONSULTAS = ROOT / "consultas"
CARPETA_RESULTADOS = ROOT / "resultados"


def ejecutar(consulta: str):
    auth = (cfg.USUARIO, cfg.CLAVE) if cfg.USUARIO else None
    r = requests.post(
        cfg.ENDPOINT_CONSULTA,
        data={"query": consulta},
        headers={"Accept": "application/sparql-results+json"},
        auth=auth, timeout=600,
    )
    r.raise_for_status()
    datos = r.json()
    columnas = datos["head"]["vars"]
    filas = [[fila.get(c, {}).get("value", "") for c in columnas]
             for fila in datos["results"]["bindings"]]
    return columnas, filas


def tabla_markdown(columnas, filas) -> str:
    lineas = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    lineas += ["| " + " | ".join(v.replace("|", "\\|") for v in fila) + " |" for fila in filas]
    return "\n".join(lineas)


def main() -> None:
    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    resumen = ["# Resultados de las consultas\n"]
    for archivo in sorted(CARPETA_CONSULTAS.glob("*.rq")):
        consulta = archivo.read_text(encoding="utf-8")
        columnas, filas = ejecutar(consulta)
        with open(CARPETA_RESULTADOS / f"{archivo.stem}.csv", "w", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            escritor.writerow(columnas)
            escritor.writerows(filas)
        resumen.append(f"## {archivo.stem}\n\n```sparql\n{consulta.strip()}\n```\n\n"
                       f"{len(filas)} filas\n\n{tabla_markdown(columnas, filas)}\n")
        print(f"{archivo.stem}: {len(filas)} filas")
    (CARPETA_RESULTADOS / "resultados.md").write_text("\n".join(resumen), encoding="utf-8")


if __name__ == "__main__":
    main()
