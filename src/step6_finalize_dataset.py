"""
Paso 6 — Limpieza final del dataset consolidado.

Entrada:  data/processed/step5_grammy_premios.csv (salida cruda del paso 5,
          con las columnas de las 5 fuentes, para las 100.000 filas originales)
Salida:   data/processed/dataset_final_enriquecido.csv  (dataset a entregar)

Dos limpiezas, en este orden:

1. Columnas: se quitan las 7 columnas ab_* (AcousticBrainz no devolvió datos
   en esta corrida -- 0% de cobertura, documentado en el informe) y
   letra_disponible / letra_palabras_top (se usaron solo para calcular
   letra_total_palabras en el paso 3, no aportan nada como columnas propias).
   `fuentes` SIEMPRE se conserva: es la columna de trazabilidad que exige el
   taller ("para cada registro deberá ser posible identificar la fuente o
   fuentes de las cuales se obtuvo la información").

2. Filas: se elimina toda fila que no haya obtenido NINGÚN dato de las 5
   fuentes de enriquecimiento (mb_recording_mbid, genero_tagtraum,
   letra_total_palabras, lastfm_tags, lastfm_similares y grammy_detalle
   todas vacías) -- esas filas solo traen lo que ya venía en el CSV
   original, sin aportar nada al ejercicio de integración. Se valida que el
   resultado siga por encima del umbral de 75.000 filas que exige el taller.

IMPORTANTE: nunca abran ni guarden dataset_final_enriquecido.csv en Excel.
Con configuración regional en español, Excel cambia el separador a ";",
trunca los decimales (405.73342 -> 40573342) y traduce True/False a
VERDADERO/FALSO al guardar -- corrompe el archivo en silencio. Para verlo,
usen el asistente "Datos > Desde texto/CSV" de Excel (sin guardar encima), o
directamente pandas/VS Code.

Uso:
    python -m src.step6_finalize_dataset
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.utils import get_logger

log = get_logger("step6")


def run() -> pd.DataFrame:
    df = pd.read_csv(config.STEP5_GRAMMY_OUT, dtype=str, low_memory=False)
    filas_antes = len(df)

    # 1. columnas sin aporte real en esta corrida
    cols_a_quitar = [c for c in config.DROP_COLUMNS_FINAL if c in df.columns]
    df = df.drop(columns=cols_a_quitar)
    log.info(f"Columnas eliminadas ({len(cols_a_quitar)}): {', '.join(cols_a_quitar)}")

    # 2. filas sin ningún dato de enriquecimiento
    score = df[config.ENRICHMENT_SCORE_COLUMNS].notna().sum(axis=1)
    df = df[score > 0].copy()
    filas_despues = len(df)
    log.info(
        f"Filas sin ningún enriquecimiento eliminadas: {filas_antes - filas_despues:,} "
        f"(quedan {filas_despues:,} de {filas_antes:,})"
    )

    if filas_despues < config.MIN_ROWS_REQUIRED:
        log.warning(
            f"ATENCION: el dataset final quedó en {filas_despues:,} filas, por debajo "
            f"del umbral de {config.MIN_ROWS_REQUIRED:,} que exige el taller."
        )
    else:
        log.info(f"OK: {filas_despues:,} filas >= {config.MIN_ROWS_REQUIRED:,} (umbral del taller cumplido).")

    log.info("% de nulos por columna en el dataset final (0% no se lista):")
    nulos_pct = df.isna().mean().mul(100).round(1).sort_values(ascending=False)
    for col, pct in nulos_pct.items():
        if pct > 0:
            log.info(f"  {col:<25} {pct:>5.1f}%")

    df.to_csv(config.FINAL_OUT, index=False)
    log.info(f"Dataset final escrito en {config.FINAL_OUT} ({filas_despues:,} filas x {len(df.columns)} columnas)")
    return df


if __name__ == "__main__":
    run()
