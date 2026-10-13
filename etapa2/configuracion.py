"""Parámetros de conexión con Apache Jena Fuseki.

Todos los scripts del proyecto leen estos valores. Para usar otra instalación
de Fuseki basta con cambiar FUSEKI_URL y NOMBRE_DATASET.
"""

FUSEKI_URL = "http://localhost:3030"
NOMBRE_DATASET = "musica"

ENDPOINT_CONSULTA = f"{FUSEKI_URL}/{NOMBRE_DATASET}/query"
ENDPOINT_ACTUALIZACION = f"{FUSEKI_URL}/{NOMBRE_DATASET}/update"
ENDPOINT_DATOS = f"{FUSEKI_URL}/{NOMBRE_DATASET}/data"

# Credenciales del Fuseki levantado con docker-compose.yml. Con una instalación
# sin autenticación, poner ambos en None.
USUARIO = "admin"
CLAVE = "admin"
