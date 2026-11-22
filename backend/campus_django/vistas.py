"""Lo que contesta Django cuando no encuentra la ruta.

Tiene que ser exactamente lo que contesta FastAPI, que son dos cosas:

1. **Si la ruta existe con la barra final cambiada**, un 307 hacia esa ruta.
   FastAPI lo hace solo (`redirect_slashes` de Starlette): `/api/cursos/`
   lleva a `/api/cursos`. Django por omisión hace otra cosa —agrega la barra,
   con 301— y solo si está `CommonMiddleware`.
2. **Si no**, un 404 con `{"error": "Ruta no encontrada"}`.

Ninguna de las dos se imita: se usa el mismo código que usa Starlette. El 307
se arma con su `RedirectResponse` y se copian sus cabeceras tal cual —sin
`content-type`, que Django agrega por omisión y Starlette no—. El 404 se
lanza con la misma excepción que lanza su router, y lo formatea el mismo
manejador del campus (ver `DEBUG_PROPAGATE_EXCEPTIONS` en `settings.py`).
"""

from __future__ import annotations

from django.http import HttpResponse
from django.urls import Resolver404, resolve
from starlette.datastructures import URL
from starlette.exceptions import HTTPException
from starlette.responses import RedirectResponse


def _existe(camino: str) -> bool:
    try:
        resolve(camino)
    except Resolver404:
        return False
    return True


def no_encontrada(request, exception=None):
    # La misma regla que `starlette.routing.Router.app`: probar con la barra
    # final cambiada —sacándola si está, agregándola si no— y redirigir si
    # así existe la ruta.
    camino = request.scope.get("path", request.path)
    if camino != "/":
        otro = camino.rstrip("/") if camino.endswith("/") else camino + "/"
        if _existe(otro):
            destino = dict(request.scope)
            destino["path"] = otro
            de_starlette = RedirectResponse(url=str(URL(scope=destino)))

            respuesta = HttpResponse(content=de_starlette.body, status=de_starlette.status_code)
            del respuesta["Content-Type"]
            for nombre, valor in de_starlette.headers.items():
                respuesta[nombre] = valor
            return respuesta

    # El router de Starlette lanza exactamente esto, con «Not Found» como
    # detalle; el manejador del campus lo traduce a «Ruta no encontrada».
    raise HTTPException(status_code=404)
