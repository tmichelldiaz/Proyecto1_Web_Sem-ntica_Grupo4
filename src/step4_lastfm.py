"""
Paso 4 — Tags y canciones similares (Last.fm Dataset for MSD).

Entrada:  data/processed/step3_musixmatch_letras.csv
Salida:   data/processed/step4_lastfm.csv

Este dataset trae, para buena parte de las canciones del MSD, un archivo JSON
con tags de usuarios de Last.fm (útil como género/mood "desde otro ángulo",
complementa a tagtraum) y una lista de canciones similares (excelente para
modelar relaciones de "colaboración/similitud" en el grafo de conocimiento).

IMPORTANTE — por qué esta versión NO extrae el .zip a disco:
Los .zip de Last.fm traen casi un millón de archivos .json en total (uno por
canción). Extraerlos todos con zipfile.extractall() es lentísimo, y si la
carpeta del proyecto vive dentro de OneDrive/Google Drive/Dropbox se vuelve
todavía peor: cada uno de esos archivos dispara una sincronización individual
y el paso puede tardar horas o dar la impresión de que el script se colgó.

En vez de eso, este script abre el .zip y arma un índice en memoria
(nombre_de_archivo -> track_id) leyendo solo la LISTA de nombres (que es
rápido, no descomprime nada), y después lee del .zip, uno por uno, solamente
los ~100.000 archivos que sí necesitamos -- sin escribir nada a disco.

Uso:
    python -m src.step4_lastfm
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd

from src import config
from src.utils import get_logger, safe_download, add_source, print_coverage

log = get_logger("step4")

TOP_N_TAGS = 5
TOP_N_SIMILAR = 5


def build_lookup(zf: zipfile.ZipFile) -> dict[str, str]:
    """
    A partir de un .zip YA ABIERTO, arma {track_id: nombre_interno_del_json}
    leyendo solo la lista de nombres (rápido, no descomprime nada), sin
    importar en qué subcarpeta interna del zip haya quedado cada archivo.
    """
    lookup = {}
    for name in zf.namelist():
        if name.endswith(".json"):
            track_id = name.rsplit("/", 1)[-1][: -len(".json")]
            lookup[track_id] = name
    return lookup


def read_track_json(zf: zipfile.ZipFile, member_name: str) -> dict | None:
    try:
        with zf.open(member_name) as f:
            return json.loads(f.read().decode("utf-8", errors="replace"))
    except (KeyError, json.JSONDecodeError, OSError):
        return None


def open_lastfm_archives() -> tuple[zipfile.ZipFile | None, zipfile.ZipFile | None]:
    """Descarga (si hace falta) y ABRE (sin extraer) los .zip de train/test."""
    ok_train = safe_download(config.LASTFM_TRAIN_URL, config.LASTFM_TRAIN_ZIP, log)
    ok_test = safe_download(config.LASTFM_TEST_URL, config.LASTFM_TEST_ZIP, log)
    if not (ok_train or ok_test):
        log.warning(
            "Sin los archivos de Last.fm no se puede completar este paso automáticamente. "
            "Bájenlos a mano desde millionsongdataset.com/lastfm (ver README)."
        )
    zf_train = zipfile.ZipFile(config.LASTFM_TRAIN_ZIP) if ok_train else None
    zf_test = zipfile.ZipFile(config.LASTFM_TEST_ZIP) if ok_test else None
    return zf_train, zf_test


def run() -> pd.DataFrame:
    df = pd.read_csv(config.STEP3_OUT, dtype=str)

    zf_train, zf_test = open_lastfm_archives()
    lookup_train = build_lookup(zf_train) if zf_train else {}
    lookup_test = build_lookup(zf_test) if zf_test else {}
    log.info(
        f"Índice armado sin extraer nada a disco: {len(lookup_train):,} canciones en train, "
        f"{len(lookup_test):,} en test"
    )

    tags_col, similar_col = [], []
    n = len(df)
    for i, track_id in enumerate(df["track_id"], 1):
        data = None
        if track_id in lookup_train:
            data = read_track_json(zf_train, lookup_train[track_id])
        elif track_id in lookup_test:
            data = read_track_json(zf_test, lookup_test[track_id])

        if data is None:
            tags_col.append(None)
            similar_col.append(None)
        else:
            tags = data.get("tags") or []
            # tags viene como lista de [nombre, peso] según la documentación
            tags_sorted = sorted(tags, key=lambda t: -_safe_int(t[1] if len(t) > 1 else 0))[:TOP_N_TAGS]
            tags_col.append(";".join(t[0] for t in tags_sorted if t))

            similars = data.get("similars") or []
            similars_sorted = sorted(similars, key=lambda s: -_safe_float(s[1] if len(s) > 1 else 0))[:TOP_N_SIMILAR]
            similar_col.append(";".join(s[0] for s in similars_sorted if s))

        if i % 20_000 == 0:
            log.info(f"  ...{i:,}/{n:,} canciones revisadas")

    if zf_train:
        zf_train.close()
    if zf_test:
        zf_test.close()

    df["lastfm_tags"] = tags_col
    df["lastfm_similares"] = similar_col

    matched_mask = df["lastfm_tags"].notna() | df["lastfm_similares"].notna()
    print_coverage(log, "Last.fm (tags + similares)", len(df), int(matched_mask.sum()))

    df["fuentes"] = add_source(df["fuentes"], matched_mask, "Last.fm")

    df.to_csv(config.STEP4_OUT, index=False)
    log.info(f"{len(df):,} filas escritas en {config.STEP4_OUT}")
    return df


def _safe_int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _safe_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    run()
