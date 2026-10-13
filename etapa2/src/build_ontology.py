"""Genera ontology.ttl: clases, jerarquías y propiedades del modelo musical.

Uso, desde la raíz del proyecto:
    python -m src.build_ontology
"""
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD

MUS = Namespace("http://example.org/musica/ontology#")
ONTOLOGY_IRI = URIRef("http://example.org/musica/ontology")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "ontology.ttl"

# (nombre, superclase, etiqueta, comentario)
CLASES = [
    ("Cancion", None, "canción",
     "Pista musical del dataset consolidado de la Etapa 1. Cada fila del dataset es una canción."),
    ("Artista", None, "artista",
     "Persona o grupo que interpreta canciones. Se identifica por su MBID de MusicBrainz."),
    ("Album", None, "álbum",
     "Disco en el que aparece una canción. Solo se conoce su nombre, por lo que se distingue por nombre y artista."),
    ("Genero", None, "género",
     "Género musical según tagtraum (15 géneros)."),
    ("Etiqueta", None, "etiqueta",
     "Etiqueta libre que los usuarios de Last.fm asignan a una canción."),
    ("NominacionGrammy", None, "nominación Grammy",
     "Nominación de una canción a un premio Grammy. Relaciona canción, categoría, año y resultado."),
    ("CancionPremiada", "Cancion", "canción premiada",
     "Canción que ganó al menos un premio Grammy."),
    ("CancionConLetra", "Cancion", "canción con letra",
     "Canción de la que se conoce el total de palabras de su letra."),
]

# (nombre, dominio, rango, etiqueta, comentario)
PROPIEDADES_OBJETO = [
    ("interpretadaPor", "Cancion", "Artista", "interpretada por",
     "Artista que interpreta la canción."),
    ("apareceEn", "Cancion", "Album", "aparece en",
     "Álbum en el que aparece la canción."),
    ("lanzadoPor", "Album", "Artista", "lanzado por",
     "Artista al que pertenece el álbum."),
    ("tieneGenero", "Cancion", "Genero", "tiene género",
     "Género asignado a la canción."),
    ("tieneEtiqueta", "Cancion", "Etiqueta", "tiene etiqueta",
     "Etiqueta de Last.fm asignada a la canción."),
    ("tieneNominacion", "Cancion", "NominacionGrammy", "tiene nominación",
     "Nominación a un Grammy que recibió la canción."),
    ("interpreta", "Artista", "Cancion", "interpreta",
     "Canción que interpreta el artista."),
    ("contiene", "Album", "Cancion", "contiene",
     "Canción que contiene el álbum."),
]

# `nombre` no declara dominio a propósito: lo usan cuatro clases y RDFS
# interpretaría varios dominios como "todos a la vez".
# (nombre, dominio, rango, etiqueta, comentario)
PROPIEDADES_DATOS = [
    ("titulo", "Cancion", XSD.string, "título", "Título de la canción."),
    ("anio", "Cancion", XSD.gYear, "año",
     "Año de lanzamiento. Si se desconoce, no se declara."),
    ("totalPalabrasLetra", "Cancion", XSD.integer, "total de palabras de la letra",
     "Número de palabras de la letra de la canción."),
    ("idTrack", "Cancion", XSD.string, "id de track",
     "Identificador de la canción en el Million Song Dataset."),
    ("mbidArtista", "Artista", XSD.string, "MBID del artista",
     "Identificador del artista en MusicBrainz."),
    ("nombre", None, XSD.string, "nombre",
     "Nombre de un artista, álbum, género o etiqueta."),
    ("categoria", "NominacionGrammy", XSD.string, "categoría",
     "Categoría del premio Grammy."),
    ("anioNominacion", "NominacionGrammy", XSD.gYear, "año de la nominación",
     "Año de la ceremonia de los Grammy."),
    ("ganada", "NominacionGrammy", XSD.boolean, "ganada",
     "Verdadero si la nominación resultó en premio."),
]


def _anotar(g: Graph, termino: URIRef, etiqueta: str, comentario: str) -> None:
    g.add((termino, RDFS.label, Literal(etiqueta, lang="es")))
    g.add((termino, RDFS.comment, Literal(comentario, lang="es")))


def _lista(g: Graph, elementos: list) -> BNode:
    cabeza = BNode()
    Collection(g, cabeza, elementos)
    return cabeza


def _restriccion(g: Graph, propiedad: URIRef, tipo: URIRef, valor) -> BNode:
    nodo = BNode()
    g.add((nodo, RDF.type, OWL.Restriction))
    g.add((nodo, OWL.onProperty, propiedad))
    g.add((nodo, tipo, valor))
    return nodo


def _uno() -> Literal:
    return Literal(1, datatype=XSD.nonNegativeInteger)


def agregar_axiomas_owl(g: Graph) -> None:
    # cardinalidad
    g.add((MUS.Cancion, RDFS.subClassOf,
           _restriccion(g, MUS.interpretadaPor, OWL.minCardinality, _uno())))
    g.add((MUS.NominacionGrammy, RDFS.subClassOf,
           _restriccion(g, MUS.categoria, OWL.cardinality, _uno())))
    g.add((MUS.Album, RDFS.subClassOf,
           _restriccion(g, MUS.lanzadoPor, OWL.cardinality, _uno())))

    # propiedades inversas
    g.add((MUS.interpretadaPor, OWL.inverseOf, MUS.interpreta))
    g.add((MUS.apareceEn, OWL.inverseOf, MUS.contiene))

    # clase equivalente: CancionConLetra = Cancion y con total de palabras
    con_letra = BNode()
    g.add((con_letra, RDF.type, OWL.Class))
    g.add((con_letra, OWL.intersectionOf, _lista(g, [
        MUS.Cancion,
        _restriccion(g, MUS.totalPalabrasLetra, OWL.someValuesFrom, XSD.integer),
    ])))
    g.add((MUS.CancionConLetra, OWL.equivalentClass, con_letra))

    # clases disjuntas
    disjuntas = BNode()
    g.add((disjuntas, RDF.type, OWL.AllDisjointClasses))
    g.add((disjuntas, OWL.members, _lista(g, [
        MUS.Cancion, MUS.Artista, MUS.Album,
        MUS.Genero, MUS.Etiqueta, MUS.NominacionGrammy,
    ])))

    # propiedad funcional
    g.add((MUS.tieneGenero, RDF.type, OWL.FunctionalProperty))

    # claves
    g.add((MUS.Cancion, OWL.hasKey, _lista(g, [MUS.idTrack])))
    g.add((MUS.Artista, OWL.hasKey, _lista(g, [MUS.mbidArtista])))


def build_ontology() -> Graph:
    g = Graph()
    g.bind("mus", MUS)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)

    g.add((ONTOLOGY_IRI, RDF.type, OWL.Ontology))
    _anotar(g, ONTOLOGY_IRI, "Ontología musical",
            "Modelo del dominio musical construido a partir del dataset consolidado de la Etapa 1.")

    for nombre, superclase, etiqueta, comentario in CLASES:
        clase = MUS[nombre]
        g.add((clase, RDF.type, RDFS.Class))
        g.add((clase, RDF.type, OWL.Class))
        if superclase:
            g.add((clase, RDFS.subClassOf, MUS[superclase]))
        _anotar(g, clase, etiqueta, comentario)

    for nombre, dominio, rango, etiqueta, comentario in PROPIEDADES_OBJETO:
        prop = MUS[nombre]
        g.add((prop, RDF.type, RDF.Property))
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.domain, MUS[dominio]))
        g.add((prop, RDFS.range, MUS[rango]))
        _anotar(g, prop, etiqueta, comentario)

    for nombre, dominio, rango, etiqueta, comentario in PROPIEDADES_DATOS:
        prop = MUS[nombre]
        g.add((prop, RDF.type, RDF.Property))
        g.add((prop, RDF.type, OWL.DatatypeProperty))
        if dominio:
            g.add((prop, RDFS.domain, MUS[dominio]))
        g.add((prop, RDFS.range, rango))
        _anotar(g, prop, etiqueta, comentario)

    agregar_axiomas_owl(g)
    return g


def main() -> None:
    g = build_ontology()
    g.serialize(destination=OUTPUT, format="turtle")
    print(f"{OUTPUT} escrito: {len(g)} tripletas")


if __name__ == "__main__":
    main()
