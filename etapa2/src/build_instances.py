"""Genera instances.ttl a partir del dataset consolidado de la Etapa 1.

El Turtle se escribe directamente, sin construir un grafo en memoria: son
más de un millón de tripletas.

Uso, desde la raíz del proyecto:
    python -m src.build_instances
"""
import csv
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "dataset_final_enriquecido.csv"
OUTPUT = ROOT / "instances.ttl"

# Mismo criterio del paso 6 de la Etapa 1: se descartan las canciones que no
# obtuvieron ningún dato de las fuentes de enriquecimiento.
COLUMNAS_ENRIQUECIMIENTO = (
    "mb_recording_mbid", "genero_tagtraum", "letra_total_palabras",
    "lastfm_tags", "lastfm_similares", "grammy_detalle",
)

BASE_RECURSOS = "http://example.org/musica/resource/"
TIPOS_RECURSO = ("cancion", "artista", "album", "genero", "etiqueta", "nominacion")
PREFIJOS = (
    "@prefix mus: <http://example.org/musica/ontology#> .\n"
    "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
    + "".join(f"@prefix {t}: <{BASE_RECURSOS}{t}/> .\n" for t in TIPOS_RECURSO)
    + "\n"
)

PATRON_TRACK = r"[A-Za-z0-9]+"
PATRON_MBID = r"[0-9a-fA-F-]+"
PATRON_ANIO = re.compile(r"^\d{4}$")
PATRON_GRAMMY = re.compile(r"^(\d{4}) (.+) \(([^()]*)\)$")


def slug(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sin_acentos.lower()).strip("-")


def hash_corto(texto: str, largo: int = 8) -> str:
    return hashlib.md5(texto.encode("utf-8")).hexdigest()[:largo]


def literal(texto: str) -> str:
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", texto)
    texto = (texto.replace("\\", "\\\\").replace('"', '\\"')
             .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))
    return f'"{texto}"'


def identificador(valor: str, patron: str) -> str:
    if not re.fullmatch(patron, valor):
        raise ValueError(f"identificador inesperado: {valor!r}")
    return valor


def id_con_slug(texto: str, semilla: str, largo_slug: int = 50) -> str:
    base = slug(texto)[:largo_slug].strip("-") or "sin-nombre"
    return f"{base}-{hash_corto(semilla)}"


def filas_enriquecidas():
    csv.field_size_limit(10**9)
    with open(DATASET, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            if any(fila[c].strip() for c in COLUMNAS_ENRIQUECIMIENTO):
                yield fila


def nominaciones(detalle: str):
    if not detalle.strip():
        return
    for entrada in detalle.split(";"):
        m = PATRON_GRAMMY.match(entrada.strip())
        if not m:
            raise ValueError(f"grammy_detalle no reconocido: {entrada!r}")
        yield m.group(1), m.group(2), m.group(3) == "ganador"


class Escritor:
    def __init__(self, destino):
        self.destino = destino
        self.tripletas = 0

    def bloque(self, sujeto: str, pares: list) -> None:
        lineas = []
        for predicado, objetos in pares:
            lineas.append(f"{predicado} {', '.join(objetos)}")
            self.tripletas += len(objetos)
        self.destino.write(sujeto + " " + " ;\n    ".join(lineas) + " .\n")


def main() -> None:
    nombres_artista = defaultdict(Counter)
    canciones_de_artista = defaultdict(list)
    albumes = {}
    canciones_de_album = defaultdict(list)
    generos = {}
    etiquetas = {}
    nomin = []
    n_canciones = 0

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as out:
        out.write(PREFIJOS)
        w = Escritor(out)

        for fila in filas_enriquecidas():
            n_canciones += 1
            tid = identificador(fila["track_id"], PATRON_TRACK)
            mbid_artista = identificador(fila["artist_mbid"].lower(), PATRON_MBID)
            cancion = f"cancion:{tid}"

            nombres_artista[mbid_artista][fila["artist_name"]] += 1
            canciones_de_artista[mbid_artista].append(tid)

            release = fila["release"]
            album_id = id_con_slug(release, f"{mbid_artista}|{release}")
            albumes[album_id] = (release, mbid_artista)
            canciones_de_album[album_id].append(tid)

            tipos = ["mus:Cancion"]
            pares = [
                ("a", tipos),
                ("mus:titulo", [literal(fila["title"])]),
                ("mus:idTrack", [literal(tid)]),
            ]
            if PATRON_ANIO.match(fila["year"]) and int(fila["year"]) > 0:
                pares.append(("mus:anio", [f'"{fila["year"]}"^^xsd:gYear']))
            if fila["letra_total_palabras"].strip():
                tipos.append("mus:CancionConLetra")
                pares.append(("mus:totalPalabrasLetra", [str(int(fila["letra_total_palabras"]))]))
            pares.append(("mus:interpretadaPor", [f"artista:{mbid_artista}"]))
            pares.append(("mus:apareceEn", [f"album:{album_id}"]))

            genero = fila["genero_tagtraum"].strip()
            if genero:
                clave = slug(genero)
                generos.setdefault(clave, genero)
                pares.append(("mus:tieneGenero", [f"genero:{clave}"]))

            claves_etiqueta = []
            for etiqueta in fila["lastfm_tags"].split(";"):
                etiqueta = etiqueta.strip()
                if not etiqueta:
                    continue
                clave = slug(etiqueta) or f"t-{hash_corto(etiqueta)}"
                etiquetas.setdefault(clave, etiqueta)
                if clave not in claves_etiqueta:
                    claves_etiqueta.append(clave)
            if claves_etiqueta:
                pares.append(("mus:tieneEtiqueta", [f"etiqueta:{c}" for c in claves_etiqueta]))

            ids_nominacion = []
            for anio, categoria, ganada in nominaciones(fila["grammy_detalle"]):
                nid = f"{tid}-{anio}-{id_con_slug(categoria, categoria, 40)}"
                ids_nominacion.append(f"nominacion:{nid}")
                nomin.append((nid, categoria, anio, ganada))
                if ganada and "mus:CancionPremiada" not in tipos:
                    tipos.append("mus:CancionPremiada")
            if ids_nominacion:
                pares.append(("mus:tieneNominacion", ids_nominacion))

            w.bloque(cancion, pares)

        for mbid in sorted(nombres_artista):
            nombre = sorted(nombres_artista[mbid].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            w.bloque(f"artista:{mbid}", [
                ("a", ["mus:Artista"]),
                ("mus:nombre", [literal(nombre)]),
                ("mus:mbidArtista", [literal(mbid)]),
                ("mus:interpreta", [f"cancion:{t}" for t in sorted(canciones_de_artista[mbid])]),
            ])

        for album_id in sorted(albumes):
            nombre, mbid = albumes[album_id]
            w.bloque(f"album:{album_id}", [
                ("a", ["mus:Album"]),
                ("mus:nombre", [literal(nombre)]),
                ("mus:lanzadoPor", [f"artista:{mbid}"]),
                ("mus:contiene", [f"cancion:{t}" for t in sorted(canciones_de_album[album_id])]),
            ])

        for clave in sorted(generos):
            w.bloque(f"genero:{clave}", [("a", ["mus:Genero"]), ("mus:nombre", [literal(generos[clave])])])

        for clave in sorted(etiquetas):
            w.bloque(f"etiqueta:{clave}", [("a", ["mus:Etiqueta"]), ("mus:nombre", [literal(etiquetas[clave])])])

        for nid, categoria, anio, ganada in sorted(nomin):
            w.bloque(f"nominacion:{nid}", [
                ("a", ["mus:NominacionGrammy"]),
                ("mus:categoria", [literal(categoria)]),
                ("mus:anioNominacion", [f'"{anio}"^^xsd:gYear']),
                ("mus:ganada", ["true" if ganada else "false"]),
            ])

    print(f"{OUTPUT} escrito")
    print(f"canciones: {n_canciones:,} | artistas: {len(nombres_artista):,} | álbumes: {len(albumes):,}")
    print(f"géneros: {len(generos)} | etiquetas: {len(etiquetas):,} | nominaciones: {len(nomin)}")
    print(f"tripletas: {w.tripletas:,}")


if __name__ == "__main__":
    main()
