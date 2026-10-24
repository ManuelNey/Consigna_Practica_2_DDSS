"""
Genero fake.png con contenido HTML en vez de una imagen real.
La extension dice que es un PNG, pero el contenido es texto.
Lo uso para probar si la validacion revisa el contenido del archivo
y no solamente la extension.
"""
from pathlib import Path

CARPETA_DESTINO = Path(__file__).parent.parent  # carpeta archivos_prueba/

CONTENIDO = (
    "Esto deberia ser una imagen pero no lo es, por lo tanto el "
    "servidor deberia no aceptarlo.\n"
)

if __name__ == "__main__":
    # Uso write_bytes para guardar el contenido sin que Python cambie
    # los saltos de linea segun el sistema operativo.
    (CARPETA_DESTINO / "fake.png").write_bytes(CONTENIDO.encode("utf-8"))
    print("fake.png generado en", CARPETA_DESTINO)
