# Competency questions — Etapa 2

**Producto de referencia:** explorador musical que permite descubrir canciones y artistas por género, etiquetas y premios, y recomendar artistas parecidos.

**Datos de partida:** dataset consolidado de la Etapa 1 (75.959 canciones tras la limpieza del paso 6).

| # | Pregunta | Qué le exige al modelo |
|---|---|---|
| CQ1 | ¿Qué canciones de Jazz hay y quiénes son sus artistas? | Canción → Género, Canción → Artista |
| CQ2 | ¿Cuáles son los 10 artistas con más canciones y en cuántos géneros distintos aparecen? | Agregación a través de Artista → Canción → Género |
| CQ3 | ¿Cuántas canciones hay por década y por género? | Año numérico, agrupación; año desconocido no es "falso" |
| CQ4 | ¿Qué canciones ganaron un Grammy, en qué año y en qué categoría? | Clase de nominación (grabación, categoría, año, ganó o no) |
| CQ5 | ¿Qué artistas se parecen a un artista dado (p. ej. Bob Dylan) según las etiquetas que comparten sus canciones? | Canción → Etiqueta, agregación por artista |
| CQ6 | ¿Qué álbumes tienen más canciones en el dataset y de qué artista son? | Clase Álbum; el álbum solo tiene nombre, se distingue por nombre + artista |
| CQ7 | ¿Qué género tiene el mayor promedio de palabras en sus letras? | Propiedad de datos con el total de palabras, AVG por género |
| CQ8 | ¿Cuáles son las 5 etiquetas de Last.fm más usadas en canciones de Metal? | Cruce Género ↔ Etiqueta, agregación |

## Notas de cobertura de los datos

- Género (tagtraum): 20 % de las canciones.
- Etiquetas de Last.fm: 52 %.
- Letra (total de palabras): 25 %.
- Año: 55 % (casi todo 1990-2009).
- Grammy: 136 canciones.
