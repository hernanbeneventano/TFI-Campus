"""Respuesta Django para caminos desconocidos.

Conserva el comportamiento público acordado:

1. **Si la ruta existe con la barra final cambiada**, un 307 hacia esa ruta:
   `/api/cursos/` lleva a `/api/cursos`. Django por omisión hace otra cosa
   —agrega la barra, con 301— y solo si está `CommonMiddleware`.
2. **Si no**, un 404 con `{"error": "Ruta no encontrada"}`.

La dirección del 307 usa la cabecera `host` si viene, si no el servidor, y
conserva la consulta. El cuerpo va vacío, con `content-length: 0` y sin
`content-type`.
"""

from __future__ import annotations

from urllib.parse import quote

from django.http import HttpResponse
from django.urls import Resolver404, resolve

from .respuestas import error_json


def _existe(camino: str) -> bool:
    try:
        resolve(camino)
    except Resolver404:
        return False
    return True


def _direccion(request, camino: str) -> str:
    """Construye la dirección absoluta de la redirección."""
    esquema = request.scheme
    direccion = f"{esquema}://{request.get_host()}{camino}"
    consulta = request.META.get("QUERY_STRING", "")
    if consulta:
        direccion += "?" + consulta
    return direccion


def no_encontrada(request, exception=None):
    del exception
    # Probar con la barra final cambiada —sacándola si está, agregándola si
    # no— y redirigir si así existe la ruta.
    camino = request.path
    if camino != "/":
        otro = camino.rstrip("/") if camino.endswith("/") else camino + "/"
        if _existe(otro):
            respuesta = HttpResponse(content=b"", status=307)
            del respuesta["Content-Type"]
            respuesta["content-length"] = "0"
            respuesta["location"] = quote(_direccion(request, otro), safe=":/%#?=@[]!$&'()*+,;")
            return respuesta

    return error_json("Ruta no encontrada", 404)
