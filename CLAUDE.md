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
- Backend: Node.js + Express (`backend/`)
- Base de datos: **todavía no definida** (propuesta: PostgreSQL + Prisma). Hoy se usan datos de prueba en `backend/src/data/mock.js`.
- Futuro: bcrypt + jsonwebtoken (login), multer (subida de archivos).
- Todo en JavaScript. Código, nombres y textos de la interfaz en **español**.

## Estructura
```
frontend/src/
  components/  MenuLateral, Encabezado, BarraHerramientas, TarjetaModulo, PanelTareas,
               CarpetaModulo, VisorItem, PestanasModulo, PanelModulo, BarraProgreso,
               Iconos (SVG propios)
  pages/       Novedades (inicio), Modulos, Modulo (interior), Calendario, Foro, Mensajes,
               EnConstruccion (página no encontrada)
  services/    api.js: todas las llamadas al backend (Vite redirige /api a localhost:3000)
               progreso.js: recursos completados y cuentas de avance (hoy en localStorage)
               preferencias.js: ajustes de la interfaz, como el menú plegado
               fechas.js: hace() → "hace 12 min", "hace 2 horas", "hace 2 meses"
  hooks/       usePresencia.js: si el usuario está conectado, ausente o desconectado
  styles/      global.css: paleta en variables CSS en :root
backend/src/
  routes/ → controllers/ → data/mock.js     middleware/errores.js
  Rutas: GET /api/salud, /api/me, /api/cursos, /api/cursos/:id, /api/tareas/pendientes
         /api/cursos/:id/modulo → todo lo de la pantalla del módulo en una sola llamada:
         { curso, carpetas, anuncios, participantes }
         GET /api/mensajes (lista + total sin leer), GET /api/mensajes/:id (y la da por leída),
         POST /api/mensajes/:id (enviar), POST /api/mensajes { paraId } (abrir o crear la charla),
         GET /api/mensajes/contactos (gente de tus módulos)
         GET /api/novedades (muro), POST /api/novedades, PUT /api/novedades/:id,
         POST /api/novedades/:id/reaccion
         GET /api/calendario?desde&hasta → entregas, exámenes, clases y eventos del rango
         GET /api/foro, POST /api/foro, GET /api/foro/:id, POST /api/foro/:id (responder)
         GET /api/contadores → { novedades, modulos, mensajes }: las campanitas del menú
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

Cada materia tiene su color en `mock.js` para la banda de su tarjeta en Módulos y para los íconos
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

En `mock.js` las personas guardan `accesoHaceMin` (hace cuántos minutos entraron), no una fecha
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
cd backend && npm install && cp .env.example .env && npm run dev    # http://localhost:3000
cd frontend && npm install && npm run dev                          # http://localhost:5173
```

## Pendiente inmediato
- Elegir y configurar la base de datos.
- Subida y descarga real de archivos (hoy la pantalla del módulo los muestra pero no los sirve).
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

Las conversaciones viven en memoria en `mock.js` y se reinician con el servidor. Mientras no haya
login, el que escribe es siempre `usuarioActual` (la constante `YO` del controlador).

La conversación abierta se cierra con la X de su cabecera. La caja de escribir tiene un clip para
adjuntar imágenes o archivos: se pueden elegir hasta 5, se ven como fichas antes de mandar y
quedan dentro de la burbuja. **De los adjuntos solo se guarda el nombre y el tamaño**: todavía no
hay dónde subir el archivo, eso llega con multer.

## Personas
`mock.js` tiene una sola lista `personas`, cada una con su id. Los módulos guardan los ids de sus
participantes (`participantes` / `participantesDeCurso`) y los cursos su `docenteId`, en vez de
repetir nombre y rol en cada lado. Los mensajes también las referencian por id.

## Módulos por cuatrimestre
La pantalla Módulos separa las materias por período, cada grupo con su título y su propio
recuadro, y los más nuevos arriba. Con los grupos separados la tarjeta no repite el período.
La preferencia está en `preferencias.js` (`leerAgruparPorPeriodo`, por defecto sí); **falta el
interruptor para verlas todas juntas, que va en Ajustes** cuando esa pantalla exista.


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
propios en `frontend/public/novedades/`. Cuando esté multer, ese campo pasa a ser un selector de
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
verifica en `novedades.controller.js` (403 si no corresponde) y además manda `puedePublicar` y
`puedeEditar` para que el frontend no muestre botones que no van. El usuario de prueba es
estudiante, así que no ve el compositor: para verlo, cambiar el `id` de `usuarioActual` en
`mock.js` al de un docente (por ejemplo 2).

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

Las clases son semanales: en `mock.js` se guardan el día y el horario (`clases`), y
`calendario.controller.js` las expande a las fechas del rango pedido. Las entregas salen de
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
