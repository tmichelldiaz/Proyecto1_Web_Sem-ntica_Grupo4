# Etapa 1 — Enriquecimiento del dataset musical (Grupo 4)

Pipeline reproducible que parte de `grupo_4.csv` (100.000 canciones del Million
Song Dataset) y lo va enriqueciendo **fuente por fuente, en orden**, uniendo
cada una a lo que ya se tenía. Está pensado para abrirse directo en Visual
Studio Code.

## Cómo está armado

Cada fuente es un script independiente en `src/`. El script del paso N lee el
CSV que dejó el paso N-1 en `data/processed/`, le agrega columnas nuevas
(uniéndolas por `track_id` o `mb_recording_mbid`, según la fuente) y escribe
su propio CSV. Así, en cualquier momento pueden abrir `data/processed/stepN_*.csv`
y ver exactamente qué llevaba el dataset justo después de integrar esa fuente.

```
Paso 0  grupo_4.csv (original)
   |    + normaliza columnas, agrega columna "fuentes"
   v
Paso 1  + MusicBrainz (MBID de la grabación) + AcousticBrainz (tempo, tonalidad,
        |  escala, danceability) -- vía el mapeo track_id -> MBID de
        |  MSD-to-MB-mapping, así no hay que hacer matching difuso
   v
Paso 2  + Género (tagtraum) -- une por track_id
   v
Paso 3  + Letras / bag-of-words (musiXmatch) -- une por track_id
   v
Paso 4  + Tags y canciones similares (Last.fm) -- une por track_id
   v
Paso 5  + Premios Grammy (grammysTo2014.csv) -- une por título+artista
        |  normalizados (única fuente sin identificador compartido)
   v
Paso 6  Limpieza final: quita columnas sin aporte (ab_*, letra_disponible,
        |  letra_palabras_top) y filas sin ningún dato de enriquecimiento
   v
data/processed/dataset_final_enriquecido.csv
```

Estas 5 fuentes fueron elegidas como las más rentables de las ~20 investigadas
para el taller: 4 de las 5 se unen directo por `track_id` sin necesidad de
llamar ninguna API en vivo (cero riesgo de rate-limit), y entre las cinco
cubren características acústicas, género, letras, similitud entre canciones y
premios — todo lo que pide el enunciado de la Etapa 1.

**Nota sobre Wikidata:** inicialmente se planeó traer nacionalidad, sello
discográfico y premios del artista vía SPARQL (`src/step5_wikidata.py`,
`artist_mbid` → propiedad P434). El endpoint público (query.wikidata.org)
resultó demasiado inestable para 100.000 consultas incluso con reintentos,
backoff exponencial y lotes más chicos (errores 429/502/504 persistentes). Se
reemplazó por el paso 5 actual (Grammy Awards, dataset estático) para no
depender de un servicio en vivo compartido. `step5_wikidata.py` se deja en el
repo por si más adelante lo quieren retomar con más tiempo y otra red, pero
**no** forma parte del pipeline que corre `run_pipeline.py`.

## 1. Preparar el entorno (en VS Code)

1. Abran esta carpeta en VS Code (`File > Open Folder...`).
2. Instalen la extensión de Python de Microsoft si no la tienen.
3. Abran una terminal (``Ctrl+ ` ``) y creen un entorno virtual:

   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. En VS Code, `Ctrl+Shift+P` → "Python: Select Interpreter" → elijan el de
   `.venv`.

## 2. Correr el pipeline

Todo de una vez (pasos 0 a 6, termina escribiendo el dataset final):

```bash
python -m src.run_pipeline
```

Solo un rango de pasos (por ejemplo, si el paso 1 ya corrió y quieren re-hacer
del 2 en adelante):

```bash
python -m src.run_pipeline --from 2 --to 6
```

Modo prueba rápida (limita las consultas a AcousticBrainz para verificar que
todo el pipeline corre sin esperar horas):

```bash
python -m src.run_pipeline --quick-test
```

También pueden correr cada paso suelto, lo cual es útil para debuggear en
VS Code (ya dejamos configuraciones de debug en `.vscode/launch.json`, F5):

```bash
python -m src.step0_prepare_base
python -m src.step1_musicbrainz_acousticbrainz
python -m src.step2_tagtraum_genre
python -m src.step3_musixmatch_lyrics
python -m src.step4_lastfm
python -m src.step5_grammy_awards
python -m src.step6_finalize_dataset
```

Al final del pipeline completo imprime un resumen así (números reales de la
corrida final del grupo):

```
RESUMEN FINAL — 75,959 canciones
  MillionSongDataset     75,959 filas  (100.0%)
  Last.fm                75,185 filas  ( 99.0%)
  MusicBrainz            25,180 filas  ( 33.1%)
  musiXmatch              24,886 filas  ( 32.8%)
  tagtraum                20,037 filas  ( 26.4%)
  GrammyAwards               136 filas  (  0.2%)
OK: 75,959 filas >= 75,000 (umbral del taller cumplido).
```

(Los porcentajes de este resumen son sobre las 75.959 filas finales, ya
filtradas en el paso 6; el % de cobertura de cada fuente reportado en el
informe de 4 páginas está calculado sobre las 100.000 filas originales, antes
de ese filtro — son dos cosas distintas, ver sección 4.)

## 3. Si la descarga automática falla

Los scripts intentan descargar cada fuente solos. Si su red la bloquea (pasa
en redes universitarias/corporativas, o si el sitio está caído un rato), el
script **no truena**: avisa por consola y deja las columnas de esa fuente
vacías, para que el resto del pipeline siga corriendo. En ese caso, bajen el
archivo a mano y pónganlo en la ruta que indica el mensaje. Las fuentes y sus
páginas de descarga:

| Fuente | Dónde conseguirla | Carpeta destino |
|---|---|---|
| MSD-to-MB mapping | https://github.com/keunwoochoi/MSD-to-MB-mapping (ver Releases/archivos del repo) | `data/raw/msd_to_mb/` |
| tagtraum (género) | https://www.tagtraum.com/msd_genre_datasets.html | `data/raw/tagtraum/` |
| musiXmatch (letras) | http://millionsongdataset.com/musixmatch/ | `data/raw/musixmatch/` |
| Last.fm (tags/similares) | http://millionsongdataset.com/lastfm/ | `data/raw/lastfm/` |
| Grammy Awards | https://github.com/DanielHadley/Grammys (`data/grammysTo2014.csv`) | `data/raw/grammy/` |

Importante: las URLs de descarga directa que usan los scripts (en
`src/config.py`) están documentadas en esas páginas pero son sitios académicos
viejos que a veces reorganizan sus archivos — si alguna cambió, ajusten la
constante correspondiente en `config.py` o descarguen a mano.

**Si su carpeta del proyecto vive dentro de OneDrive/Google Drive/Dropbox**,
tengan en cuenta que el paso 4 (Last.fm) trabaja con un .zip que contiene casi
un millón de archivos .json. El script está hecho para leer esos archivos
directo desde adentro del .zip sin extraerlos a disco, justamente para evitar
que OneDrive intente sincronizar un millón de archivos sueltos uno por uno
(eso sí puede parecer que el script "se cuelga" por horas). Si en algún otro
paso ven que la carpeta `data/raw/` empieza a llenarse de miles de archivos
chiquitos y todo se vuelve lentísimo, es la misma causa: mejor mover la
carpeta del proyecto fuera de la carpeta sincronizada (por ejemplo a
`C:\dev\proyecto_etapa1`) antes de correr el pipeline completo.

AcousticBrainz dejó de aceptar análisis nuevos desde 2022 (proyecto congelado);
en la corrida final del grupo la API no devolvió resultados a tiempo (0 filas,
0.0% de cobertura, documentado así en el informe). Su API de lectura y su dump
histórico siguen disponibles en https://acousticbrainz.org/download — si
quieren intentarlo de nuevo, `src/step1_musicbrainz_acousticbrainz.py` ya
paraleliza las consultas con varios hilos (`config.AB_MAX_WORKERS`) y cachea
en disco por MBID para que sea reanudable si se interrumpe.

**IMPORTANTE — no abran `dataset_final_enriquecido.csv` en Excel.** Con
configuración regional en español, Excel cambia el separador a `;`, trunca
los decimales (`405.73342` → `40573342`) y traduce `True`/`False` a
`VERDADERO`/`FALSO` en cuanto lo guardan — corrompe el archivo en silencio y
sin avisar. Para revisarlo usen el asistente **Datos > Desde texto/CSV** de
Excel (sin guardar encima del original), o ábranlo con pandas/VS Code.

## 4. Columna de trazabilidad (`fuentes`)

Cada fila termina con una columna `fuentes` tipo `MillionSongDataset;MusicBrainz;tagtraum;GrammyAwards`
que dice, canción por canción, de qué fuentes salió información — esto es lo
que pide explícitamente el taller ("para cada registro deberá ser posible
identificar la fuente o fuentes de las cuales se obtuvo la información").
Los identificadores usados para cada unión quedan también como columnas
propias: `mb_recording_mbid` (MusicBrainz/AcousticBrainz, vía el paso 1),
`artist_mbid` (ya venía en el CSV original).

Cobertura por fuente, sobre la corrida completa de 100.000 filas (antes del
filtro de filas del paso 6):

| Fuente | Filas enriquecidas | Cobertura |
|---|---|---|
| MusicBrainz | 25,180 | 25.2% |
| AcousticBrainz | 0 * | 0.0% * |
| tagtraum (género) | 20,037 | 20.0% |
| musiXmatch (letras) | 24,886 | 24.9% |
| Last.fm (tags/similares) | 94,900 | 94.9% |
| Grammy Awards | 136 | 0.1% |

\* AcousticBrainz no devolvió filas en esta corrida (ver nota arriba); no es
obligatoria según el taller.

## 5. Dataset final entregado

`data/processed/dataset_final_enriquecido.csv` (salida del paso 6):
**75,959 filas × 16 columnas** — `track_id, title, artist_name, release,
year, duration, artist_mbid, fuentes, mb_recording_mbid, genero_tagtraum,
letra_total_palabras, lastfm_tags, lastfm_similares, grammy_nominaciones,
grammy_premios_ganados, grammy_detalle`.

Se llega a esas 75,959 filas a partir de las 100,000 originales quitando las
24,041 que no obtuvieron ningún dato de las 5 fuentes de enriquecimiento —
sigue muy por encima del umbral de 75,000 que exige el taller. % de nulos por
columna en el dataset final (el resto de columnas queda 100% poblada):

| Columna | % nulos |
|---|---|
| grammy_detalle | 99.8% |
| genero_tagtraum | 73.6% |
| letra_total_palabras | 67.2% |
| mb_recording_mbid | 66.9% |
| lastfm_tags | 30.9% |
| lastfm_similares | 21.7% |

`grammy_detalle` se conserva a pesar de su altísimo % de nulos: Grammy Awards
solo cubre 136 canciones de las 100.000, pero el taller exige poder
identificar la fuente de cada dato, no cobertura completa por fuente.
`grammy_nominaciones` y `grammy_premios_ganados` sí quedan 100% pobladas (0
por defecto cuando no hay match).

## 6. Pruebas

La lógica de parseo (archivos `.cls` de tagtraum, bag-of-words de musiXmatch,
el mapeo MSD→MusicBrainz, la trazabilidad de fuentes) tiene pruebas
unitarias con datos de ejemplo, sin necesitar red ni los datasets completos:

```bash
pytest -v
```

## 7. Estructura de carpetas

```
proyecto_etapa1/
├── data/
│   ├── raw/            # archivos descargados (no se suben a git, ver .gitignore)
│   │   └── grupo_4.csv # el dataset original del curso, sí se versiona
│   └── processed/       # salida de cada paso (se regenera corriendo el pipeline)
├── src/
│   ├── config.py                        # rutas, URLs y constantes de limpieza
│   ├── utils.py                          # helpers (descarga, provenance, subcarpetas MSD)
│   ├── step0_prepare_base.py
│   ├── step1_musicbrainz_acousticbrainz.py
│   ├── step2_tagtraum_genre.py
│   ├── step3_musixmatch_lyrics.py
│   ├── step4_lastfm.py
│   ├── step5_grammy_awards.py
│   ├── step5_wikidata.py                 # alternativa descartada, no se usa (ver nota arriba)
│   ├── step6_finalize_dataset.py         # limpieza final -> dataset_final_enriquecido.csv
│   └── run_pipeline.py
├── tests/
│   └── test_parsers.py
├── requirements.txt
└── README.md
```

## 8. Modelo conceptual y documento del taller

El modelo conceptual preliminar (grafo RDF/RDFS: clases + propiedades con
dominio/rango + jerarquías `rdfs:subClassOf`) y el documento de máximo 4
páginas exigido por el taller se entregan por separado (no van en este
repo de código). El checklist completo de fuentes evaluadas quedó guardado en
el documento del proyecto "Web Semántica" (`etapa1-fuentes-enriquecimiento.md`),
junto con las ~15 fuentes adicionales que no se automatizaron aquí (Discogs,
Genius, Billboard, etc.) por si quieren sumar más cobertura en la Etapa 2.
