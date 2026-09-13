"""
Paso 5 — Wikidata (Linked Data real, vía SPARQL).

Entrada:  data/processed/step4_lastfm.csv
Salida:   data/processed/step5_wikidata.csv  (== dataset_final_enriquecido.csv)

A diferencia de los pasos anteriores (archivos estáticos unidos por track_id),
este paso consulta en vivo el endpoint SPARQL público de Wikidata, usando el
identificador de MusicBrainz que YA tenemos (`artist_mbid`) contra la
propiedad P434 ("MusicBrainz artist ID") de Wikidata. Como Wikidata es RDF de
verdad, esto además deja el terreno preparado para la Etapa 3 (enlace con
Linked Data / DBpedia).

Como hay muchas menos artistas únicos que canciones (en grupo_4.csv:
~27.000 artistas para 100.000 canciones), agrupamos los mbid en lotes de
`config.WIKIDATA_BATCH_SIZE` y hacemos una sola consulta SPARQL por lote
(usando VALUES), en vez de una consulta por artista.

El endpoint público de Wikidata (query.wikidata.org) es compartido por todo
el mundo y de vez en cuando responde con errores transitorios (502/503/504,
"Bad Gateway", timeouts) cuando está ocupado o cuando una consulta puntual
sale cara de resolver. Este script:
  1. Reintenta cada lote unas cuantas veces con espera creciente.
  2. Si un lote sigue fallando, lo PARTE EN DOS y reintenta cada mitad por
     separado -- así, si el problema es un solo artista con una consulta
     particularmente cara (por ejemplo, alguien con cientos de premios),
     solo se pierde ese artista puntual y no los otros 49 del lote.

Uso:
    python -m src.step5_wikidata
    python -m src.step5_wikidata --limit-artists 200   # prueba rápida
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time

import pandas as pd
import requests

from src import config
from src.utils import get_logger, add_source, print_coverage

log = get_logger("step5")

# Los géneros/premios/sellos se traen con subconsultas (SELECT anidado) en vez
# de mezclarlos todos en un solo GROUP BY: si un artista tiene, por ejemplo,
# 10 géneros y 8 premios, unirlos directo generaría un producto cruzado de
# 80 filas antes de agrupar -- eso es justo el tipo de consulta que hace que
# Wikidata responda con 502/timeout. Con subconsultas, cada propiedad se
# agrupa por separado y el resultado final tiene una sola fila por artista.
SPARQL_TEMPLATE = """
SELECT ?mbid ?artistLabel ?nationalityLabel ?birthDate ?genres ?awards ?labels
WHERE {{
  VALUES ?mbid {{ {values} }}
  ?artist wdt:P434 ?mbid .
  OPTIONAL {{ ?artist wdt:P27 ?nationality . }}
  OPTIONAL {{ ?artist wdt:P569 ?birthDate . }}
  OPTIONAL {{
    SELECT ?artist (GROUP_CONCAT(DISTINCT ?genreLabel; separator=";") AS ?genres) WHERE {{
      ?artist wdt:P136 ?genre .
      ?genre rdfs:label ?genreLabel .
      FILTER(LANG(?genreLabel) = "es" || LANG(?genreLabel) = "en")
    }} GROUP BY ?artist
  }}
  OPTIONAL {{
    SELECT ?artist (GROUP_CONCAT(DISTINCT ?awardLabel; separator=";") AS ?awards) WHERE {{
      ?artist wdt:P166 ?award .
      ?award rdfs:label ?awardLabel .
      FILTER(LANG(?awardLabel) = "es" || LANG(?awardLabel) = "en")
    }} GROUP BY ?artist
  }}
  OPTIONAL {{
    SELECT ?artist (GROUP_CONCAT(DISTINCT ?labelLabel; separator=";") AS ?labels) WHERE {{
      ?artist wdt:P264 ?label .
      ?label rdfs:label ?labelLabel .
      FILTER(LANG(?labelLabel) = "es" || LANG(?labelLabel) = "en")
    }} GROUP BY ?artist
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}}
"""

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
MIN_BATCH_SIZE = 5  # por debajo de esto, si sigue fallando, se descarta ese mini-lote
POLITE_DELAY_SECONDS = 0.5  # pausa corta entre lotes exitosos, para no saturar el endpoint público


class _RetryableWikidataError(Exception):
    """HTTPError con el status code a la mano, para poder distinguir 504 del resto."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _batch_cache_key(mbids: list[str]) -> str:
    return hashlib.sha1(",".join(sorted(mbids)).encode()).hexdigest()[:16]


def _rows_from_bindings(bindings: list[dict]) -> list[dict]:
    rows = []
    for b in bindings:
        rows.append({
            "artist_mbid": b.get("mbid", {}).get("value"),
            "wd_artist_label": b.get("artistLabel", {}).get("value"),
            "wd_nacionalidad": b.get("nationalityLabel", {}).get("value"),
            "wd_fecha_nacimiento": b.get("birthDate", {}).get("value"),
            "wd_generos": b.get("genres", {}).get("value") or None,
            "wd_premios": b.get("awards", {}).get("value") or None,
            "wd_sellos": b.get("labels", {}).get("value") or None,
        })
    return rows


def _request_once(mbids: list[str]) -> list[dict]:
    """Una sola llamada HTTP al endpoint. Lanza excepción si falla (incluye status reintentable)."""
    values = " ".join(f'"{m}"' for m in mbids)
    query = SPARQL_TEMPLATE.format(values=values)
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": config.WIKIDATA_USER_AGENT,
    }
    resp = requests.get(
        config.WIKIDATA_SPARQL_ENDPOINT,
        params={"query": query},
        headers=headers,
        timeout=90,
    )
    if resp.status_code in RETRYABLE_STATUS:
        raise _RetryableWikidataError(
            resp.status_code, f"{resp.status_code} para {config.WIKIDATA_SPARQL_ENDPOINT}"
        )
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def query_wikidata_batch(mbids: list[str]) -> list[dict]:
    """
    Consulta un lote de mbids, con caché en disco, reintentos con espera
    creciente para errores transitorios, y partición automática en mitades si
    el lote sigue fallando (o de una vez si el error es 504: un timeout
    significa que la consulta salió cara, y reintentar la MISMA consulta del
    mismo tamaño rara vez ayuda -- mejor partirla ya).
    """
    cache_file = config.WIKIDATA_CACHE_DIR / f"batch_{_batch_cache_key(mbids)}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            bindings = _request_once(mbids)
            rows = _rows_from_bindings(bindings)
            cache_file.write_text(json.dumps(rows))
            time.sleep(POLITE_DELAY_SECONDS)  # ser buenos ciudadanos del endpoint público
            return rows
        except _RetryableWikidataError as exc:
            last_exc = exc
            if exc.status_code == 504 and len(mbids) > MIN_BATCH_SIZE:
                log.warning(
                    f"Wikidata devolvió 504 (la consulta tardó demasiado) para un lote de "
                    f"{len(mbids)} mbid; en vez de reintentar la misma consulta, se parte de "
                    f"una vez en mitades más chicas."
                )
                break
            wait = 3 * (2 ** (attempt - 1))  # 3s, 6s, 12s
            log.warning(
                f"Intento {attempt}/{MAX_RETRIES} falló para lote de {len(mbids)} mbid ({exc}); "
                f"esperando {wait}s antes de reintentar..."
            )
            time.sleep(wait)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            wait = 3 * (2 ** (attempt - 1))
            log.warning(
                f"Intento {attempt}/{MAX_RETRIES} falló para lote de {len(mbids)} mbid ({exc}); "
                f"esperando {wait}s antes de reintentar..."
            )
            time.sleep(wait)

    if len(mbids) > MIN_BATCH_SIZE:
        mid = len(mbids) // 2
        log.warning(f"Partiendo lote de {len(mbids)} mbid en dos mitades más chicas ({last_exc}).")
        return query_wikidata_batch(mbids[:mid]) + query_wikidata_batch(mbids[mid:])

    log.warning(
        f"Se descarta un mini-lote de {len(mbids)} mbid tras agotar reintentos y no poder "
        f"partirlo más: {last_exc}. Esos artistas quedarán sin datos de Wikidata."
    )
    return []


def run(limit_artists: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(config.STEP4_OUT, dtype=str)

    artist_ids = df["artist_mbid"].dropna().unique().tolist()
    if limit_artists is not None:
        artist_ids = artist_ids[:limit_artists]
        log.info(f"--limit-artists activo: solo se consultarán {len(artist_ids)} artistas (modo prueba)")

    log.info(f"Consultando Wikidata para {len(artist_ids):,} artistas únicos, en lotes de {config.WIKIDATA_BATCH_SIZE}")

    all_rows: list[dict] = []
    n_batches = (len(artist_ids) - 1) // config.WIKIDATA_BATCH_SIZE + 1 if artist_ids else 0
    for i in range(0, len(artist_ids), config.WIKIDATA_BATCH_SIZE):
        batch = artist_ids[i:i + config.WIKIDATA_BATCH_SIZE]
        all_rows.extend(query_wikidata_batch(batch))
        batch_num = i // config.WIKIDATA_BATCH_SIZE + 1
        if batch_num % 20 == 0 or batch_num == n_batches:
            log.info(f"  ...lote {batch_num}/{n_batches}")

    wd_df = pd.DataFrame(all_rows).drop_duplicates(subset="artist_mbid") if all_rows else pd.DataFrame(columns=["artist_mbid"])
    log.info(f"Wikidata devolvió datos para {len(wd_df):,} artist_mbid")

    df = df.merge(wd_df, on="artist_mbid", how="left")

    matched_mask = df["wd_artist_label"].notna()
    print_coverage(log, "Wikidata (artistas)", len(df), int(matched_mask.sum()))

    df["fuentes"] = add_source(df["fuentes"], matched_mask, "Wikidata")

    df.to_csv(config.STEP5_OUT, index=False)
    df.to_csv(config.FINAL_OUT, index=False)
    log.info(f"{len(df):,} filas escritas en {config.STEP5_OUT}")
    log.info(f"Dataset final: {config.FINAL_OUT}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-artists", type=int, default=None, help="Limitar cantidad de artistas consultados (pruebas rápidas)")
    args = parser.parse_args()
    run(limit_artists=args.limit_artists)
