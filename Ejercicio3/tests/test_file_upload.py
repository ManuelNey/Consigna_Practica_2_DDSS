import os
import subprocess
from pathlib import Path

import requests

# Uso requests porque la app esta corriendo en un contenedor de Docker
# y necesito hacer las peticiones HTTP directamente.
BASE_URL = os.environ.get("EJ3_BASE_URL", "http://localhost:8080")
CONTAINER = "cinebuscador3"
PELICULA_ID = 5  # ID de Avengers: Endgame.

# Guardo la ruta de los archivos que uso para probar las subidas.
ARCHIVOS_PRUEBA = Path(__file__).parent / "archivos_prueba"


# Leo el contenido de un archivo de prueba.
# La hice como una funcion para no repetir el mismo codigo en cada test.
def _leer(nombre_archivo):
    return (ARCHIVOS_PRUEBA / nombre_archivo).read_bytes()



# Consulto los archivos que hay en la carpeta /uploads (la que almacena los archivos subidos dentro del contenedor) para ver si aparece alguno nuevo.
def _listar_uploads():
    resultado = subprocess.run(
        ["docker", "exec", CONTAINER, "ls", "/uploads"],
        capture_output=True, text=True, timeout=10,
    )
    return set(resultado.stdout.split())


# Reviso si existe un archivo en una ruta dentro del contenedor.
def _existe_en_contenedor(ruta_absoluta):
    resultado = subprocess.run(
        ["docker", "exec", CONTAINER, "test", "-f", ruta_absoluta],
        capture_output=True, timeout=10,
    )
    return resultado.returncode == 0


# Envio un archivo al endpoint de subida y devuelvo la respuesta.
def _upload(nombre_archivo, contenido, content_type="image/jpeg"):
    archivos = {"afiche": (nombre_archivo, contenido, content_type)}
    return requests.post(
        f"{BASE_URL}/upload/{PELICULA_ID}",
        files=archivos,
        allow_redirects=False,
        timeout=10,
    )


def test_upload_con_extension_no_permitida_no_se_guarda():
    """
    Pruebo subir un archivo .html para comprobar que se rechacen
    las extensiones que no estan permitidas (jpg, jpeg y png).
    """
    archivos_antes = _listar_uploads()
    contenido = _leer("malicioso.html")

    respuesta = _upload("malicioso.html", contenido, content_type="text/html")
    assert respuesta.status_code != 302, (
        "El upload no deberia aceptarse con una extension no permitida"
    )

    # Comparo los archivos antes y despues para ver si se guardo alguno.
    archivos_despues = _listar_uploads()
    assert archivos_despues == archivos_antes, (
        "No deberia haberse agregado ningun archivo nuevo en /uploads"
    )

    descarga = requests.get(f"{BASE_URL}/uploads/malicioso.html", timeout=10)
    assert descarga.status_code != 200, "El archivo no deberia quedar accesible ni siquiera existir en /uploads"


# Pruebo que no se pueda guardar un archivo fuera de /uploads usando ../., algo que no
# no llegué a probar en el Practico 2 pero que me di cuenta que también se soluciona con la 
# mitigación que se realizó.
def test_upload_con_path_traversal_en_el_nombre_no_escribe_fuera_de_uploads():
    # Leo una imagen valida
    contenido = _leer("afiche_valido.jpg")

    # Pongo ../ varias veces para intentar salir de /uploads y subir más arriba de uploads.
    nombre_malicioso = "../../../../../../tmp/traversal_test.jpg"

    # Intento subir la imagen con ese nombre.
    _upload(nombre_malicioso, contenido)

    # Reviso si el archivo aparecio en /tmp, fuera de /uploads.
    escapo_de_uploads = _existe_en_contenedor("/tmp/traversal_test.jpg")

    # Si se guardo fuera de la carpeta permitida, lo borro.
    # Para que no quede basura en el contenedor y no afecte a otros tests.
    if escapo_de_uploads:
        subprocess.run(
            ["docker", "exec", CONTAINER, "rm", "-f", "/tmp/traversal_test.jpg"],
            timeout=10,
        )

    # El test pasa si el archivo no se guardo fuera de /uploads.
    assert not escapo_de_uploads, (
        "El archivo se guardo fuera de /uploads usando path traversal"
    )


# Pruebo que se rechacen las descargas de archivos con extensiones no permitidas.
def test_descarga_de_extension_no_permitida_se_rechaza_antes_de_mirar_si_existe():
    # Uso un archivo .txt que no existe para probar el control de extension.
    # Asi compruebo que se revise la extension antes de buscar el archivo.

    # Intento descargar el archivo desde /uploads.
    respuesta = requests.get(
        f"{BASE_URL}/uploads/no-existe-12345.txt",
        timeout=10,  # Espero como maximo 10 segundos por la respuesta.
    )

    # Compruebo que la app rechace la descarga con el codigo 415.
    assert respuesta.status_code == 415


def test_upload_con_extension_png_pero_contenido_html_no_es_imagen_valida():
    """
    Intento subir fake.png, que tiene extension .png pero contiene HTML.
    Lo uso para comprobar que se revise el contenido real y no solo
    la extension del archivo.
    
    ImageIO.read() intenta leer la imagen y devuelve null si no puede
    interpretarla como una imagen valida, por lo que la subida se rechaza.

    Un PNG valido con un script agregado al final puede pasar este control.
    Pruebo ese caso en el siguiente test.
    """
    archivos_antes = _listar_uploads()
    contenido = _leer("fake.png")

    respuesta = _upload("fake.png", contenido, content_type="image/png")
    assert respuesta.status_code != 302

    # Compruebo que el archivo no se haya guardado.
    archivos_despues = _listar_uploads()
    assert archivos_despues == archivos_antes


def test_imagen_con_script_oculto_no_esta_cubierto():
    """
    Pruebo subir una imagen JPEG valida que tiene un script agregado
    al final del archivo.

    ImageIO.read() puede leer la imagen sin problemas porque no necesita
    interpretar los bytes que vienen despues del marcador de fin de imagen
    (EOI). Por eso, esta validacion no detecta el script agregado y acepta
    la subida tanto en la version vulnerable como en la corregida.
    """
    # Leo la imagen que tiene el script agregado.
    contenido = _leer("imagen_con_script_oculto.jpg")

    # Intento subirla y compruebo si la app la acepta.
    respuesta = _upload("imagen_con_script_oculto.jpg", contenido)

    # La subida se acepta porque la validacion no detecta el script agregado.
    assert respuesta.status_code == 302


def test_upload_de_imagen_valida_funciona():
    """
    Test funcional (no de seguridad): pruebo que subir una imagen valida
    (el afiche real de Avengers) siga funcionando despues de los cambios
    de seguridad. Sirve para comprobar que los tests de arriba no pasan
    porque la app esta rota, sino porque la mitigacion funciona.

    Deberia pasar tanto en main como en Practico-2.
    """
    # Guardo la lista de archivos antes de subir la imagen.
    archivos_antes = _listar_uploads()
    contenido = _leer("afiche_valido.jpg")
    # Subo la imagen y compruebo que la app responda correctamente.
    respuesta = _upload("afiche_valido.jpg", contenido)
    assert respuesta.status_code == 302

    # Busco el archivo nuevo para obtener su nombre.
    archivos_despues = _listar_uploads()
    archivos_nuevos = archivos_despues - archivos_antes
    assert len(archivos_nuevos) == 1

    # Descargo la imagen y compruebo que se devuelva correctamente.
    nombre_guardado = archivos_nuevos.pop()
    descarga = requests.get(
        f"{BASE_URL}/uploads/{nombre_guardado}",
        timeout=10,
    )
    assert descarga.status_code == 200
    assert descarga.headers["Content-Type"].startswith("image/jpeg")