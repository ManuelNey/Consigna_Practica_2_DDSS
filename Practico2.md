# Práctico 2 — Seguridad en Aplicaciones Web

**Materia:** Desarrollo de Software Seguro
**Nombre y Apellido:** Manuel Cabrera
**Docente:** Adolfo Nidegger
**Institución:** Universidad Católica del Uruguay (UCU)
**Fecha de entrega:** 12 de septiembre de 2026

## Índice

1. [Introducción](#introducción)
2. [Ejercicio 1 — Inyección SQL (SQLi)](#ejercicio-1)
3. [Ejercicio 2 — Cross Site Scripting (XSS)](#ejercicio-2)
4. [Ejercicio 3 — File Upload](#ejercicio-3)
5. [Ejercicio 4 — Server-Side Template Injection (SSTI)](#ejercicio-4)
6. [Ejercicio 5 — Almacenamiento inseguro](#ejercicio-5)
7. [Conclusión general](#conclusión-general)

<a id="introducción"></a>

## Introducción

Este documento reúne los cinco ejercicios del práctico de Desarrollo de
Software Seguro. Los cinco parten de la misma base: una aplicación de
cine ("CineBuscador"), cada versión con una vulnerabilidad distinta
metida a propósito, corriendo en un contenedor Docker dentro de una VM
de Kali Linux. Para cada ejercicio seguí el mismo procedimiento: levantar el
ambiente, encontrar y explotar la vulnerabilidad, revisar el código para
entender la causa, mitigarla y volver a probar que la mitigación
funciona.

<a id="ejercicio-1"></a>

## Ejercicio 1 — Inyección SQL (SQLi)

### Definición de la vulnerabilidad

Una inyección SQL ocurre cuando una aplicación arma una consulta a la base de
datos incluyendo directamente el texto que escribió el usuario. Entonces el servidor no
distingue entre lo que es un dato de búsqueda y lo que es una instrucción SQL. Por esto si el texto ingresado contiene elementos propios del lenguaje SQL (comillas,
palabras reservadas, operadores u otros elementos similares), el motor de base de datos los interpreta como
parte del comando, no como texto plano.

Básicamente, el programa termina ejecutando una consulta distinta a la
que el desarrollador tenía pensada, porque una parte de esa consulta la terminó escribiendo el usuario sin que el sistema se diera cuenta.

El riesgo principal es la pérdida de confidencialidad, como las bases de
datos suelen contener información sensible, un atacante puede leer datos a los
que no debería tener acceso. También puede usarse para saltear mecanismos de
autenticación. Por ejemplo, si el login se valida con una consulta SQL mal construida, es
posible iniciar sesión como otro usuario sin conocer su contraseña. En casos más graves un usuario mediante esta vulnerabilidad puede modificar o eliminar información de la base de datos.

**Fuente:** MITRE clasifica esta vulnerabilidad como **CWE-89: Improper
Neutralization of Special Elements used in an SQL Command ('SQL Injection')**.
La definición oficial señala que el producto construye total o parcialmente un
comando SQL usando input externo, pero no neutraliza (o neutraliza
incorrectamente) los elementos especiales que podrían alterar ese comando antes
de que llegue a la base de datos [1].

### Cómo levanté el ambiente

Me coloqué en la carpeta `Ejercicio1` del repo, que ya traía armados el
`Dockerfile` y el `docker-compose.yml`, y levanté todo con:

```bash
docker compose up -d
docker compose ps
```

El build corrió los pasos esperados del `Dockerfile`: copia `requirements.txt`,
instala las dependencias con `pip install --no-cache-dir -r requirements.txt`
y después copia el resto del proyecto. Al terminar, `docker compose ps` mostró
el contenedor `ejercicio1-sqli` en estado `Up`, publicando el puerto 5000
(`0.0.0.0:5000->5000/tcp`).

![Terminal con docker compose up -d construyendo la imagen del Ejercicio 1 y docker compose ps mostrando el contenedor Up](imagenes/imagen%201%20arranque%20del%20contenedor%20del%20ejercicio%201.png)

*Figura 1. `docker compose up -d` construyendo la imagen del Ejercicio 1 y `docker compose ps` confirmando que el contenedor `ejercicio1-sqli` quedó `Up`, con el puerto 5000 publicado.*

Con el contenedor arriba, entré a `http://localhost:5000` desde Firefox en la
VM y cargó la aplicación que por lo que entendí es un buscador de
funciones de cine con un campo de texto y dos select para ordenar los
resultados.

![Portada de CineBuscador recién cargada, con el campo de búsqueda vacío](imagenes/imagen%202%20inicio%20de%20la%20app%20ejercicio%201.png)

*Figura 2. Portada de CineBuscador en `localhost:5000`, con el ambiente ya levantado y funcionando.*

### Análisis del código / dónde está la vulnerabilidad

La función que arma la consulta es `buscar_funciones`, en `app.py`. El valor de `query`, que viene directo de lo que el usuario escribe en el
buscador (`request.args.get('buscar', '')`), se inserta con el armado de
texto con variables insertadas directamente dentro de las comillas del
`LIKE`. No hay ningún filtro ni
tratamiento especial: lo que el usuario escriba pasa a formar parte literal de
la consulta SQL.

![Código de buscar_funciones en app.py con la cláusula LIKE y el sort_dir final resaltados como los puntos donde entra el input del usuario](imagenes/imagen%203%20lugar%20del%20codigo%20vulnerable.png)

*Figura 3. Función `buscar_funciones` en `app.py`: el `LIKE '%{query}%'` y el `{sort_dir}` del `ORDER BY` quedan resaltados como los dos puntos donde el input del usuario se concatena directo en el SQL.*

Además del campo de búsqueda, el parámetro `sentido` (que controla si el
orden es ascendente o descendente) tampoco tiene ninguna validación. A
diferencia de `sort_by`, que sí está limitado por un `if/else` a solo dos
valores posibles (`peliculas.nombre` o `funciones.fecha_hora`), `sort_dir` se
concatena directamente en la consulta sin ningún control. Esto deja dos puntos
de inyección independientes en la misma función: uno en el `WHERE` (`query`) y
otro en el `ORDER BY` (`sort_dir`).

### Prueba de Concepto (explotación)

Primero probé una búsqueda normal, por ejemplo `Dune`, para confirmar que la
app funciona bien y devuelve la película con sus funciones. En la práctica, la
captura que dejé de esta prueba corresponde a una búsqueda con `a`, que
también devuelve resultados normales sin ningún error:

![Búsqueda de "a" devolviendo 17 funciones encontradas, ordenadas por nombre de película](imagenes/imagen%204%20resultado%20buscar%20a.png)

*Figura 4. Búsqueda normal (`buscar=a`) funcionando sin errores: 17 funciones encontradas, ordenadas por nombre de película.*

**Paso 1 — Romper la consulta con una comilla**

Después probé escribir una sola comilla simple (`'`) en el buscador:

```text
http://localhost:5000/?buscar='
```

La aplicación tiró un error:

![Error de sintaxis SQL al inyectar una comilla sola en el parámetro buscar](imagenes/imagen%205%20como%20se%20rompio%20con%20una%20comilla.png)

*Figura 5. `buscar='`: `sqlite3.OperationalError: unrecognized token: "' ORDER BY peliculas.nombre ASC"`.*

Esto confirma la vulnerabilidad: mi comilla se metió directo en la consulta SQL
y rompió su estructura. Si el sistema no tuviera esta falla, debería tratar mi
búsqueda como un texto normal: no importaría qué caracteres escriba, nunca
debería romper la consulta.

**Paso 2 — Intentar forzar que devuelva todo**

Mi idea era escribir `' or 1=1 --` para forzar que la condición del WHERE
siempre sea verdadera y así traer todos los resultados sin importar el nombre
de la película. Por error escribí `' or 1='`, pero igual la app devolvió las 21 funciones de la base de
datos:

![Búsqueda con la entrada incompleta ' or 1=' devolviendo igualmente 21 funciones encontradas](imagenes/imagen%206%20inyeccion%20que%20toque%20enter%20sin%20querer.png)

*Figura 6. Prueba incompleta `' or 1='` (typo, quedó a mitad de camino) devolviendo igualmente las 21 funciones de la base.*

Al principio pensé que esto pasaba porque `1='%'` se estaba evaluando como
verdadero. Investigando un poco más en la documentación de SQLite, encontré que
al comparar un número contra un texto que no es numérico (como `'%'`), SQLite
lo trata como falso, no como verdadero [2]. Entonces la razón real por la que
salió todo era otra: mi comilla dejó activo el `LIKE '%'` original de la
aplicación, y ese `%` ya significa "cualquier cosa" en SQL, así que alcanzaba
solo con eso para que el WHERE coincidiera con todas las películas.

**Paso 3 — usando `' or 1=1 --`**

Repetí la prueba en el input de la página, con la idea de que el WHERE diera
siempre true.

![Búsqueda con la entrada ' or 1=1 -- devolviendo 21 funciones encontradas](imagenes/imagen%207%20con%201%20igual%201%20y%20comentando%20el%20resto.png)

*Figura 7. Prueba con `' or 1=1 --`: `1=1` es una comparación numérica siempre verdadera y `--` comenta el resto de la consulta original. Resultado: las 21 funciones de la base, esta vez por el motivo buscado y no por casualidad.*

Comparando esta captura con la del Paso 2, noté algo más: la lista de
películas que se muestra no queda en el mismo orden en los dos casos, aunque
ambas digan "21 funciones encontradas". En el Paso 2 (`' or 1='`, sin `--`) el
orden sigue siendo alfabético por nombre de película, porque el `ORDER BY
peliculas.nombre ASC` de la consulta original queda intacto. Acá, en cambio,
el `--` comenta todo lo que viene después, así que también borra el
`ORDER BY` que estaba a continuación del `WHERE`. Sin ningún `ORDER BY`,
SQLite devuelve las filas en el orden que le resulta más simple internamente
(según cómo las tiene guardadas), y por eso la lista sale desordenada
respecto del nombre de película.

Acá `1=1` es una comparación numérica que siempre es verdadera y como ya dijimos el `--`
comenta el resto de la consulta original para que no interfiera. 


**Segundo punto de inyección — parámetro `sentido`**

Como mencioné en el análisis del código, `sort_dir` tampoco tiene validación.
Probé:

```text
http://localhost:5000/?buscar=a&ordenar_por=nombre&sentido='
```

![Error unrecognized token al inyectar una comilla en el parámetro sentido, rompiendo la cláusula ORDER BY](imagenes/imagen%208%20url%20tocada%20para%20ver%20si%20se%20puede%20modificar%20el%20sentido%20de%20la%20consulta.png)

*Figura 8. Inyección en el parámetro `sentido` (`buscar=a&ordenar_por=nombre&sentido='`): `sqlite3.OperationalError: unrecognized token: "'"`, un error corto y distinto al del Paso 1, porque acá `buscar=a` es un valor válido y lo único que se rompe es la cláusula `ORDER BY`.*

La app devolvió el mismo tipo de error (`unrecognized token`) que en el
Paso 1, pero acá el token que queda sin reconocer es corto — solo la
comilla (`"'"`) — en vez de arrastrar el resto de la consulta como en el
Paso 1. Tiene sentido: acá `buscar=a` es un valor válido, así que lo único
que se rompe es la cláusula `ORDER BY`. Esto confirma un segundo punto de
inyección independiente en la misma función, sobre una parte distinta de la
consulta.

**Otro detalle que noté:** este error también mostró información de más —
nombres de archivos del código y en qué línea falló. Eso pasa por el mismo
motivo que en el Paso 1 (la app corre en modo debug) y es otro problema aparte
de la inyección SQL.

### Impacto de la vulnerabilidad

El impacto en este caso puntual termina siendo limitado, porque la base de datos solo
contiene dos tablas (`peliculas` y `funciones`) con información de la cartelera
de cine, no cuenta con datos sensibles como usuarios, contraseñas o información
personal. Por eso no tiene sentido forzar una extracción de datos con algo
como un `UNION SELECT`, ya que no hay nada crítico que robar.

Dicho esto, la vulnerabilidad existe y es grave, independientemente
de qué datos haya en esta base específica. Lo que demuestra la prueba es que un
atacante puede alterar completamente la lógica de la consulta SQL a través de un
parámetro de la URL o del campo de búsqueda. Sin ningún tipo de filtro se puede 
romper la sintaxis de la consulta y forzar que la condición del `WHERE` sea siempre verdadera
para traer todos los registros.

En una aplicación real con esta misma falla del código —donde sí va a haber
tablas de usuarios, contraseñas, o datos personales— el mismo tipo de ataque
permitiría extraer esa información completa o incluso saltear un login sin
conocer la contraseña. El problema aquí es que el código no distingue en ningún momento entre datos del
usuario y código SQL.

### Mitigación implementada

Mientras revisaba el resto del código para entender mejor el proyecto, me fijé
en `init_db.py`, que es el archivo que carga las películas de ejemplo en la
base. Ahí encontré esto:

![Fragmento de init_db.py usando executemany con placeholders (?) para insertar las películas](imagenes/imagen%209%20ejemplo%20de%20como%20se%20parametriza%20en%20el%20init%20de%20la%20bd.png)

*Figura 9. `init_db.py` insertando las películas de ejemplo con `executemany` y placeholders `?`: los datos van aparte de la consulta SQL.*

Acá los `?` funcionan como espacios reservados, donde el valor real de cada campo
(nombre, género, director) se pasa aparte, en la lista que viene después. Básicamente lo que se hace es evitar que se escriba directamente adentro del texto SQL.

Me pareció relevante mencionar esto porque es exactamente lo contrario de lo que
hace `buscar_funciones`, donde el texto que escribe el usuario se pega
directo dentro del comando SQL.

De esta manera apliqué las mitigaciones en dos partes, empezando por la más relevante, es decir la
cláusula `LIKE` de la consulta.

**Mitigación 1 — Parámetro `buscar` (cláusula `WHERE ... LIKE`)**

Cambié la consulta para que el valor de búsqueda no se arme más con el
armado de texto con variables insertadas, sino que se pase como parámetro
separado del SQL:

![Código corregido de buscar_funciones: LIKE ? en el SQL y el valor pasado aparte en db.execute](imagenes/imagen%2010%20consulta%20en%20el%20where%20parametrizada.png)

*Figura 10. `buscar_funciones` corregida: el `WHERE` queda como `LIKE ?` y el valor de búsqueda (`f'%{query}%'`) se pasa como parámetro aparte en `db.execute(sql, (...))`, en vez de concatenarse dentro del SQL.*

Básicamente lo que hace el código es parametrizar la consulta para que lo que
escriba el usuario nunca pueda ser leído por el servidor como parte del SQL. 
El `?` queda fijo en la consulta y el contenido de `query` viaja aparte, como un
dato.

Después de aplicar el cambio, reconstruí la imagen de Docker con
`docker compose up -d --build`, porque el código había cambiado y necesitaba
que la imagen se reconstruyera con el archivo actualizado:

![docker compose up --build reconstruyendo la imagen con el cambio en el WHERE ya aplicado](imagenes/imagen%2011%20docker%20build%20del%20cambio.png)

*Figura 11. `docker compose up -d --build` reconstruyendo la imagen del Ejercicio 1 con la corrección del `WHERE` ya aplicada en el código.*

**Mitigación 2 — Parámetro `sentido` (cláusula `ORDER BY`)**

Para el segundo punto de inyección hice un filtro que revisa el valor que
llega en el parámetro `sentido` y solo deja pasar `ASC` o `DESC`, sin permitir
que la variable tome otro valor distinto dentro del `ORDER BY`.

Con este cambio, `orden` nunca contiene lo que el usuario haya escrito
literalmente, solo puede terminar siendo uno de estos dos valores fijos que definimos
en el código.

Al guardar este cambio y reconstruir, `docker compose ps` me mostró el
contenedor en estado `Restarting` por unos segundos.

![docker compose ps mostrando el contenedor ejercicio1-sqli en estado Restarting tras aplicar el cambio en sort_dir](imagenes/imagen%2012%20contenedor%20reiniciando%20despues%20del%20cambio.png)

*Figura 12. `docker compose ps` mostrando el contenedor `ejercicio1-sqli` en `Restarting (1) 34 seconds ago`, justo después de guardar el cambio de la lista de valores permitidos en `sort_dir`.*

Volví al editor a revisar el `if/else` que acababa de escribir para asegurarme
de que estuviera bien formado antes de seguir.

![Código de buscar_funciones en VS Code con el if/else de la lista de valores permitidos de sort_dir ya revisado](imagenes/imagen%2013%20revisando%20el%20codigo%20del%20if%20else.png)

*Figura 13. Revisión del `if sort_dir.upper() == 'ASC': ... else: ...` en VS Code, después del sobresalto del contenedor reiniciando.*

### Verificación de la mitigación

**Verificación de la mitigación (parámetro `buscar`)**

Con el cambio aplicado (`LIKE ?` + `db.execute(sql, (f'%{query}%',))`),
repetí exactamente las mismas entradas que antes explotaban la
vulnerabilidad.

**Antes de la mitigación:**
- `buscar='` → error de sintaxis SQL (`OperationalError`)
- `buscar=' or 1=1 --` → devolvía las 21 funciones de la base, ignorando el
  filtro de búsqueda

**Después de la mitigación:**
- `buscar='` → ya no rompe la consulta: la app responde con normalidad, sin
  ningún `OperationalError`

![Búsqueda con la entrada ' después de la mitigación, sin error de sintaxis](imagenes/imagen%2014%20con%20el%20codigo%20corregido%20del%20where.png)

*Figura 14. Después de la mitigación, una comilla sola (`'`) ya no rompe la consulta: la app responde con normalidad.*

- `buscar=' or 1=1 --` → "No se encontraron funciones para `' or 1=1 --`"

![Búsqueda con la entrada ' or 1=1 -- después de la mitigación, sin resultados encontrados](imagenes/imagen%2014.1%20con%201%20igual%201%20despues%20de%20la%20mitigacion.png)

*Figura 14.1. Después de la mitigación, la entrada `' or 1=1 --` ya no rompe la consulta ni devuelve toda la base: la app responde "No se encontraron funciones para `' or 1=1 --`".*

Ambos tipos de entrada ahora pasan a tratarse como texto literal de búsqueda, sin
afectar la estructura de la consulta SQL. Esto confirma que la
parametrización con `?` corrigió el problema y por lo tanto el valor ingresado por el
usuario ya no se interpreta como código SQL, sino como un dato de búsqueda
común, sin importar qué caracteres contenga.

**Verificación de la mitigación (parámetro `sentido`)**

Antes de meterme con la sentencia if/else, repetí la entrada `sentido='` ya con la
mitigación del `WHERE` puesta, para confirmar que los dos puntos de inyección
son realmente independientes, ya que si solo arreglaba el `LIKE`, el `ORDER BY`
tenía que seguir roto.

![Error unrecognized token en sentido=' después de aplicar la mitigación del WHERE pero antes de la del ORDER BY, con la línea db.execute(sql, (f'%{query}%',)) ya parametrizada visible en el error completo](imagenes/imagen%2015%20sentido%20sigue%20roto%20despues%20del%20fix%20del%20where.png)

*Figura 15. `sentido='` sigue rompiendo la consulta (`unrecognized token: "'"`) incluso con el `WHERE` ya parametrizado: en el error completo se ve `db.execute(sql, (f'%{query}%',))`, la versión corregida del `LIKE`, lo que confirma que este es un segundo punto de inyección independiente del primero.*

Y se confirmó lo que supuse, el error seguía siendo el mismo que antes de tocar
nada. Recién ahí apliqué la sentencia if/else en `sort_dir` y repetí el mismo dato de entrada.

```text
http://localhost:5000/?buscar=a&ordenar_por=nombre&sentido='
```

![Código con la lista de valores permitidos de sort_dir aplicada, dejando pasar solo ASC o DESC](imagenes/imagen%2016%20correccion%20del%20order%20by.png)

*Figura 16. Código de la mitigación en `sort_dir`: si el valor recibido, en mayúsculas, es `'ASC'`, `orden` queda en `'ASC'`; para cualquier otro caso (incluida una comilla) cae en el `else` y queda en `'DESC'`.*

**Antes de la mitigación:** `sqlite3.OperationalError: unrecognized token`

**Después de la mitigación:** la app responde con normalidad, sin ningún
error.

![Búsqueda "dune" ordenada por fecha y hora funcionando sin errores, con sentido=' en la URL](imagenes/imagen%2017%20arreglo%20de%20order%20by%20funcionando%20bien.png)

*Figura 17. Con la lista de valores permitidos aplicada, `sentido='` ya no rompe la consulta: la búsqueda "dune" se muestra ordenada por fecha y hora sin ningún error.*

Como la comilla no coincide con el string `'ASC'`, la variable `orden` cae en
el `else` y toma el valor `'DESC'`, que es un valor válido y seguro para el
SQL. Cualquier otro texto que se mande en `sentido` va a tener el mismo
resultado, nunca se insertará directamente en la consulta, solo se usa para
decidir entre dos valores fijos y controlados.

### Resumen de mitigaciones — Ejercicio 1

| Punto de inyección | Mitigación aplicada |
|---|---|
| Parámetro `buscar` (cláusula `WHERE ... LIKE`) | Consulta parametrizada con `?` |
| Parámetro `sentido` (cláusula `ORDER BY`) | Lista de valores permitidos (`ASC`/`DESC`) |

Ambas correcciones siguen la misma idea: nunca insertar
directamente en el SQL un valor que provenga del usuario sin antes separarlo
del comando (parametrización) o restringirlo a un conjunto cerrado de
opciones válidas (lista de valores permitidos). El parámetro `sort_by` ya tenía este segundo
enfoque aplicado desde el código original, y me sirvió como referencia sobre que hacer con
`sort_dir` de la misma manera.

### Referencias

[1] MITRE. *CWE-89: Improper Neutralization of Special Elements used in an SQL
Command ('SQL Injection').* https://cwe.mitre.org/data/definitions/89.html

[2] SQLite. *Datatypes In SQLite — Type Conversions Prior To Comparison.*
https://www.sqlite.org/datatype3.html

<a id="ejercicio-2"></a>

## Ejercicio 2 — Cross Site Scripting (XSS)

### Definición de la vulnerabilidad

El **Cross-Site Scripting (XSS)** ocurre cuando una aplicación web incluye en
una página contenido proporcionado por un usuario sin procesarlo o
codificarlo correctamente. El navegador no distingue entre lo que escribió el
usuario y lo que es código que la página debe ejecutar: si el contenido
ingresado contiene elementos propios de HTML o JavaScript, puede
interpretarlos como código en lugar de mostrarlos simplemente como texto.

Básicamente, el código termina generando una página con código creado y
controlado por el atacante. Lo vulnerable de todo esto ocurre cuando otro
usuario accede a esa misma página, ya que su navegador ejecuta el código
controlado o alterado por el atacante, pudiendo hacerle creer que el sitio es
legítimo.

El riesgo principal de todo esto es la pérdida de **confidencialidad e
integridad**: un atacante puede manipular el contenido que puede visualizar
la víctima, realizar acciones en su nombre o acceder a información disponible
dentro del contexto de la aplicación. Dependiendo de las características de
la aplicación y de las medidas de seguridad implementadas, un ataque XSS
también puede utilizarse para, por ejemplo, agregar un formulario que envíe
la información al correo del atacante, obteniendo sus credenciales, capturar
información ingresada por el usuario o realizar otras acciones maliciosas.

**Fuente:** MITRE clasifica esta vulnerabilidad como **CWE-79: Improper
Neutralization of Input During Web Page Generation ('Cross-site
Scripting')**. La definición oficial señala que el software no neutraliza
correctamente la entrada controlada por el usuario antes de colocarla como
parte de una página web, permitiendo que el navegador de otro usuario
interprete ese contenido como código ejecutable [1].

### Cómo levanté el ambiente

Levanté el contenedor con Docker Compose dentro de la carpeta del ejercicio:

```bash
docker compose up
```

![Terminal con docker compose up construyendo y levantando el contenedor del Ejercicio 2](imagenes/imagen%2018%20arranque%20del%20contenedor%20del%20ejercicio%202.png)

*Figura 18. `docker compose up` construyendo la imagen del Ejercicio 2 y levantando el contenedor `ejercicio2-xss`, sirviendo la app Flask en el puerto 5000.*

Al entrar, la aplicación se ve igual que en el Ejercicio 1, el mismo buscador
de funciones de cine, pero cada resultado tiene un link que lleva a un
formulario donde se puede modificar el nombre, el género, el director y la
descripción de la película.

![Portada de CineBuscador con la columna Descripción y el link Editar visible en cada resultado](imagenes/imagen%2019%20pantalla%20principal%20del%20ejercicio%202.png)

*Figura 19. Portada de CineBuscador en el Ejercicio 2: además del buscador, cada función tiene una columna de descripción y un link "Editar" hacia el formulario de edición.*

### Prueba de Concepto (explotación)

**Primer intento — campo Nombre**

Antes de encontrar el punto exacto, probé insertar HTML en el campo
**Nombre** del formulario de edición, para ver si se interpretaba por el navegador.

```text
Dune: Parte Dos <p> Se ve sin la p? </p>
```

![Prueba de HTML en el campo Nombre antes de guardar](imagenes/imagen%2020%20intento%20de%20xss.png)

*Figura 20. Intento de inyección de HTML en el campo Nombre, antes de guardar los cambios.*

Al guardar, el título de la página (`<h2>Editar: {{ pelicula['nombre'] }}
...`) mostró el texto completo tal cual lo escribí, con los símbolos `<` y
`>` visibles como texto literal — no se generó ningún párrafo nuevo ni se
interpretó como HTML.

![Texto mostrado como literal en el título tras guardar, con los símbolos < y > visibles](imagenes/imagen%2021%20no%20se%20renderizo%20el%20html.png)

*Figura 21. El campo Nombre no interpreta el HTML: el texto se muestra escapado, tal como corresponde, tanto en el `<h2>` como en el propio campo.*

Esto confirma que el campo Nombre está protegido correctamente. Repetí la
misma prueba en Género y Director con el mismo resultado: en ningún caso se
interpretó el HTML.

**Segundo intento — campo Descripción**

El campo que sí resultó vulnerable fue **Descripción**. Edité la película
"Dune: Parte Dos" y agregué una etiqueta simple:

```text
<p> hola :D </p>
```

![Etiqueta p escrita en el campo Descripción, previo a guardar los cambios](imagenes/imagen%2022%20prueba%20con%20descripcion.png)

*Figura 22. Etiqueta `<p> hola :D </p>` escrita en el campo Descripción, previo a guardar los cambios.*

Al guardar y volver a entrar a editar esa misma película, encontré lo que estaba buscando: el texto se muestra sin las etiquetas HTML visibles en la parte de descripción.

![Descripción actual con el párrafo interpretado arriba y el textarea con el texto literal abajo](imagenes/imagen%2023%20se%20renderizo%20el%20parrafo%20en%20la%20descripcion.png)

*Figura 23. En el bloque "Descripción actual" (arriba) el `<p>` se interpretó como HTML real, generando un salto de línea; en el textarea (abajo) el mismo texto aparece literal, con los símbolos `<` y `>` visibles.*

En el textarea del formulario, el texto aparece literal, tal como debería
ser. En el bloque de "Descripción actual" (la vista previa, arriba del
formulario), en cambio, vemos directamente el texto "hola :D" separado del
resto, porque el navegador interpretó mi etiqueta `<p>` como una etiqueta
HTML real y creó un párrafo nuevo, en vez de mostrarla como texto.

Esto nos confirma que podemos inyectar código HTML en la aplicación, y que se
ejecuta específicamente en esa vista previa de la descripción.

### Intento con ejecutar un Script de JS

El siguiente paso fue confirmar que no solo se puede insertar HTML, sino
ejecutar código JavaScript real. En el mismo campo de descripción escribí:

```html
<script>alert('Te estamos hackeado >:(')</script>
```

![Script alert en el campo Descripción, previo a guardar los cambios](imagenes/imagen%2024%20script%20de%20javascript%20escrito%20en%20la%20descripcion.png)

*Figura 24. Código `<script>alert(...)</script>` en el campo Descripción, previo a guardar los cambios.*

Al guardar y volver a entrar a `/edit/1`, apareció automáticamente una
ventana del navegador con mi mensaje, apenas la página terminó de
cargar.

![Ventana emergente del navegador mostrando el mensaje del alert al cargar la página](imagenes/imagen%2025%20script%20de%20javascript%20ejecutandose%20en%20la%20pagina.png)

*Figura 25. El script se ejecuta automáticamente al renderizar la página, mostrando la ventana emergente "Te estamos hackeado >:(".*

Esto confirma que el navegador no está tratando mi texto solo como una
descripción de película, sino como código JavaScript que se ejecuta al
renderizar la página. Un `alert()` es inofensivo, pero nos muestra que en ese
mismo lugar podría ejecutarse cualquier otro código JavaScript. Por ejemplo,
uno que robe la cookie de sesión de quien esté viendo la página, o que
redirija a otro sitio directamente.

### Tipo de XSS

Este caso corresponde a un **XSS almacenado (stored)**. Ya que el código malicioso
no viaja en la URL ni depende de que la víctima haga clic en un link
especial, sino queda guardado directamente en la base de datos, en la columna
`descripcion` de la tabla `peliculas`, a través del `UPDATE` que ejecuta
`edit_post()` en `app.py`.

A partir de ese momento, cualquier usuario que visite `/edit/1` (no solo
quien lo escribió) va a ejecutar el `alert()` automáticamente al cargar la
página, sin necesidad de realizar ninguna acción en particular. Esto lo hace
más grave que un XSS reflejado, porque el ataque queda activo de forma
persistente hasta que alguien corrija el dato a nivel de base de datos.

### Dónde está el problema en el código

Revisando `edit.html`, encontré la causa exacta: hay dos lugares donde se
muestra la descripción, y uno de ellos tiene un filtro que hace que el
contenido se interprete como HTML en vez de mostrarse como texto.

![Línea 86 de edit.html mostrando el filtro safe aplicado sobre la descripción](imagenes/imagen%2026%20codigo%20que%20ocasiona%20el%20problema.png)

*Figura 26. Línea 86 de `edit.html`: `{{ pelicula['descripcion'] | safe }}`. El filtro `| safe` hace que este campo se muestre como HTML real, a diferencia del resto de los campos (como el `<textarea>` de la línea 89), donde las etiquetas se ven tal cual, como texto.*

El filtro `| safe` de Jinja2 (la biblioteca que usa el proyecto) hace que el
contenido se interprete directamente como HTML en lugar de mostrarse como
texto. Sin ese filtro, Jinja2 convierte automáticamente los caracteres
especiales (`<`, `>`) a su versión de texto antes de insertarlos en la
página, y por eso el navegador nunca los interpreta como código — que es
justo lo que pasa en el `<textarea>`, en el `<h2>` del nombre, y en los demás
campos del formulario.

### Impacto de la vulnerabilidad

El impacto en este caso es alto porque el formulario de edición no
requiere ningún tipo de autenticación: cualquier persona que
entre a `/edit/<id>` puede modificar la
descripción de cualquier película y dejar un script malicioso. Posteriormente ese script queda guardado de forma persistente y se ejecutará automáticamente para
cualquier otra persona que visite esa misma página después, sin que la
víctima tenga que hacer clic en ningún link especial ni realizar ninguna
acción distinta a entrar a editar la película.

En un escenario real, en vez de un `alert()` inofensivo, ese mismo punto
podría usarse para robar la cookie de sesión de quien vea la página y
suplantar su identidad, o para redirigir a un sitio falso que imite el login
de la aplicación.

### Mitigación implementada

Después de mirar bien el código encontré que el problema estaba únicamente en `edit.html`, en la línea que muestra la
vista previa de la descripción. El `| safe` no está mal en sí mismo, tiene sentido usarlo cuando el HTML que se muestra es generado por
la propia aplicación y no por un usuario, como lo es un campo editable. El error acá fue aplicarlo sobre un
dato que viene directamente de lo que cualquier persona escribe en el
formulario de edición, sin ningún tipo de control adicional.

La corrección fue sacar el filtro `| safe`.

![Línea 86 de edit.html corregida, sin el filtro safe](imagenes/imagen%2027%20codigo%20del%20front%20ya%20arreglado.png)

*Figura 27. Línea 86 de `edit.html` corregida: se eliminó `| safe`, quedando protegida igual que el resto de los campos.*

Está bueno mencionar que no hizo falta modificar `app.py` ya que el problema estaba solo en cómo se
mostraba el dato dentro del frontend.

### Verificación de la mitigación

Con el cambio aplicado, reconstruí el contenedor:

```bash
docker compose up -d --build
```

Repetí la prueba con `<p>` (ya que ahora se deberían ver las etiquetas `</p>` directamente). Al momento de probar esto, el bloque de "Descripción actual" y el
textarea mostraron exactamente el mismo texto, sin ninguna
diferencia entre ambos y sin interpretación del HTML.

![Descripción actual y textarea mostrando el mismo texto literal con las etiquetas p visibles, después de la mitigación](imagenes/imagen%2028%20descripcion%20mostrada%20como%20texto%20despues%20del%20arreglo.png)

*Figura 28. Después de la mitigación, la entrada `<p> ahora se deberían ver las etiquetas </p>` se muestra igual en ambos bloques: ya no se interpreta como HTML, solo como texto.*

Con el `<p>` de prueba se puede comprobar que el contenido de la descripción ahora se muestra como texto y no se interpreta como HTML.

Repetí también la prueba con código JavaScript para confirmar que la mitigación no solo protege contra HTML simple, sino que también evita la ejecución de JavaScript.

```html
<script>alert('Te estamos hackeado >:(')</script>
```

![Script mostrado como texto literal en ambos bloques, sin ejecutarse, tras la mitigación](imagenes/imagen%2029%20script%20sin%20ejecutarse%20despues%20del%20arreglo.png)

*Figura 29. Tras la mitigación, el script no se ejecuta: se muestra como texto plano tanto en "Descripción actual" como en el textarea, igual que con el `<p>` de la prueba anterior.*

A diferencia de antes de la mitigación (donde el `alert()` se disparaba
automáticamente al cargar la página), ahora el contenido se trata siempre
como texto, nunca como código, sin importar qué caracteres o etiquetas
contenga.

### Referencias

[1] MITRE. *CWE-79: Improper Neutralization of Input During Web Page
Generation ('Cross-site Scripting').*
https://cwe.mitre.org/data/definitions/79.html

<a id="ejercicio-3"></a>

## Ejercicio 3 — File Upload

### Definición de la vulnerabilidad

Un File Upload ocurre cuando una aplicación permite que un usuario
suba un archivo al servidor sin controlar correctamente qué tipo de archivo
es el que se está subiendo, ni qué contiene ni dónde queda guardado. Si el servidor confía plenamente en
lo que dice el nombre o la extensión del archivo, sin revisar su contenido
real, un atacante puede subir algo que aparenta ser "normal" para el servidor.

Pensando más en esto, el caso más grave posible sería subir un archivo que en realidad es código ejecutable,
ocultándolo bajo una extensión permitida por el servidor. Si ese archivo queda guardado en una carpeta desde la que el servidor puede ejecutar código, y no simplemente entregarlo como descarga, el atacante podría ejecutar su propio código directamente en el servidor. Esto podría permitirle realizar acciones no autorizadas sobre el sistema y comprometer una parte importante de la aplicación y sus recursos.

El riesgo principal es la **pérdida total de integridad y confidencialidad del servidor**. Con código propio ejecutándose ahí, un atacante podría acceder a información de la aplicación, modificar archivos del sistema o mantener acceso al servidor sin que nadie lo note.

**Fuente:** MITRE clasifica esta vulnerabilidad como **CWE-434: Unrestricted
Upload of File with Dangerous Type**. La definición oficial señala que el
producto permite la subida o transferencia de tipos de archivo peligrosos,
que son procesados automáticamente dentro de su propio entorno [1].

### Cómo levanté el ambiente

Este ejercicio cambia de tecnología: es Java con Spring
Boot (Maven), en vez de Python con Flask como los anteriores. Levanté el contenedor con Docker
Compose dentro de la carpeta del trabajo.

```bash
docker compose up -d --build
```

Con el contenedor arriba, la aplicación quedó accesible en
`http://localhost:8080`.

![Listado de películas funcionando en localhost:8080, con Sin afiche como placeholder](imagenes/imagen%2030%20app%20del%20ejercicio%203.png)

*Figura 30. La aplicación funcionando correctamente en `localhost:8080`: un listado de películas, cada una con un botón "Subir afiche" y el placeholder "Sin afiche" mientras no se cargó ninguna imagen.*

### Prueba de Concepto (explotación)

**Paso 1 — Confirmar que no hay ningún filtro de tipo**

Antes de intentar lograr un ataque como tal, probé subir un archivo de texto (un .txt) para ver qué hacía el servidor al momento de subirlo.

![Subiendo textoEjercicio3.txt desde el formulario de carga](imagenes/imagen%2031%20subiendo%20un%20archivo%20de%20texto%20a%20ver%20que%20hace.png)

*Figura 31. Subiendo `textoEjercicio3.txt` desde el formulario "Subir afiche", sin que el input ni el servidor pongan ningún obstáculo.*

La aplicación lo aceptó sin ningún problema. En el listado, la película quedó
con un ícono de imagen roto en vez del placeholder con el texto de "Sin afiche" ya que se ve que el
navegador intentó renderizar el `.txt` como si fuera una imagen.

![Listado mostrando el afiche roto después de subir el archivo de texto, comparado con las demás películas sin afiche](imagenes/imagen%2032%20comparacion%20de%20afiches%20con%20el%20archivo%20de%20texto.png)

*Figura 32. Comparación en el listado: la película donde subí el `.txt` muestra un ícono de imagen rota ("Afiche"), mientras las demás siguen mostrando el placeholder "Sin afiche".*

Después de ver que el .txt había quedado guardado en el servidor, probé acceder directamente a la URL del recurso para ver qué mostraba.

```text
http://localhost:8080/uploads/textoEjercicio3.txt
```

![El archivo de texto servido correctamente por el navegador como texto plano](imagenes/imagen%2033%20el%20archivo%20de%20texto%20se%20ve%20tal%20cual.png)

*Figura 33. El servidor devuelve `textoEjercicio3.txt` tal cual, mostrando su contenido real como texto plano en el navegador.*

El servidor permitió acceder al recurso porque no había ningún control que verificara el tipo de archivo antes de guardarlo ni al momento de devolverlo. Por eso fue posible subir y acceder directamente a un archivo HTML.

**Paso 2 — Escalar a un archivo HTML con JavaScript**

Repetí el mismo tipo de prueba, esta vez subiendo un archivo HTML que contenía un script de JavaScript para comprobar qué ocurría con un archivo que no era una imagen.

```html
<html>
<body>
<h1>Esto no es una imagen</h1>
<script>alert('Soy un archivo html... si me ves me estoy ejecutando')</script>
</body>
</html>
```

Lo subí desde el formulario de la misma forma que el `.txt`, sin que la aplicación hiciera ninguna validación sobre el tipo de archivo.

![Subiendo ataqueEjercicio3.html desde el formulario de carga](imagenes/imagen%2034%20subiendo%20el%20archivo%20html.png)

*Figura 34. Subiendo `ataqueEjercicio3.html` (174 bytes) desde el formulario "Subir afiche", para la película Interstellar.*

Al acceder directamente a la URL donde quedó guardado el archivo, el navegador lo interpretó como una página HTML y ejecutó el script automáticamente, mostrando el `alert()`.

![El alert ejecutándose automáticamente al abrir la URL del archivo html subido](imagenes/imagen%2035%20el%20alert%20ejecutandose%20al%20abrir%20el%20html.png)

*Figura 35. `http://localhost:8080/uploads/ataqueEjercicio3.html` ejecuta el script apenas se abre la URL, mostrando el `alert()` "Soy un archivo html... si me ves me estoy ejecutando".*

Esto confirma que el servidor no solo permite subir archivos de cualquier tipo, sino que además devuelve esos archivos de una forma que hace que el navegador pueda interpretarlos como código. En este caso, el código llegó a la aplicación a través de un archivo subido y no de un campo de texto, como ocurre en un XSS.

### Dónde está el problema en el código

La vulnerabilidad tiene tres partes ubicadas en `PeliculaController.java` y
`upload.html`.

**1. Al subir el archivo — no se valida nada**

![Código de uploadFile original sin ninguna validación, usando el nombre original del archivo tal cual](imagenes/imagen%2036%20codigo%20de%20subida%20sin%20ninguna%20validacion.png)

*Figura 36. `uploadFile()` original: `filename` se toma directo de `archivo.getOriginalFilename()` y se usa tal cual para guardar el archivo con `Files.copy(...)`, sin ninguna validación de por medio.*

`filename` corresponde al nombre del archivo que el navegador envía como parte del formulario al servidor, y es un dato que puede controlar directamente la persona que lo sube. En ningún momento se verifica la extensión ni el contenido real del archivo. El archivo se copia directamente con el nombre recibido.

**2. Al acceder al archivo — se decide el tipo según el nombre, no según el contenido**

![Código de serveFile original decidiendo el Content-Type según la extensión del nombre, con Content-Disposition inline](imagenes/imagen%2037%20codigo%20que%20no%20chequea%20nada%20al%20mostrar%20el%20archivo.png)

*Figura 37. `serveFile()` original: `MediaTypeFactory.getMediaType(resource)` infiere el `Content-Type` a partir de la extensión del nombre, y la respuesta usa `Content-Disposition: inline`.*


`MediaTypeFactory.getMediaType()` determina el tipo de contenido a partir de la extensión del nombre del archivo y no de su contenido real. Como mi archivo se llamaba `ataqueEjercicio3.html`, el servidor lo devolvió con `Content-Type: text/html`, por lo que el navegador lo va a interpretar como una página web.

Además, la respuesta utiliza `Content-Disposition: inline`, que le indica al navegador que puede mostrar el archivo directamente. Si se utilizara el valor `attachment`, el navegador lo trataría como un archivo para descargar en lugar de mostrarlo como una página. En este caso, al usar `inline` y ser el archivo un HTML, el navegador lo interpretó como una página web y ejecutó el script que contenía.


**3. Sin ninguna restricción del lado de la página web**

Como el código del frontend está realizado de esta manera:
```html
<input type="file" name="afiche" id="afiche" accept="*/*" required>
```

Ni siquiera existe un filtro básico en el navegador: `accept="*/*"` permite seleccionar cualquier tipo de archivo. De los tres puntos, este es el menos importante, ya que el atributo `accept` solo controla lo que se puede seleccionar desde el navegador y no sirve como una medida de seguridad real. Igual me pareció importante mencionarlo para complementar el análisis.

Estos tres puntos muestran que en ningún momento se controla correctamente qué tipo de archivo se está recibiendo. Por eso, es posible subir un archivo que no sea una imagen y, una vez guardado, el servidor lo entrega de una forma que hace que el navegador pueda interpretarlo y ejecutarlo como código, en lugar de tratarlo simplemente como un archivo.

### Impacto de la vulnerabilidad

Lo que demostré con la prueba es que un archivo subido anteriormente puede hacer que se ejecute código en el navegador de la persona que abre el link. Es bastante similar a lo que vimos con XSS en el Ejercicio 2, solo que en este caso la entrada del usuario es un archivo y no un campo de texto.

El problema es que el archivo queda guardado directamente en el servidor y pasa a estar disponible mediante una URL. Esto hace que cualquiera pueda compartir ese link y que cualquier otra persona que lo abra termine ejecutando el mismo código en su propio navegador.

En un escenario real, un archivo de este tipo podría utilizarse para ejecutar JavaScript en el navegador de otras personas. Dependiendo de la aplicación y de sus medidas de seguridad, esto podría permitir modificar el contenido que ve la víctima, redirigirla a otro sitio o intentar acceder a información de su sesión.

Con esta prueba confirmamos que el código se ejecuta en el navegador de la víctima y no directamente en el servidor. En este caso, `serveFile()` simplemente devuelve el archivo tal cual está guardado, no lo ejecuta en el servidor.

Igualmente, el problema sigue siendo que la aplicación confía en el nombre y la extensión del archivo sin comprobar realmente qué contiene. Esta falta de control es el principal punto débil, ya que en otras configuraciones podría llegar a permitir la ejecución de código directamente en el servidor.


### Mitigación implementada

Hice cambios en los dos puntos donde se estaba dando el problema. Primero modifiqué `serveFile()`, que es la parte encargada de devolver los archivos que ya están guardados, para que solo permita los tipos de archivo que definimos. Después modifiqué `uploadFile()`, para controlar también el archivo en el momento en que se sube y evitar usar directamente el nombre que proporciona el usuario.

**1. Control al acceder al archivo (`serveFile()`)**

Agregué una lista de extensiones permitidas (`jpg`, `jpeg`, `png`). Si la extensión del archivo solicitado no está en esa lista, la respuesta es `415` en vez de devolver el contenido.

![Código de serveFile con la validación de la lista de extensiones permitidas](imagenes/imagen%2038%20codigo%20revisando%20si%20el%20archivo%20es%20valido%20antes%20de%20mostrarlo.png)

*Figura 38. `serveFile()` con la lista de extensiones permitidas aplicada antes de devolver el archivo: si la extensión no es válida, responde `415` en vez de devolver el contenido.*

Con esta mitigación ya aplicada, repetí el acceso directo al archivo `ataqueEjercicio3.html` que había quedado guardado desde la prueba inicial:


```text
http://localhost:8080/uploads/ataqueEjercicio3.html
```

![Error 415 Unsupported Media Type al intentar acceder al archivo html ya guardado, con serveFile mitigado pero uploadFile todavía sin restricciones](imagenes/imagen%2039%20error%20al%20intentar%20acceder%20al%20html%20ya%20guardado.png)

*Figura 39. Con `serveFile()` ya mitigado, el navegador reporta "Error code: 415 Unsupported Media Type" al intentar acceder al `ataqueEjercicio3.html` que ya estaba guardado. En este punto `uploadFile()` todavía no tenía ninguna restricción — de hecho, en ese momento se podría haber vuelto a subir el mismo archivo sin problema — pero `serveFile()` ya bloqueaba su ejecución al devolverlo. Esto demuestra que el cambio en `serveFile()` alcanza por sí solo para neutralizar el ataque, incluso antes de tocar `uploadFile()`.*

**2. Al subir (`uploadFile()`)**

El paso siguiente fue cortar el problema también en el punto de entrada, para
no depender únicamente de `serveFile()`. La idea era agregar la misma
lista de extensiones permitidas (`jpg`, `jpeg`, `png`) y generar un nombre propio
con `UUID.randomUUID()` en vez de usar el nombre original.

![Código final de uploadFile mitigado, compilando correctamente con la lista de extensiones permitidas y el nombre generado con UUID](imagenes/imagen%2040%20codigo%20que%20arregla%20la%20falla%20al%20subir.png)

*Figura 40. Versión final de `uploadFile()`: lista de extensiones permitidas (`jpg`, `jpeg`, `png`) y nombre de archivo generado con `UUID.randomUUID()` en vez del nombre original.*

Al probar esta mitigación con el mismo `ataqueEjercicio3.html`, la aplicación
lo rechazó — aunque en ese momento todavía lo hacía mostrando una página de
error genérica de Spring Boot (500 Internal Server Error), poco clara para un
usuario real.

![Whitelabel Error Page genérica de Spring Boot al rechazar el archivo html](imagenes/imagen%2041%20rechazo%20al%20subir%20el%20archivo%20html.png)

*Figura 41. Al subir `ataqueEjercicio3.html` con la validación ya implementada en `uploadFile()`, la aplicación rechaza el archivo mediante una excepción, pero Spring Boot todavía muestra su página de error genérica (500), sin mostrar el mensaje personalizado.*

Los logs del contenedor confirman el mismo rechazo del lado del servidor,
mostrando el dispatch al manejador de error por defecto con status 500:

```text
o.s.web.servlet.DispatcherServlet : "ERROR" dispatch for POST "/error", parameters={multipart}
...
o.s.web.servlet.DispatcherServlet : Exiting from "ERROR" dispatch, status 500
```

No llegué a mejorar esto — la Whitelabel Error Page genérica de Spring Boot
quedó tal cual para este caso. En un trabajo real, este error se debería
manejar en los dos lados: en el backend, con un capturador de excepciones
que atrape el error y devuelva una página propia (o una respuesta JSON
clara si el front consume una API) en vez de la página genérica de Spring
Boot; y en el frontend, validando la extensión del archivo antes de
enviarlo al servidor, para que el usuario vea el error al instante sin
necesidad de esperar la respuesta del backend. Ninguna de las dos cosas
llegué a implementarla acá, solo quedó la validación del lado del servidor.

Con los dos cambios ya activos, `uploadFile()` corta los archivos no permitidos
antes de guardarlos, y `serveFile()` queda como respaldo para
cualquier archivo que —como pasó en mi propia prueba— haya quedado guardado
de antes, sin depender de un único punto de control.

### Verificación de la mitigación

Con ambas mitigaciones aplicadas, repetí las pruebas:

**Intento de subir `ataqueEjercicio3.html` de nuevo:**

La aplicación rechazó el archivo con la misma excepción que se
ve en la Figura 41 (`IllegalArgumentException: EL tipo de archivo no es
válido`), sin llegar a guardarlo, mostrando la misma Whitelabel Error Page
genérica.

**Acceso directo al `ataqueEjercicio3.html` que ya estaba guardado de antes
de aplicar cualquier mitigación:**

Este caso ya había quedado demostrado en la Figura 39, cuando probé
`serveFile()` por primera vez: el archivo viejo se bloquea con `415
Unsupported Media Type` en vez de ejecutarse, sin importar si `uploadFile()`
ya está restringido o no. Repetir la prueba con ambas mitigaciones activas da
el mismo resultado, confirmando que el control de `serveFile()`
sigue funcionando de forma independiente del de `uploadFile()`.

**Subida de un archivo de imagen real, para confirmar que el flujo normal
sigue funcionando:**

![Seleccionando un archivo de imagen real (avengers.jpeg) para subir como afiche](imagenes/imagen%2042%20subiendo%20un%20afiche%20real.png)

*Figura 42. Seleccionando `avengers.jpeg` (67 KB, una imagen real) para subirla como afiche de Avengers: Endgame, ya con ambas mitigaciones activas.*

![Resultado final mostrando el afiche real de Avengers Endgame ya cargado correctamente](imagenes/imagen%2043%20resultado%20final%20con%20el%20afiche%20real.png)

*Figura 43. El afiche real de Avengers: Endgame se sube y se muestra correctamente en el listado, confirmando que el flujo legítimo de la aplicación sigue funcionando sin problemas tras aplicar ambas mitigaciones.*

Con esto quedan cubiertos los tres escenarios: el flujo legítimo sigue
funcionando, un archivo peligroso nuevo se rechaza al subir, y un archivo
peligroso que ya estaba guardado de antes queda bloqueado al intentar acceder a él.

### Referencias

[1] MITRE. *CWE-434: Unrestricted Upload of File with Dangerous Type.*
https://cwe.mitre.org/data/definitions/434.html

<a id="ejercicio-4"></a>

## Ejercicio 4 — Server-Side Template Injection (SSTI)

### Definición de la vulnerabilidad

Una **Server-Side Template Injection (SSTI)** ocurre cuando una aplicación utiliza información ingresada por el usuario dentro de una plantilla que luego es procesada por el servidor, sin controlar correctamente qué puede introducirse.

El problema aparece cuando el servidor no trata esa información solamente como texto, sino que también puede interpretarla como una expresión de la plantilla.

En este caso, un atacante puede ingresar una expresión y hacer que el servidor la evalúe. Dependiendo de cómo esté configurada la aplicación, esto puede permitir acceder a información que no debería estar disponible, modificar datos o incluso ejecutar comandos en el servidor.

Por esto, una SSTI puede tener un impacto importante, ya que el problema no queda solamente en la aplicación, sino que puede llegar al servidor donde está funcionando.

**Fuente:** MITRE clasifica esta vulnerabilidad como **CWE-1336: Improper Neutralization of Special Elements Used in a Template Engine**. La definición explica que ocurre cuando una aplicación utiliza un motor de plantillas para procesar información ingresada desde fuera, pero no controla correctamente los elementos especiales que puede contener esa información, haciendo que sean interpretados por el motor [1].

### Cómo levanté el ambiente

Al igual que en el Ejercicio 3, este ejercicio está hecho en Java con Spring Boot (Maven).

Levanté el contenedor con Docker Compose dentro de la carpeta del ejercicio:

```bash
cd ~/Consigna_Practica_2_DDSS/Ejercicio4
docker compose up -d --build
```

La aplicación es nuevamente un buscador de funciones de cine, pero en este ejercicio aparece un cartel arriba del buscador indicando que existe una vulnerabilidad de SSTI (SpEL injection).

### Prueba de Concepto (explotación)

#### Paso 1 — Prueba de detección

Antes de intentar nada más, probé una entrada sencilla para comprobar si existía una SSTI. Por lo que leí en PortSwigger, una forma de detectarla es introducir una operación matemática en el campo de búsqueda, en vez de un nombre de película:

```text
3*3
```

![Buscador de Ejercicio 4 con 3*3 en el campo de busqueda y Resultados buscando por: 9 en el mensaje](imagenes/imagen%2044%20resultado%20del%203%20por%203.png)

*Figura 44. Valor `3*3` en el buscador de Ejercicio 4. El mensaje de resultados muestra "Resultados buscando por: 9", en vez del texto `3*3`.*

La aplicación devolvió `9` en el mensaje de resultados, en vez de mostrar el texto `3*3`. Esto indica que la entrada que escribí no se está tratando solamente como texto, sino que la aplicación está evaluando la expresión matemática.

Esta es una de las pruebas que recomienda PortSwigger para detectar SSTI. Si una operación como `7*7` aparece como texto, significa que no fue evaluada. En cambio, si aparece como `49`, significa que la expresión fue evaluada por el motor de plantillas, lo que indica que existe una posible vulnerabilidad [2].

Repetí también la prueba utilizando el ejemplo que aparece en PortSwigger:

```text
{7*7}
```

![Resultado de {7*7} mostrando Resultados buscando por: [49]](imagenes/imagen%2045%20confirmando%20con%20siete%20por%20siete%20da%2049.png)

*Figura 45. `{7*7}` devuelve `[49]`, confirmando el mismo comportamiento que con `3*3`.*

#### Paso 2 — Identificar el motor utilizado

Al revisar la estructura del proyecto, encontré un archivo llamado `SpelEvaluator.java`. Esto me permitió identificar que la aplicación estaba utilizando **SpEL (Spring Expression Language)**, que es el lenguaje de expresiones de Spring.

![Codigo completo de SpelEvaluator.java sin mitigar, con las lineas standardContext.setVariable("system", ...) y ("runtime", ...) resaltadas](imagenes/imagen%2046%20codigo%20original%20sin%20arreglar.png)

*Figura 46. `SpelEvaluator.java` original. `parser.parseExpression(expression)` recibe directamente el texto del buscador y las variables `system` y `runtime` quedan disponibles dentro de la expresión.*

Revisando el código, encontré dos problemas en el método `evaluate()`.

Primero, el parámetro `expression` recibe directamente el texto que llega desde el buscador. Luego, la línea `expr.getValue(standardContext)` evalúa ese texto como una expresión de SpEL.

El segundo problema es que el código deja disponibles las variables `system` y `runtime` dentro de la expresión. En particular, `Runtime` permite ejecutar comandos del sistema operativo.

Por lo tanto, al poder ingresar expresiones desde el buscador y tener acceso a `Runtime`, la aplicación permite llegar a ejecutar comandos en el servidor.

También encontré que el código ya tenía definido un `SimpleEvaluationContext`, que es un contexto más restringido, pero no se estaba utilizando. La evaluación se hacía con `standardContext`, que permitía realizar muchas más operaciones.

#### Paso 3 — Probar la ejecución de comandos

Una vez comprobado que las expresiones se estaban evaluando, probé si la variable `runtime` realmente estaba disponible:

```text
#runtime.getRuntime()
```

![Resultado de #runtime.getRuntime() mostrando Resultados buscando por: java.lang.Runtime@648673b3](imagenes/imagen%2047%20resultado%20pidiendo%20el%20runtime.png)

*Figura 47. `#runtime.getRuntime()` devuelve `java.lang.Runtime@648673b3`, mostrando que se pudo obtener una instancia de `Runtime` del servidor.*

Después utilicé esa instancia para ejecutar un comando del sistema operativo:

```text
#runtime.getRuntime().exec('ls')
```

![Resultado de #runtime.getRuntime().exec('ls') mostrando Resultados buscando por: Process[pid=91, exitValue=not exited]](imagenes/imagen%2048%20resultado%20haciendo%20un%20ls.png)

*Figura 48. `#runtime.getRuntime().exec('ls')` devuelve `Process[pid=91, exitValue="not exited"]`. El resultado es un proceso creado por Java. El PID obtenido muestra que el comando fue ejecutado en el servidor.*

Repetí esta prueba varias veces durante la exploración, obteniendo distintos PID en los resultados. También probé con `exec('whoami')`, aunque en este caso no saqué una captura del navegador y solamente quedó registrado en los logs del contenedor.

Además, probé acceder a las variables de entorno del servidor utilizando la otra variable que estaba disponible:

```text
#system.getenv()
```

![Resultado de #system.getenv() mostrando las variables de entorno del contenedor, incluyendo JAVA_HOME, HOSTNAME y SPRING_DATASOURCE_URL](imagenes/imagen%2049%20resultado%20con%20las%20variables%20del%20sistema.png)

*Figura 49. `#system.getenv()` devuelve las variables de entorno del contenedor, incluyendo `HOSTNAME`, `SPRING_DATASOURCE_URL`, `JAVA_HOME`, entre otras.*

Entre los datos obtenidos aparece, por ejemplo, la URL utilizada para conectarse a la base de datos. Esta información no debería estar disponible desde un buscador de películas.

También intenté obtener directamente la salida de texto de un comando utilizando `java.util.Scanner` para leer el resultado del proceso. No logré encontrar la sintaxis correcta en SpEL para hacerlo y tuve varios errores de parseo, que quedaron registrados en los logs del contenedor.

![Log del contenedor mostrando un primer error al intentar usar java.util.Scanner](imagenes/imagen%2050%20primer%20error%20probando%20lo%20del%20scanner.png)

*Figura 50. Primer intento de utilizar `java.util.Scanner`. SpEL muestra un error de sintaxis.*

![Log del contenedor mostrando un segundo error al intentar usar java.util.Scanner](imagenes/imagen%2051%20segundo%20error%20probando%20lo%20del%20scanner.png)

*Figura 51. Segundo intento con `java.util.Scanner`. Se obtiene un error diferente al intentar utilizar esa clase desde SpEL.*

No seguí profundizando en esta parte porque no era necesario para demostrar la vulnerabilidad. La prueba con `exec('ls')` ya mostró que se podía ejecutar un comando en el servidor, y `#system.getenv()` permitió obtener información del entorno del contenedor.

### Dónde está el problema en el código

La vulnerabilidad tiene dos partes.

La primera está en `SpelEvaluator.java`, que vimos en el Paso 2. El texto ingresado desde el buscador se evalúa directamente como una expresión de SpEL y además están disponibles las variables `system` y `runtime`.

La segunda parte está en `FuncionController.java`. Ahí confirmé que el parámetro `buscar`, que contiene lo escrito en el campo de búsqueda, se pasa directamente a `spelEval.evaluate()`:

![Codigo original de FuncionController.java, con la linea String spelResultado = spelEval.evaluate(buscar) visible](imagenes/imagen%2075%20codigo%20original%20del%20controlador%20sin%20arreglar.png)

*Figura 75. `FuncionController.java` original. La línea `String spelResultado = spelEval.evaluate(buscar);` pasa directamente el texto del formulario al evaluador de SpEL.*

No hay ningún chequeo entre el texto ingresado y la evaluación. Por eso, cualquier expresión válida que se escriba en el buscador puede ser evaluada antes de utilizar el resultado para buscar las funciones de cine.

### Impacto de la vulnerabilidad

Un atacante que tenga acceso al buscador puede ejecutar comandos del sistema operativo con los permisos del proceso de la aplicación. También puede acceder a información del entorno del servidor, como se comprobó con `#system.getenv()`.

En este caso, incluso se pudo obtener la URL de conexión a la base de datos. Por lo tanto, el problema no se limita a la información de la aplicación, sino que también puede afectar al servidor donde está funcionando.

De los ejercicios realizados hasta este punto, considero que este tiene uno de los impactos más altos porque permite ejecutar comandos directamente en el servidor.

### Mitigación implementada

Apliqué dos cambios diferentes para comprobar primero una solución que restringiera SpEL y después una solución que eliminara su uso.

#### Mitigación 1 — Restringir el contexto de evaluación

En `SpelEvaluator.java`, utilicé el `SimpleEvaluationContext` que ya estaba definido en el código pero no se estaba utilizando. También eliminé el contexto anterior y las variables `system` y `runtime`:

![Codigo de SpelEvaluator.java con la Mitigacion 1 aplicada, usando unicamente SimpleEvaluationContext](imagenes/imagen%2052%20codigo%20ya%20arreglado%20la%20primera%20vez.png)

*Figura 52. `SpelEvaluator.java` con la Mitigación 1 aplicada. Se utiliza únicamente `SimpleEvaluationContext` y ya no están disponibles las variables `system` y `runtime`.*

Este contexto tiene menos permisos que el anterior y no permite acceder de la misma forma a clases de Java como `Runtime`.

**Verificación de la Mitigación 1:**

Repetí el intento de ejecutar un comando:

```text
#runtime.getRuntime().exec(...)
```

![Error 500 al repetir el intento de ejecutar un comando despues de aplicar la Mitigacion 1](imagenes/imagen%2053%20el%20runtime%20ya%20no%20funciona%20despues%20del%20arreglo.png)

*Figura 53. Con la Mitigación 1 aplicada, el mismo intento de ejecutar un comando produce un error 500 y ya no permite acceder a `runtime`.*

El comando ya no funcionó porque `runtime` dejó de estar disponible.

Sin embargo, las expresiones matemáticas simples seguían funcionando:

```text
{7==9}
```

![Resultado de {7==9} mostrando Resultados buscando por: [false] despues de la Mitigacion 1](imagenes/imagen%2054%20la%20cuenta%20sigue%20funcionando%20despues%20del%20arreglo.png)

*Figura 54. `{7==9}` sigue siendo evaluado después de la Mitigación 1 y devuelve `[false]`. Esto muestra que las expresiones simples todavía se pueden evaluar, aunque ya no se puede acceder a `Runtime`.*

#### Mitigación 2 — Eliminar el uso de SpEL

Aunque la primera mitigación impedía ejecutar comandos, decidí eliminar directamente el uso de SpEL en esta parte de la aplicación.

Al revisar `FuncionController.java`, vi que la búsqueda de películas no necesitaba evaluar expresiones. Solamente necesitaba comparar el texto ingresado con el nombre de las funciones.

Por eso, eliminé el uso de `SpelEvaluator` del controller y reemplacé la lógica por una comparación directa de texto:

![Codigo de FuncionController.java sin ningun uso de SpelEvaluator, comparando buscar directamente contra el nombre de la funcion](imagenes/imagen%2055%20codigo%20ya%20arreglado%20del%20todo.png)

*Figura 55. `FuncionController.java` con la Mitigación 2 aplicada. Ya no se utiliza `SpelEvaluator` y la búsqueda se realiza directamente sobre el texto ingresado.*

### Verificación de la mitigación final

Con la Mitigación 2 aplicada, repetí la prueba de detección:

```text
{7*7}
```

![Resultado de {7*7} despues de la Mitigacion 2, mostrando No se encontraron coincidencias](imagenes/imagen%2056%20siete%20por%20siete%20ya%20no%20hace%20nada.png)

*Figura 56. `{7*7}` después de la Mitigación 2. La aplicación responde "No se encontraron coincidencias" y trata la entrada como texto.*

También repetí el intento de ejecutar un comando:

![Resultado del intento de ejecutar un comando despues de la Mitigacion 2, mostrando No se encontraron coincidencias](imagenes/imagen%2057%20intento%20de%20comando%20que%20ya%20no%20funciona.png)

*Figura 57. El intento de ejecutar un comando después de la Mitigación 2 responde "No se encontraron coincidencias". La entrada ya no se evalúa como una expresión.*

En ambos casos, la aplicación trata lo ingresado como texto normal. Si el texto coincide con una función, se muestran los resultados correspondientes; si no coincide, simplemente no se encuentran resultados.

### Aclaración

Antes de decidir cuál de las dos opciones utilizar, tuve una duda sobre cuál era la mejor solución como tal, si restringir el uso de SpEL para mantener la funcionalidad, como hice en la Mitigación 1, o eliminarlo directamente cuando no es necesario, como hice en la Mitigación 2.

Por eso documenté las dos opciones. Finalmente dejé aplicada la segunda, ya que la búsqueda no necesitaba utilizar SpEL y de esta forma se elimina el problema en lugar de mantener un evaluador que no era necesario para esta funcionalidad.

### Resumen de mitigaciones — Ejercicio 4

| Paso | Mitigación aplicada                                                                                   | Resultado                                                                                                        |
| ---- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 1    | Cambio de `StandardEvaluationContext` a `SimpleEvaluationContext` y eliminación de `system`/`runtime` | Se bloqueó el acceso a `Runtime` y la ejecución de comandos, aunque las expresiones simples seguían funcionando. |
| 2    | Eliminación completa del uso de SpEL en `FuncionController.java`                                      | Las expresiones dejaron de evaluarse y la búsqueda pasó a tratar la entrada solamente como texto.                |

### Referencias

[1] MITRE. *CWE-1336: Improper Neutralization of Special Elements Used in a Template Engine.*

https://cwe.mitre.org/data/definitions/1336.html

[2] PortSwigger. *Server-side template injection.*

https://portswigger.net/research/server-side-template-injection


<a id="ejercicio-5"></a>

## Ejercicio 5 — Almacenamiento inseguro

### Definición de la vulnerabilidad

Un almacenamiento inseguro ocurre cuando una aplicación guarda información
sensible (contraseñas, tokens, datos personales) de una forma que no la
protege adecuadamente si alguien logra acceder al lugar donde queda
guardada. El problema no aparece en el momento en que un usuario interactúa
con la aplicación, como sí pasa con una inyección SQL o un XSS, sino en cómo
esos datos quedan almacenados de fondo, en la base de datos o en el código.

**Fuentes:** MITRE relaciona este problema con dos CWE diferentes, que en conjunto permiten describir las dos fallas encontradas a lo largo de este ejercicio:

* **CWE-327: Use of a Broken or Risky Cryptographic Algorithm:** MITRE define esta categoría para casos en los que se utiliza un algoritmo o protocolo criptográfico roto o inseguro [1]. En este caso se relaciona con el uso de AES en modo ECB, que no es adecuado para proteger contraseñas porque genera el mismo resultado cuando se cifra la misma contraseña.

* **CWE-798: Use of Hard-coded Credentials:** esta categoría corresponde al uso de credenciales o claves criptográficas escritas directamente en el código [2]. Es lo que ocurre en este ejercicio, donde la clave utilizada para cifrar las contraseñas está definida directamente en la aplicación.


### Cómo levanté el ambiente

Levanté el contenedor con Docker Compose dentro de la carpeta del ejercicio:

```bash
cd ~/Consigna_Practica_2_DDSS/Ejercicio5
docker compose up -d --build
```

![Terminal con docker compose up -d --build construyendo y levantando el contenedor del Ejercicio 5](imagenes/imagen%2058%20arranque%20del%20contenedor%20del%20ejercicio%205.png)

*Figura 58. `docker compose up -d --build` construyendo la imagen del Ejercicio 5 y levantando el contenedor `ejercicio5-cinebuscador5-1`.*

Al navegar a la app encontré que tiene registro y login de usuarios.

![Pantalla inicial de CineBuscador con el formulario de registro](imagenes/imagen%2059%20pantalla%20inicial%20con%20el%20formulario%20de%20registro.png)

*Figura 59. Pantalla inicial de CineBuscador al entrar por primera vez, con la pestaña "Registrarse" activa.*

Posteriormente me registré y me logueé para empezar a probar la app, y vi el mensaje
"Password cifrada" del usuario logueado, en un bloque de "Datos de la
cuenta (ejercicio)". Esto en sí mismo es un dato importante, ya que la aplicación
expone la contraseña cifrada directamente en la interfaz del usuario, sin que haga
falta ningún acceso especial para verla.

![Pantalla de login mostrando la password cifrada del usuario logueado](imagenes/imagen%2060%20login%20mostrando%20la%20password%20cifrada.png)

*Figura 60. Login exitoso como "Manuel": la pantalla muestra directamente "Password cifrada: `PGG6RWjAIU1vvozOcfCepg==`" en el bloque "Datos de la cuenta (ejercicio)".*

### Análisis del código

Revisando `EncryptionService.java`, encontré tres problemas.

**1. La clave de cifrado está hardcodeada en el código**

![Comentario de la clase y declaración de SECRET_KEY resaltada en EncryptionService.java](imagenes/imagen%2061%20la%20clave%20secreta%20en%20el%20codigo%20fuente.png)

*Figura 61. Comentario de la clase ("VULNERABILIDAD CRÍTICA") y declaración de `SECRET_KEY` en `EncryptionService.java`, con la clave embebida directamente como string literal.*

Es la misma clave siempre, para todos los usuarios, embebida
directamente en el código. Cualquiera con acceso al repositorio o al codigo en ejecución tiene la clave completa. 
Básicamente si el código llega a
filtrarse alguna vez, todas las contraseñas cifradas de todos los usuarios
quedan comprometidas.

**2. Se usa el modo de cifrado ECB, que es determinístico**

![Comentario VULNERABILIDAD 2 ECB mode determinístico y declaración de CIPHER_ALGO](imagenes/imagen%2062%20comentario%20del%20modo%20ecb%20en%20el%20codigo.png)

*Figura 62. Comentario "VULNERABILIDAD #2: ECB mode (determinístico)" y declaración de `CIPHER_ALGO = "AES/ECB/PKCS5Padding"`.*

AES como algoritmo está bien, pero el problema está en que se está usando ECB. Con este modo, si se cifra exactamente el mismo texto, se obtiene siempre el mismo resultado.

Por eso, si dos usuarios tienen la misma contraseña, la aplicación va a guardar exactamente el mismo valor para los dos. Entonces, aunque un atacante solamente consiga acceder a la base de datos y no tenga la clave, puede darse cuenta de qué usuarios tienen la misma contraseña sin necesidad de descifrarla.


**3. Funciones que exponen la clave directamente**

![Las tres funciones getStaticKey, getKeyBytes y getKeyHex, con el comentario del comando de OpenSSL dentro de getKeyHex](imagenes/imagen%2063%20funciones%20que%20exponen%20la%20clave.png)

*Figura 63. Las tres funciones que exponen la clave (`getStaticKey`, `getKeyBytes`, `getKeyHex`), marcadas como "VULNERABILIDAD" en sus propios comentarios Javadoc. El comentario de `getKeyHex()` incluye el comando de OpenSSL de ejemplo para descifrar con la clave.*

Al revisar el resto del código, no encontré ningún controller que utilice estas funciones, por lo que desde la aplicación web no se pueden llamar directamente en este momento.

De todas formas, siguen siendo un problema porque permiten obtener la clave de cifrado. Si en algún momento se agregara una funcionalidad que utilizara estas funciones y permitiera acceder a ellas desde la aplicación, un atacante podría obtener la clave sin necesidad de tener acceso al código fuente.

Además, dentro de `getKeyHex()` hay un comentario que muestra directamente el comando de OpenSSL necesario para descifrar una contraseña usando la clave en formato hexadecimal. Esto también ayuda a entender que el ejercicio está pensado para demostrar el problema utilizando esa clave.


### Prueba con el modo ECB

Para comprobar el problema con ECB, registré dos usuarios distintos usando la misma contraseña. El primero, "Manuel", ya había quedado registrado y logueado en la Figura 60, con la contraseña almacenada como `PGG6RWjAIU1vvozOcfCepg==`. Después registré un segundo usuario, "Juan", usando la misma contraseña:

![Formulario de registro completando el usuario Juan con la misma contraseña que Manuel](imagenes/imagen%2064%20registro%20de%20juan%20con%20la%20misma%20clave%20que%20manuel.png)

*Figura 64. Registrando un segundo usuario, "Juan", con la misma contraseña que "Manuel".*

![Login de Juan mostrando exactamente el mismo valor cifrado que Manuel](imagenes/imagen%2065%20login%20de%20juan%20con%20el%20mismo%20valor%20cifrado%20que%20manuel.png)

*Figura 65. Login de "Juan": la contraseña almacenada es exactamente `PGG6RWjAIU1vvozOcfCepg==`, el mismo valor que obtuvo "Manuel" con la misma contraseña.*

Los dos usuarios obtuvieron exactamente el mismo resultado al cifrar la contraseña. Esto confirma el problema de ECB, alguien que consiga acceder a la base de datos podría darse cuenta de qué usuarios tienen la misma contraseña, incluso sin conocer la clave de cifrado.

### Prueba con la clave hardcodeada y OpenSSL

A diferencia de las otras vulnerabilidades, esta prueba no necesita hacerse desde la aplicación web. Al tener acceso al código fuente, se puede ver directamente la clave dentro de `EncryptionService.java`. Además, como la aplicación permite obtener una contraseña cifrada, puedo usar esa clave junto con una herramienta externa como OpenSSL para intentar descifrarla.

Para hacer la prueba, seguí el mismo procedimiento que aparece en el comentario del código y utilicé el comando de OpenSSL que se indica ahí.

**Paso 1 — Calcular la clave en hexadecimal**

Primero necesitaba saber cuánto medía la clave definida en `EncryptionService.java`, así que lo comprobé desde la terminal:

```bash
$ echo -n 'MySup3rS3cr3tK3y!2024CineBuscadorAES' | wc -c

36
```

![Terminal mostrando el error de zsh con las comillas dobles, el conteo intermedio equivocado en 30 y el conteo correcto en 36](imagenes/imagen%2066%20error%20de%20la%20terminal%20con%20las%20comillas.png)

*Figura 66. Pruebas realizadas en la terminal para contar los caracteres de la clave. Al principio tuve un error de zsh por usar comillas dobles con el `!` y también un conteo incorrecto porque había escrito mal la clave. Finalmente, con la clave completa entre comillas simples, el resultado fue `36`.*

La clave tiene 36 caracteres, pero AES-256 utiliza una clave de 32 bytes. Al revisar el código, encontré que si la clave es más larga, la aplicación utiliza solamente los primeros 32 bytes:

```java
} else {
    secretKey = new SecretKeySpec(Arrays.copyOf(keyBytes, 32), "AES");
}
```

Por eso, primero necesitaba obtener la clave en formato hexadecimal y después tomar solamente los primeros 32 bytes, que son los que realmente utiliza la aplicación para AES-256.

Para obtener el valor hexadecimal completo ejecuté:

```bash
$ echo -n 'MySup3rS3cr3tK3y!2024CineBuscadorAES' | xxd -p | tr -d '\n'

4d7953757033725333637233744b3379213230323443696e654275736361646f...
```

![Terminal mostrando el comando xxd -p calculando el hexadecimal completo de la clave](imagenes/imagen%2067%20calculando%20el%20hexadecimal%20de%20la%20clave.png)

*Figura 67. Comando utilizado para obtener la clave completa en formato hexadecimal.*

**Paso 2 — Quedarme con los 32 bytes que usa AES**

Guardé el hexadecimal completo en un archivo y usé `cut -c1-64` para quedarme con los primeros 64 caracteres. Como cada byte se representa con dos caracteres hexadecimales, esos 64 caracteres corresponden a los primeros 32 bytes que utiliza AES-256:

```bash
$ cut -c1-64 clave_completa.txt > clave_final.txt

$ cat clave_final.txt

4d7953757033725333637233744b3379213230323443696e654275736361646f
```

Así obtuve la clave en hexadecimal que voy a utilizar después con OpenSSL para intentar descifrar la contraseña.

**Paso 3 — Descifrar la contraseña**

Con la clave en hexadecimal y el valor que aparecía en la aplicación (`PGG6RWjAIU1vvozOcfCepg==`), utilicé OpenSSL para intentar recuperar la contraseña.

Primero comprobé que OpenSSL estuviera instalado:

```bash
$ which openssl

/usr/bin/openssl
```

Después ejecuté:

```bash
$ echo "PGG6RWjAIU1vvozOcfCepg==" | base64 -d | openssl enc -aes-256-ecb -d -nosalt -K 4d7953757033725333637233744b3379213230323443696e654275736361646f

12345678
```

![Terminal con todo el proceso completo: recorte de la clave a 64 caracteres, confirmación de openssl, y el descifrado final devolviendo 12345678](imagenes/imagen%2068%20terminal%20con%20el%20descifrado%20final%20dando%2012345678.png)

*Figura 68. Proceso completo para obtener los 32 bytes de la clave, comprobar que OpenSSL estaba instalado y descifrar el valor almacenado en la aplicacion*

### Impacto

Con acceso al código fuente, donde la clave está escrita directamente, y a una contraseña cifrada obtenida de la aplicación, es posible recuperar la contraseña original sin tener que romper AES. El problema es que la clave utilizada para cifrar está expuesta en el propio código, por lo que cualquiera que tenga acceso a ella puede utilizarla para descifrar las contraseñas almacenadas.

Además, en este caso la contraseña recuperada (`12345678`) es muy débil. Esto muestra que la aplicación tampoco exige una contraseña segura al usuario. Es un problema distinto al de la clave hardcodeada, pero aumenta aún más el riesgo.

### Mitigación implementada

Descarté la opción de simplemente modificar el cifrado existente, por ejemplo, moviendo la clave a una variable de entorno o cambiando ECB por un modo más seguro como GCM. Aunque esos cambios mejorarían la implementación actual, la aplicación seguiría usando cifrado reversible para almacenar contraseñas.

Para las contraseñas, la opción correcta es utilizar un algoritmo de hash diseñado específicamente para este propósito, como bcrypt. A diferencia del cifrado, un hash no está pensado para poder recuperar la contraseña original. Para verificar un login, se compara la contraseña ingresada con el hash almacenado, sin necesidad de descifrar nada.

Agregué la dependencia necesaria al `pom.xml`:

![pom.xml con la dependencia spring-security-crypto agregada, resaltada](imagenes/imagen%2069%20dependencias%20agregadas%20al%20pom.xml.png)

*Figura 69. `pom.xml` con la dependencia `spring-security-crypto` agregada al final del bloque `<dependencies>`.*

Elegí utilizar `spring-security-crypto` en lugar del starter completo de Spring Security, ya que para este ejercicio solamente necesitaba la funcionalidad de bcrypt y no toda la configuración de autenticación de Spring Security.

**Nuevo `EncryptionService.java`:**

![Nuevo EncryptionService.java usando BCryptPasswordEncoder en vez del cifrado AES](imagenes/imagen%2070%20nuevo%20servicio%20de%20encriptacion.png)

*Figura 70. `EncryptionService.java` reescrito para utilizar `BCryptPasswordEncoder`. Ya no existe una clave AES y los métodos `encrypt()` y `matches()` se encargan de generar y verificar los hashes.*

Con este cambio desaparece la lógica de cifrado AES que tenía la aplicación. Ya no existe la `SECRET_KEY`, tampoco se utiliza ECB y se eliminaron los métodos que permitían obtener la clave (`getStaticKey`, `getKeyBytes` y `getKeyHex`).

**Cambio en `AuthController.java`:**

Dentro del método `login`, reemplacé `EncryptionService.decrypt(user.getPassword())` y la posterior comparación de texto plano por `EncryptionService.matches(password, user.getPassword())`.

![Método login de AuthController.java actualizado para usar EncryptionService.matches en vez de descifrar](imagenes/imagen%2071%20codigo%20del%20nuevo%20login.png)

*Figura 71. Método `login()` de `AuthController.java` actualizado: ahora utiliza `EncryptionService.matches()` para verificar la contraseña sin descifrarla.*

El método `register` no necesitó cambios, ya que sigue llamando a `EncryptionService.encrypt(password)`. La diferencia es que ahora este método genera un hash bcrypt en lugar de cifrar la contraseña.

### Verificación de la mitigación

**Registré dos usuarios nuevos con la misma contraseña.** A diferencia de lo que ocurría anteriormente con ECB, los hashes bcrypt obtenidos fueron distintos entre sí. Esto confirma que ya no se genera siempre el mismo resultado para una misma contraseña.

![Login de Manuel tras la mitigación, mostrando un hash bcrypt](imagenes/imagen%2072%20login%20de%20manuel%20ya%20arreglado.png)

*Figura 72. Login de "Manuel" con el nuevo esquema. La contraseña ahora aparece almacenada como un hash bcrypt.*

![Login de Juan tras la mitigación, mostrando un hash bcrypt distinto al de Manuel pese a tener la misma contraseña](imagenes/imagen%2073%20login%20de%20juan%20ya%20arreglado.png)

*Figura 73. Login de "Juan", utilizando la misma contraseña que "Manuel". El hash obtenido es diferente al de la Figura 72 debido al salt aleatorio que utiliza bcrypt.*

**También confirmé que el login sigue funcionando.** Inicié sesión con las credenciales de un usuario registrado y el sistema lo autenticó correctamente utilizando `EncryptionService.matches()`.

**Repetí la prueba con OpenSSL**, utilizando uno de los nuevos hashes bcrypt:

```bash
$ docker compose up -d --build

...

$ echo '$2a$10$kKb/w4jLA5aIBwFK1jQ.SeARaLwbS9LVa7FQd6M3NP1tO6Zs7AtHS' | base64 -d | openssl enc -aes-256-ecb -d -nosalt -K 4d7953757033725333637233744b3379213230323443696e654275736361646f

base64: entrada inválida

bad decrypt

803769DD4870000:error:1C80006B:Provider routines::ossl_cipher_generic_block_final:wrong final block length:providers/implementations/ciphers/ciphercommon_block.c:968:
```

![Terminal mostrando la reconstrucción del contenedor y el error final de OpenSSL al intentar descifrar un hash bcrypt](imagenes/imagen%2074%20intento%20de%20descifrado%20que%20ya%20no%20funciona.png)

*Figura 74. Tras reconstruir el contenedor con la mitigación aplicada, el mismo comando de OpenSSL falla al intentar descifrar un hash bcrypt.*

La prueba ya no funciona porque la aplicación dejó de utilizar AES para las contraseñas. El valor almacenado ahora es un hash bcrypt, por lo que no puede ser descifrado utilizando la clave y el algoritmo AES que se utilizaban antes.

### Resumen de mitigaciones — Ejercicio 5

| Vulnerabilidad                                                               | Mitigación aplicada                                                                   |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Clave AES hardcodeada en el código (CWE-798)                                 | Eliminada junto con toda la lógica de cifrado AES.                                    |
| Modo ECB determinístico (CWE-327)                                            | Eliminado al reemplazar AES por bcrypt, que utiliza un salt diferente para cada hash. |
| Funciones que exponían la clave (`getStaticKey`, `getKeyBytes`, `getKeyHex`) | Eliminadas porque ya no existe una clave de cifrado que gestionar.                    |

Las tres vulnerabilidades se resolvieron reemplazando el cifrado reversible por un hash diseñado específicamente para almacenar contraseñas.

La aplicación originalmente utilizaba AES-256, que es un algoritmo de cifrado estándar, pero el problema estaba en cómo se estaba utilizando: la clave estaba incluida directamente en el código, se utilizaba ECB y además existían métodos que permitían obtener la clave. Por eso, aunque el algoritmo utilizado era seguro en sí mismo, la implementación no protegía correctamente las contraseñas.

### Referencias

[1] MITRE. *CWE-327: Use of a Broken or Risky Cryptographic Algorithm.*

https://cwe.mitre.org/data/definitions/327.html

[2] MITRE. *CWE-798: Use of Hard-coded Credentials.*

https://cwe.mitre.org/data/definitions/798.html

<a id="conclusión-general"></a>

## Conclusión general
Después de hacer los cinco ejercicios, me quedó como principal conclusión que muchas de las vulnerabilidades aparecen cuando la aplicación no diferencia correctamente entre un dato ingresado por el usuario y algo que el sistema va a interpretar o ejecutar. En el Ejercicio 1 esto pasaba con la consulta SQL, en el Ejercicio 2 con el HTML, en el Ejercicio 3 con los archivos que se podían subir y en el Ejercicio 4 con las expresiones de SpEL. El Ejercicio 5 es un poco diferente, porque el problema estaba en cómo se almacenaban las contraseñas, pero también había una mala elección de cómo proteger la información: se estaba usando cifrado reversible cuando para las contraseñas correspondía utilizar un hash.

También pude ver que no siempre la mejor solución es agregar un filtro para impedir exactamente la prueba que hice. En varios ejercicios primero probé una solución que bloqueaba el caso que había demostrado, pero después busqué una forma de cambiar la parte del código que estaba causando el problema. Por ejemplo, parametrizar la consulta SQL, evitar que la entrada se interpretara como HTML, controlar los archivos que se podían subir, eliminar el uso de SpEL donde no era necesario y reemplazar el cifrado de contraseñas por bcrypt.

Lo que más me llevo de este práctico es que las vulnerabilidades no fueron difíciles de detectar una vez que entendí cómo estaba funcionando cada aplicación. En varios casos alcanzó con probar entradas simples y observar qué hacía el sistema. Lo que me resultó más importante fue revisar después el código para entender por qué esas entradas funcionaban y qué cambio había que hacer para solucionarlo, en vez de simplemente bloquear la prueba que había utilizado.