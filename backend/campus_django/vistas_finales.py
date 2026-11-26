"""Explicit Django views for module finales."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import finales as operaciones_finales
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_finales_0_0(request):
    yo = identificar_id(request)
    resultado = operaciones_finales.listar_mesas(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_finales_0(request):
    if request.method == 'GET':
        return _op_finales_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_finales_1_0(request):
    yo = identificar_id(request)
    resultado = operaciones_finales.proximas(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_finales_1(request):
    if request.method == 'GET':
        return _op_finales_1_0(request)
    return metodo_no_permitido(('GET',))

def _op_finales_2_0(request):
    yo = identificar_id(request)
    resultado = operaciones_finales.resultados(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_finales_2(request):
    if request.method == 'GET':
        return _op_finales_2_0(request)
    return metodo_no_permitido(('GET',))

def _op_finales_3_0(request, id_mesa):
    yo = identificar_id(request)
    id_mesa = convertir(id_mesa, int)
    resultado = operaciones_finales.inscribirse(id_mesa=id_mesa, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _op_finales_3_1(request, id_mesa):
    yo = identificar_id(request)
    id_mesa = convertir(id_mesa, int)
    resultado = operaciones_finales.cancelar(id_mesa=id_mesa, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_finales_3(request, id_mesa):
    if request.method == 'POST':
        return _op_finales_3_0(request, id_mesa)
    if request.method == 'DELETE':
        return _op_finales_3_1(request, id_mesa)
    return metodo_no_permitido(('DELETE', 'POST'))

urlpatterns = [
    path('api/finales/mesas', _vista_finales_0),
    path('api/finales/proximas', _vista_finales_1),
    path('api/finales/resultados', _vista_finales_2),
    path('api/finales/mesas/<str:id_mesa>/inscripcion', _vista_finales_3),
]
