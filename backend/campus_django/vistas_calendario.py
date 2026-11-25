"""Explicit Django views for module calendario."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import calendario as operaciones_calendario
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_calendario_0_0(request):
    yo = identificar(request)
    desde = parametro(request, 'desde', str | None, None)
    hasta = parametro(request, 'hasta', str | None, None)
    resultado = operaciones_calendario.listar_calendario(desde=desde, hasta=hasta, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_calendario_0(request):
    if request.method == 'GET':
        return _op_calendario_0_0(request)
    return metodo_no_permitido(('GET',))

urlpatterns = [
    path('api/calendario', _vista_calendario_0),
]
