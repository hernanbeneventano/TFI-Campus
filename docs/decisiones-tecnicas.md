# Registro de decisiones técnicas

Cada entrada deja asentada una decisión de diseño: qué se decidió, qué alternativas se
descartaron y por qué. El propósito es que una decisión tomada hace dos semanas no haya
que volver a discutirla por no recordar el motivo.

**Formato de cada entrada:** contexto, decisión, alternativas descartadas y consecuencias.

| N.º | Decisión | Fecha | Estado |
|---|---|---|---|
| [1](#1-javascript-en-las-dos-puntas) | JavaScript en las dos puntas | 28/10/2026 | Reemplazada por la 21 |
| [2](#2-react-con-vite-en-lugar-de-create-react-app) | React con Vite | 28/10/2026 | Vigente |
| [3](#3-separar-el-servidor-en-rutas-controladores-y-datos) | Servidor en capas | 30/10/2026 | Vigente |
| [4](#4-datos-de-prueba-en-memoria-antes-que-la-base-definitiva) | Datos de prueba en memoria | 30/10/2026 | Vigente, con plazo |
| [5](#5-variables-de-color-nombradas-por-su-función) | Variables de color por función | 30/10/2026 | Vigente |
| [6](#6-el-rojo-tiene-dos-significados-y-ninguno-más) | Economía del rojo | 31/10/2026 | Vigente |
| [7](#7-las-entregas-se-abren-dentro-del-módulo) | Entregas dentro del módulo | 31/10/2026 | Vigente |
| [8](#8-reemplazar-la-pantalla-actividad-por-un-calendario) | Calendario en lugar de Actividad | 01/11/2026 | Vigente |
| [9](#9-mensajería-y-foro-dentro-del-alcance-inicial) | Mensajería y foro en el alcance | 01/11/2026 | Vigente |
| [10](#10-las-reacciones-son-anónimas-en-el-servidor) | Anonimato en el servidor | 01/11/2026 | Vigente |
| [11](#11-firebase-como-base-de-datos) | Firebase como base de datos | 01/11/2026 | Vigente |
| [12](#12-las-pestañas-son-estado-de-la-pantalla-y-no-rutas) | Pestañas como estado | 01/11/2026 | Vigente, revisable |
| [13](#13-desplegable-propio-en-lugar-del-selector-del-navegador) | Desplegable propio | 02/11/2026 | Vigente |
| [14](#14-avisos-entre-componentes-alejados) | Avisos entre componentes | 02/11/2026 | Vigente |
| [15](#15-los-catálogos-externos-se-consultan-desde-el-servidor) | Catálogos externos desde el servidor | 02/11/2026 | Vigente |
| [16](#16-solo-se-muestran-las-acciones-que-la-fuente-ofrece) | Sin botones decorativos | 02/11/2026 | Vigente |
| [17](#17-un-material-tiene-enlace-o-archivo-nunca-ambos) | Enlace o archivo, no ambos | 02/11/2026 | Vigente |
| [18](#18-los-archivos-se-validan-por-su-contenido) | Validación por contenido | 02/11/2026 | Vigente |
| [19](#19-modera-el-docente-hasta-que-exista-el-rol-de-administrador) | Modera el docente | 02/11/2026 | Provisoria |
| [20](#20-postergar-la-autenticación) | Postergar la autenticación | 02/11/2026 | Provisoria |
| [21](#21-python-con-fastapi-en-el-servidor) | Python con FastAPI en el servidor | 07/11/2026 | Vigente |

---

## 1. JavaScript en las dos puntas

**Contexto.** Había que elegir los lenguajes del navegador y del servidor. El equipo son
dos personas con un plazo de 21 días.

**Decisión.** Usar JavaScript en ambos extremos.

**Alternativas descartadas.** Python con Django o Flask del lado del servidor, que el
equipo también conoce.

**Por qué.** Con dos personas y un plazo corto, cambiar de lenguaje al pasar de una
parte a la otra tiene un costo real. Compartir lenguaje permite además compartir
criterios de escritura y que cada integrante pueda leer el código del otro sin fricción.

**Consecuencias.** Se renuncia al tipado estático. Se compensa con nombres explícitos y
validación en los límites del sistema.

**Estado.** Reemplazada el 07/11/2026 por la decisión [21](#21-python-con-fastapi-en-el-servidor).

---

## 2. React con Vite en lugar de Create React App

**Contexto.** Hacía falta una herramienta de construcción para el proyecto de interfaz.

**Decisión.** Vite.

**Alternativas descartadas.** Create React App, que es la opción más difundida en
material de aprendizaje.

**Por qué.** Create React App está sin mantenimiento activo. Vite arranca el servidor de
desarrollo en menos tiempo porque no empaqueta los archivos por adelantado, y resuelve
la redirección de las consultas al servidor con unas pocas líneas de configuración.

---

## 3. Separar el servidor en rutas, controladores y datos

**Contexto.** El servidor iba a crecer hasta varias decenas de puntos de acceso.

**Decisión.** Tres capas: `routes/` asocia direcciones a funciones, `controllers/`
contiene la lógica, `data/` resuelve el acceso al almacenamiento. Más adelante se agregó
`services/` para la lógica que no pertenece a un único controlador.

**Alternativas descartadas.** Definir las rutas y su lógica en el mismo archivo, que es
más rápido al principio.

**Por qué.** La migración a Firestore era previsible desde el inicio. Con las capas
separadas, esa migración toca únicamente `data/`.

---

## 4. Datos de prueba en memoria antes que la base definitiva

**Contexto.** Al comenzar no estaba decidido el motor de base de datos.

**Decisión.** Construir las pantallas sobre un conjunto de datos de prueba en memoria,
en `backend/src/data/mock.js` (la implementación Node.js anterior; hoy los datos iniciales
están en `backend/app/datos_iniciales.json`), y migrar después.

**Alternativas descartadas.** Definir primero la base y construir las pantallas encima.

**Por qué.** Varias decisiones sobre la forma de los datos surgieron al ver las pantallas
funcionando. El contador de avance de una tarea, por ejemplo, necesitó que el servidor
devolviera la carpeta completa junto a cada tarea, algo que no se había previsto.
Congelar el esquema antes habría obligado a modificarlo igual.

**Consecuencias.** Los datos se reinician al reiniciar el servidor. Es aceptable durante
el desarrollo y no lo es para la entrega: la migración es el trabajo pendiente de mayor
prioridad.

---

## 5. Variables de color nombradas por su función

**Contexto.** La paleta cambió cinco veces durante el desarrollo.

**Decisión.** Nombrar las variables por su función y no por su color: `--oscuro`,
`--principal`, `--alerta`, y no `--azul` o `--rojo`.

**Por qué.** Con nombres por color, cambiar el acento de rojo a azul deja variables
llamadas `--rojo` que contienen azul. Con nombres por función, probar otra paleta es
modificar un único bloque del archivo de estilos.

**Consecuencias.** La paleta pasó por cinco variantes sin tocar una sola regla fuera de
ese bloque.

---

## 6. El rojo tiene dos significados y ninguno más

**Contexto.** La paleta inicial usaba rojo como color de acento general.

**Decisión.** El rojo señala únicamente dos cosas: lo que está mal, como atrasos y
errores, y lo que está sin leer. El resto de los acentos usa azul.

**Por qué.** Si el rojo aparece en un botón habitual y también en un aviso de atraso,
deja de comunicar urgencia.

**Consecuencias.** Hubo que resolver por otros medios la distinción entre lo urgente y lo
habitual: negrita, ícono de reloj en lo atrasado y triángulo en lo que falta empezar. El
resultado también beneficia a quienes perciben los colores de manera diferente.

---

## 7. Las entregas se abren dentro del módulo

**Contexto.** El panel lateral lista las tareas pendientes. Había que decidir adónde
llevan.

**Decisión.** Cada tarea pendiente conduce a la pantalla de entrega dentro de su módulo,
mediante una dirección que incluye el identificador de la tarea.

**Alternativas descartadas.** Llevar a una pantalla intermedia que concentre todas las
entregas.

**Por qué.** La pantalla intermedia agrega un paso sin agregar información. El lugar
donde se entrega es el módulo.

**Consecuencias.** Esta decisión dejó sin propósito a la pantalla Actividad y condujo
directamente a la decisión 8. El identificador queda en la dirección, de modo que el
enlace sirve para compartir y para recargar.

---

## 8. Reemplazar la pantalla Actividad por un calendario

**Contexto.** La planificación preveía una pantalla Actividad como bandeja de
notificaciones.

**Decisión.** Reemplazarla por un calendario académico que integre entregas, exámenes,
clases y eventos.

**Por qué.** Tras la decisión 7, la bandeja duplicaba información que ya aparecía en el
panel de tareas pendientes. Un calendario, en cambio, aporta algo que ninguna otra
pantalla ofrecía: la ubicación temporal de los compromisos.

---

## 9. Mensajería y foro dentro del alcance inicial

**Contexto.** Ninguno de los dos figuraba en la planificación de hitos.

**Decisión.** Incorporarlos a la primera versión.

**Por qué.** Las instituciones prefieren que el intercambio entre docentes y estudiantes
no ocurra en aplicaciones de mensajería personal. Esa preferencia se sostiene solo si la
plataforma ofrece un canal propio. Sin mensajería interna, la comunicación migra a
canales informales y se pierde la trazabilidad.

**Consecuencias.** La búsqueda de destinatarios se limita a quienes comparten un módulo
con quien consulta, y no a todo el campus.

---

## 10. Las reacciones son anónimas en el servidor

**Contexto.** Las novedades admiten tres reacciones. Había que decidir si se muestra
quién reaccionó.

**Decisión.** El servidor guarda los identificadores de quienes reaccionaron, pero nunca
los incluye en la respuesta. Devuelve los totales y la reacción propia de quien consulta.

**Alternativas descartadas.** Enviar la lista completa y que la pantalla no la muestre.

**Por qué.** Si el dato viaja al navegador, cualquiera puede verlo inspeccionando la
respuesta. El anonimato que depende de que la pantalla omita mostrar algo no es
anonimato.

---

## 11. Firebase como base de datos

**Contexto.** La propuesta original era PostgreSQL con Prisma.

**Decisión.** Firebase: Firestore para los datos, Authentication para el inicio de sesión
y Storage para los archivos.

**Alternativas descartadas.** PostgreSQL con Prisma.

**Por qué.** El proyecto necesita tres cosas además de la base: autenticación,
almacenamiento de archivos y despliegue sin administrar un servidor. Con PostgreSQL cada
una requería una pieza aparte y, con el plazo disponible, integrar tres servicios
distintos competía con terminar las funcionalidades.

**Consecuencias en ese momento.** Quedaban sin uso bcrypt, jsonwebtoken y multer, que
figuraban como dependencias futuras. Se postergó decidir si Express permanecería como
capa intermedia o si la interfaz consultaría Firestore directamente. Esa implementación
de Express fue reemplazada por Python/FastAPI en la decisión 21.

---

## 12. Las pestañas son estado de la pantalla y no rutas

**Contexto.** La pantalla de un módulo tiene cuatro pestañas.

**Decisión.** Mantenerlas como estado del componente y no como rutas propias.

**Por qué.** Es más simple y no requiere definir cuatro rutas por módulo.

**Consecuencias.** No se puede compartir el enlace a una pestaña determinada. Si eso
resulta necesario, conviene pasarlas a rutas hijas. Queda asentado como revisable.

---

## 13. Desplegable propio en lugar del selector del navegador

**Contexto.** Los filtros usaban el elemento de selección estándar.

**Decisión.** Construir un componente propio que sigue el patrón de caja combinada, con
navegación por teclado y los atributos de accesibilidad correspondientes.

**Por qué.** La lista que despliega el navegador no admite estilos. El resultado rompía
visualmente con el resto de la interfaz y variaba según el sistema operativo.

**Consecuencias.** Hubo que implementar a mano el recorrido con las flechas, el cierre
con la tecla de escape y el cierre al tocar fuera del componente.

---

## 14. Avisos entre componentes alejados

**Contexto.** El menú lateral mantiene su propia copia de los módulos y la pide una sola
vez, al iniciarse. Al marcar un favorito desde la pantalla Módulos, el menú no se
enteraba.

**Decisión.** La capa de servicios emite un aviso al que el componente se suscribe.

**Alternativas descartadas.** Un almacén de estado global, o subir el estado al
componente raíz y pasarlo hacia abajo.

**Por qué.** Son dos o tres casos puntuales. Un almacén global agrega una dependencia y
un concepto nuevo para resolver algo acotado.

**Consecuencias.** Si los casos se multiplican, conviene reconsiderar el almacén global.

---

## 15. Los catálogos externos se consultan desde el servidor

**Contexto.** La Biblioteca consulta Google Books y Open Library.

**Decisión.** Consultarlos desde el servidor y no desde el navegador.

**Por qué.** Tres motivos. La clave de acceso de Google no viaja al navegador. La memoria
intermedia de resultados se comparte entre todos los usuarios en lugar de rehacerse en
cada navegador. Y la unificación de resultados entre las dos fuentes se resuelve una vez,
del lado del servidor.

**Consecuencias.** El servidor pasa a depender de servicios externos, lo que obligó a
definir tiempos máximos de espera y comportamiento ante fallas.

---

## 16. Solo se muestran las acciones que la fuente ofrece

**Contexto.** Los catálogos externos devuelven libros con distintos niveles de
disponibilidad: algunos se leen completos, otros admiten préstamo, la mayoría solo tiene
ficha.

**Decisión.** Mostrar únicamente las acciones que la fuente informa como disponibles. El
botón de descarga aparece solo si la fuente declara la obra como de dominio público.
Cuando no hay ninguna acción posible, la ficha lo indica.

**Alternativas descartadas.** Mostrar siempre los botones y que fallen al usarlos.

**Por qué.** Un botón que no funciona es peor que la ausencia del botón: hace perder un
clic y enseña a desconfiar de la interfaz.

---

## 17. Un material tiene enlace o archivo, nunca ambos

**Contexto.** La biblioteca aloja material propio, pero gran parte de la bibliografía
tiene derechos reservados.

**Decisión.** Cada material conserva un enlace a la fuente legítima o un archivo alojado,
y nunca los dos. Al subir un archivo, el enlace se descarta.

**Por qué.** Evita la ambigüedad sobre cuál es la copia válida y deja explícito el
criterio: si no hay autorización para alojar la obra, se enlaza.

---

## 18. Los archivos se validan por su contenido

**Contexto.** La biblioteca recibe archivos de los usuarios.

**Decisión.** Validar la extensión, que el tipo declarado coincida con ella y, sobre
todo, que los primeros bytes correspondan efectivamente al formato declarado. Además, el
nombre se depura antes de usarse y la descarga se entrega siempre como archivo adjunto
con la indicación de no inferir el tipo.

**Alternativas descartadas.** Confiar en la extensión, o en el tipo que declara el
navegador.

**Por qué.** Cualquiera renombra un archivo. La extensión no prueba nada sobre el
contenido, y el tipo que declara el navegador lo controla quien envía.

**Consecuencias.** Las pruebas verifican que un ejecutable renombrado como PDF se
rechaza, y que un nombre con rutas relativas se almacena depurado.

---

## 19. Modera el docente hasta que exista el rol de administrador

**Contexto.** La Biblioteca necesita moderación. La lista de personas del sistema
contiene únicamente los roles de Estudiante y Docente.

**Decisión.** Hasta que exista el rol de Administrador, la moderación la ejerce el
Docente.

**Alternativas descartadas.** Crear un sistema de permisos paralelo al de roles.

**Por qué.** Un segundo sistema de permisos conviviendo con el existente es una fuente
de inconsistencias. El docente es, además, quien responde por el material de su cátedra.

**Consecuencias.** La decisión está concentrada en una única función del controlador,
`puedeModerar`. Incorporar el rol requiere modificar un solo punto del código.

**Estado.** Provisoria. Se revisa cuando se incorporen los roles definitivos.

---

## 20. Postergar la autenticación

**Contexto.** El inicio de sesión estaba previsto para el hito 2.

**Decisión.** Postergarlo hasta después de la migración a Firestore, y desarrollar
mientras tanto con un usuario de prueba fijo.

**Por qué.** Implementar autenticación propia con bcrypt y tokens, para reemplazarla
semanas después por Firebase Authentication, significaba escribir dos veces lo mismo.

**Consecuencias.** Se asume una deuda explícita. Para que esa deuda no se vuelva
estructural, los controladores ya verifican los permisos por rol, y la identidad se lee
de una única constante por controlador. El cambio se reduce a leer esa identidad de la
credencial en lugar de la constante.

**Riesgo asumido.** El criterio de evaluación sobre seguridad y control de acceso queda
cubierto de manera parcial mientras esto siga pendiente.

**Estado.** Provisoria. Es la primera tarea después de la migración.

---

## 21. Python con FastAPI en el servidor

**Contexto.** La API creció y el equipo decidió pasar el servidor de Express a Python,
manteniendo React y Vite en el frontend.

**Decisión.** Usar FastAPI para el backend principal y mantener la interfaz HTTP que
consume el frontend. La implementación está en `backend/`.

**Alternativas descartadas.** Continuar ampliando el servidor Express existente.

**Por qué.** El backend Python permite organizar las rutas por funcionalidad, generar
documentación OpenAPI interactiva y avanzar con un lenguaje distinto al del frontend.

**Consecuencias.** El backend requiere Python 3.11 o superior y sus dependencias de
`backend/requirements.txt`. Los datos siguen siendo de prueba y se reinician al reiniciar
el servidor. Las pantallas anteriores de Actividad e Información se mantienen mediante
rutas de compatibilidad. La implementación de Express fue retirada del proyecto.

**Estado.** Vigente.
