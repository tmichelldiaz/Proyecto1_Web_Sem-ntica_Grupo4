"""
Paso 3 — Letras (musiXmatch bag-of-words).

Entrada:  data/processed/step2_tagtraum_genero.csv
Salida:   data/processed/step3_musixmatch_letras.csv

Por licencia, musiXmatch no distribuye el texto completo de las letras, sino
un "bag of words": para cada canción, qué tan seguido aparece cada una de las
5.000 palabras (ya stemizadas) más comunes del dataset. Con eso no podemos
mostrar la letra completa, pero sí derivar features útiles: si la canción
tiene letra disponible, cuántas palabras en total, y cuáles son las palabras
más repetidas (útil, por ejemplo, para clasificar tono/temática).

Formato de mxm_dataset_*.txt (dentro del .zip):
    % palabra1,palabra2,...,palabra5000      <- línea de cabecera (empieza con %)
    # comentario                              <- líneas de comentario
    TRACK_ID,MXM_TRACK_ID,idx:cnt,idx:cnt,... <- una línea por canción

Uso:
    python -m src.step3_musixmatch_lyrics
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.utils import get_logger, safe_download, unzip, add_source, print_coverage

log = get_logger("step3")

TOP_N_WORDS = 10


def parse_mxm_file(path, word_list: list[str] | None, lyrics: dict[str, dict]) -> list[str]:
    """
    Parsea un archivo mxm_dataset_{train,test}.txt.
    Devuelve la lista de palabras (índice 1..5000) leída de la línea de cabecera,
    o reutiliza `word_list` si ya se cargó (train y test comparten diccionario).
    Va llenando `lyrics` con {track_id: {"total_words": int, "top_words": [..]}}.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("%"):
                word_list = line[1:].split(",")
                continue
            if line.startswith("#"):
                continue

            parts = line.split(",")
            if len(parts) < 3:
                continue
            track_id, _mxm_id, *pairs = parts

            counts: dict[str, int] = {}
            total = 0
            for pair in pairs:
                if ":" not in pair:
                    continue
                idx_str, cnt_str = pair.split(":", 1)
                try:
                    idx, cnt = int(idx_str), int(cnt_str)
                except ValueError:
                    continue
                total += cnt
                if word_list and 1 <= idx <= len(word_list):
                    counts[word_list[idx - 1]] = cnt

            top_words = sorted(counts.items(), key=lambda kv: -kv[1])[:TOP_N_WORDS]
            lyrics[track_id] = {
                "total_words": total,
                "top_words": ";".join(w for w, _ in top_words),
            }
    return word_list or []


def load_musixmatch_lyrics() -> dict[str, dict]:
    ok_train = safe_download(config.MUSIXMATCH_TRAIN_URL, config.MUSIXMATCH_TRAIN_ZIP, log)
    ok_test = safe_download(config.MUSIXMATCH_TEST_URL, config.MUSIXMATCH_TEST_ZIP, log)
    if not (ok_train or ok_test):
        log.warning(
            "Sin los archivos de musiXmatch no se puede completar este paso automáticamente. "
            "Bájenlos a mano desde millionsongdataset.com/musixmatch (ver README)."
        )
        return {}

    if ok_train:
        unzip(config.MUSIXMATCH_TRAIN_ZIP, config.MUSIXMATCH_DIR, log)
    if ok_test:
        unzip(config.MUSIXMATCH_TEST_ZIP, config.MUSIXMATCH_DIR, log)

    txt_files = list(config.MUSIXMATCH_DIR.glob("mxm_dataset_*.txt"))
    if not txt_files:
        log.warning(f"No se encontró ningún mxm_dataset_*.txt dentro de {config.MUSIXMATCH_DIR}")
        return {}

    lyrics: dict[str, dict] = {}
    word_list: list[str] = []
    for txt_file in txt_files:
        word_list = parse_mxm_file(txt_file, word_list, lyrics) or word_list

    log.info(f"Letras (bag-of-words) cargadas para {len(lyrics):,} track_id")
    return lyrics


def run() -> pd.DataFrame:
    df = pd.read_csv(config.STEP2_OUT, dtype=str)

    lyrics = load_musixmatch_lyrics()
    # letra_disponible y letra_palabras_top no se guardan como columnas del CSV final
    # (a pedido del equipo); igual se calculan aquí para medir cobertura y para
    # armar letra_total_palabras, que sí se conserva.
    letra_disponible = df["track_id"].isin(lyrics.keys())
    df["letra_total_palabras"] = df["track_id"].map(lambda t: lyrics.get(t, {}).get("total_words"))

    matched_mask = letra_disponible
    print_coverage(log, "musiXmatch (letras)", len(df), int(matched_mask.sum()))

    df["fuentes"] = add_source(df["fuentes"], matched_mask, "musiXmatch")

    df.to_csv(config.STEP3_OUT, index=False)
    log.info(f"{len(df):,} filas escritas en {config.STEP3_OUT}")
    return df


if __name__ == "__main__":
    run()
