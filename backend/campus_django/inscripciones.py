"""La inscripción a materias, atendida por Django.

Llama a las mismas funciones que FastAPI (`servicios/inscripcion_materias`):
correlatividades, cupo, período, el candado de los cupos y el módulo que se
crea o se borra están una sola vez.
"""

from __future__ import annotations

from django.urls import path

from app.servicios import inscripcion_materias as servicio

from .adaptadores import con_sesion, entero, responder, rutas


@con_sesion
def listar(request, yo):
    return responder(servicio.listar_materias(yo["id"]))


@con_sesion
def inscribirse(request, yo, id_materia):
    return responder(servicio.inscribirse(entero(id_materia), yo["id"]), estado=201)


@con_sesion
def dar_de_baja(request, yo, id_materia):
    return responder(servicio.dar_de_baja(entero(id_materia), yo["id"]))


urlpatterns = [
    path("api/inscripciones/materias", rutas(get=listar)),
    path("api/inscripciones/materias/<str:id_materia>", rutas(post=inscribirse, delete=dar_de_baja)),
]
