# Practico — Desarrollo Seguro de Software

## Índice

1. [Introducción](#1-introducción)
2. [Tests de seguridad (Práctico 4)](#2-tests-de-seguridad-práctico-4)
   - [Ejercicio 1 — SQL Injection](#ejercicio-1--sql-injection-unitarios-pytest)
   - [Ejercicio 2 — Cross Site Scripting](#ejercicio-2--cross-site-scripting-unitarios-pytest)
   - [Ejercicio 3 — File Upload](#ejercicio-3--file-upload-integración)
   - [Ejercicio 4 — SSTI](#ejercicio-4--ssti-integración)
   - [Ejercicio 5 — Almacenamiento inseguro](#ejercicio-5--almacenamiento-inseguro-unitarios-junit)
3. [Decisiones de diseño](#3-decisiones-de-diseño)

## 1. Introducción

Este repositorio contiene los prácticos 2 y 4 de la materia Desarrollo Seguro de Software.

Cada carpeta `Ejercicio/` tiene una app con una versión de CineBuscador, una aplicación para buscar y gestionar funciones de cine. En cada ejercicio se encuentra una vulnerabilidad distinta:

| Ejercicio | Tecnologías | Vulnerabilidad |
|---|---|---|
| Ejercicio1 | Flask + SQLite | SQL Injection |
| Ejercicio2 | Flask + SQLite | Cross Site Scripting (XSS) |
| Ejercicio3 | Spring Boot | File Upload inseguro |
| Ejercicio4 | Spring Boot (SpEL) | Server Side Template Injection (SSTI) |
| Ejercicio5 | Spring Boot + H2 | Almacenamiento inseguro de credenciales |

Para comparar la aplicación vulnerable con la versión corregida, como pide el práctico se pueden utilzar las siguientes 2 ramas:

- **`main`**: tiene las vulnerabilidades originales.
- **`Practico-2`**: incluye las mitigaciones del Práctico 2.

La explicación de cada vulnerabilidad y de su mitigación está en `Practico2.md`.

---

## 2. Tests de seguridad (Práctico 4)

Los mismos tests se ejecutan en las dos ramas. En general, los tests de seguridad deberían fallar en `main`, donde sigue presente la vulnerabilidad, y pasar en `Practico-2`, donde se aplicó la mitigación.

También hay tests funcionales que deberían pasar en ambas ramas. Esos sirven para comprobar que la aplicación siga funcionando con entradas normales. En cada ejercicio se resume qué prueba cada test y qué resultado se espera.

### Ejercicio 1 — SQL Injection (unitarios, Pytest)

Estos tests no necesitan Docker ni la base de datos real (`cine.db`). Crean una base SQLite temporal con `tmp_path` y llaman directamente a `buscar_funciones()`.

Para ejecutarlos:

```bash
cd Ejercicio1
```

```bash
python -m pytest tests/test_sqli.py -v
```

| Test | Qué comprueba | `main` | `Practico-2` |
|---|---|:---:|:---:|
| `test_query_con_entrada_sqli_no_trae_resultados_de_mas` | Busca `' or 1=1 --` y comprueba que no aparezcan películas de más. | Falla: devuelve todas las funciones. | Pasa |
| `test_query_con_comilla_simple_no_rompe_la_consulta` | Busca solo `'` y comprueba que la consulta no se rompa. | Falla: `sqlite3.OperationalError`. | Pasa |
| `test_sort_dir_con_comilla_no_rompe_la_consulta` | Envía `'` en `sort_dir` y comprueba que la consulta no se rompa. | Falla: `sqlite3.OperationalError`. | Pasa |
| `test_busqueda_normal_devuelve_la_funcion_esperada` | Busca "Dune" y comprueba que aparezca el resultado correcto. | Pasa (funcional) | Pasa (funcional) |

### Ejercicio 2 — Cross Site Scripting (unitarios, Pytest)

Estos tests tampoco necesitan Docker ni la base de datos real (`cine2.db`). Usan `app.test_client()` de Flask y una base SQLite temporal creada con `tmp_path`.

Para ejecutarlos:

```bash
cd Ejercicio2
```

```bash
python -m pytest tests/test_xss.py -v
```

| Test | Qué comprueba | `main` | `Practico-2` |
|---|---|:---:|:---:|
| `test_descripcion_con_script_se_muestra_como_texto_plano` | Guarda una descripción con `<script>alert(...)</script>` y comprueba que se muestre como texto, no como código HTML. | Falla: el script aparece sin escapar. | Pasa |
| `test_descripcion_con_img_onerror_se_muestra_como_texto_plano` | Hace lo mismo con una etiqueta `<img onerror=...>`. | Falla | Pasa |
| `test_descripcion_normal_se_muestra_igual` | Guarda una descripción normal y comprueba que se vea igual. | Pasa (funcional) | Pasa (funcional) |

### Ejercicio 3 — File Upload (integración)

Estos tests hacen peticiones HTTP con `requests`. También usan `docker exec` para revisar los archivos dentro del contenedor y comprobar que los archivos rechazados no se hayan guardado.

Pasos para correrlos:

1. Entrar a la carpeta del ejercicio:

   ```bash
   cd Ejercicio3
   ```

2. Levantar el contenedor (esto construye la imagen si no existe y la deja corriendo en segundo plano, `-d`):

   ```bash
   docker compose up --build -d
   ```

3. Confirmar que el contenedor esté `Up` antes de correr los tests (si todavía dice `Starting`, esperar unos segundos y volver a mirar):

   ```bash
   docker compose ps
   ```

4. Correr los tests:

   ```bash
   python -m pytest tests/test_file_upload.py -v
   ```

5. Importante: bajar el contenedor cuando termines, para liberar el puerto 8080 y no chocar con los contenedores de Ejercicio4 (que usa el mismo puerto):

   ```bash
   docker compose down
   ```

Si el puerto 8080 ya está ocupado (por ejemplo porque quedó corriendo el contenedor de otro ejercicio y no se bajó con `docker compose down`), se puede usar otro puerto y configurar la variable `EJ3_BASE_URL` en vez del paso 2:

```bash
docker run -d --name cinebuscador3 -p 8090:8080 \
  -e SPRING_DATASOURCE_URL="jdbc:h2:file:/data/cine3;AUTO_SERVER=TRUE" \
  -e APP_UPLOAD_DIR="/uploads" \
  ejercicio3-cinebuscador:latest

EJ3_BASE_URL="http://localhost:8090" python -m pytest tests/test_file_upload.py -v
```

| Test | Qué comprueba | `main` | `Practico-2` |
|---|---|:---:|:---:|
| `test_upload_con_extension_no_permitida_no_se_guarda` | Intenta subir un archivo `.html` y comprueba que se rechace y no quede accesible. | Falla: se guarda y queda accesible. | Pasa |
| `test_upload_con_path_traversal_en_el_nombre_no_escribe_fuera_de_uploads` | Sube una imagen válida con `../../` en el nombre y comprueba que no se guarde fuera de `/uploads`. | Falla: escribe en `/tmp`. | Pasa |
| `test_descarga_de_extension_no_permitida_se_rechaza_antes_de_mirar_si_existe` | Pide un archivo `.txt` que no existe y espera un `415`, no un `404`. | Falla: devuelve `404`. | Pasa |
| `test_upload_con_extension_png_pero_contenido_html_no_es_imagen_valida` | Intenta subir un `.png` cuyo contenido es HTML y comprueba que se rechace. | Falla: se acepta. | Pasa |
| `test_imagen_con_script_oculto_no_esta_cubierto` | Sube una imagen JPEG válida con un script pegado al final y comprueba que la subida se acepte. Es un límite que se conoció al momento de probar la mitigación realizada en el práctico anterior, se tomó registro de dicha vulnerabilidad para mostrar en un caso real que podría ocurrir; se explica en la sección 3. | Pasa | Pasa |
| `test_upload_de_imagen_valida_funciona` | Sube una imagen válida (el afiche de Avengers) y comprueba que se pueda descargar. | Pasa (funcional) | Pasa (funcional) |

Los archivos de prueba están en `tests/archivos_prueba/`:

- `malicioso.html`: un archivo HTML con extensión `.html`.
- `fake.png`: texto plano guardado con extensión `.png`.
- `afiche_valido.jpg`: una imagen real.
- `imagen_con_script_oculto.jpg`: la misma imagen real con un script pegado al final.

Los primeros tres archivos se pueden volver a generar con los scripts de `tests/archivos_prueba/scripts_generacion/`. En la sección 3 se explica por qué se terminaron utilizando estos archivos.

### Ejercicio 4 — SSTI (integración)

Estos tests hacen peticiones HTTP con `requests`. Usan entradas de prueba que permiten ver si SpEL interpreta lo que se recibe como entrada como si fuese código. Las pruebas hacen operaciones aritméticas o consultan objetos y variables del servidor.

Pasos para correrlos:

1. Entrar a la carpeta del ejercicio:

   ```bash
   cd Ejercicio4
   ```

2. Levantar el contenedor:

   ```bash
   docker compose up --build -d
   ```

3. Confirmar que esté `Up`:

   ```bash
   docker compose ps
   ```

4. Correr los tests:

   ```bash
   python -m pytest tests/test_ssti.py -v
   ```

5. Bajar el contenedor al terminar, para liberar el puerto 8080 (lo usa también Ejercicio3):

   ```bash
   docker compose down
   ```

Si el puerto 8080 ya está ocupado, se puede usar otro y configurar `EJ4_BASE_URL`, igual que en Ejercicio3.

| Test | Qué comprueba | `main` | `Practico-2` |
|---|---|:---:|:---:|
| `test_busqueda_con_operacion_aritmetica_no_se_evalua_como_spel` | Busca `3*3` y comprueba que no se evalúe como `9`. | Falla: muestra `9`. | Pasa |
| `test_busqueda_con_llaves_y_aritmetica_no_se_evalua_como_spel` | Busca `{7*7}` y comprueba que no se evalúe como `[49]`. | Falla: muestra `[49]`. | Pasa |
| `test_busqueda_con_acceso_a_runtime_no_expone_el_objeto` | Busca `#runtime.getRuntime()` y comprueba que no se devuelva el objeto. | Falla: expone `Runtime`. | Pasa |
| `test_busqueda_con_variables_de_entorno_no_revela_configuracion_sensible` | Busca `#system.getenv()` y comprueba que no se muestren variables de entorno. | Falla: muestra variables, incluida la URL de la base de datos. | Pasa |
| `test_busqueda_con_texto_normal_funciona_sin_romper` | Busca "Inception" y comprueba que la búsqueda normal funcione. | Falla: devuelve `500`. | Pasa |
| `test_busqueda_vacia_muestra_todas_las_funciones` | Deja la búsqueda vacía y comprueba que aparezcan todas las funciones. | Pasa (funcional) | Pasa (funcional) |

### Ejercicio 5 — Almacenamiento inseguro (unitarios, JUnit)

Estos tests usan JUnit 5 para probar `EncryptionService` directamente.

Para que funcionen, hay que tener la dependencia `junit-jupiter` en el `pom.xml`. Como no venía en el proyecto original, se agregó

Para ejecutarlos:

```bash
cd Ejercicio5
```

```bash
mvn test
```

| Test | Qué comprueba | `main` | `Practico-2` |
|---|---|:---:|:---:|
| `encriptarLaMismaContrasenaDosVecesNoDaElMismoResultado` | Encripta dos veces la misma contraseña y comprueba que los resultados sean distintos. | Falla: AES/ECB devuelve el mismo resultado. | Pasa: BCrypt usa un salt aleatorio. |
| `elResultadoDeEncriptarTieneElFormatoDeUnHashBcrypt` | Comprueba que el resultado tenga el formato de un hash BCrypt, como `$2a$10$...`. | Falla: devuelve Base64 del cifrado AES, no un hash BCrypt. | Pasa |
| `encriptarUnaContrasenaValidaDevuelveUnResultadoNoVacio` | Comprueba que una contraseña válida genere un resultado no vacío. | Pasa (funcional) | Pasa (funcional) |
| `laContrasenaNuncaQuedaGuardadaEnTextoPlano` | Comprueba que el resultado nunca sea la contraseña tal cual ni la contenga. | Pasa | Pasa |

---

## 3. Decisiones de diseño

En esta sección explico algunas decisiones que tomé al preparar los tests y por qué se realizaron de esta manera.

### Por qué hay un test funcional en cada ejercicio

Además de los tests de seguridad, cada ejercicio tiene al menos una prueba con una entrada normal que debería pasar en las dos ramas. Como se trabajó en clase, siempre hay que comprobar que la aplicación siga funcionando correctamente y que los tests de seguridad no pasen simplemente porque algo se rompió.

### Ejercicio 3 — el test del script oculto (`test_imagen_con_script_oculto_no_esta_cubierto`)

Este test sube una imagen JPEG válida que tiene `<script>alert(1)</script>` pegado al final del archivo. La subida de dicho archivos es aceptada tanto en `main` como en `Practico-2`.
No es un fallo nuevo que haya introducido con los tests como tal. Es una limitación de la mitigación que realicé que ya tiene la aplicación, y considero que es mejor dejarla documentada.

**¿Por qué se acepta en las dos ramas?**

`ImageIO.read()` puede leer los datos de la imagen hasta encontrar su marcador de fin (EOI en un JPEG). No necesariamente revisa lo que viene después (que es donde se agrega en dicho test). Por eso, aunque el archivo tenga un script pegado al final, la lectura de la imagen puede funcionar y la validación lo acepta.

**¿Cómo se podría corregir?**

Una opción sería volver a guardar la imagen después de validarla, en vez de guardar directamente los mismos bytes que llegaron. Para eso, el servidor podría leerla con `ImageIO.read()` y después escribir una nueva imagen con `ImageIO.write()`. Así se guardan los datos de imagen que se pudieron leer, sin conservar el contenido que se podría haber agregado después.

No implementé ese cambio porque el objetivo de este práctico es probar las mitigaciones que ya se hicieron en el Práctico 2.

**¿Por qué no significa que el script se ejecute en este caso?**

Que la aplicación acepte el archivo no significa que el navegador vaya a ejecutar ese script. La app guarda el archivo con un nombre nuevo (UUID) y extensión `.jpg`. Cuando se descarga mediante `GET /uploads/<uuid>.jpg`, responde con `Content-Type: image/jpeg`, que se determina a partir de la extensión y no del contenido real de dicho archivo.

Con ese encabezado, el navegador intenta mostrar el archivo como una imagen, no como una página HTML. En este flujo, el script que está después del final de la imagen queda como contenido extra que no hace nada.

El riesgo es que la validación solo comprueba que el archivo se pueda leer como imagen; no verifica que todo su contenido corresponda a una imagen. Si el mismo archivo se usara en otro contexto que no respete el `Content-Type`, podría comportarse de otra manera.

Esto pasa igual en `main` y en `Practico-2`. La lógica que define el `Content-Type` al descargar (`MediaTypeFactory.getMediaType(resource)`) no cambió entre las ramas. Por eso, en este caso, la diferencia no es que el script se ejecute en una rama y en la otra no. La diferencia es que `main` no valida la extensión, el contenido ni el nombre del archivo, lo que permite otros problemas que sí cubren los tests: guardar archivos fuera de `/uploads`, aceptar archivos de cualquier tipo y servirlos sin los controles correspondientes.

### Ejercicio 3 — el test de path traversal

El test `test_upload_con_path_traversal_en_el_nombre_no_escribe_fuera_de_uploads` salió de revisar las diferencias entre las dos ramas y de ver como se podría "romper" la seguridad de la app. Como la mitigación genera un nombre nuevo con `UUID.randomUUID()` en lugar de usar directamente `archivo.getOriginalFilename()`. Eso también evita que el nombre enviado por el usuario se use para intentar guardar el archivo fuera de `/uploads`, así que agregué un test para comprobarlo.

### Ejercicio 3 — por qué se utilizan los archivos de prueba

Los archivos `malicioso.html`, `fake.png` e `imagen_con_script_oculto.jpg` están guardados en `tests/archivos_prueba/` en vez de crearse dentro de cada test. Así queda claro qué archivo se está usando y se puede volver a generar con los scripts de `tests/archivos_prueba/scripts_generacion/`. Cada archivo tiene su propio script de generación, para que se pueda repetir el proceso sin tener que deducir cómo se creó mirando el test. `afiche_valido.jpg` es una imagen real de Avengers que agregué manualmente, no se genera con un script.

### Ejercicio 4 — por qué no ejecuto comandos reales

Las entradas `3*3` y `{7*7}` sirven para comprobar si el buscador ejecuta lo que escribo como código en vez de tratarlo como texto para buscar. Por ejemplo, si devuelve `9` en vez de buscar el texto `3*3`, significa que está interpretando la entrada como una operación matemática.

Las entradas `#runtime.getRuntime()` y `#system.getenv()` prueban si también se puede acceder a cosas internas del servidor, como el objeto que permite ejecutar comandos o las variables de configuración, donde puede estar la URL de la base de datos.

No usé `#runtime.getRuntime().exec('ls')` porque eso ejecutaría un comando real en el servidor cada vez que se corran los tests. Con probar `#runtime.getRuntime()` ya puedo comprobar si se puede acceder a ese objeto, sin necesidad de ejecutar ningún comando.

### Ejercicio 5 — por qué agregué la dependencia al `pom.xml`

El proyecto original no tenía una dependencia de testing declarada, ni JUnit ni `spring-boot-starter-test`. Agregué `junit-jupiter` como dependencia de test para poder compilar y ejecutar los tests con `mvn test`. Ese cambio también lo hice en el `pom.xml` de `main`.