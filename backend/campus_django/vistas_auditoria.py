"""Explicit Django views for module auditoria."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import auditoria as operaciones_auditoria
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_auditoria_0_0(request):
    yo = identificar(request)
    resultado = operaciones_auditoria.opciones(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_auditoria_0(request):
    if request.method == 'GET':
        return _op_auditoria_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_auditoria_1_0(request):
    yo = identificar(request)
    request = request
    resultado = operaciones_auditoria.mis_materias(request=request, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_auditoria_1(request):
    if request.method == 'GET':
        return _op_auditoria_1_0(request)
    return metodo_no_permitido(('GET',))

def _op_auditoria_2_0(request):
    yo = identificar(request)
    request = request
    resultado = operaciones_auditoria.exportar(request=request, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_auditoria_2(request):
    if request.method == 'GET':
        return _op_auditoria_2_0(request)
    return metodo_no_permitido(('GET',))

def _op_auditoria_3_0(request):
    yo = identificar(request)
    request = request
    resultado = operaciones_auditoria.listar(request=request, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_auditoria_3(request):
    if request.method == 'GET':
        return _op_auditoria_3_0(request)
    return metodo_no_permitido(('GET',))

def _op_auditoria_4_0(request, id_evento):
    yo = identificar(request)
    id_evento = convertir(id_evento, int)
    resultado = operaciones_auditoria.ver(id_evento=id_evento, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_auditoria_4(request, id_evento):
    if request.method == 'GET':
        return _op_auditoria_4_0(request, id_evento)
    return metodo_no_permitido(('GET',))

urlpatterns = [
    path('api/auditoria/opciones', _vista_auditoria_0),
    path('api/auditoria/mis-materias', _vista_auditoria_1),
    path('api/auditoria/exportar', _vista_auditoria_2),
    path('api/auditoria', _vista_auditoria_3),
    path('api/auditoria/<str:id_evento>', _vista_auditoria_4),
]
