"""Las tareas pendientes, atendidas por Django.

Llama a la misma función que FastAPI (`servicios/tareas.pendientes_de`).
Solo esta ruta: el resto de `/api/tareas/...` es de Mi cursada y sigue en
FastAPI (ver `MIGRADOS_EXACTOS` en `despachador.py`).
"""

from __future__ import annotations

from django.urls import path

from app.servicios import tareas

from .adaptadores import con_sesion, responder, rutas


@con_sesion
def pendientes(request, yo):
    return responder(tareas.pendientes_de(yo))


urlpatterns = [
    path("api/tareas/pendientes", rutas(get=pendientes)),
]
