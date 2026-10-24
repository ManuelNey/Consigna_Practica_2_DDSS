"""
Tests de seguridad del Ejercicio 4: SSTI mediante SpEL.
Pruebas para comprobar que la busqueda se interprete como texto y no como codigo.
"""

import os
import requests

# Guardo la URL de la app.
BASE_URL = os.environ.get("EJ4_BASE_URL", "http://localhost:8080")


# Hago una peticion con el texto que quiero buscar.
def _buscar(buscar):
    return requests.get(f"{BASE_URL}/", params={"buscar": buscar}, timeout=10)


# Pruebo que una expresion matematica no se ejecute.
# Misma entrada que use en el Practico 2 (Figura 44: '3*3' -> 'Resultados
# buscando por: 9').
def test_busqueda_con_operacion_aritmetica_no_se_evalua_como_spel():
    resp = _buscar("3*3")

    # Compruebo que la busqueda funcione y no muestre el resultado 9.
    assert resp.status_code == 200
    assert "Resultados buscando por: 9" not in resp.text
    assert "No se encontraron coincidencias." in resp.text


# Pruebo la otra forma de deteccion que tambien use en el Practico 2
# (Figura 45: '{7*7}' -> 'Resultados buscando por: [49]'), que envuelve
# la expresion en llaves (sintaxis de lista de SpEL).
def test_busqueda_con_llaves_y_aritmetica_no_se_evalua_como_spel():
    resp = _buscar("{7*7}")

    # Compruebo que se busque el texto literal y no se muestre [49].
    assert resp.status_code == 200
    assert "Resultados buscando por: [49]" not in resp.text
    assert "No se encontraron coincidencias." in resp.text


# Pruebo que no se pueda obtener el objeto Runtime del servidor.
# Misma entrada que use en el Practico 2 (Figura 47), sin llegar a
# ejecutar un comando como hice ahi con '.exec('ls')' -- esto solo
# demuestra que la variable 'runtime' esta disponible, no corre nada.
def test_busqueda_con_acceso_a_runtime_no_expone_el_objeto():
    resp = _buscar("#runtime.getRuntime()")

    # Compruebo que la expresion no se ejecute como codigo.
    assert resp.status_code == 200
    assert "No se encontraron coincidencias." in resp.text


# Pruebo que no se puedan consultar las variables de entorno del
# servidor. Misma entrada que use en el Practico 2 (Figura 49), donde
# se filtraba SPRING_DATASOURCE_URL entre otras variables.
def test_busqueda_con_variables_de_entorno_no_revela_configuracion_sensible():
    resp = _buscar("#system.getenv()")

    # Compruebo que no aparezca ninguna variable de entorno del
    # contenedor (ej. la URL de la base de datos).
    assert resp.status_code == 200
    assert "SPRING_DATASOURCE_URL" not in resp.text
    assert "No se encontraron coincidencias." in resp.text


# Pruebo que una busqueda normal funcione correctamente.
def test_busqueda_con_texto_normal_funciona_sin_romper():
    resp = _buscar("Inception")

    # Compruebo que la pagina muestre las coincidencias.
    assert resp.status_code == 200
    assert "Resultados buscando por: Inception" in resp.text
    assert "Inception" in resp.text


# Pruebo que al dejar la busqueda vacia se muestren todas las funciones.
def test_busqueda_vacia_muestra_todas_las_funciones():
    # Abro la pagina sin enviar el parametro buscar.
    resp = requests.get(f"{BASE_URL}/", timeout=10)

    # Compruebo que se muestren las funciones de ejemplo.
    assert resp.status_code == 200
    assert "Mostrando todas las funciones." in resp.text
    assert "Inception" in resp.text
    assert "The Matrix" in resp.text
    assert "Avengers: Endgame" in resp.text
