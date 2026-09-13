"""
Paso 2 — Géneros de tagtraum (MAGD/CD2C).

Entrada:  data/processed/step1_musicbrainz_acousticbrainz.csv
Salida:   data/processed/step2_tagtraum_genero.csv

El Million Song Dataset original no trae género confiable. tagtraum publicó
una anotación de género por track_id derivada de AllMusic/Beatport, que es el
estándar de facto que usa la comunidad para tapar ese hueco. Es una unión
directa por track_id, sin API de por medio.

Formato del archivo .cls (una vez descomprimido):
    # comentarios empiezan con '#'
    TRACKID<TAB>GENERO[<TAB>GENERO_ALTERNO]

Uso:
    python -m src.step2_tagtraum_genre
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.utils import get_logger, safe_download, unzip, add_source, print_coverage

log = get_logger("step2")


def parse_cls_file(path) -> dict[str, str]:
    genres: dict[str, str] = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            track_id, *labels = parts
            genres[track_id] = ";".join(l for l in labels if l)
    return genres


def load_tagtraum_genres() -> dict[str, str]:
    ok = safe_download(config.TAGTRAUM_URL, config.TAGTRAUM_ZIP, log)
    if not ok:
        log.warning(
            "Sin el archivo de tagtraum no se puede completar este paso automáticamente. "
            "Bájenlo a mano desde tagtraum.com/msd_genre_datasets.html (ver README)."
        )
        return {}

    if not unzip(config.TAGTRAUM_ZIP, config.TAGTRAUM_DIR, log):
        return {}

    cls_files = list(config.TAGTRAUM_DIR.glob("*.cls"))
    if not cls_files:
        log.warning(f"No se encontró ningún .cls dentro de {config.TAGTRAUM_DIR}")
        return {}

    genres: dict[str, str] = {}
    for cls_file in cls_files:
        genres.update(parse_cls_file(cls_file))
    log.info(f"Géneros tagtraum cargados para {len(genres):,} track_id")
    return genres


def run() -> pd.DataFrame:
    df = pd.read_csv(config.STEP1_OUT, dtype=str)

    genres = load_tagtraum_genres()
    df["genero_tagtraum"] = df["track_id"].map(genres)

    matched_mask = df["genero_tagtraum"].notna()
    print_coverage(log, "tagtraum (género)", len(df), int(matched_mask.sum()))

    df["fuentes"] = add_source(df["fuentes"], matched_mask, "tagtraum")

    df.to_csv(config.STEP2_OUT, index=False)
    log.info(f"{len(df):,} filas escritas en {config.STEP2_OUT}")
    return df


if __name__ == "__main__":
    run()
