"""Explicit Django views for module tareas."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import tareas as operaciones_tareas
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_tareas_0_0(request):
    yo = identificar(request)
    resultado = operaciones_tareas.listar_pendientes(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_tareas_0(request):
    if request.method == 'GET':
        return _op_tareas_0_0(request)
    return metodo_no_permitido(('GET',))

urlpatterns = [
    path('api/tareas/pendientes', _vista_tareas_0),
]
