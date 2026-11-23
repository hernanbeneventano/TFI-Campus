"""El punto de entrada del servidor: reparte cada petición entre FastAPI y Django.

Es lo que permite migrar de a un módulo por vez. El frontend sigue pegándole
a `/api/...` como siempre, y acá se decide quién contesta. Pasar un módulo a
Django es agregar su prefijo a `MIGRADOS`; volver atrás es sacarlo.

Lo que no está en la lista lo atiende FastAPI, exactamente como antes de que
existiera este archivo: para esas peticiones esto es un pasamanos, no las
mira, no las toca y no les agrega nada.

Un solo proceso, a propósito
----------------------------
FastAPI y Django corren acá adentro, juntos. Nunca en dos servidores: serían
dos copias de la memoria del campus y dos procesos guardando por diferencia
sobre el mismo Firestore, y el último en escribir pisaría al otro sin que
nada fallara. Con un proceso hay una sola memoria, un solo freno y un solo
guardado.

Lo que pasa con una petición que va a Django
--------------------------------------------
No se le arma una pila nueva: **se usa la de FastAPI**. Mismos middlewares
—el freno, la auditoría, el guardado, el CORS—, en el mismo orden, con los
mismos manejadores de error, construidos con el mismo código con el que los
construye Starlette (`Starlette.build_middleware_stack`). Lo único que cambia
es lo que va en el centro: Django en vez del router de FastAPI.

    ServerErrorMiddleware      el 500, con el manejador del campus
      freno                    \
      guardado                  | los de app/main.py, los mismos objetos
      auditoría (IP)            |
      CORS                     /
        ExceptionMiddleware    el 400, el 401, el 404… con el manejador del campus
          Django               solo enruta y ejecuta la vista

Así el formato de un error, las cabeceras de CORS o el 413 del freno son los
mismos por construcción, no por imitación. Y si mañana alguien le agrega un
middleware a FastAPI, las rutas de Django lo heredan solas.

El freno tiene además una razón propia para estar afuera: Django lee el
cuerpo entero antes de llegar a cualquier middleware suyo. Un pedido que
anuncia 40 MB quedaría esperando bytes que no van a llegar, en vez de recibir
el 413 en el acto.

El arranque
-----------
Lo hace FastAPI, como siempre: el `lifespan` —conectar Firestore, traer el
campus, asignar legajos, conectar R2— y el guardado al cerrar. El despachador
le pasa esos mensajes sin tocarlos, así corren una sola vez.
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_django.settings")

from starlette.middleware import Middleware  # noqa: E402
from starlette.middleware.errors import ServerErrorMiddleware  # noqa: E402
from starlette.middleware.exceptions import ExceptionMiddleware  # noqa: E402

from app.main import app as fastapi  # noqa: E402

# ===================== Qué atiende Django =====================
# Prefijos completos: «/api/foro» atiende «/api/foro» y «/api/foro/...», pero
# no «/api/forobar». Para un apartado que tiene su prefijo para él solo.
#
# Volver atrás es sacar la línea: la ruta de FastAPI sigue en su lugar.
MIGRADOS: tuple[str, ...] = (
    "/api/calendario",
    "/api/panel",
    "/api/auditoria",
    "/api/inscripciones",
    # Finales del alumno. «/api/finales» entero no: «/api/finales/gestion/…»
    # es de la cátedra y sigue en FastAPI. Debajo de estos tres no hay nada
    # de la gestión.
    "/api/finales/mesas",
    "/api/finales/proximas",
    "/api/finales/resultados",
    "/api/archivos",
    "/api/me",
    "/api/contadores",
)

# Caminos exactos: solo esa dirección, nada que cuelgue de ella. Para las
# rutas que viven bajo un prefijo que comparten varios archivos —«/api/cursos»,
# «/api/tareas», «/api/finales», «/api/salud»—. Con «/api/tareas/pendientes»
# como prefijo, «/api/tareas/pendientes/mi-entrega» también iría a Django y
# contestaría 404, cuando hoy la atiende Mi cursada (con «pendientes» como id
# de tarea: 400). Exacto, todo lo demás sigue en FastAPI por construcción.
MIGRADOS_EXACTOS: tuple[str, ...] = (
    "/api/tareas/pendientes",
)


# Módulos enteros, por el nombre de su archivo en `app/rutas/`. Es la forma
# de migrar los que comparten prefijo: `/api/cursos/...` es de cursos, de la
# gestión del módulo, de Mi cursada y de asistencias, y ningún prefijo ni
# camino exacto separa `/api/cursos/{id}/notas` de `/api/cursos/{id}/asistencias`.
# Para estos se pregunta **qué ruta de FastAPI la atendería** —con la misma
# regla que Starlette: primero la que coincide en camino y método, si no la
# primera que coincide en camino— y si es de un módulo migrado va a Django.
# Las vistas las arma `campus_django/puente.py`.
MODULOS: tuple[str, ...] = (
    "salud",
    "mensajes",
    "foro",
)

# Rutas sueltas de un módulo que no se migra entero: (módulo, camino de FastAPI)
RUTAS_SUELTAS: tuple[tuple[str, str], ...] = (
    ("main", "/api/salud"),
)


def _ruta_que_atiende(camino: str, metodo: str):
    """La ruta de FastAPI que atendería esa petición, o `None` si ninguna."""
    from starlette.routing import Match

    alcance = {"type": "http", "path": camino, "root_path": "", "method": metodo}
    parcial = None
    for ruta in fastapi.router.routes:
        coincide, _ = ruta.matches(alcance)
        if coincide == Match.FULL:
            return ruta
        if coincide == Match.PARTIAL and parcial is None:
            parcial = ruta
    return parcial


def es_de_django(camino: str, metodo: str = "GET") -> bool:
    if camino in MIGRADOS_EXACTOS or any(
        camino == p or camino.startswith(p + "/") for p in MIGRADOS
    ):
        return True
    if not MODULOS and not RUTAS_SUELTAS:
        return False
    ruta = _ruta_que_atiende(camino, metodo)
    endpoint = getattr(ruta, "endpoint", None)
    if endpoint is None:
        # Ninguna ruta: el 404 o la barra final los contesta FastAPI
        return False
    modulo = endpoint.__module__.rsplit(".", 1)[-1]
    return modulo in MODULOS or (modulo, ruta.path) in RUTAS_SUELTAS


# ===================== La pila de FastAPI, con Django en el centro =====================
def pila_de(referencia, interior):
    """Lo mismo que `Starlette.build_middleware_stack`, con otro centro.

    Se copia la lógica de Starlette línea por línea y se leen los middlewares
    y los manejadores **del propio FastAPI**, así no puede haber diferencias
    entre las dos pilas.
    """
    debug = referencia.debug
    manejador_500 = None
    manejadores = {}
    for clave, valor in referencia.exception_handlers.items():
        if clave in (500, Exception):
            manejador_500 = valor
        else:
            manejadores[clave] = valor

    capas = (
        [Middleware(ServerErrorMiddleware, handler=manejador_500, debug=debug)]
        + referencia.user_middleware
        + [Middleware(ExceptionMiddleware, handlers=manejadores, debug=debug)]
    )

    aplicacion = interior
    for cls, args, kwargs in reversed(capas):
        aplicacion = cls(aplicacion, *args, **kwargs)
    return aplicacion


_django = None


def django():
    """Django con la pila de FastAPI alrededor. Se arma la primera vez que se
    necesita: mientras no haya nada migrado, Django ni siquiera se carga."""
    global _django
    if _django is None:
        from django.core.asgi import get_asgi_application

        pila = pila_de(fastapi, get_asgi_application())

        async def con_pila(scope, receive, send):
            # Lo mismo que hace `Starlette.__call__` antes de entrar a la pila
            scope["app"] = fastapi
            await pila(scope, receive, send)

        _django = con_pila
    return _django


# ===================== El reparto =====================
async def aplicacion(scope, receive, send):
    """El ASGI del servidor.

    Solo las peticiones HTTP de un módulo migrado van a Django. Todo lo demás
    —incluido el `lifespan`, que es el arranque y el cierre— va a FastAPI tal
    cual llegó.
    """
    if scope["type"] == "http" and es_de_django(scope["path"], scope.get("method", "GET")):
        await django()(scope, receive, send)
        return
    await fastapi(scope, receive, send)


# Con algo migrado, Django se arma al arrancar y no con la primera petición:
# una configuración rota tiene que impedir que el servidor levante, no
# aparecer cuando un alumno abre el foro.
if MIGRADOS or MIGRADOS_EXACTOS or MODULOS or RUTAS_SUELTAS:
    django()
