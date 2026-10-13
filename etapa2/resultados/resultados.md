# Resultados de las consultas

## cq1_jazz

```sparql
PREFIX mus:    <http://example.org/musica/ontology#>
PREFIX genero: <http://example.org/musica/resource/genero/>

# CQ1: ¿Qué canciones de Jazz hay y quiénes son sus artistas? (primeras 20)
SELECT ?titulo ?artista
WHERE {
  ?cancion a mus:Cancion ;
           mus:tieneGenero genero:jazz ;
           mus:titulo ?titulo ;
           mus:interpretadaPor ?a .
  ?a mus:nombre ?artista .
}
ORDER BY ?artista ?titulo ?cancion
LIMIT 20
```

20 filas

| titulo | artista |
|---|---|
| Where You At | 23 Skidoo |
| Dance With Me | 3rd Force |
| Is She Ready? | 3rd Force |
| Fever | A Fine Frenzy |
| Blue Monk | Abbey Lincoln |
| You Made Me Funny | Abbey Lincoln |
| Only In My Dreams | Acoustic Alchemy |
| Shelter Island Drive | Acoustic Alchemy |
| The Detroit Shuffle | Acoustic Alchemy |
| The Velvet Swing | Acoustic Alchemy |
| Hiphopanonamous | Addison Groove Project |
| Autumn Leaves | Ahmad Jamal |
| Moonlight In Vermont | Ahmad Jamal |
| Someday | Akiko Yano |
| Yokogao (Profile) | Akiko Yano |
| Short Tales Of The Black Forest | Al Di Meola |
| The Wizard | Al Di Meola |
| Two To Tango | Al Di Meola |
| 3 in 4 | Alain Caron |
| Black Paws | Alain Caron |

## cq2_artistas_top

```sparql
PREFIX mus: <http://example.org/musica/ontology#>

# CQ2: ¿Cuáles son los 10 artistas con más canciones y en cuántos géneros distintos aparecen?
SELECT ?artista (COUNT(DISTINCT ?cancion) AS ?canciones) (COUNT(DISTINCT ?genero) AS ?generos)
WHERE {
  ?a a mus:Artista ;
     mus:nombre ?artista ;
     mus:interpreta ?cancion .
  OPTIONAL { ?cancion mus:tieneGenero ?genero }
}
GROUP BY ?a ?artista
ORDER BY DESC(?canciones) ?artista ?a
LIMIT 10
```

10 filas

| artista | canciones | generos |
|---|---|---|
| Joan Baez | 27 | 1 |
| Duran Duran | 26 | 2 |
| Beyoncé | 25 | 2 |
| Bob Dylan | 25 | 2 |
| Aerosmith | 24 | 1 |
| Faron Young | 24 | 1 |
| The Smashing Pumpkins | 24 | 1 |
| Neil Young | 23 | 1 |
| The Doors | 23 | 1 |
| Dolly Parton | 22 | 1 |

## cq3_decada_genero

```sparql
PREFIX mus: <http://example.org/musica/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

# CQ3: ¿Cuántas canciones hay por década y por género?
# El año es xsd:gYear: se convierte a entero antes de operar, porque comparar
# gYear directamente puede descartar filas sin avisar.
SELECT ?decada ?genero (COUNT(?cancion) AS ?canciones)
WHERE {
  ?cancion mus:anio ?anio ;
           mus:tieneGenero ?g .
  ?g mus:nombre ?genero .
  BIND(xsd:integer(FLOOR(xsd:integer(STR(?anio)) / 10)) * 10 AS ?decada)
}
GROUP BY ?decada ?genero
ORDER BY ?decada ?genero
```

96 filas

| decada | genero | canciones |
|---|---|---|
| 1920 | Blues | 7 |
| 1920 | Reggae | 1 |
| 1930 | Blues | 12 |
| 1930 | Jazz | 2 |
| 1940 | Blues | 10 |
| 1940 | Country | 5 |
| 1940 | Jazz | 5 |
| 1950 | Blues | 13 |
| 1950 | Country | 10 |
| 1950 | Folk | 4 |
| 1950 | Jazz | 44 |
| 1950 | RnB | 5 |
| 1950 | Rock | 17 |
| 1960 | Blues | 52 |
| 1960 | Country | 29 |
| 1960 | Electronic | 1 |
| 1960 | Folk | 42 |
| 1960 | Jazz | 64 |
| 1960 | Latin | 2 |
| 1960 | Pop | 11 |
| 1960 | Reggae | 6 |
| 1960 | RnB | 68 |
| 1960 | Rock | 122 |
| 1960 | World | 1 |
| 1970 | Blues | 19 |
| 1970 | Country | 41 |
| 1970 | Electronic | 4 |
| 1970 | Folk | 35 |
| 1970 | Jazz | 83 |
| 1970 | Latin | 10 |
| 1970 | Metal | 10 |
| 1970 | New Age | 3 |
| 1970 | Pop | 41 |
| 1970 | Punk | 17 |
| 1970 | Reggae | 33 |
| 1970 | RnB | 129 |
| 1970 | Rock | 458 |
| 1970 | World | 3 |
| 1980 | Blues | 30 |
| 1980 | Country | 51 |
| 1980 | Electronic | 26 |
| 1980 | Folk | 23 |
| 1980 | Jazz | 103 |
| 1980 | Latin | 5 |
| 1980 | Metal | 56 |
| 1980 | New Age | 23 |
| 1980 | Pop | 90 |
| 1980 | Punk | 61 |
| 1980 | Rap | 25 |
| 1980 | Reggae | 59 |
| 1980 | RnB | 71 |
| 1980 | Rock | 708 |
| 1980 | World | 4 |
| 1990 | Blues | 178 |
| 1990 | Country | 236 |
| 1990 | Electronic | 412 |
| 1990 | Folk | 64 |
| 1990 | Jazz | 372 |
| 1990 | Latin | 67 |
| 1990 | Metal | 206 |
| 1990 | New Age | 35 |
| 1990 | Pop | 205 |
| 1990 | Punk | 90 |
| 1990 | Rap | 213 |
| 1990 | Reggae | 173 |
| 1990 | RnB | 138 |
| 1990 | Rock | 1618 |
| 1990 | World | 54 |
| 2000 | Blues | 145 |
| 2000 | Country | 333 |
| 2000 | Electronic | 1476 |
| 2000 | Folk | 198 |
| 2000 | Jazz | 490 |
| 2000 | Latin | 108 |
| 2000 | Metal | 611 |
| 2000 | New Age | 32 |
| 2000 | Pop | 753 |
| 2000 | Punk | 108 |
| 2000 | Rap | 585 |
| 2000 | Reggae | 287 |
| 2000 | RnB | 390 |
| 2000 | Rock | 3620 |
| 2000 | World | 76 |
| 2010 | Blues | 2 |
| 2010 | Country | 19 |
| 2010 | Electronic | 56 |
| 2010 | Folk | 4 |
| 2010 | Jazz | 7 |
| 2010 | Metal | 17 |
| 2010 | Pop | 11 |
| 2010 | Punk | 1 |
| 2010 | Rap | 11 |
| 2010 | Reggae | 2 |
| 2010 | RnB | 8 |
| 2010 | Rock | 125 |
| 2010 | World | 3 |

## cq4_grammy

```sparql
PREFIX mus: <http://example.org/musica/ontology#>

# CQ4: ¿Qué canciones ganaron un Grammy, en qué año y en qué categoría? (primeras 20)
SELECT ?titulo ?artista ?anio ?categoria
WHERE {
  ?cancion mus:tieneNominacion ?n ;
           mus:titulo ?titulo ;
           mus:interpretadaPor ?a .
  ?a mus:nombre ?artista .
  ?n mus:ganada true ;
     mus:anioNominacion ?anio ;
     mus:categoria ?categoria .
}
ORDER BY ?anio ?categoria ?titulo ?artista ?cancion
LIMIT 20
```

20 filas

| titulo | artista | anio | categoria |
|---|---|---|---|
| Tom Dooley | Kingston Trio | 1958 | Best Country & Western Performance |
| El Paso | Marty Robbins | 1960 | Best Country & Western Performance |
| Big Bad John | Jimmy Dean | 1961 | Best Country & Western Recording |
| Days Of Wine And Roses | Henry Mancini | 1963 | Best Background Arrangement |
| Detroit City | Bobby Bare | 1963 | Best Country & Western Recording |
| Days Of Wine And Roses | Henry Mancini | 1963 | Record Of The Year |
| Days Of Wine And Roses | Henry Mancini | 1963 | Song Of The Year |
| Don't Touch Me | Jeannie Seely | 1966 | Best Country & Western Vocal Performance - Female |
| Crying Time | Ray Charles | 1966 | Best Rhythm & Blues Recording |
| Crying Time | Ray Charles | 1966 | Best Rhythm & Blues Solo Vocal Performance, Male Or Female |
| Gentle on My Mind | John Hartford | 1967 | Best Country & Western Song |
| Gentle on My Mind | John Hartford | 1967 | Best Folk Performance |
| Classical Gas (LP Version) | Mason Williams | 1968 | Best Contemporary Pop Performance, Instrumental |
| Classical Gas (LP Version) | Mason Williams | 1968 | Best Instrumental Theme |
| Chain Of Fools | Aretha Franklin | 1968 | Best Rhythm & Blues Vocal Performance, Female |
| Games People Play (2002 Digital Remaster) | Joe South | 1969 | Best Contemporary Song |
| MacArthur Park | Waylon Jennings | 1969 | Best Country Performance By A Duo Or Group With Vocal |
| A Boy Named Sue | Johnny Cash | 1969 | Best Country Vocal Performance, Male |
| Games People Play (2002 Digital Remaster) | Joe South | 1969 | Song Of The Year |
| Rose Garden | Lynn Anderson | 1970 | Best Country Vocal Performance, Female |

## cq5_artistas_parecidos

```sparql
PREFIX mus: <http://example.org/musica/ontology#>

# CQ5: ¿Qué artistas se parecen a Bob Dylan según las etiquetas que comparten sus canciones?
SELECT ?parecido (COUNT(DISTINCT ?etiqueta) AS ?etiquetasEnComun)
WHERE {
  # etiquetas de las canciones de Bob Dylan
  {
    SELECT DISTINCT ?base ?etiqueta
    WHERE {
      ?base mus:nombre "Bob Dylan" ;
            mus:interpreta/mus:tieneEtiqueta ?etiqueta .
    }
  }
  # otros artistas con canciones que tienen esas mismas etiquetas
  ?cancion mus:tieneEtiqueta ?etiqueta ;
           mus:interpretadaPor ?otro .
  ?otro a mus:Artista ;
        mus:nombre ?parecido .
  FILTER (?otro != ?base)
}
GROUP BY ?otro ?parecido
ORDER BY DESC(?etiquetasEnComun) ?parecido ?otro
LIMIT 10
```

10 filas

| parecido | etiquetasEnComun |
|---|---|
| Neil Young | 11 |
| Tim Buckley | 10 |
| Van Morrison | 10 |
| Loggins & Messina | 9 |
| Simon & Garfunkel | 9 |
| Bruce Springsteen | 8 |
| Cat Stevens | 8 |
| John Denver | 8 |
| The Lovin' Spoonful | 8 |
| Creedence Clearwater Revival | 7 |

## cq6_albumes_top

```sparql
PREFIX mus: <http://example.org/musica/ontology#>

# CQ6: ¿Qué álbumes tienen más canciones en el dataset y de qué artista son?
SELECT ?album ?artista (COUNT(?cancion) AS ?canciones)
WHERE {
  ?al a mus:Album ;
      mus:nombre ?album ;
      mus:lanzadoPor ?a ;
      mus:contiene ?cancion .
  ?a mus:nombre ?artista .
}
GROUP BY ?al ?album ?artista
ORDER BY DESC(?canciones) ?album ?artista ?al
LIMIT 10
```

10 filas

| album | artista | canciones |
|---|---|---|
| Keep An Eye On The Sky | Big Star | 10 |
| Anthology | John Lennon | 9 |
| Solo Un Uomo | Mondo Marcio | 9 |
| The Syliphone Years | Bembeya Jazz National | 9 |
| 52 Weeks | Into It. Over It. | 8 |
| Dogma | Asterisk* | 8 |
| Masterplan | Stefanie Heinzmann | 8 |
| Ran | Toru Takemitsu | 8 |
| Rarities & B-Sides | The Smashing Pumpkins | 8 |
| The Collection | Girlschool | 8 |

## cq7_letras_genero

```sparql
PREFIX mus: <http://example.org/musica/ontology#>

# CQ7: ¿Qué género tiene el mayor promedio de palabras en sus letras?
SELECT ?genero (COUNT(?cancion) AS ?canciones) (ROUND(AVG(?palabras)) AS ?promedioPalabras)
WHERE {
  ?cancion mus:tieneGenero ?g ;
           mus:totalPalabrasLetra ?palabras .
  ?g mus:nombre ?genero .
}
GROUP BY ?genero
ORDER BY DESC(?promedioPalabras) ?genero
```

15 filas

| genero | canciones | promedioPalabras |
|---|---|---|
| Rap | 498 | 4827.0 |
| RnB | 437 | 3210.0 |
| Reggae | 199 | 2557.0 |
| Pop | 771 | 2419.0 |
| Country | 535 | 2209.0 |
| Rock | 4379 | 2061.0 |
| Folk | 188 | 2058.0 |
| Blues | 114 | 1924.0 |
| Latin | 109 | 1773.0 |
| Metal | 712 | 1733.0 |
| Punk | 237 | 1733.0 |
| Jazz | 188 | 1732.0 |
| Electronic | 334 | 1649.0 |
| New Age | 13 | 1329.0 |
| World | 27 | 831.0 |

## cq8_etiquetas_metal

```sparql
PREFIX mus:    <http://example.org/musica/ontology#>
PREFIX genero: <http://example.org/musica/resource/genero/>

# CQ8: ¿Cuáles son las 5 etiquetas más usadas en las canciones de Metal?
SELECT ?etiqueta (COUNT(DISTINCT ?cancion) AS ?canciones)
WHERE {
  ?cancion mus:tieneGenero genero:metal ;
           mus:tieneEtiqueta ?e .
  ?e mus:nombre ?etiqueta .
}
GROUP BY ?e ?etiqueta
ORDER BY DESC(?canciones) ?etiqueta ?e
LIMIT 5
```

5 filas

| etiqueta | canciones |
|---|---|
| metal | 689 |
| death metal | 224 |
| heavy metal | 214 |
| metalcore | 188 |
| thrash metal | 167 |
