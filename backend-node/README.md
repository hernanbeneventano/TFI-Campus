# Catálogos externos — el servicio de Node

Busca libros en **Google Books** y **Open Library**, los unifica y los devuelve
en una sola forma. Es el segundo backend del campus.

> Este servicio sigue separado del backend principal Django: la frontera está
> en `backend/app/servicios/libros_externos.py`, que expone las funciones
> `buscar_libros_externos` y `obtener_libro_externo`. Las vistas de Django las
> llaman sin trasladar a este proceso las rutas ni los permisos del campus.
> Ver «La frontera», más abajo.

## Por qué esta parte está en Node y el resto no

El campus trabaja sobre una copia en memoria de sí mismo (`backend/app/datos.py`):
las rutas la leen y la escriben directamente, y `servicios/persistencia.py` manda
a Firestore lo que cambió después de cada petición. Eso obliga a **un solo
proceso**: con dos, cada uno tendría su propio campus y el último en guardar
pisaría al otro sin que nada fallara.

Node no puede compartir la memoria de Python. Por eso no se parte el campus por
apartados: Mensajes, Foro o Biblioteca escriben en esa memoria, emiten eventos de
auditoría y mandan avisos, y llevarlos a otro proceso significaría dos dueños
para las mismas colecciones.

Los catálogos externos son la excepción, y por eso son lo que se movió:

| | |
|---|---|
| Estado propio | ninguno |
| Colecciones de Firestore que escribe | ninguna |
| Permisos que decide | ninguno |
| Lo que hace | esperar a dos servidores ajenos a la vez y unir lo que contestan |

Es I/O concurrente contra servicios de terceros, sin estado compartido: la forma
de trabajo en la que Node es la mejor herramienta y no un agregado. Una fuente
que tarda 9 segundos no puede arrastrar a la otra, y ninguna de las dos puede
arrastrar al campus.

## Levantarlo

```bash
cd backend-node
npm install
cp .env.example .env     # opcional: todo tiene un valor por defecto
npm start                # http://127.0.0.1:4000
npm run dev              # igual, pero se reinicia al guardar
npm test                 # 42 comprobaciones, sin salir a internet
```

Necesita **Node 22.15 o más nuevo**: usa `fetch`, el corredor de pruebas y
`--env-file-if-exists`, todo nativo. La única dependencia es Express.

El campus y este servicio se levantan por separado, en cualquier orden.

## Si no está levantado

El campus **sigue funcionando entero**. Lo único que no se puede es buscar en
catálogos externos, y falla avisando: el error viaja en `fuentes`, con la misma
forma que cuando se cae Google, y la pantalla ya sabe mostrarlo. Es la regla de
siempre: que una fuente ajena no deje sin biblioteca al campus.

## La frontera

```
navegador  ──►  campus (Django)  ──►  este servicio  ──►  Google Books
                 │                                                   Open Library
                 │  quién pregunta, su freno por persona,
                 └─ sus favoritos, la biblioteca de la materia
```

El navegador **nunca** le habla a este servicio. Le habla al campus, que ya
comprobó quién es y si tiene permiso, y el campus le habla a este servicio por
dentro de la máquina. De ahí sale todo lo demás:

- No hay tokens de Firebase acá, ni roles, ni CORS. **Duplicar la capa de
  permisos en otro lenguaje es la forma más segura de que las dos digan cosas
  distintas.**
- El freno por persona (30 búsquedas por minuto) se queda en el campus, que es
  el único que sabe quién pregunta. El de acá es por minuto y para todos: lo que
  protege no es el servicio sino **el cupo de Google**, que es compartido.
- Los favoritos son un dato del campus y viven en Firestore, aunque el libro sea
  externo.

### Lo que el campus llama

Ninguna de las dos funciones de `libros_externos.py` levanta excepción: si el
servicio no está, el error llega como una fuente caída.

```python
from ..servicios.libros_externos import buscar_libros_externos, obtener_libro_externo

resultado = await buscar_libros_externos(texto, campo, idioma)
# {"libros": [...], "fuentes": [...], "desdeCache": False}

libro = await obtener_libro_externo("google:ABC123")   # el libro, o None
```

### Las rutas

```
GET /salud                    estado, si hay clave de Google, cómo viene la caché
GET /catalogos/buscar         ?texto (2 letras o más) &campo &idioma
                              → { libros, fuentes, desdeCache }
GET /catalogos/libro          ?id=google:xxx | openlibrary:/works/OL1W
                              → { libro }  ·  404 si no está
```

`campo` vale `todo` (el valor por defecto), `titulo`, `autor`, `isbn` o `tema`.
Un campo desconocido busca en todo, igual que antes. Los errores salen como
`{"detail": "..."}`, el formato del campus.

## Las reglas que hay adentro

**Solo se ofrece lo que la fuente ofrece de verdad.** El enlace de descarga
aparece únicamente si Google dice que el libro es de dominio público; el de
préstamo, solo si Open Library lo marca `borrowable`. Nada de armar enlaces
porque el libro «parece» libre: un botón que lleva a un 404 —o peor, a repartir
algo que no tenemos derecho a repartir— es mucho peor que no tener botón. Cinco
de las pruebas existen solo para esto.

**Un libro que está en las dos fuentes se muestra una vez.** Se compara por ISBN
cuando lo hay y, si no, por título y autor sin tildes ni mayúsculas. Gana el de
Google —trae descripción y portada más seguido—, se le tapan los huecos con el de
Open Library y queda anotado el «También en». Es la misma regla con la que la
Biblioteca detecta duplicados dentro de una materia, a propósito: dos criterios
distintos para «el mismo libro» en la misma pantalla sería inexplicable.

**Que una fuente falle es lo normal.** Sin `GOOGLE_BOOKS_API_KEY` Google devuelve
429 casi siempre, porque el cupo por IP es bajo. Por eso el estado de cada fuente
viaja en la respuesta en vez de tragarse el error, y por eso un resultado vacío
porque las dos fallaron **no se cachea**: conviene reintentar.

**La caché es solo velocidad.** Vive en memoria, 10 minutos, 200 búsquedas. Si se
pierde al reiniciar, la próxima búsqueda sale a la red y nada más. No es un dato
del campus, y guardarla en Firestore sería darle a este servicio un dueño de
datos, que es justamente lo que no tiene que tener.

## Seguridad

- **Escucha en 127.0.0.1.** No se publica: el navegador no lo llama.
- **Secreto compartido opcional** (`CLAVE_INTERNA` acá, `CATALOGOS_CLAVE` en
  `backend/.env`). Con `HOST` en 127.0.0.1 no llega nadie de afuera, así que en
  desarrollo no hace falta; al publicarlo detrás de un proxy, sí.
- **No recibe cuerpos.** Solo GET, y sin `express.json()`: no hay forma de
  mandarle 20 MB para que los intente parsear.
- **No tiene las claves del campus.** Ni Firebase ni R2: no las necesita y no hay
  que dárselas. Lo único sensible que puede tener es la clave de Google Books.
- **Los errores no cuentan nada.** El 500 responde un mensaje fijo y el detalle
  va al registro del servidor.

## Las pruebas

```bash
npm test
```

42 comprobaciones, y **ninguna sale a internet**: el `fetch` global se reemplaza.
Una prueba que le pega a Google de verdad falla cuando no hay red, cuando Google
devuelve 429 y cuando alguien cambia su catálogo, y ninguna de las tres es un
error nuestro.

Lo que se cubre: la unificación y el orden de los resultados, que no se ofrezcan
enlaces inventados, la caché y su vencimiento, el freno, el secreto compartido y
—lo que más importa— **que una fuente caída no deje la pantalla vacía**.

## Mapa de los archivos

```
src/
  servidor.js      el arranque y el apagado ordenado
  aplicacion.js    la aplicación armada, sin escuchar (para las pruebas)
  rutas.js         las rutas, el secreto compartido y el freno
  catalogos.js     la búsqueda: las dos fuentes en paralelo y la caché
  google.js        Google Books: cómo se le pregunta y cómo se lee
  openlibrary.js   Open Library: lo mismo
  unificar.js      la huella de un libro y cómo se unen dos fichas
  cache.js         caché con vencimiento y tope
  freno.js         el límite por minuto
  config.js        las variables de entorno, en un solo lugar
```
