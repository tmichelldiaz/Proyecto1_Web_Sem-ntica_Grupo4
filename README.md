# Etapa 1 — Enriquecimiento del dataset musical (Grupo 4)

Pipeline reproducible que parte de `grupo_4.csv` (100.000 canciones del Million
Song Dataset) y lo va enriqueciendo **fuente por fuente, en orden**, uniendo
cada una a lo que ya se tenía. Está pensado para abrirse directo en Visual
Studio Code.

## Cómo está armado

Cada fuente es un script independiente en `src/`. El script del paso N lee el
CSV que dejó el paso N-1 en `data/processed/`, le agrega columnas nuevas
(uniéndolas por `track_id` o `mb_recording_mbid`, según la fuente) y escribe
su propio CSV.

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

`src/step5_wikidata.py` es una alternativa que se descartó (endpoint SPARQL
público muy inestable) y **no** corre como parte de `run_pipeline.py` — se
dejó en el repo solo por si más adelante la quieren retomar.

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

Al final del pipeline completo imprime un resumen de cobertura por fuente y
confirma si el dataset final quedó por encima del umbral de 75,000 filas que
exige el taller (los números concretos de esta corrida están en el informe).

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

AcousticBrainz dejó de aceptar análisis nuevos desde 2022 (proyecto congelado).
Si la API en vivo no les responde, `src/step1_musicbrainz_acousticbrainz.py`
ya paraleliza las consultas con varios hilos (`config.AB_MAX_WORKERS`) y
cachea en disco por MBID para que sea reanudable si se interrumpe; también
pueden bajar el dump histórico (https://acousticbrainz.org/download) y
adaptar `fetch_acousticbrainz_features` para leer de ahí en vez de la API.

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

`data/processed/dataset_final_enriquecido.csv` (salida del paso 6) es el
dataset a entregar. El detalle de filas/columnas finales, cobertura por
fuente y % de nulos está en el informe, no aquí.

## 5. Pruebas

La lógica de parseo (archivos `.cls` de tagtraum, bag-of-words de musiXmatch,
el mapeo MSD→MusicBrainz, la trazabilidad de fuentes) tiene pruebas
unitarias con datos de ejemplo, sin necesitar red ni los datasets completos:

```bash
pytest -v
```

## 6. Estructura de carpetas

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
