"""
Funciones compartidas por todos los pasos del pipeline.
"""
from __future__ import annotations

import logging
import sys
import time
import zipfile
import bz2
from pathlib import Path
from typing import Iterable

import requests

try:
    from tqdm import tqdm
except ImportError:  # tqdm es opcional: solo da la barra de progreso bonita
    def tqdm(iterable=None, total=None, unit=None, unit_scale=None, desc=None):
        class _Noop:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def update(self, n):
                pass

        if iterable is not None:
            return iterable
        return _Noop()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def safe_download(url: str, dest: Path, logger: logging.Logger | None = None) -> bool:
    """
    Descarga `url` a `dest` con barra de progreso.
    - Si `dest` ya existe y no está vacío, no vuelve a descargar (idempotente).
    - Si falla (red bloqueada, 403, timeout, etc.) devuelve False en vez de
      reventar el pipeline, para que el script llamador pueda avisar al
      usuario que baje el archivo a mano y lo ponga en `dest`.
    """
    log = logger or get_logger("download")
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and dest.stat().st_size > 0:
        log.info(f"Ya existe {dest.name}, no se vuelve a descargar.")
        return True

    log.info(f"Descargando {url} -> {dest}")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(dest, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc=dest.name
            ) as bar:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)
                    bar.update(len(chunk))
        return True
    except Exception as exc:  # noqa: BLE001 - queremos capturar cualquier falla de red
        log.warning(
            f"No se pudo descargar automáticamente {url} ({exc}). "
            f"Bájenlo manualmente y guárdenlo en: {dest}"
        )
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False


def unzip(zip_path: Path, dest_dir: Path, logger: logging.Logger | None = None) -> bool:
    log = logger or get_logger("unzip")
    if not zip_path.exists():
        return False
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(dest_dir)
        log.info(f"Descomprimido {zip_path.name} en {dest_dir}")
        return True
    except zipfile.BadZipFile:
        log.warning(f"{zip_path} no es un zip válido (¿descarga incompleta o bloqueada?).")
        return False


def read_bz2_text(path: Path) -> Iterable[str]:
    """Itera línea por línea sobre un .bz2 sin cargarlo completo en memoria."""
    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def msd_track_id_to_subpath(track_id: str, suffix: str = ".json") -> str:
    """
    El Million Song Dataset (y varios datasets derivados: Last.fm, letras, etc.)
    distribuyen un archivo por canción, organizados en subcarpetas usando los
    caracteres 3, 4 y 5 del track_id. Ej:

        TRAAAAW128F429D538  ->  A/A/A/TRAAAAW128F429D538.json

    (los dos primeros caracteres siempre son "TR", por eso se ignoran)
    """
    return f"{track_id[2]}/{track_id[3]}/{track_id[4]}/{track_id}{suffix}"


def add_source(fuentes_series, mask, source_name: str):
    """
    Actualiza la columna `fuentes` (texto tipo "MSD;MusicBrainz;tagtraum")
    agregando `source_name` solo en las filas donde `mask` es True y donde
    ese nombre no esté ya presente.
    """
    def _append(value: str, matched: bool) -> str:
        if not matched:
            return value
        parts = [p for p in value.split(";") if p]
        if source_name not in parts:
            parts.append(source_name)
        return ";".join(parts)

    return [
        _append(v, m) for v, m in zip(fuentes_series.tolist(), mask.tolist())
    ]


def print_coverage(logger: logging.Logger, step_name: str, total: int, matched: int):
    pct = (matched / total * 100) if total else 0
    logger.info(
        f"== {step_name}: {matched:,}/{total:,} filas enriquecidas ({pct:.1f}%) =="
    )


def polite_sleep(seconds: float):
    time.sleep(seconds)
