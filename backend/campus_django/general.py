"""Rutas nativas de Django para salud, perfil y contadores."""

from __future__ import annotations

import logging

from django.urls import path

from app import datos as d
from app.servicios import general
from app.servicios.autenticacion import identificar
from app.servicios.firestore import verificar_conexion

from .respuestas import error_json, json_respuesta, metodo_no_permitido

logger = logging.getLogger(__name__)

def salud(request):
    if request.method != "GET":
        return metodo_no_permitido(("GET",))

    from app.main import ARRANQUE

    return json_respuesta({"estado": "ok", "app": "CampusTFI", "instancia": ARRANQUE})


def yo_mismo(request):
    if request.method != "GET":
        return metodo_no_permitido(("GET",))
    return json_respuesta(general.yo_mismo(identificar(request)))


def contadores(request):
    if request.method != "GET":
        return metodo_no_permitido(("GET",))
    return json_respuesta(general.contadores(identificar(request)))


def salud_firestore(request):
    if request.method != "GET":
        return metodo_no_permitido(("GET",))
    yo = identificar(request)
    if not d.tiene_rol(yo, "Administrador", "Supervisor"):
        return error_json("Solo la administración del campus puede ver esto", 403)
    try:
        verificar_conexion()
    except Exception:
        logger.exception("No se pudo comprobar la conexión con Firestore")
        return error_json("Firestore no está disponible", 503)
    return json_respuesta({"estado": "ok", "firestore": "conectado"})


urlpatterns = [
    path("api/salud", salud),
    path("api/me", yo_mismo),
    path("api/contadores", contadores),
]
