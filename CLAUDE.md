# CampusTFI: contexto del proyecto

Campus virtual web (LMS) para el Trabajo Final Integrador de FaCENA – UNNE.
Integrantes: **Sosa Santiago Rafael** (frontend, diseño) y **Beneventano Hernán** (backend, base de datos).
Nombre provisorio: CampusTFI.

## Idea
Muchos campus universitarios son poco estéticos y difíciles de entender: cuesta ver dónde está cada cosa
y cómo hacer cada tarea. CampusTFI busca una experiencia más intuitiva y un diseño visual cuidado,
para estudiantes y docentes. Inspiración propia; Blackboard es solo una referencia más.

## Stack
- Frontend: React 18 + Vite + React Router (`frontend/`)
- Backend: Python + FastAPI (`backend/`)
- Base de datos: **Firebase** (decidido). Queda descartado PostgreSQL + Prisma, que era la
  propuesta original. Ya está inicializado en `frontend/src/services/firebase.js`, con las claves
  en `frontend/.env.local` (ignorado: pedírselo a Hernán, no viaja por el repo).
- Login y archivos: **Firebase Authentication** y **Firebase Storage**. Eso reemplaza lo que
  figuraba antes como futuro (bcrypt, jsonwebtoken y multer): ya no hacen falta.
- Los datos todavía viven en memoria en el backend Python; Firebase aún no está integrado.
- Frontend en JavaScript y backend en Python. Nombres y textos de la interfaz en **español**.

## Estructura
```
frontend/src/
  components/  MenuLateral, Encabezado, BarraHerramientas, TarjetaModulo, PanelTareas,
               CarpetaModulo, VisorItem, PestanasModulo, PanelModulo, BarraProgreso,
               Iconos (SVG propios)
  pages/       Novedades (inicio), Modulos, Modulo (interior), Calendario, Foro, Mensajes,
               Biblioteca, Ajustes, EnConstruccion (página no encontrada)
  services/    api.js: todas las llamadas al backend (Vite redirige /api a localhost:3000)
               progreso.js: recursos completados y cuentas de avance (hoy en localStorage)
               preferencias.js: ajustes de la interfaz, como el menú plegado
               fechas.js: hace() → "hace 12 min", "hace 2 horas", "hace 2 meses"
  hooks/       usePresencia.js: si el usuario está conectado, ausente o desconectado
  styles/      global.css: paleta en variables CSS en :root
backend/app/
  main.py → rutas/ → datos.py
  datos_iniciales.json
  Rutas: GET /api/salud, /api/me, /api/cursos, /api/cursos/:id, /api/actividad,
         /api/tareas/pendientes
         /api/cursos/:id/modulo → todo lo de la pantalla del módulo en una sola llamada:
         { curso, carpetas, anuncios, participantes }
         POST /api/cursos/:id/favorito → marca o desmarca el módulo y devuelve el curso
         GET /api/mensajes (lista + total sin leer), GET /api/mensajes/:id (y la da por leída),
         POST /api/mensajes/:id (enviar), POST /api/mensajes { paraId } (abrir o crear la charla),
         GET /api/mensajes/contactos (gente de tus módulos)
         GET /api/novedades (muro), POST /api/novedades, PUT /api/novedades/:id,
         POST /api/novedades/:id/reaccion
         GET /api/calendario?desde&hasta → entregas, exámenes, clases y eventos del rango
         GET /api/foro, POST /api/foro, GET /api/foro/:id, POST /api/foro/:id (responder)
         GET /api/contadores → { novedades, informacion, modulos, mensajes }: las campanitas del menú
         /api/biblioteca/... → catálogo, aportes, moderación y archivos (ver Biblioteca)
equipo/        información del equipo y planificación de hitos
```

## Diseño
Paleta (usar siempre las variables de `global.css`, nunca el color escrito a mano).
Las variables se llaman por su rol, no por el color, así probar otra paleta es cambiar
solo el bloque `:root`.
- `--oscuro` `#2B2D42`: menú lateral y títulos
- `--gris` `#8D99AE`: bordes y detalles; el texto secundario usa `--texto-suave` `#5F6B7E`,
  una versión oscurecida, porque el gris puro no llega al contraste mínimo sobre los paneles
- `--panel` `#EDF2F4`: recuadros y paneles
- `--principal` `#D80032`: color principal y acentos
- Derivados: `--tinta` `#3A3D57` (pestañas del menú), `--fondo` `#F8FAFB` (fondo de la
  página, más claro que los paneles), `--borde` `#CCD4DE`

La paleta tiene un solo rojo, así que `--alerta` es el mismo `--principal`: el rojo quiere decir
"prestá atención". Lo urgente se distingue por la negrita y por el ícono (reloj en lo atrasado,
triángulo en lo que falta empezar), no por el tono. Lo que está en fecha va en `--oscuro` y lo
entregado en verde, para no confundirlos con lo atrasado.

Avance de una carpeta: `--progreso-bajo` (el rojo) hasta 39%, `--progreso-medio` `#D9A21B`
hasta 79%, `--progreso-alto` `#2F8F5B` desde 80%. El verde se reserva para cuando falta poco.
Es el único lugar con amarillo y verde: son semáforo, no marca.

Cada materia tiene su color en los datos de `backend/app/datos_iniciales.json` para la banda de su tarjeta en Módulos y para los íconos
de sus carpetas. Son tonos de la misma familia y todos tienen contraste suficiente con el texto
blanco encima. El encabezado de la pantalla del módulo **no** usa ese color: va en `--oscuro`,
el mismo del menú lateral.

El avatar del alumno es `IconoEstudiante`, una silueta rellena con birrete; los docentes usan
`IconoUsuario`, de línea como el resto de los íconos.

Layout de la pantalla Módulos (según boceto): menú lateral a la izquierda (logo, Novedades,
Módulos, Calendario, Foro, Mensajes, usuario abajo) · encabezado con el nombre del apartado · barra
(vista tarjetas/lista, búsqueda, filtro Fechas, filtro Apartados especiales = favoritos) · grilla de
módulos · panel derecho con tareas pendientes recientes y atrasadas. Responsive: en celular el menú
pasa arriba con 4 botones.

El menú va pegado al borde izquierdo y ocupa todo el alto, redondeado del lado que da al
contenido. Lleva un contorno degradado, hecho con un borde de 1px relleno con un degradado y
recortado con `mask-composite: exclude`, así sigue la curva de las esquinas. Lleva `z-index: 10`:
`position: sticky` arma su propio contexto de apilamiento y sin eso lo que salga del menú queda
por debajo de las tarjetas del contenido.

Adentro: logo, línea divisoria, las opciones como recuadros redondeados (la activa llena en
`--gris`, con texto `#1B1D2B` porque sobre ese gris `--oscuro` no llega al contraste mínimo, y una
barrita del mismo gris pegada al borde izquierdo del menú), otra línea divisoria abajo y el
usuario con su avatar redondo y su puntito de presencia.

Al pasar el mouse por el usuario (o llegar con el teclado, vía `:focus-within`) el nombre y el rol
se desvanecen y en su lugar, al lado del avatar, aparecen los botones de Ajustes y Cerrar sesión.
**Todavía no hacen nada**: faltan esas pantallas y el login. Con el menú plegado no hay lugar al
lado del avatar, así que salen a la derecha, fuera de la barra; ahí un `::before` invisible hace
de puente sobre la separación, para que el mouse pueda cruzar sin que se cierren.

Presencia (`.avatar-estado` + `conectado` / `ausente` / `desconectado`): verde, amarillo y gris.
El del usuario que está navegando es real y sale de `usePresencia`, que mira la actividad en la
página: ausente tras 5 minutos sin tocar nada, desconectado si se va a otra pestaña. El de los
demás lo calcula el backend con los mismos cortes a partir del último acceso. Cuando haya sesiones
de verdad, `usePresencia` debería avisarle al servidor en vez de quedarse solo en la pantalla.

En `backend/app/datos_iniciales.json` las personas guardan `accesoHaceMin` (hace cuántos minutos entraron), no una fecha
fija: `conPresencia()` calcula la fecha y el estado en cada pedido, así los estados siguen
teniendo sentido por más que el servidor lleve horas levantado.
Se pliega con el botón de arriba: pasa de `--ancho-menu` a `--ancho-menu-cerrado` y quedan solo los
íconos, que llevan `title` como ayuda. La preferencia se recuerda en `services/preferencias.js`.
Al entrar a un módulo (`/modulos/:id`) se pliega solo, para dejarle lugar al contenido; al salir
vuelve a lo que haya elegido el usuario. Adentro se puede desplegar a mano, y eso sí se guarda:
el único plegado que no pisa la preferencia es el automático.
Las reglas del plegado están dentro de `@media (min-width: 761px)`, porque en celular el menú ya es
la barra de arriba y plegarlo no tendría sentido.

Pantalla interior de un módulo (`/modulos/:id`), en este orden: enlace "Módulos" para volver ·
encabezado en `--oscuro` (código, nombre, docente, período) · pestañas (Contenido,
Anuncios con su contador, Participantes, Notas) · cuerpo en dos columnas.

A la izquierda, según la pestaña: en Contenido va el título y el buscador del módulo y abajo las
carpetas, que se abren y se cierran con los elementos adentro (página, archivo, tarea, tablero);
al buscar quedan solo las carpetas con coincidencias y se abren solas. Cada recurso tiene un check
para marcarlo como completado — las tareas no, porque se completan al entregarlas — y la cabecera
de la carpeta muestra cuántos van y una barra de avance. El texto del avance toma el color de la
barra y lleva un triángulo de advertencia mientras falte material; al llegar al verde pasa a un
check. Los checks de los recursos son redondos (dibujados a mano con `appearance: none`, porque
el del navegador no se puede redondear).

A la derecha, el panel del módulo: equipo del módulo (docente y cuántos estudiantes), detalles y
acciones (atajos a las otras pestañas) y el avance de todo el módulo.

Al abrir un elemento se muestra a pantalla completa, con una barra oscura arriba con la ruta
"módulo › carpeta › elemento" y una X para cerrar (también cierra con Escape).

Las pestañas son estado de la pantalla, no rutas. Si más adelante conviene poder compartir el
enlace a una pestaña, pasarlas a rutas hijas de `/modulos/:id`.

Transiciones: todo lo que aparece entra con un fundido (`@keyframes aparecer` / `aparecer-subiendo`
en `global.css`) — al cambiar de apartado, al entrar a un módulo y al abrir o cerrar un elemento.
Las carpetas se abren y se cierran animando la altura con `grid-template-rows: 0fr → 1fr`, así no
hay que medirla: los elementos quedan siempre montados y `visibility` los saca del tabulador
mientras está cerrada. Con `prefers-reduced-motion` las duraciones se achican casi a cero, pero no a
cero del todo: el visor espera el fin de la animación para cerrarse.

Cada tarea del panel derecho de Módulos se muestra así: campanita con el color del módulo
(reloj rojo si está atrasada: ya se pasó el tiempo) ·
la materia arriba · el título · el vencimiento abajo · y a la derecha un contador "X/Y" con
cuánto lleva hecho el alumno **en la carpeta donde vive esa tarea**. Ahí las tareas también
cuentan (`avanceDeApartado`, no `calcularAvance`): si leyó el PDF pero no entregó, va 1/2. El
color del contador sale de la misma escala que las barras de avance.

Para eso `GET /api/tareas/pendientes` devuelve, en cada tarea, un `apartado` con el título de la
carpeta y sus items (`id`, `tipo` y, en las tareas, `entregada`).

Cada tarea pendiente abre la entrega: va a
`/modulos/:cursoId?tarea=:tareaId`, y la pantalla del módulo busca esa tarea entre sus carpetas,
despliega la que la contiene y abre el visor. El parámetro queda en la URL, así el enlace sirve
para compartir o recargar. Si la tarea no aparece en ninguna carpeta, se abre el módulo sin más.

Lo que haya que entregar o mirar se abre siempre dentro del módulo: ni Novedades ni el Calendario
son lugares donde se actúa, solo llevan al módulo.

## Planificación (21 días)
1. Definición: alcance, stack, modelo ER, endpoints, wireframes.
2. Base y cursos: login con roles, CRUD de cursos, dashboard y navegación.
3. Tareas y notas: entregas con archivos, calificaciones, vistas de notas.
4. Testing, validaciones, pulido responsive y presentación.

Alcance de la primera versión: login y roles, cursos e inscripciones, contenido por semana,
tareas con entrega de archivos, corrección con nota y comentario, Novedades, Calendario, Foro,
Mensajes, Notas.
Queda para después: control de plagio/IA, grupos, rúbricas detalladas, mails.
Mensajes y Foro entraron al alcance: las instituciones no quieren que la comunicación pase por
WhatsApp. La pantalla Actividad se reemplazó por el Calendario académico.

## Cómo levantar
```
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.main    # http://localhost:3000

cd frontend
npm install
npm run dev           # http://localhost:5173
```

## Pendiente inmediato
- **Pasar los datos de prueba de `backend/app/datos_iniciales.json` a Firestore**, colección por colección. Conviene empezar por las
  que ya tienen forma estable: `personas`, `cursos`, `publicaciones`.
- **Integrar Firestore desde el backend FastAPI** y conservar la API como capa intermedia. Las
  rutas deben seguir aplicando las validaciones y permisos del servidor.
- Las reglas de seguridad de Firestore tienen que reflejar los permisos que hoy están en el
  backend: por ejemplo, que solo los docentes puedan publicar o editar novedades.
- Pedirle a Hernán el `frontend/.env.local` con las claves de Firebase: está ignorado y no viaja
  por el repo.
- Subida y descarga real de archivos con Firebase Storage (hoy la pantalla del módulo los
  muestra pero no los sirve, y en Mensajes y Novedades solo se guarda el nombre o la dirección).
- Publicar en el tablero de consultas (el botón todavía no hace nada).
- Guardar el progreso del alumno en la base por usuario, en vez de en localStorage.
- Login y roles.


## Mensajes
Pantalla `/mensajes`: las charlas a la izquierda y el hilo abierto a la derecha, con su caja de
escribir. Son conversaciones de a dos, entre cualquier par de personas del campus.

Arriba de las charlas hay un buscador que filtra las conversaciones y, debajo, muestra gente de
**tus módulos** con la que todavía no hablaste, para empezar la charla. No busca en todo el campus:
`GET /api/mensajes/contactos` devuelve solo a quienes comparten un módulo con el usuario, con el
nombre de esos módulos. En las rutas va declarado antes que `/:id`, si no `contactos` se tomaría
como un id.

Desde los participantes de un módulo, el ícono de globo lleva a `/mensajes?con=:personaId`, que
abre la charla con esa persona o la crea si no existía. Es solo el ícono, sin texto al lado.

Las conversaciones viven en memoria en el backend y se reinician con el servidor. Mientras no haya
login, el que escribe es siempre `usuarioActual` (la constante `YO` del controlador).

La conversación abierta se cierra con la X de su cabecera. La caja de escribir tiene un clip para
adjuntar imágenes o archivos: se pueden elegir hasta 5, se ven como fichas antes de mandar y
quedan dentro de la burbuja. **De los adjuntos solo se guarda el nombre y el tamaño**: todavía no
hay dónde subir el archivo, eso llega con Firebase Storage.

## Personas
`backend/app/datos_iniciales.json` tiene una sola lista `personas`, cada una con su id. Los módulos guardan los ids de sus
participantes (`participantes` / `participantesDeCurso`) y los cursos su `docenteId`, en vez de
repetir nombre y rol en cada lado. Los mensajes también las referencian por id.

## Cambio de vista y reflejo en Módulos
Al pasar de tarjetas a lista, el contenedor lleva `key={vista}`: con eso se vuelve a montar y
cada módulo reproduce su animación de entrada, escalonada con la variable `--retraso`
(35 ms por posición, con tope en la 12.ª para que una lista larga no tarde una eternidad).

Los módulos con novedades llevan la clase `con-novedades` y un brillo que les cruza por encima
cada tanto (`@keyframes reflejo`, un `::before` con `pointer-events: none`). Cruza rápido y
después espera: un movimiento constante cansa. En las tarjetas el brillo es blanco, porque se ve
sobre la banda de color; en la vista lista el recuadro es blanco, así que ahí lleva un tinte del
color de acento o no se vería.

## Módulos por cuatrimestre
La pantalla Módulos separa las materias por período, cada grupo con su título y su propio
recuadro, y los más nuevos arriba. Con los grupos separados la tarjeta no repite el período.
Es así siempre: no hay interruptor para verlas todas juntas y la preferencia que lo permitía se
borró. Las materias de un mismo cuatrimestre ya están juntas, y poder mezclarlas no agregaba nada.

Los favoritos van arriba dentro de su cuatrimestre, con una estrella amarilla; los demás no llevan
marca. Marcar uno pega en `POST /api/cursos/:id/favorito`, que lo da vuelta y devuelve el curso.
Como el menú lateral tiene su propia copia de los módulos y la pide una sola vez al arrancar,
`marcarFavorito` (en `api.js`) dispara el evento `campustfi:cursos` y el menú vuelve a pedirlos:
sin eso la estrella aparecía en la grilla pero no en la barra. Es el mismo truco que
`campustfi:perfil`.


## Barra de desplazamiento
Está estilada en `global.css` (`::-webkit-scrollbar` y `scrollbar-color`) para no quedarnos con la
del navegador. El pulgar lleva un borde del color del fondo que lo rodea, que es lo que lo hace
ver finito: por eso hay variantes para los paneles y para el menú, que es oscuro.


## Novedades
Pantalla `/novedades`, que además es el inicio. Es un muro al estilo de una red social: cada
publicación es una tarjeta con el autor y su avatar, cuánto hace, las etiquetas de ámbito y
categoría, el título y el texto. Los textos largos se recortan con "Leer la novedad completa".

Arriba va una **portada**: el título de la sección con su bajada, el botón "Ver todas" (que baja
a la lista completa) y un carrusel con las tres novedades más importantes, de a una, con flechas
y puntos. Cada slide tiene el lugar de la ilustración a la izquierda y el texto a la derecha, con
la fecha y el ámbito en una fila de datos.

La primera del carrusel es la **destacada** (`anclada` en los datos) y es la única que lleva esa
etiqueta. Solo puede haber una: al anclar otra, el backend desancla la anterior. Los docentes la
eligen con la casilla "Destacar arriba de todo" del formulario.

Abajo va la lista completa en un mosaico de tres columnas con `column-count`, no con grid: así
cada tarjeta ocupa el alto que necesita y las columnas se acomodan solas. Las del carrusel también
aparecen ahí: la portada destaca, no reemplaza.

**Imágenes**: cada publicación puede tener una (`imagen`), y se ve tanto en el carrusel como en la
tarjeta. Si no tiene, el carrusel cae en el ícono de megáfono y la tarjeta va sin imagen. Por ahora
el campo es una dirección, no una subida: el formulario pide la ruta y las de prueba son SVG
propios en `frontend/public/novedades/`. Cuando esté Firebase Storage, ese campo pasa a ser un selector de
archivo.

**Leer la novedad completa**: las tarjetas recortan el texto pasados 170 caracteres y el botón
(abajo del todo, adentro del recuadro) abre la novedad entera superpuesta, con el fondo oscurecido
(`.lector`). Se cierra con la X, con Escape o tocando afuera, y mientras está abierta la página de
atrás no se mueve (`body.style.overflow`). La imagen de la tarjeta también la abre.

El visor **vuela desde la tarjeta** hasta el centro y vuelve a ella al cerrarse (`volarDesde`, la
técnica FLIP: el visor ya está en su lugar final y se lo transforma para que parezca que todavía
está en la tarjeta; después se saca la transformación y el navegador anima la diferencia). Dos
cosas importantes ahí: se mide el visor **sin transformación**, porque en modo estricto React
corre el efecto dos veces y la segunda mediría un rectángulo ya deformado; y la escala es una sola
para los dos ejes, porque con dos distintas el texto se estira.

El carrusel de la portada desliza una pista con todas las novedades al lado (`transform`
+ `transition`), en vez de cambiar el contenido de golpe. Las que no se ven llevan `inert`.

## Reacciones
Cada novedad tiene tres reacciones: "Lo leí", "Me sirve" y "Me genera dudas". Cada persona pone
una sola; tocar otra reemplaza la anterior y tocar la misma la saca.

Son **anónimas**: el backend guarda los ids de quienes reaccionaron, pero `conAutor()` nunca los
manda — saca el campo `reacciones` de la respuesta y en su lugar devuelve `cuenta` (los totales) y
`miReaccion` (la del que pregunta). Se ve cuántos fueron, nunca quiénes.

`POST /api/novedades/:id/reaccion` con `{ tipo }` (o `null`) devuelve la publicación actualizada,
así el frontend reemplaza esa sola en la lista en vez de volver a pedir todo.

**Permisos**: publicar y editar es solo para docentes, y editar solo la propia. El backend lo
verifica en `backend/app/rutas/novedades.py` (403 si no corresponde) y además manda `puedePublicar` y
`puedeEditar` para que el frontend no muestre botones que no van. El usuario de prueba es
estudiante, así que no ve el compositor: para verlo, cambiar el `id` de `usuario_actual` en
`backend/app/datos.py` al de un docente (por ejemplo 2).

## Campanitas del menú
Cada apartado del menú muestra una campana rellena con la cantidad en un círculo rojo encima:
Novedades (publicaciones de la semana), Módulos (cuántos módulos tienen algo nuevo) y Mensajes
(mensajes sin leer). Calendario y Foro no llevan, porque no acumulan pendientes.

Los números salen de `GET /api/contadores`, que `App.jsx` vuelve a pedir en cada cambio de ruta:
así al salir de Mensajes el contador ya refleja lo que se acaba de leer. Con el menú plegado no
entra la campana al lado del ícono, así que queda solo el número en la esquina del recuadro.

Ojo al probar: el estado de "leído" vive en memoria en el backend, así que una vez que se abre una
conversación el contador baja hasta que se reinicie el servidor.


## Calendario
Pantalla `/calendario`, debajo de Módulos en el menú. Muestra cuatro tipos de cosas, que se
distinguen por el color del borde izquierdo: entregas (rojo), exámenes (ámbar), clases (gris) y
eventos de la facultad (verde). Las entregas son enlaces: llevan a la pantalla de entrega del
módulo.

Arriba hay filtros para elegir qué ver: "Ver todo" y un botón por tipo, con cuántos hay de cada
uno en el período. No se pueden apagar los cuatro (dejaría la grilla vacía sin motivo) y la
elección se recuerda en `preferencias.js`.

En la vista mensual las clases se muestran solo con el código de la materia: el título completo no
entra en la celda, y que sea una clase ya lo dicen el ícono y el color. El título entero está en
el globito de ayuda y en la vista semanal.

Cuidado con los nombres de clase: el tipo va con prefijo (`tipo-clase`, `tipo-evento`…) porque
`.evento.evento` no significa "de tipo evento", significa "tiene la clase evento", y eso lo
cumplen todos los chips.

Dos vistas, **mes** y **semana**, con flechas para moverse y un botón "Hoy". La grilla es siempre
de siete columnas: en la vista mensual arranca el lunes de la semana del día 1 y termina el
domingo de la semana del último día, así que se ven días del mes vecino, apagados. El día de hoy
va recuadrado.

Las clases son semanales: en `backend/app/datos_iniciales.json` se guardan el día y el horario
(`clases`), y `backend/app/rutas/calendario.py` las expande a las fechas del rango pedido. Las entregas salen de
`tareas` y el resto de `eventos`.

## Foro
Pantalla `/foro`. Los temas se listan de la última actividad hacia atrás, con filtros por
asignatura arriba. Abrir un tema muestra la consulta (destacada) y sus respuestas, con una caja
para contestar. "Nuevo tema" pide asignatura, título y consulta.

El tema y sus respuestas son la misma lista `mensajes`: el primero es el que abre el tema, por eso
`respuestas` es `mensajes.length - 1`. Igual que en Mensajes, todo vive en memoria y el que
escribe es siempre `usuarioActual`.


## Módulos colgando del menú
La opción Módulos del menú lateral se despliega y lista las materias, para saltar de una a otra
sin pasar por la grilla. Van **separadas por cuatrimestre**, y cada cuatrimestre se puede
minimizar por su cuenta (se guarda en `preferencias.js`, los cerrados). Cada materia lleva su
color (con un aro claro, si no los módulos oscuros desaparecerían contra el fondo del menú) y una
campanita si tiene novedades.

Tanto la lista entera como cada cuatrimestre se abren y se cierran animando la altura con
`grid-template-rows: 0fr → 1fr` (`.menu-panel`), el mismo truco que las carpetas de un módulo. La opción Módulos
usa `end` en su NavLink: estando dentro de un módulo se marca el módulo en la sublista, no el
padre. La lista se abre sola al entrar a un módulo y su estado se recuerda en `preferencias.js`.

Con el menú plegado la sublista no se muestra: no hay lugar para los nombres. **Ojo**: al entrar a
un módulo el menú también se pliega solo, así que ahí la sublista queda oculta hasta desplegarlo a
mano. Si molesta, conviene sacar el plegado automático.

## Biblioteca
Pantalla `/biblioteca`, debajo de Mensajes en el menú. Junta dos cosas que se ven distinto:
los **materiales del campus** (etiqueta oscura "En el campus") y los **libros de catálogos
externos** (etiqueta clara con el nombre de la fuente). La diferencia importa: de un libro
externo nunca tenemos el archivo, solo adónde ir a buscarlo.

Cuatro pestañas: Catálogo, Guardados, Mis aportes y, solo para quien modera, Revisión con su
contador. Arriba, el buscador, el desplegable de dónde buscar (todo, título, autor, ISBN, tema)
y el botón de aportar. Debajo, las categorías como chips con cuántos hay, y la fila de filtros
(fuente, tipo, carrera, materia, idioma, orden) con "Limpiar filtros" cuando hay alguno puesto.

Lo que se escribe no se busca en el acto: se espera 400 ms a que pares de teclear, porque cada
búsqueda pega contra dos APIs externas.

### Catálogos externos
`services/librosExternos.js` consulta **Google Books** y **Open Library** en paralelo, del lado
del servidor. Va en el backend a propósito: la clave de Google (si se usa) no viaja al navegador,
la caché sirve para todos y, si una fuente se cae, la pantalla sigue andando con la otra.

Las dos respuestas se normalizan a la misma forma y se **unen por ISBN** o, si no hay, por título
y autor sin tildes. Cuando un libro está en las dos se queda el de Google (trae descripción y
portada más seguido), se completan los huecos con el de Open Library y se anota "También en".

**Solo se muestran las acciones que la fuente ofrece de verdad.** Nada de inventar un botón de
descarga: el PDF solo aparece si Google dice que el libro es de dominio público, el préstamo solo
si Open Library lo marca como `borrowable`. Si no hay nada, se dice que no lo hay.

Hay caché en memoria de 10 minutos (las mismas búsquedas se repiten muchísimo), espera máxima de
9 s por fuente — Open Library ronda los 4 s — y un freno de 30 búsquedas por minuto. Cuando una
fuente falla, el listado trae `fuentes` con el estado y la pantalla lo avisa arriba de los
resultados.

Ojo: **sin `GOOGLE_BOOKS_API_KEY` Google devuelve 429 casi siempre**, porque el cupo por IP es
bajo. La clave va en `backend/.env` (ver `.env.example`). Open Library no pide nada.

### Materiales propios
Están en `backend/app/datos_iniciales.json` (`materiales`, `categorias`, `carreras`, `favoritosBiblioteca`,
`moderacionBiblioteca`). Son ocho de ejemplo, uno o dos por área: alcanza para ver cómo queda, el
catálogo de verdad sale de la búsqueda externa.

Cada material tiene **`enlace` o `archivo`, nunca los dos**. Si no tenemos derecho a alojar el
libro, va el enlace a la fuente legítima; si el archivo está en el campus, el enlace se borra al
subirlo. Los de ejemplo son todos de licencia abierta o con enlace a donde consultarlos.

### El archivo
No hay Firebase Storage todavía, así que los bytes viven en memoria en `backend/app/datos.py`
(`guardar_archivo` / `leer_archivo`), aparte de la ficha: el material guarda nombre, tamaño y tipo.
Se pierden al reiniciar, como todo lo demás. Cuando esté Storage, eso pasa a ser una referencia
al bucket y el resto no cambia.

Suben en base64 dentro del JSON por `POST /api/biblioteca/:id/archivo`, con un límite específico
para los archivos: no hay motivo para que el foro pueda recibir 20 MB. El frontend
usa `XMLHttpRequest` y no `fetch`, porque es lo único que avisa cómo va la subida.

Validación, toda del lado del servidor: solo PDF y EPUB, **se miran los bytes** (`%PDF-` y, en el
EPUB, que sea un ZIP que declare `application/epub+zip`), que el tipo coincida con la extensión,
que no esté vacío y que no pase de `BIBLIOTECA_MAX_MB` (15 por defecto). La extensión sola no
prueba nada: cualquiera renombra un `.exe` a `.pdf`. El nombre se limpia antes de usarlo
(`../../etc/passwd` queda en `passwd.pdf`).

La descarga (`GET /api/biblioteca/:id/archivo`) pasa por el mismo control de acceso que la ficha y
va siempre como `attachment` con `nosniff`: un archivo de otra persona no se abre dentro del
campus.

### Permisos y moderación
**La facultad todavía no tiene rol de administrador**: en `personas` solo hay Estudiante y
Docente. Hasta que exista, **modera el docente**, que es quien responde por el material de su
cátedra. Está en una sola función (`puedeModerar` en el controlador): el día que se agregue el
rol, se cambia ahí y nada más.

- Cualquiera puede aportar, pero lo de un estudiante queda **pendiente** hasta que un docente lo
  apruebe. Lo que sube quien modera se publica directo.
- Un pendiente o un rechazado lo ven **solo quien lo subió y los docentes**, tanto la ficha como
  el archivo. No aparece en el catálogo.
- Editar y retirar: quien lo subió o un docente. Si lo edita quien lo subió y no modera, vuelve a
  la cola: el texto que se aprobó ya no es el que está.
- **Rechazar exige motivo** (400 si no viene): sin eso, quien aportó no sabe qué corregir. El
  motivo se le muestra en Mis aportes y queda en `moderacionBiblioteca` con quién y cuándo.

Todo se verifica en el backend, no solo escondiendo botones: `puedeAportar` / `puedeEditar` /
`puedeModerar` viajan en la respuesta para que el frontend no muestre lo que no va, pero la que
manda es la comprobación del servidor.

Al aportar hay que **confirmar que se tiene autorización** para compartir el material. Es la
casilla destacada del formulario y el backend la exige (400 si no viene): compartir material
ajeno sin permiso es el riesgo principal de toda la sección.

Los enlaces se validan: solo `http` y `https`, para que nadie deje un `javascript:` en la ficha.

### Favoritos
La estrella guarda tanto un material propio como un libro externo: el id externo
(`google:xxx`, `openlibrary:/works/OL1W`) es estable y se guarda tal cual. Por eso los ids van
codificados en la ruta (`encodeURIComponent`), si no las barras romperían el camino.

### Rutas
```
GET    /api/biblioteca/opciones      categorías con cuántos hay, carreras, materias, idiomas,
                                     tipos y qué puede hacer quien pregunta
GET    /api/biblioteca               catálogo: ?q &campo &fuente &categoria &tipo &carrera
                                     &materia &idioma &orden &pagina &porPagina
GET    /api/biblioteca/mis-aportes   los propios, con estado e historial
GET    /api/biblioteca/pendientes    la cola de revisión (solo docentes)
GET    /api/biblioteca/favoritos
GET    /api/biblioteca/:id           ficha, relacionados e historial
POST   /api/biblioteca               aportar
PATCH  /api/biblioteca/:id           editar
DELETE /api/biblioteca/:id           retirar
POST   /api/biblioteca/:id/archivo   subir (base64)
GET    /api/biblioteca/:id/archivo   descargar
POST   /api/biblioteca/:id/aprobar
POST   /api/biblioteca/:id/rechazar  { motivo } obligatorio
POST   /api/biblioteca/:id/favorito  y DELETE para quitarla
```
Las rutas con nombre fijo van **antes** que `/:id`, si no `favoritos` se tomaría como un id
(el mismo cuidado que `contactos` en Mensajes).

### Pendiente de la Biblioteca
- Mover los archivos a Firebase Storage y dejar en la base solo la referencia.
- Conseguir la `GOOGLE_BOOKS_API_KEY`, o la mitad de las búsquedas se queda sin Google.
- Las reglas de Firestore tienen que repetir estos permisos: que un pendiente no lo lea nadie
  más que su autor y los docentes.
- Rol de administrador de verdad, en vez de que modere cualquier docente.
- Reportar contenido (la tabla de moderación ya está, falta quién lo denuncia).
