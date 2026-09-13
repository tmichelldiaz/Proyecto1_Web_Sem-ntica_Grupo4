"""
Paso 0 — Prepara el dataset base.

Solo copia grupo_4.csv, valida que las columnas esperadas estén presentes y
agrega la columna `fuentes` que los pasos siguientes irán completando con el
nombre de cada fuente externa que aportó datos a esa fila.

Uso:
    python -m src.step0_prepare_base
"""
import pandas as pd

from src import config
from src.utils import get_logger

log = get_logger("step0")

EXPECTED_COLUMNS = [
    "track_id", "title", "artist_name", "release", "year", "duration", "artist_mbid",
]


def run() -> pd.DataFrame:
    log.info(f"Leyendo {config.GRUPO_CSV}")
    df = pd.read_csv(config.GRUPO_CSV, dtype=str)

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas esperadas en grupo_4.csv: {missing}")

    # year/duration vuelven a numérico donde se pueda
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["duration"] = pd.to_numeric(df["duration"], errors="coerce")

    df["fuentes"] = "MillionSongDataset"

    df.to_csv(config.STEP0_OUT, index=False)
    log.info(f"{len(df):,} filas escritas en {config.STEP0_OUT}")
    return df


if __name__ == "__main__":
    run()
