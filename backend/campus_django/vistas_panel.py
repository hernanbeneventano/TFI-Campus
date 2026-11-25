"""Explicit Django views for module panel."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import panel as operaciones_panel
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_panel_0_0(request):
    yo = identificar(request)
    resultado = operaciones_panel.ver_panel(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_panel_0(request):
    if request.method == 'GET':
        return _op_panel_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_panel_1_0(request):
    yo = identificar(request)
    resultado = operaciones_panel.ver_alertas(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_panel_1(request):
    if request.method == 'GET':
        return _op_panel_1_0(request)
    return metodo_no_permitido(('GET',))

urlpatterns = [
    path('api/panel', _vista_panel_0),
    path('api/panel/alertas', _vista_panel_1),
]
