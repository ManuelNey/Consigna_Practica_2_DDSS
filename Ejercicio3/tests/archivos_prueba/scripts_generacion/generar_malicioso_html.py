"""
Genero malicioso.html con contenido HTML y extension .html.
Lo uso para probar que el sistema rechace archivos con extensiones
que no estan permitidas, como .html en vez de jpg, jpeg o png.
"""
from pathlib import Path

CARPETA_DESTINO = Path(__file__).parent.parent  # carpeta archivos_prueba/

CONTENIDO = (
    "<html>\n"
    "    <body>\n"
    "        <p>ESTO ES UNA ATAQUE CON FILE UPLOAD</p>\n"
    "        <script>alert('Soy un archivo html... si me ves me estoy ejecutando')</script>\n"
    "    </body>\n"
    "</html>"
)

if __name__ == "__main__":
    # Guardo el contenido como bytes para mantener los saltos de linea
    # iguales aunque ejecute el script en otro sistema operativo.
    (CARPETA_DESTINO / "malicioso.html").write_bytes(CONTENIDO.encode("utf-8"))
    print("malicioso.html generado en", CARPETA_DESTINO)