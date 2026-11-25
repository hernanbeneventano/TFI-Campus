"""El cliente con el que las pruebas le hablan al campus, y quién lo usa.

**Es el único archivo de `pruebas/` que sabe cómo se le habla al servidor.**
Las suites piden el cliente acá y no lo arman por su cuenta.

El cliente es `httpx` con un transporte propio que entrega cada pedido al
servidor del campus (`campus_django/asgi.py`) **en el mismo proceso**, sin
levantar nada: las pruebas también miran la memoria del servidor
—`d.auditoria`, `d.personas`— para comprobar que lo que devuelve una ruta es
lo que de verdad quedó guardado.

Arma cada pedido con el mismo formato de la captura histórica del contrato:
el mismo `host`
(`testserver`), las mismas cabeceras por omisión y el mismo cliente
(`testclient:50000`, que es lo que ven el freno y la auditoría). Si el
servidor se cae, el error llega a la prueba (salvo que se pida lo contrario).

Qué necesita una suite de este archivo:

    from .cliente import como, crear_cliente

    cliente = crear_cliente()
    como(SANTIAGO)
"""

from __future__ import annotations

import io
from urllib.parse import unquote

import httpx
from asgiref.sync import async_to_sync

from app.servicios import autenticacion


class _Transporte(httpx.BaseTransport):
    """Entrega el pedido a una aplicación ASGI y devuelve lo que contesta."""

    def __init__(self, app, relanzar: bool = True) -> None:
        self.app = app
        self.relanzar = relanzar

    def handle_request(self, pedido: httpx.Request) -> httpx.Response:
        esquema = pedido.url.scheme
        lugar = pedido.url.netloc.decode("ascii")
        puerto_comun = {"http": 80, "https": 443}[esquema]
        if ":" in lugar:
            host, puerto = lugar.split(":", 1)
            puerto = int(puerto)
        else:
            host, puerto = lugar, puerto_comun

        cabeceras = [] if "host" in pedido.headers else [(b"host", host.encode())]
        cabeceras += [(k.lower().encode(), v.encode()) for k, v in pedido.headers.multi_items()]

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": pedido.method,
            "path": unquote(pedido.url.path),
            "raw_path": pedido.url.raw_path.split(b"?", 1)[0],
            "root_path": "",
            "scheme": esquema,
            "query_string": pedido.url.query,
            "headers": cabeceras,
            "client": ["testclient", 50000],
            "server": [host, puerto],
            "extensions": {"http.response.debug": {}},
            "state": {},
        }

        cuerpo = pedido.read()
        leido = False
        respuesta: dict = {"stream": io.BytesIO()}
        empezo = False
        terminada = None  # se arma adentro del bucle de eventos del pedido

        def _terminada():
            nonlocal terminada
            if terminada is None:
                import asyncio

                terminada = asyncio.Event()
            return terminada

        async def receive():
            nonlocal leido
            if leido:
                # La desconexión llega recién cuando termina la respuesta. Si
                # llegara antes, Django la toma como un cliente que se fue y
                # descarta la respuesta.
                await _terminada().wait()
                return {"type": "http.disconnect"}
            leido = True
            return {"type": "http.request", "body": cuerpo}

        async def send(mensaje):
            nonlocal empezo
            if mensaje["type"] == "http.response.start":
                respuesta["status_code"] = mensaje["status"]
                respuesta["headers"] = [(k.decode(), v.decode()) for k, v in mensaje.get("headers", [])]
                empezo = True
            elif mensaje["type"] == "http.response.body":
                if pedido.method != "HEAD":
                    respuesta["stream"].write(mensaje.get("body", b""))
                if not mensaje.get("more_body", False):
                    _terminada().set()

        try:
            async_to_sync(self.app)(scope, receive, send)
        except BaseException:
            if self.relanzar:
                raise
        if not empezo:
            respuesta = {"status_code": 500, "headers": [], "stream": io.BytesIO()}
        respuesta["stream"].seek(0)
        salida = httpx.Response(
            status_code=respuesta["status_code"],
            headers=respuesta["headers"],
            stream=httpx.ByteStream(respuesta["stream"].read()),
            request=pedido,
        )
        salida.read()
        return salida


class ClienteDePrueba(httpx.Client):
    """Un `httpx.Client` que le habla al campus en el mismo proceso."""

    def __init__(self, app, raise_server_exceptions: bool = True, follow_redirects: bool = True):
        super().__init__(
            base_url="http://testserver",
            headers={"user-agent": "testclient"},
            transport=_Transporte(app, raise_server_exceptions),
            follow_redirects=follow_redirects,
        )


def crear_cliente(**opciones) -> ClienteDePrueba:
    """Un cliente que le pega al campus sin levantar el servidor.

    Sin el arranque (`lifespan`), a propósito: conectaría Firestore y R2 de
    verdad. Las pruebas trabajan sobre la memoria.
    """
    from campus_django.asgi import aplicacion

    return ClienteDePrueba(aplicacion, **opciones)


def como(persona_id: int | None) -> None:
    """Las siguientes peticiones las hace esa persona.

    `identificar` lo consulta antes de mirar el token, así que no hace falta
    Firebase ni una sesión de verdad para probar quién ve qué.
    """
    autenticacion.actuar_como(persona_id)


def sin_suplantar() -> None:
    """Vuelve a la verificación de siempre."""
    autenticacion.actuar_como(None)
