"""Finales, la mitad del alumno, atendida por Django.

Llama a las mismas funciones que FastAPI (`servicios/finales_alumno`): el
estado de cada mesa, las correlativas para rendir y el candado de los cupos
están una sola vez. La gestión docente (`/api/finales/gestion/...`) sigue en
FastAPI.
"""

from __future__ import annotations

from django.urls import path

from app.servicios import finales_alumno as servicio

from .adaptadores import con_sesion, entero, responder, rutas


@con_sesion
def listar_mesas(request, yo):
    return responder(servicio.listar_mesas(yo["id"]))


@con_sesion
def proximas(request, yo):
    return responder(servicio.proximas(yo["id"]))


@con_sesion
def resultados(request, yo):
    return responder(servicio.resultados(yo["id"]))


@con_sesion
def inscribirse(request, yo, id_mesa):
    return responder(servicio.inscribirse(entero(id_mesa), yo["id"]), estado=201)


@con_sesion
def cancelar(request, yo, id_mesa):
    return responder(servicio.cancelar(entero(id_mesa), yo["id"]))


urlpatterns = [
    path("api/finales/mesas", rutas(get=listar_mesas)),
    path("api/finales/proximas", rutas(get=proximas)),
    path("api/finales/resultados", rutas(get=resultados)),
    path("api/finales/mesas/<str:id_mesa>/inscripcion", rutas(post=inscribirse, delete=cancelar)),
]
