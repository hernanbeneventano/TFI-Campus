"""El panel de control de la institución, atendido por Django.

Las dos vistas llaman a las mismas funciones que FastAPI
(`servicios/panel.tablero` y `resumen_de_alertas`): la lógica y el control de
acceso están una sola vez.
"""

from __future__ import annotations

from django.urls import path

from app.servicios import panel

from .adaptadores import con_sesion, responder, rutas


@con_sesion
def ver_panel(request, yo):
    return responder(panel.tablero(yo))


@con_sesion
def ver_alertas(request, yo):
    return responder(panel.resumen_de_alertas(yo))


urlpatterns = [
    path("api/panel", rutas(get=ver_panel)),
    path("api/panel/alertas", rutas(get=ver_alertas)),
]
