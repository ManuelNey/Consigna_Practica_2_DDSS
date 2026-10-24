import sqlite3

from app import app


# Esta funcion crea una base de datos de prueba con una pelicula, similar a lo que ocurre con el primer
# ejercicio, pero con la diferencia de que tiene un campo descripcion que es el que se va a usar para probar la vulnerabilidad XSS.
def _crear_db_con_pelicula(db_path, descripcion):
    conexion = sqlite3.connect(db_path)
    conexion.executescript(
        """
        CREATE TABLE peliculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            genero TEXT NOT NULL,
            director TEXT NOT NULL,
            descripcion TEXT
        );
        CREATE TABLE funciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pelicula_id INTEGER NOT NULL,
            fecha_hora TEXT NOT NULL,
            asientos_totales INTEGER NOT NULL DEFAULT 100,
            asientos_ocupados INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(pelicula_id) REFERENCES peliculas(id)
        );
        """
    )
    conexion.execute(
        "INSERT INTO peliculas (nombre, genero, director, descripcion) "
        "VALUES (?, ?, ?, ?)",
        ("Pelicula de prueba", "Drama", "Alguien", descripcion),
    )
    conexion.commit()
    conexion.close()



# Esta función crea una base de datos temporal con la descripcion que se va a probar,
# se cambia la configuracion de la app para usar esa base y devuelve el cliente
# que necesito para hacer las peticiones a las rutas de Flask.
def _crear_cliente_con_descripcion(tmp_path, descripcion):
    db_path = tmp_path / "test_cine2.db"  # Defino la ruta de la base temporal.
    _crear_db_con_pelicula(str(db_path), descripcion)  # Creo la pelicula con esa descripcion.
    app.config["DATABASE"] = str(db_path)  # Cambio la ruta para usar esta base.
    return app.test_client()  # Devuelvo el cliente http para probar los endpoints de Flask con esa base de datos.


def test_descripcion_con_script_se_muestra_como_texto_plano(tmp_path):
    """
    Este test prueba que una descripcion que contiene un script se muestre
    como texto y no como codigo HTML que se puede ejecutar.

    En la version vulnerable, el filtro safe hace que el script se muestre.
    En la version corregida, el motor de plantillas convierte los caracteres
    especiales a texto para que el navegador no lo interprete como HTML.
    """
    entrada_descripcion = "<script>alert('Te estamos hackeado >:(')</script>"  # Simulo una entrada con un script que intenta ejecutar JavaScript.
    cliente = _crear_cliente_con_descripcion(tmp_path, entrada_descripcion)  # Hacemos que el cliente use la base de datos temporal con esa descripcion.

    respuesta = cliente.get("/edit/1")  # Entro a la pagina de edicion de la pelicula.
    html_respuesta = respuesta.data.decode("utf-8")  # Paso la respuesta a texto para revisar el HTML.

    assert respuesta.status_code == 200
    assert "<script>alert('Te estamos hackeado >:(')</script>" not in html_respuesta  # Verifico que el script no aparezca sin escapar.
    assert "&lt;script&gt;alert(&#39;Te estamos hackeado &gt;:(&#39;)&lt;/script&gt;" in html_respuesta  # Verifico que aparezca como texto.



def test_descripcion_con_img_onerror_se_muestra_como_texto_plano(tmp_path):
    """
    Aca pruebo otra forma de XSS usando el elemento html de una imagen con el evento onerror,
    para comprobar que la proteccion no dependa solamente de bloquear
    la etiqueta <script>.

    En la version vulnerable, el navegador interpreta la etiqueta img
    y puede ejecutar el codigo de onerror. En la version corregida,
    Jinja2 escapa la etiqueta y la muestra como texto normal.
    """
    entrada_descripcion = "<img src=x onerror=alert(1)>"  # Simulamos otra entrada que intenta ejecutar JavaScript.
    cliente = _crear_cliente_con_descripcion(tmp_path, entrada_descripcion) # Hacemos que el cliente use la base de datos temporal con esa descripcion.

    respuesta = cliente.get("/edit/1")  # Obtenemos la pagina de edicion de la pelicula.
    html_respuesta = respuesta.data.decode("utf-8")  # Paso la respuesta a texto para revisar el HTML.

    assert respuesta.status_code == 200 # Verifico que la respuesta sea correcta.
    assert entrada_descripcion not in html_respuesta  # Verifico que la etiqueta no aparezca como HTML que se pueda ejecutar.
    assert "&lt;img src=x onerror=alert(1)&gt;" in html_respuesta  # Verificamos que se muestre como unicamente texto plano, sin que el navegador lo interprete como HTML.


def test_descripcion_normal_se_muestra_igual(tmp_path):
    """
    Este test valida que una descripcion normal se siga mostrando correctamente
    despues del cambio de seguridad.

    Este test deberia pasar tanto en main como en Practico-2, porque la
    descripcion no contiene codigo HTML que haya que neutralizar.
    """
    entrada_descripcion = "Descripcion normal sin ningun rastro de codigo ejecutable, sino sería muyy malo :( )"  # Simulamos una descripcion normal.
    cliente = _crear_cliente_con_descripcion(tmp_path, entrada_descripcion)

    respuesta = cliente.get("/edit/1")  # Entramos a la pagina de edicion con el cliente.
    html_respuesta = respuesta.data.decode("utf-8")  # Pasamos la respuesta a texto para revisar el HTML.

    assert respuesta.status_code == 200 # Verifico que la respuesta sea correcta, si no fuera un 200 significa que la pagina no se cargo correctamente y el test falla.
    assert entrada_descripcion in html_respuesta  # Verifico que la descripcion siga apareciendo normalmente.
