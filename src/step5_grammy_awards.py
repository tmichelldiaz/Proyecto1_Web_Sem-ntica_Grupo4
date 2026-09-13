"""
Paso 5 (alternativa a Wikidata) — Premios Grammy, por canción.

Entrada:  data/processed/step4_lastfm.csv
Salida:   data/processed/step5_grammy_premios.csv  (con las 5 fuentes, sin limpiar
          todavía -- el paso 6 (src/step6_finalize_dataset.py) es el que arma
          dataset_final_enriquecido.csv a partir de este archivo)

A diferencia de Wikidata (que depende de un endpoint público compartido y
puede rechazar o demorar las consultas), esta fuente es un único .csv
histórico de nominaciones/premios Grammy -- se descarga una sola vez, sin
llave de API ni límites de tasa.

Como el dataset de Grammy no trae ningún identificador en común con el
nuestro (ni track_id ni MBID), la unión se hace por TEXTO: se normalizan
título y artista de ambos lados (minúsculas, sin acentos, sin puntuación, sin
paréntesis tipo "(feat. ...)") y se cruzan por título exacto normalizado +
artista contenido en el campo de artista/intérpretes de Grammy. Esto da una
unión a nivel de CANCIÓN (no solo de artista), pero con cobertura parcial:
Grammy nomina un puñado de canciones por año, así que la mayoría de las
100.000 canciones del dataset simplemente no van a tener premio -- eso es
normal y se debe documentar así en el informe.

El archivo que se descarga automáticamente (grammysTo2014.csv) solo lista
GANADORES por categoría y año, no la lista completa de nominados, y llega
hasta el Grammy de 2013 (premios entregados en 2014) -- de ahí en adelante
no hay datos. Si quieren nominados también (no solo ganadores) y/o años más
recientes, pueden bajar a mano cualquier otro CSV de premios Grammy con
columnas year/category/nominee (o title)/artist (o winners)/winner y
ponerlo en data/raw/grammy/grammysTo2014.csv -- el parser detecta los
nombres de columna sin importar mayúsculas ni el orden, y si no encuentra
una columna de tipo booleano "winner" asume que TODO el archivo son
ganadores (que es el caso de este archivo).

Uso:
    python -m src.step5_grammy_awards
"""
from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict

import pandas as pd

from src import config
from src.utils import get_logger, safe_download, add_source, print_coverage

log = get_logger("step5")

CANDIDATE_COLUMNS = {
    "year": ["year"],
    "category": ["category"],
    "nominee": ["nominee", "title", "work", "song", "workname"],
    "artist": ["artist", "workers", "performer", "artists", "winners"],
    "winner": ["winner", "won", "is_winner"],
}


def normalize(text) -> str:
    """minúsculas, sin acentos, sin puntuación, sin paréntesis -- para poder comparar texto."""
    if not isinstance(text, str) or not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"\(.*?\)", " ", text)  # "(feat. x)", "(remix)", etc.
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lower_map = {f.lower(): f for f in fieldnames}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None


def _is_winner(value) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "si", "sí", "winner")


def load_grammy_lookup() -> dict[str, list[dict]]:
    """
    Devuelve {nominee_normalizado: [ {year, category, artist_raw, artist_normalizado, winner}, ... ]}
    """
    ok = safe_download(config.GRAMMY_URL, config.GRAMMY_CSV, log)
    if not ok:
        log.warning(
            "Sin el archivo de premios Grammy no se puede completar este paso automáticamente. "
            "Bájenlo a mano (ver docstring de este archivo) y pónganlo en "
            f"{config.GRAMMY_CSV}"
        )
        return {}

    lookup: dict[str, list[dict]] = defaultdict(list)
    with open(config.GRAMMY_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        col_nominee = _find_column(fieldnames, CANDIDATE_COLUMNS["nominee"])
        col_artist = _find_column(fieldnames, CANDIDATE_COLUMNS["artist"])
        col_year = _find_column(fieldnames, CANDIDATE_COLUMNS["year"])
        col_category = _find_column(fieldnames, CANDIDATE_COLUMNS["category"])
        col_winner = _find_column(fieldnames, CANDIDATE_COLUMNS["winner"])

        if not col_nominee:
            log.warning(
                f"No se encontró una columna de título/nominado en {config.GRAMMY_CSV} "
                f"(columnas disponibles: {fieldnames}). Revisen el archivo a mano."
            )
            return {}

        # Si el archivo NO trae una columna booleana de "ganador" (ej. True/False)
        # separada, asumimos que TODO el archivo son ganadores -- es el caso de
        # grammysTo2014.csv, que solo lista quién ganó cada categoría cada año,
        # sin la lista completa de nominados.
        assume_all_winners = col_winner is None
        if assume_all_winners:
            log.info(
                f"{config.GRAMMY_CSV.name} no trae columna de ganador/nominado por separado; "
                f"se asume que todas las filas son GANADORES."
            )

        n_rows = 0
        for row in reader:
            n_rows += 1
            nominee_norm = normalize(row.get(col_nominee, ""))
            if not nominee_norm:
                continue
            winner = True if assume_all_winners else _is_winner(row.get(col_winner))
            lookup[nominee_norm].append({
                "year": row.get(col_year, "") if col_year else "",
                "category": row.get(col_category, "") if col_category else "",
                "artist_raw": row.get(col_artist, "") if col_artist else "",
                "artist_norm": normalize(row.get(col_artist, "")) if col_artist else "",
                "winner": winner,
            })

    log.info(f"Premios Grammy cargados: {n_rows:,} filas, {len(lookup):,} títulos distintos (normalizados)")
    return lookup


def match_track(title_norm: str, artist_norm: str, lookup: dict[str, list[dict]]) -> list[dict]:
    candidates = lookup.get(title_norm, [])
    if not candidates or not artist_norm:
        return []
    matches = []
    for c in candidates:
        if not c["artist_norm"]:
            continue
        if artist_norm in c["artist_norm"] or c["artist_norm"] in artist_norm:
            matches.append(c)
    return matches


def run() -> pd.DataFrame:
    df = pd.read_csv(config.STEP4_OUT, dtype=str)

    lookup = load_grammy_lookup()

    nominaciones_col, ganados_col, detalle_col = [], [], []
    title_norms = df["title"].map(normalize)
    artist_norms = df["artist_name"].map(normalize)

    for title_norm, artist_norm in zip(title_norms, artist_norms):
        matches = match_track(title_norm, artist_norm, lookup)
        if not matches:
            nominaciones_col.append(0)
            ganados_col.append(0)
            detalle_col.append(None)
        else:
            n_win = sum(1 for m in matches if m["winner"])
            nominaciones_col.append(len(matches))
            ganados_col.append(n_win)
            detalle_col.append(";".join(
                f"{m['year']} {m['category']} ({'ganador' if m['winner'] else 'nominado'})"
                for m in matches
            ))

    df["grammy_nominaciones"] = nominaciones_col
    df["grammy_premios_ganados"] = ganados_col
    df["grammy_detalle"] = detalle_col

    matched_mask = df["grammy_nominaciones"] > 0
    print_coverage(log, "Grammy Awards (premios por canción)", len(df), int(matched_mask.sum()))

    df["fuentes"] = add_source(df["fuentes"], matched_mask, "GrammyAwards")

    df.to_csv(config.STEP5_GRAMMY_OUT, index=False)
    log.info(f"{len(df):,} filas escritas en {config.STEP5_GRAMMY_OUT}")
    log.info("Corran el paso 6 (src/step6_finalize_dataset.py) para generar el dataset final a entregar.")
    return df


if __name__ == "__main__":
    run()
