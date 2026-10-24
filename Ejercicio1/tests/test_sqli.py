import sqlite3

import pytest

from app import app, buscar_funciones


# Esta funcion crea una base de datos de prueba con 3 peliculas y 3 funciones
# para probar la inyeccion SQL sin modificar la base de datos original.
def _crear_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE peliculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            genero TEXT NOT NULL,
            director TEXT NOT NULL
        );
        CREATE TABLE funciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pelicula_id INTEGER NOT NULL,
            fecha_hora TEXT NOT NULL,
            asientos_totales INTEGER NOT NULL DEFAULT 100,
            asientos_ocupados INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (pelicula_id) REFERENCES peliculas(id)
        );
        """
    )
    conn.executemany(
        "INSERT INTO peliculas (nombre, genero, director) VALUES (?, ?, ?)",
        [
            ("Dune: Parte Dos", "Ciencia Ficcion", "Denis Villeneuve"),
            ("Oppenheimer", "Drama", "Christopher Nolan"),
            ("Wonka", "Fantasia", "Paul King"),
        ],
    )
    conn.executemany(
        "INSERT INTO funciones "
        "(pelicula_id, fecha_hora, asientos_totales, asientos_ocupados) "
        "VALUES (?, ?, ?, ?)",
        [
            (1, "2026-07-13 14:30:00", 120, 85),
            (2, "2026-07-13 16:00:00", 100, 92),
            (3, "2026-07-13 11:00:00", 100, 95),
        ],
    )
    conn.commit()
    conn.close()


# Se utiliza fixture de pytest para tener una base de datos separada
# para cada test, sin depender de la base de datos real.
# Por ultimo se guarda la configuracion original para restaurarla al terminar.
@pytest.fixture
def db_temporal(tmp_path):
    db_path = tmp_path / "test_cine.db"  # Definimos la ruta de la base de datos temporal.
    _crear_db(str(db_path))  # Creamos las tablas y agrego los datos de prueba.

    db_anterior = app.config.get("DATABASE")  # Se guarda la ruta que usa la app actualmente.
    app.config["DATABASE"] = str(db_path)  # Ajustamos la ruta para usar la base temporal.

    yield db_path  # Se ejecuta el test que usa este fixture.

    app.config["DATABASE"] = db_anterior  # Se restaura la ruta original al terminar.


def test_query_con_entrada_sqli_no_trae_resultados_de_mas(db_temporal):
    """
    Se prueba una entrada que intenta modificar la consulta SQL para
    devolver todas las funciones, sin importar el filtro de busqueda.

    En la version vulnerable, el OR 1=1 hace que se devuelvan todas
    las filas. En la version corregida, la entrada se trata como texto
    y no deberia encontrar ninguna pelicula.
    """
    entrada = "' or 1=1 --"  # Entrada para un intento de inyeccion SQL.

    with app.app_context():
        resultados = buscar_funciones(entrada)  # Ejecuto la busqueda con esa entrada.

    assert resultados == []  # Verifico que no devuelva resultados, ya que tendría sentido que dicha consulta no retorne ninguna función.


def test_query_con_comilla_simple_no_rompe_la_consulta(db_temporal):
    """
    Se prueba que una comilla simple no rompa la consulta SQL.

    Si la entrada se concatena directamente en la consulta, la comilla
    puede generar un error de sintaxis. Si uso parametros, se interpreta
    como texto y la consulta funciona normalmente.
    """
    with app.app_context():
        try:
            resultados = buscar_funciones("'")  # Pruebo la busqueda con una comilla sola.
        except sqlite3.OperationalError as exc:
            # Si ocurre este error, la comilla rompio la consulta y el test falla.
            pytest.fail(
                "La query no esta parametrizada: una comilla simple "
                f"rompe la sentencia SQL ({exc})"
            )

    assert resultados == []  # Verifico que no encuentre ninguna pelicula.


def test_sort_dir_con_comilla_no_rompe_la_consulta(db_temporal):
    """
    Se prueba una comilla simple sobre el parametro sort_dir, que
    define el orden en el que aparecen los resultados.

    En la version vulnerable, la comilla se interpola directo en el
    ORDER BY y rompe la consulta (sqlite3.OperationalError). En la
    version corregida, solo se aceptan ASC o DESC, por lo que la
    comilla no coincide con 'ASC' y la consulta usa 'DESC' sin romperse.
    """
    with app.app_context():
        try:
            resultados = buscar_funciones("a", sort_dir="'")  # Intento de inyeccion en el ORDER BY.
        except sqlite3.OperationalError as exc:
            pytest.fail(
                "sort_dir no esta validado: una comilla simple rompe "
                f"la sentencia SQL ({exc})"
            )

    assert len(resultados) >= 1  # La busqueda "a" sigue funcionando, sin romperse.


def test_busqueda_normal_devuelve_la_funcion_esperada(db_temporal):
    """
    Este test comprueba que la busqueda funcione correctamente despues
    de aplicar los cambios de seguridad.

    Este test deberia pasar tanto en main como en Practico-2, porque
    estoy haciendo una busqueda normal y no un intento de inyeccion SQL.
    """
    with app.app_context():
        resultados = buscar_funciones("Dune")  # Busco una pelicula por su nombre.

    assert len(resultados) == 1  # Verifico que devuelva una sola funcion.
    assert resultados[0]["pelicula"] == "Dune: Parte Dos"  # Verifico que sea la pelicula correcta.