"""Los archivos del campus, atendidos por Django.

Llama a las mismas funciones que FastAPI (`servicios/acceso_archivos`): los
permisos de cada carpeta del bucket, las firmas y la validación están una
sola vez.

Los caminos van con `re_path` y **las mismas expresiones que arma
Starlette**, no con los conversores de Django: `{o:path}` de Starlette acepta
un camino vacío (`.*`) y `<path:o>` de Django no (`.+`). Con los conversores,
`/api/archivos/firma/` caería al 404 general («Ruta no encontrada») en vez de
contestar desde la ruta («No se encontró el archivo»), como hoy.

`ver` es **pública**, igual que en FastAPI: una etiqueta `<img>` no manda la
sesión, así que la credencial es la dirección firmada. Es una de las vistas
que la prueba de los adaptadores acepta sin `con_sesion`.
"""

from __future__ import annotations

from django.urls import path, re_path

from app.servicios import acceso_archivos as servicio

from .adaptadores import con_sesion, cuerpo, descargar, responder, rutas


@con_sesion
def estado(request, yo):
    return responder(servicio.estado(yo))


@con_sesion
def pedir_enlace(request, yo):
    return responder(servicio.pedir_enlace(cuerpo(request), yo))


@con_sesion
def confirmar(request, yo):
    return responder(servicio.confirmar(cuerpo(request), yo))


@con_sesion
def enlace(request, yo, objeto):
    return responder(servicio.enlace(objeto, yo))


def ver(request, f, o):
    archivo = servicio.ver(f, o)
    return descargar(archivo.contenido, archivo.tipo, archivo.cabeceras)


# En el mismo orden que FastAPI: `/enlace` antes que el camino libre
VER = r"^api/archivos/(?P<f>[^/]+)/(?P<o>.*)$"
urlpatterns = [
    path("api/archivos/estado", rutas(get=estado)),
    path("api/archivos/enlace-de-subida", rutas(post=pedir_enlace)),
    path("api/archivos/confirmar", rutas(post=confirmar)),
    re_path(r"^api/archivos/(?P<objeto>.*)/enlace$", rutas(get=enlace)),
    re_path(VER, rutas(get=ver)),
]
