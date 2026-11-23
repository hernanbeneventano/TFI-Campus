"""Quién soy y las campanitas del menú, atendidos por Django.

Llaman a las mismas funciones que FastAPI (`servicios/general`).
"""

from __future__ import annotations

from django.urls import path

from app.servicios import general

from .adaptadores import con_sesion, responder, rutas


@con_sesion
def yo_mismo(request, yo):
    return responder(general.yo_mismo(yo))


@con_sesion
def contadores(request, yo):
    return responder(general.contadores(yo))


urlpatterns = [
    path("api/me", rutas(get=yo_mismo)),
    path("api/contadores", rutas(get=contadores)),
]
