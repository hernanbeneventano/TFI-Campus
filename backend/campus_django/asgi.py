"""El servidor del campus: Django, con lo que antes ponía FastAPI alrededor.

Lo sirve uvicorn (`python -m app.main`). Django atiende las rutas; acá están
las capas que las envuelven, en el **mismo orden** en que las armaba FastAPI
y con el mismo comportamiento —verificado contra lo que grabó FastAPI antes
de irse—:

    el error 500         afuera de todo: lo que nadie atajó
      el freno           el tamaño y las peticiones por minuto (413, 429)
        el guardado      después de cada petición, lo que cambió va a Firestore
          la IP          la petición a mano de la auditoría
            CORS         el frontend en otro puerto
              los 4xx    los errores de las rutas, como {"error": "..."}
                Django   enruta y ejecuta la vista

El orden no es un detalle: el 413 y el 429 salen **sin** cabeceras de CORS
(se contestan antes de llegar ahí) y un 404 **con** ellas; un 500 no se
guarda, porque la petición no terminó.

Y el arranque (`lifespan`): conectar Firestore, traer el campus, asignar
legajos y conectar R2; al cerrar, guardar lo último.
"""

from __future__ import annotations

import os
from urllib.parse import parse_qsl

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_django.settings")

from asgiref.sync import sync_to_async  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from app import main  # noqa: E402  (arranca la configuración del campus)
from app.servicios import auditoria, frenos, persistencia  # noqa: E402
from app.web import (  # noqa: E402
    ErrorDeValidacion,
    HTTPException,
    JSONResponse,
    PlainTextResponse,
    Response,
)


# ===================== La petición =====================
class Cabeceras:
    """Las cabeceras de la petición, sin distinguir mayúsculas."""

    def __init__(self, crudas: list) -> None:
        self._lista = [(k.decode("latin-1").lower(), v.decode("latin-1")) for k, v in crudas]

    def get(self, nombre: str, defecto=None):
        nombre = nombre.lower()
        return next((v for k, v in self._lista if k == nombre), defecto)

    def __getitem__(self, nombre: str) -> str:
        valor = self.get(nombre)
        if valor is None:
            raise KeyError(nombre)
        return valor

    def __contains__(self, nombre: str) -> bool:
        return self.get(nombre) is not None

    def keys(self):
        return [k for k, _ in self._lista]

    def items(self):
        return list(self._lista)


class Cliente:
    def __init__(self, host: str, port: int) -> None:
        self.host, self.port = host, port


class Peticion:
    """Lo que el freno, la auditoría y las rutas miran de una petición: las
    cabeceras, el método, de dónde viene y la consulta. Se arma con lo que
    manda el servidor (`scope`), igual que el `Request` de Starlette."""

    def __init__(self, scope: dict) -> None:
        self.scope = scope
        self.method = scope.get("method", "GET")
        self.headers = Cabeceras(scope.get("headers") or [])
        cliente = scope.get("client")
        self.client = Cliente(cliente[0], cliente[1]) if cliente else None
        crudo = (scope.get("query_string") or b"").decode("latin-1")
        # Con un parámetro repetido gana el último, como en Starlette
        self.query_params = dict(parse_qsl(crudo, keep_blank_values=True))


async def _enviar(respuesta: Response, send) -> None:
    await send({
        "type": "http.response.start",
        "status": respuesta.status_code,
        "headers": [(k.encode("latin-1"), v.encode("latin-1")) for k, v in respuesta.cabeceras],
    })
    await send({"type": "http.response.body", "body": respuesta.body})


# ===================== Las capas =====================
def errores_500(app):
    """Lo que nadie atajó: 500 con «Error interno del servidor», y el error
    sigue su camino para que el servidor lo registre (como Starlette)."""

    async def capa(scope, receive, send):
        empezo = False

        async def enviar(mensaje):
            nonlocal empezo
            if mensaje["type"] == "http.response.start":
                empezo = True
            await send(mensaje)

        try:
            await app(scope, receive, enviar)
        except Exception as error:
            if not empezo:
                print(f"Error no previsto: {error!r}")
                await _enviar(JSONResponse({"error": "Error interno del servidor"}, 500), send)
            raise

    return capa


def freno(app):
    """El primero que mira la petición: frenar después de identificar,
    auditar y leer el cuerpo sería hacer todo el trabajo que se quería
    evitar. Ver `servicios/frenos.py`."""

    async def capa(scope, receive, send):
        peticion = Peticion(scope)
        if frenos.demasiado_grande(peticion):
            await _enviar(JSONResponse(
                {"error": f"El envío supera los {frenos.MAXIMO_MB} MB."}, 413), send)
            return
        if frenos.excede(peticion):
            await _enviar(JSONResponse(
                {"error": "Demasiadas peticiones seguidas. Esperá un momento."}, 429,
                headers={"Retry-After": str(frenos.VENTANA_SEGUNDOS)}), send)
            return
        await app(scope, receive, send)

    return capa


def guardado(app):
    """Después de cada petición, lo que cambió en memoria va a Firestore.

    Se guarda **antes** de mandar la respuesta, como antes: cuando la
    pantalla recibe el «listo», el dato ya está en la base. Si la petición
    se cayó no se guarda: no terminó. Ver `servicios/persistencia.py`.
    """

    async def capa(scope, receive, send):
        mensajes = []

        async def juntar(mensaje):
            mensajes.append(mensaje)

        await app(scope, receive, juntar)
        if persistencia.activo():
            await sync_to_async(persistencia.guardar_cambios, thread_sensitive=False)()
        for mensaje in mensajes:
            await send(mensaje)

    return capa


def ip_para_la_auditoria(app):
    """Deja la petición a mano de `servicios/auditoria.registrar`, que anota
    la IP: sin esto, cada ruta tendría que recibirla y pasarla."""

    async def capa(scope, receive, send):
        marca = auditoria.peticion_actual.set(Peticion(scope))
        try:
            await app(scope, receive, send)
        finally:
            auditoria.peticion_actual.reset(marca)

    return capa


# Portado de `starlette.middleware.cors.CORSMiddleware` con la configuración
# del campus: el origen del frontend, todos los métodos, todas las cabeceras,
# sin credenciales.
METODOS = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")


def cors(app, origenes: list[str]):
    previas = {
        "vary": "Origin",
        "access-control-allow-methods": ", ".join(METODOS),
        "access-control-max-age": "600",
    }

    async def capa(scope, receive, send):
        cabeceras = Cabeceras(scope.get("headers") or [])
        origen = cabeceras.get("origin")
        if origen is None:
            await app(scope, receive, send)
            return

        # La consulta previa del navegador, antes de un pedido «no simple»
        if scope["method"] == "OPTIONS" and "access-control-request-method" in cabeceras:
            salida = dict(previas)
            fallas = []
            if origen in origenes:
                salida["access-control-allow-origin"] = origen
            else:
                fallas.append("origin")
            if cabeceras["access-control-request-method"] not in METODOS:
                fallas.append("method")
            pedidas = cabeceras.get("access-control-request-headers")
            if pedidas is not None:
                salida["access-control-allow-headers"] = pedidas
            if fallas:
                await _enviar(PlainTextResponse("Disallowed CORS " + ", ".join(fallas), 400, salida), send)
            else:
                await _enviar(PlainTextResponse("OK", 200, salida), send)
            return

        async def con_cors(mensaje):
            if mensaje["type"] == "http.response.start" and origen in origenes:
                lista = list(mensaje.get("headers") or [])
                lista = [(k, v) for k, v in lista if k.lower() != b"access-control-allow-origin"] + [
                    (b"access-control-allow-origin", origen.encode("latin-1"))
                ]
                vary = next((v for k, v in lista if k.lower() == b"vary"), None)
                nuevo = (vary.decode("latin-1") + ", Origin") if vary else "Origin"
                lista = [(k, v) for k, v in lista if k.lower() != b"vary"] + [(b"vary", nuevo.encode("latin-1"))]
                mensaje = {**mensaje, "headers": lista}
            await send(mensaje)

        await app(scope, receive, con_cors)

    return capa


def errores_de_las_rutas(app):
    """Los errores que lanzan las rutas, como los espera el frontend:
    `{"error": "..."}` en castellano. Va por dentro de CORS, así que un 404
    también lleva sus cabeceras."""

    async def capa(scope, receive, send):
        empezo = False

        async def enviar(mensaje):
            nonlocal empezo
            if mensaje["type"] == "http.response.start":
                empezo = True
            await send(mensaje)

        try:
            await app(scope, receive, enviar)
        except HTTPException as error:
            if empezo:
                raise
            detalle = error.detail
            if error.status_code == 404 and detalle == "Not Found":
                detalle = "Ruta no encontrada"
            await _enviar(JSONResponse({"error": detalle}, error.status_code), send)
        except ErrorDeValidacion:
            if empezo:
                raise
            await _enviar(JSONResponse({"error": "Los datos enviados no son válidos"}, 400), send)

    return capa


# ===================== El arranque =====================
def con_arranque(app):
    """El `lifespan`: lo que corre una sola vez al levantar y al cerrar."""

    async def servidor(scope, receive, send):
        if scope["type"] != "lifespan":
            await app(scope, receive, send)
            return
        while True:
            mensaje = await receive()
            if mensaje["type"] == "lifespan.startup":
                try:
                    main.al_arrancar()
                except Exception as error:  # noqa: BLE001
                    await send({"type": "lifespan.startup.failed", "message": repr(error)})
                    raise
                await send({"type": "lifespan.startup.complete"})
            elif mensaje["type"] == "lifespan.shutdown":
                main.al_cerrar()
                await send({"type": "lifespan.shutdown.complete"})
                return

    return servidor


def armar(django=None):
    """El campus entero: las capas, en orden, con Django en el centro."""
    django = django or get_asgi_application()
    origenes = [os.environ.get("FRONTEND_URL") or "http://localhost:5173"]
    adentro = errores_de_las_rutas(django)
    adentro = cors(adentro, origenes)
    adentro = ip_para_la_auditoria(adentro)
    adentro = guardado(adentro)
    adentro = freno(adentro)
    adentro = errores_500(adentro)
    return con_arranque(adentro)


aplicacion = armar()
