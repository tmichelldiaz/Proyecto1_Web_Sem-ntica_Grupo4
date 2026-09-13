"""
Rutas y constantes centrales del pipeline.

La idea: cada script `stepN_*.py` LEE el CSV que dejó el paso anterior en
data/processed/ y ESCRIBE un nuevo CSV con las columnas nuevas que aportó su
fuente, más una columna `fuentes` acumulada que dice de dónde salió cada fila.

Así, en cualquier momento pueden abrir data/processed/stepN_*.csv y ver
exactamente qué llevaba el dataset justo después de integrar la fuente N.
"""

from pathlib import Path

# Carpeta raíz del proyecto (donde está este archivo, subiendo dos niveles)
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# --- Archivo base entregado por el curso ---
GRUPO_CSV = RAW_DIR / "grupo_4.csv"

# --- Paso 0: dataset base normalizado ---
STEP0_OUT = PROCESSED_DIR / "step0_original.csv"

# --- Paso 1: MusicBrainz + AcousticBrainz (vía mapping MSD-to-MB) ---
MSD_TO_MB_DIR = RAW_DIR / "msd_to_mb"
# URL documentada por el autor del mapping (keunwoochoi/MSD-to-MB-mapping).
# Si esta URL cambia, bájenlo a mano y pónganlo en MSD_TO_MB_DIR con el mismo nombre.
MSD_TO_MB_JSON_URL = (
    "https://raw.githubusercontent.com/keunwoochoi/MSD-to-MB-mapping/"
    "master/msd-mbid-2016-01-results-ab.json.bz2"
)
MSD_TO_MB_JSON_FILE = MSD_TO_MB_DIR / "msd-mbid-2016-01-results-ab.json.bz2"

ACOUSTICBRAINZ_CACHE_DIR = RAW_DIR / "acousticbrainz_cache"
ACOUSTICBRAINZ_API = "https://acousticbrainz.org/api/v1"
# AcousticBrainz está en modo solo-lectura desde 2022 (no acepta análisis nuevos).
# Si la API ya no responde en su red, usen el dump masivo (ver README, sección 5).
AB_REQUEST_DELAY_SECONDS = 0.4  # pausa por hilo entre requests -- con varios hilos en paralelo (AB_MAX_WORKERS)
                                 # ya no hace falta que sea tan larga como si fuera un solo hilo
AB_MAX_WORKERS = 16  # hilos en paralelo para consultar AcousticBrainz (en serie, con miles de MBIDs, tarda horas)

STEP1_OUT = PROCESSED_DIR / "step1_musicbrainz_acousticbrainz.csv"

# --- Paso 2: géneros de tagtraum ---
TAGTRAUM_DIR = RAW_DIR / "tagtraum"
# CD2C = combinación de CD1+CD2 con mejor cobertura (ver tagtraum.com/msd_genre_datasets.html)
TAGTRAUM_URL = "https://www.tagtraum.com/genres/msd_tagtraum_cd2c.cls.zip"
TAGTRAUM_ZIP = TAGTRAUM_DIR / "msd_tagtraum_cd2c.cls.zip"

STEP2_OUT = PROCESSED_DIR / "step2_tagtraum_genero.csv"

# --- Paso 3: letras musiXmatch (bag-of-words) ---
MUSIXMATCH_DIR = RAW_DIR / "musixmatch"
MUSIXMATCH_TRAIN_URL = (
    "http://millionsongdataset.com/sites/default/files/AdditionalFiles/"
    "mxm_dataset_train.txt.zip"
)
MUSIXMATCH_TEST_URL = (
    "http://millionsongdataset.com/sites/default/files/AdditionalFiles/"
    "mxm_dataset_test.txt.zip"
)
MUSIXMATCH_TRAIN_ZIP = MUSIXMATCH_DIR / "mxm_dataset_train.txt.zip"
MUSIXMATCH_TEST_ZIP = MUSIXMATCH_DIR / "mxm_dataset_test.txt.zip"

STEP3_OUT = PROCESSED_DIR / "step3_musixmatch_letras.csv"

# --- Paso 4: tags + canciones similares de Last.fm ---
LASTFM_DIR = RAW_DIR / "lastfm"
LASTFM_TRAIN_URL = "http://millionsongdataset.com/sites/default/files/lastfm/lastfm_train.zip"
LASTFM_TEST_URL = "http://millionsongdataset.com/sites/default/files/lastfm/lastfm_test.zip"
LASTFM_TRAIN_ZIP = LASTFM_DIR / "lastfm_train.zip"
LASTFM_TEST_ZIP = LASTFM_DIR / "lastfm_test.zip"

STEP4_OUT = PROCESSED_DIR / "step4_lastfm.csv"

# --- Paso 5: Wikidata (vía SPARQL, usando artist_mbid -> P434) ---
WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_CACHE_DIR = RAW_DIR / "wikidata_cache"
WIKIDATA_BATCH_SIZE = 15  # lotes más chicos = consultas más baratas = menos 502/504 (timeout)
WIKIDATA_USER_AGENT = (
    "ProyectoWebSemanticaMISIS/1.0 (uso academico; contacto: cambiar-email@uniandes.edu.co)"
)

STEP5_OUT = PROCESSED_DIR / "step5_wikidata.csv"

# --- Paso 5 (alternativa): premios Grammy, sin depender de un endpoint en vivo ---
# OJO: este archivo solo lista GANADORES (no nominados) y llega hasta el Grammy
# de 2013 (premios entregados en 2014) -- coincide razonablemente bien con la
# época de las canciones del Million Song Dataset.
GRAMMY_DIR = RAW_DIR / "grammy"
GRAMMY_URL = "https://raw.githubusercontent.com/DanielHadley/Grammys/master/data/grammysTo2014.csv"
GRAMMY_CSV = GRAMMY_DIR / "grammysTo2014.csv"
STEP5_GRAMMY_OUT = PROCESSED_DIR / "step5_grammy_premios.csv"

# --- Paso 6: limpieza final (columnas sin aporte + filas sin enriquecimiento) ---
# ab_* quedó vacío en la corrida final (AcousticBrainz no se completó, ver README);
# letra_disponible/letra_palabras_top solo se usaron para calcular letra_total_palabras
# en el paso 3 y no aportan nada como columnas propias. `fuentes` NUNCA se quita: es
# la columna de trazabilidad que exige el taller.
DROP_COLUMNS_FINAL = [
    "ab_bpm", "ab_key", "ab_scale", "ab_loudness", "ab_danceability", "ab_mood_happy", "ab_mood_sad",
    "letra_disponible", "letra_palabras_top",
]
# Columnas que cuentan como "esta fila sí trajo algo de alguna de las 5 fuentes"
ENRICHMENT_SCORE_COLUMNS = [
    "mb_recording_mbid", "genero_tagtraum", "letra_total_palabras",
    "lastfm_tags", "lastfm_similares", "grammy_detalle",
]
MIN_ROWS_REQUIRED = 75_000  # umbral mínimo de filas que exige el taller

# --- Salida final (después del paso 6: dataset a entregar) ---
FINAL_OUT = PROCESSED_DIR / "dataset_final_enriquecido.csv"

for _dir in (
    RAW_DIR, PROCESSED_DIR, MSD_TO_MB_DIR, ACOUSTICBRAINZ_CACHE_DIR,
    TAGTRAUM_DIR, MUSIXMATCH_DIR, LASTFM_DIR, WIKIDATA_CACHE_DIR, GRAMMY_DIR,
):
    _dir.mkdir(parents=True, exist_ok=True)
