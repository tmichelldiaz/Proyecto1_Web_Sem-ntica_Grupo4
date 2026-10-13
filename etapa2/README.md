# Etapa 2 — Ontología musical (Grupo 4)

Web Semántica, MISIS Uniandes. Este proyecto formaliza como ontología (RDF, RDFS y OWL) el modelo conceptual de la Etapa 1, convierte el dataset consolidado en instancias RDF, las carga en Apache Jena Fuseki y responde 8 competency questions con SPARQL.

> **Ubicación:** en el repositorio, esta etapa vive en la carpeta `etapa2/` (la Etapa 1 está en la raíz). Todos los comandos de abajo se ejecutan desde `etapa2/`.

## Contenido

| Ruta | Qué es |
|---|---|
| `ontology.ttl` | Ontología: clases, jerarquías, propiedades, dominios, rangos y axiomas OWL. |
| `instances.ttl` | Instancias generadas desde el dataset de la Etapa 1 (≈1,14 millones de tripletas junto con la ontología). |
| `src/build_ontology.py` | Genera `ontology.ttl` con RDFLib. |
| `src/build_instances.py` | Genera `instances.ttl` a partir de `data/dataset_final_enriquecido.csv`. |
| `src/cargar_fuseki.py` | Carga `ontology.ttl` e `instances.ttl` en Fuseki. |
| `src/ejecutar_consultas.py` | Ejecuta las consultas de `consultas/` y guarda los resultados en `resultados/`. |
| `configuracion.py` | Parámetros de conexión con Fuseki (dataset y endpoints). |
| `consultas/*.rq` | Las 8 competency questions escritas en SPARQL. |
| `resultados/` | Resultado de cada consulta en CSV, más `resultados.md` con consulta y tabla. |
| `docs/competency_questions.md` | Listado de las 8 competency questions. |
| `data/dataset_final_enriquecido.csv` | Dataset consolidado de la Etapa 1 (75.959 canciones tras la limpieza final). |
| `docker-compose.yml` | Fuseki listo para usar (opcional). |

## Requisitos

- Python 3.10 o superior.
- Apache Jena Fuseki 5.x, con un dataset **TDB2** y las actualizaciones habilitadas. Se puede usar el `docker-compose.yml` incluido (necesita Docker) o una instalación propia.

```bash
pip install -r requirements.txt
```

## Cómo reproducir todo

### 1. Levantar Fuseki

**Con Docker** (crea el dataset `musica`, con usuario `admin` y contraseña `admin`):

```bash
docker compose up -d
```

La interfaz queda en http://localhost:3030.

**Con una instalación propia de Fuseki**: crea un dataset (por ejemplo `musica`, tipo TDB2, persistente) desde la interfaz web, o inicia el servidor con actualizaciones habilitadas:

```bash
fuseki-server --update --tdb2 --loc=databases/musica /musica
```

### 2. Revisar `configuracion.py`

Todos los scripts leen los parámetros de este archivo. Si tu Fuseki usa otra URL o nombre de dataset, solo se cambian `FUSEKI_URL` y `NOMBRE_DATASET`. Si no tiene autenticación, se ponen `USUARIO` y `CLAVE` en `None`.

```python
FUSEKI_URL = "http://localhost:3030"
NOMBRE_DATASET = "musica"
```

### 3. Generar los archivos Turtle (opcional)

`ontology.ttl` e `instances.ttl` ya vienen generados. Para regenerarlos, desde la raíz del proyecto:

```bash
python -m src.build_ontology
python -m src.build_instances
```

La generación es determinista: los mismos datos producen los mismos IRIs y el mismo archivo. `build_instances` tarda unos 20 segundos.

### 4. Cargar en Fuseki

```bash
python -m src.cargar_fuseki
```

Reemplaza el contenido del dataset (primero la ontología, luego las instancias), así que se puede repetir. Al final imprime el total de tripletas: **1.145.265**.

### 5. Ejecutar las consultas

```bash
python -m src.ejecutar_consultas
```

Ejecuta cada archivo de `consultas/` contra el endpoint y escribe `resultados/<consulta>.csv` y `resultados/resultados.md`. Todas las consultas tienen `ORDER BY` determinista, así que la respuesta es la misma en cada ejecución. También se pueden pegar directamente en la pestaña *query* de Fuseki.

> Las consultas no dependen de razonamiento (inferencia): las propiedades inversas y los tipos derivados (`CancionConLetra`, `CancionPremiada`) se escriben explícitamente en `instances.ttl`, de modo que funcionan en un Fuseki sin reasoner.

## Las 8 competency questions

| # | Pregunta | Archivo |
|---|---|---|
| CQ1 | ¿Qué canciones de Jazz hay y quiénes son sus artistas? | `cq1_jazz.rq` |
| CQ2 | ¿Cuáles son los 10 artistas con más canciones y en cuántos géneros distintos aparecen? | `cq2_artistas_top.rq` |
| CQ3 | ¿Cuántas canciones hay por década y por género? | `cq3_decada_genero.rq` |
| CQ4 | ¿Qué canciones ganaron un Grammy, en qué año y en qué categoría? | `cq4_grammy.rq` |
| CQ5 | ¿Qué artistas se parecen a Bob Dylan según las etiquetas que comparten sus canciones? | `cq5_artistas_parecidos.rq` |
| CQ6 | ¿Qué álbumes tienen más canciones en el dataset y de qué artista son? | `cq6_albumes_top.rq` |
| CQ7 | ¿Qué género tiene el mayor promedio de palabras en sus letras? | `cq7_letras_genero.rq` |
| CQ8 | ¿Cuáles son las 5 etiquetas de Last.fm más usadas en canciones de Metal? | `cq8_etiquetas_metal.rq` |

## Modelo en una mirada

- **Clases:** `Cancion`, `Artista`, `Album`, `Genero`, `Etiqueta`, `NominacionGrammy`; subclases `CancionConLetra` y `CancionPremiada` de `Cancion`.
- **Propiedades de objeto:** `interpretadaPor` / `interpreta`, `apareceEn` / `contiene`, `lanzadoPor`, `tieneGenero`, `tieneEtiqueta`, `tieneNominacion`.
- **Propiedades de datos:** `titulo`, `anio`, `totalPalabrasLetra`, `idTrack`, `mbidArtista`, `nombre`, `categoria`, `anioNominacion`, `ganada`.
- **OWL:** cardinalidad, propiedades inversas, clase equivalente, clases disjuntas, propiedad funcional y claves (`hasKey`). El detalle y la justificación están en el documento de la entrega.

## Identificadores

Los IRIs de los recursos son estables entre ejecuciones:

| Recurso | IRI |
|---|---|
| Canción | `.../resource/cancion/{track_id}` |
| Artista | `.../resource/artista/{mbid}` |
| Álbum | `.../resource/album/{nombre}-{hash de mbid y nombre}` |
| Género | `.../resource/genero/{nombre}` |
| Etiqueta | `.../resource/etiqueta/{nombre}` |
| Nominación | `.../resource/nominacion/{track_id}-{año}-{categoría}-{hash}` |

## Limitaciones conocidas

- La cobertura del dataset es parcial: género 20 %, etiquetas de Last.fm 52 %, letras 25 %, año 55 %. Una canción sin dato simplemente no tiene la tripleta (no se escribe un valor falso).
- Todas las nominaciones Grammy del dataset son ganadoras; por eso `ganada` es siempre verdadero.
- En el dataset de la Etapa 1, `mb_recording_mbid` coincide con `artist_mbid` en todas las filas, así que no es un identificador de canción y no se incluye en la ontología.
