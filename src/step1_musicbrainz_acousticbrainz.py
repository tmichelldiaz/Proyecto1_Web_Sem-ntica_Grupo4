"""
Paso 1 — MusicBrainz + AcousticBrainz.

Entrada:  data/processed/step0_original.csv
Salida:   data/processed/step1_musicbrainz_acousticbrainz.csv

Qué hace:
  1. Descarga (o usa si ya está local) el mapeo MSD -> MusicBrainz/AcousticBrainz
     de github.com/keunwoochoi/MSD-to-MB-mapping. Ese archivo ya resuelve, para
     ~250.000 track_id del MSD, cuál es el MBID de grabación en MusicBrainz que
     además tiene datos en AcousticBrainz. Con eso NO hay que hacer matching
     difuso por título+artista contra MusicBrainz: se une directo por track_id.
  2. Une esa tabla (track_id -> mb_recording_mbid) contra nuestro dataset.
  3. Para cada mbid encontrado, consulta la API de AcousticBrainz (o el caché
     local si ya se consultó antes) y extrae features acústicas: tempo (bpm),
     tonalidad, escala, sonoridad, danceability.

Nota importante: AcousticBrainz dejó de aceptar análisis nuevos en 2022, pero
el histórico sigue siendo consultable. Si en su red la API no responde,
lean la sección 5 del README para usar el dump masivo en su lugar.

Uso:
    python -m src.step1_musicbrainz_acousticbrainz
    python -m src.step1_musicbrainz_acousticbrainz --limit 500   # prueba rápida
    python -m src.step1_musicbrainz_acousticbrainz --skip-acousticbrainz  # solo MusicBrainz, sin llamadas a la API

Nota de rendimiento: AcousticBrainz se consulta con varios hilos en paralelo
(config.AB_MAX_WORKERS) en vez de uno por uno, porque con decenas de miles de
MBIDs y 2 llamadas HTTP + pausa por cada uno, hacerlo en serie puede tomar
horas. Cada resultado se guarda en disco (data/raw/acousticbrainz_cache/) tan
pronto se consulta, así que si necesitan interrumpir el script (Ctrl+C) y
correrlo de nuevo después, retoma donde iba -- no vuelve a consultar lo que
ya tiene cacheado.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re

import pandas as pd
import requests

from src import config
from src.utils import (
    get_logger, safe_download, read_bz2_text, add_source,
    print_coverage, polite_sleep,
)

log = get_logger("step1")

# El archivo de keunwoochoi/MSD-to-MB-mapping no tiene una forma de JSON fija
# y documentada (a veces los "match" vienen como listas de listas, no como
# diccionarios con claves nombradas, y a veces el archivo entero viene
# "minificado" en una sola línea sin saltos de línea) — en vez de adivinar la
# estructura exacta y romper si cambia, buscamos directamente los dos
# patrones de texto que nos interesan, sin importar en qué nivel de
# anidación estén ni si hay saltos de línea de por medio:
#   - un track_id del MSD:      "TR" + 16 caracteres alfanuméricos
#   - un MBID de MusicBrainz:   un UUID con guiones (8-4-4-4-12)
# IMPORTANTE: se usa un solo patrón combinado con findall/finditer (no
# search) para encontrar TODAS las coincidencias en orden, no solo la
# primera -- si no hay saltos de línea reales, todo el archivo llega como
# una sola "línea" gigante, y con .search() solo se habría encontrado la
# primera canción de las 100.000 (ese fue exactamente el bug reportado).
TRACK_ID_RE = re.compile(r"\bTR[A-Z0-9]{16}\b")
MBID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_COMBINED_RE = re.compile(f"(?:{TRACK_ID_RE.pattern})|(?:{MBID_RE.pattern})")


def load_msd_to_mb_mapping() -> dict[str, str]:
    """
    Devuelve {track_id: mb_recording_mbid}.

    Recorre el archivo línea por línea (sin cargarlo completo en memoria) y
    va llevando cuál es el "track_id actual": cada vez que aparece uno nuevo,
    abre una entrada nueva; el primer MBID que aparezca después de ese
    track_id (y antes del siguiente) se guarda como su mejor match. Como el
    archivo lista las canciones en orden, esto reconstruye la asociación
    correcta sin necesitar parsear el JSON como estructura.
    """
    ok = safe_download(config.MSD_TO_MB_JSON_URL, config.MSD_TO_MB_JSON_FILE, log)
    if not ok:
        log.warning(
            "Sin el mapeo MSD-to-MB no se puede hacer este paso automáticamente. "
            "Bajen el archivo a mano (ver README) y vuelvan a correr este script."
        )
        return {}

    mapping, n_tracks_seen = extract_mapping_from_lines(read_bz2_text(config.MSD_TO_MB_JSON_FILE))

    log.info(
        f"Mapeo MSD->MusicBrainz: {n_tracks_seen:,} track_id vistos en el archivo, "
        f"{len(mapping):,} con al menos un MBID asociado"
    )
    return mapping


def extract_mapping_from_lines(lines) -> tuple[dict[str, str], int]:
    """
    Lógica pura (fácil de probar) del escaneo. Funciona igual si `lines` trae
    muchas líneas cortas (JSON-lines/pretty-print) o una sola línea gigante
    (JSON minificado sin saltos de línea): en cualquier caso se recorren
    TODAS las coincidencias de cada "línea", en el orden en que aparecen.
    """
    mapping: dict[str, str] = {}
    current_track: str | None = None
    n_tracks_seen = 0

    for line in lines:
        for token in _COMBINED_RE.findall(line):
            if TRACK_ID_RE.fullmatch(token):
                current_track = token
                n_tracks_seen += 1
            elif current_track is not None and current_track not in mapping:
                mapping[current_track] = token

    return mapping, n_tracks_seen


def fetch_acousticbrainz_features(mbid: str) -> dict:
    """Consulta (con caché en disco) low-level + high-level de un MBID."""
    cache_file = config.ACOUSTICBRAINZ_CACHE_DIR / f"{mbid}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except json.JSONDecodeError:
            pass

    features: dict = {}
    try:
        low = requests.get(f"{config.ACOUSTICBRAINZ_API}/{mbid}/low-level", timeout=15)
        polite_sleep(config.AB_REQUEST_DELAY_SECONDS)
        if low.status_code == 200:
            lj = low.json()
            features["ab_bpm"] = lj.get("rhythm", {}).get("bpm")
            features["ab_key"] = lj.get("tonal", {}).get("key_key")
            features["ab_scale"] = lj.get("tonal", {}).get("key_scale")
            features["ab_loudness"] = lj.get("lowlevel", {}).get("average_loudness")

        high = requests.get(f"{config.ACOUSTICBRAINZ_API}/{mbid}/high-level", timeout=15)
        polite_sleep(config.AB_REQUEST_DELAY_SECONDS)
        if high.status_code == 200:
            hj = high.json().get("highlevel", {})
            if "danceability" in hj:
                features["ab_danceability"] = hj["danceability"].get("value")
            if "mood_happy" in hj:
                features["ab_mood_happy"] = hj["mood_happy"].get("value")
            if "mood_sad" in hj:
                features["ab_mood_sad"] = hj["mood_sad"].get("value")
    except requests.RequestException as exc:
        log.debug(f"AcousticBrainz falló para {mbid}: {exc}")

    cache_file.write_text(json.dumps(features))
    return features


def run(limit: int | None = None, skip_acousticbrainz: bool = False) -> pd.DataFrame:
    df = pd.read_csv(config.STEP0_OUT, dtype=str)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["duration"] = pd.to_numeric(df["duration"], errors="coerce")

    mapping = load_msd_to_mb_mapping()
    df["mb_recording_mbid"] = df["track_id"].map(mapping)

    matched_mask = df["mb_recording_mbid"].notna()
    print_coverage(log, "MusicBrainz (mapping MSD-to-MB)", len(df), int(matched_mask.sum()))

    ab_cols = ["ab_bpm", "ab_key", "ab_scale", "ab_loudness", "ab_danceability", "ab_mood_happy", "ab_mood_sad"]
    for c in ab_cols:
        df[c] = None

    mbids_to_query = df.loc[matched_mask, "mb_recording_mbid"].dropna().unique().tolist()
    if limit is not None:
        mbids_to_query = mbids_to_query[:limit]
        log.info(f"--limit activo: solo se consultarán {len(mbids_to_query)} MBIDs (modo prueba)")

    ab_results: dict[str, dict] = {}
    if skip_acousticbrainz:
        log.info("--skip-acousticbrainz activo: no se consulta la API, solo queda el match de MusicBrainz.")
    else:
        n_workers = max(1, config.AB_MAX_WORKERS)
        est_seconds = len(mbids_to_query) * config.AB_REQUEST_DELAY_SECONDS * 2 / n_workers
        log.info(
            f"Consultando AcousticBrainz para {len(mbids_to_query):,} MBIDs únicos "
            f"con {n_workers} hilos en paralelo (estimado: ~{est_seconds/60:,.0f} min; "
            f"cada resultado se cachea en disco, así que se puede interrumpir y retomar)..."
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(fetch_acousticbrainz_features, mbid): mbid for mbid in mbids_to_query}
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                mbid = futures[future]
                try:
                    ab_results[mbid] = future.result()
                except Exception as exc:  # no dejar que un solo mbid tumbe todo el paso
                    log.debug(f"AcousticBrainz falló para {mbid}: {exc}")
                    ab_results[mbid] = {}
                if i % 25 == 0 or i == len(mbids_to_query):
                    log.info(f"  ...{i:,}/{len(mbids_to_query):,} MBIDs consultados")

    for c in ab_cols:
        df[c] = df["mb_recording_mbid"].map(lambda m: ab_results.get(m, {}).get(c) if isinstance(m, str) else None)

    ab_matched_mask = df["ab_bpm"].notna() | df["ab_key"].notna()
    print_coverage(log, "AcousticBrainz (features acústicas)", len(df), int(ab_matched_mask.sum()))

    df["fuentes"] = add_source(df["fuentes"], matched_mask, "MusicBrainz")
    df["fuentes"] = add_source(df["fuentes"], ab_matched_mask, "AcousticBrainz")

    df.to_csv(config.STEP1_OUT, index=False)
    log.info(f"{len(df):,} filas escritas en {config.STEP1_OUT}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limitar consultas a AcousticBrainz (pruebas rápidas)")
    parser.add_argument(
        "--skip-acousticbrainz", action="store_true",
        help="No consultar la API de AcousticBrainz (solo deja el match de MusicBrainz, mucho más rápido)",
    )
    args = parser.parse_args()
    run(limit=args.limit, skip_acousticbrainz=args.skip_acousticbrainz)
