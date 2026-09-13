"""
Corre los 7 pasos en orden (0 -> 6), cada uno alimentándose del CSV que dejó
el anterior, y al final imprime un resumen de cobertura por fuente. El paso 6
es limpieza final (columnas sin aporte + filas sin ningún enriquecimiento) y
es el que efectivamente escribe dataset_final_enriquecido.csv.

Uso:
    python -m src.run_pipeline                  # corre todo, de punta a punta
    python -m src.run_pipeline --from 2 --to 4   # solo pasos 2, 3 y 4
    python -m src.run_pipeline --quick-test      # con límites bajos, para probar que todo corre
"""
from __future__ import annotations

import argparse

import pandas as pd

from src import config
from src.utils import get_logger
from src import (
    step0_prepare_base,
    step1_musicbrainz_acousticbrainz,
    step2_tagtraum_genre,
    step3_musixmatch_lyrics,
    step4_lastfm,
    step5_grammy_awards,
    step6_finalize_dataset,
)

log = get_logger("pipeline")

STEPS = {
    0: ("Dataset base", step0_prepare_base.run),
    1: ("MusicBrainz + AcousticBrainz", step1_musicbrainz_acousticbrainz.run),
    2: ("tagtraum (género)", step2_tagtraum_genre.run),
    3: ("musiXmatch (letras)", step3_musixmatch_lyrics.run),
    4: ("Last.fm (tags + similares)", step4_lastfm.run),
    5: ("Grammy Awards (premios por canción)", step5_grammy_awards.run),
    6: ("Limpieza final (columnas sin aporte + filas sin enriquecimiento)", step6_finalize_dataset.run),
}
# Nota: Wikidata (src/step5_wikidata.py) se dejó de usar por lo inestable que
# resultó el endpoint público el día que se corrió el pipeline (ver el chat/
# bitácora del proyecto). El archivo sigue en el repo por si más adelante
# quieren retomarlo con más tiempo y una red distinta.


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print(f"RESUMEN FINAL — {len(df):,} canciones")
    print("=" * 60)
    if "fuentes" in df.columns:
        from collections import Counter
        counter = Counter()
        for fuentes in df["fuentes"].dropna():
            for f in fuentes.split(";"):
                counter[f] += 1
        for fuente, n in counter.most_common():
            print(f"  {fuente:<20} {n:>7,} filas  ({n/len(df)*100:5.1f}%)")
    print("=" * 60)
    if len(df) < config.MIN_ROWS_REQUIRED:
        print(f"ATENCION: el dataset final tiene menos de {config.MIN_ROWS_REQUIRED:,} filas — revisar el umbral del taller.")
    else:
        print(f"OK: {len(df):,} filas >= {config.MIN_ROWS_REQUIRED:,} (umbral del taller cumplido).")


def run(start: int, end: int, quick_test: bool = False) -> None:
    df = None
    for i in range(start, end + 1):
        name, fn = STEPS[i]
        log.info(f"\n----- Paso {i}: {name} -----")
        if quick_test and i == 1:
            df = fn(limit=300)
        else:
            df = fn()

    if df is None and end == max(STEPS):
        df = pd.read_csv(config.FINAL_OUT, dtype=str)
    if df is not None:
        print_summary(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="start", type=int, default=0)
    parser.add_argument("--to", dest="end", type=int, default=6)
    parser.add_argument("--quick-test", action="store_true",
                         help="Limita las consultas a APIs (AcousticBrainz/Wikidata) para probar rápido que el pipeline corre")
    args = parser.parse_args()
    run(args.start, args.end, quick_test=args.quick_test)
