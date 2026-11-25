"""Lo que contesta Django cuando no encuentra la ruta.

Lo mismo que contestaba FastAPI antes de la migración, que son dos cosas:

1. **Si la ruta existe con la barra final cambiada**, un 307 hacia esa ruta:
   `/api/cursos/` lleva a `/api/cursos`. Django por omisión hace otra cosa
   —agrega la barra, con 301— y solo si está `CommonMiddleware`.
2. **Si no**, un 404 con `{"error": "Ruta no encontrada"}`.

La dirección del 307 se arma como la armaba Starlette (`URL(scope=...)`): con
la cabecera `host` si viene, si no con el servidor, y la consulta tal cual. El
cuerpo va vacío, con `content-length: 0` y sin `content-type`.
"""

from __future__ import annotations

from urllib.parse import quote

from django.http import HttpResponse
from django.urls import Resolver404, resolve

from app.web import HTTPException


def _existe(camino: str) -> bool:
    try:
        resolve(camino)
    except Resolver404:
        return False
    return True


def _direccion(scope: dict, camino: str) -> str:
    """La dirección absoluta hacia `camino`, como `starlette.datastructures.URL`."""
    esquema = scope.get("scheme", "http")
    servidor = scope.get("server")
    host = next((v.decode("latin-1") for k, v in scope.get("headers") or [] if k == b"host"), None)
    if host is not None:
        direccion = f"{esquema}://{host}{camino}"
    elif servidor is None:
        direccion = camino
    else:
        nombre, puerto = servidor
        if puerto == {"http": 80, "https": 443}.get(esquema):
            direccion = f"{esquema}://{nombre}{camino}"
        else:
            direccion = f"{esquema}://{nombre}:{puerto}{camino}"
    consulta = scope.get("query_string") or b""
    if consulta:
        direccion += "?" + consulta.decode()
    return direccion


def no_encontrada(request, exception=None):
    # Probar con la barra final cambiada —sacándola si está, agregándola si
    # no— y redirigir si así existe la ruta.
    camino = request.scope.get("path", request.path)
    if camino != "/":
        otro = camino.rstrip("/") if camino.endswith("/") else camino + "/"
        if _existe(otro):
            respuesta = HttpResponse(content=b"", status=307)
            del respuesta["Content-Type"]
            respuesta["content-length"] = "0"
            respuesta["location"] = quote(_direccion(request.scope, otro), safe=":/%#?=@[]!$&'()*+,;")
            return respuesta

    # Sin detalle es «Not Found», y las capas del campus lo traducen a
    # «Ruta no encontrada» (ver `campus_django/asgi.py`).
    raise HTTPException(status_code=404)
