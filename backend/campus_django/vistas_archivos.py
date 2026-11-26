"""Explicit Django views for module archivos."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import archivos as operaciones_archivos
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_archivos_0_0(request):
    yo = identificar(request)
    resultado = operaciones_archivos.estado(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_archivos_0(request):
    if request.method == 'GET':
        return _op_archivos_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_archivos_1_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_archivos.pedir_enlace(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_archivos_1(request):
    if request.method == 'POST':
        return _op_archivos_1_0(request)
    return metodo_no_permitido(('POST',))

def _op_archivos_2_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_archivos.confirmar(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_archivos_2(request):
    if request.method == 'POST':
        return _op_archivos_2_0(request)
    return metodo_no_permitido(('POST',))

def _op_archivos_3_0(request, objeto):
    yo = identificar(request)
    objeto = convertir(objeto, str)
    resultado = operaciones_archivos.enlace(objeto=objeto, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_archivos_3(request, objeto):
    if request.method == 'GET':
        return _op_archivos_3_0(request, objeto)
    return metodo_no_permitido(('GET',))

def _op_archivos_4_0(request, f, o):
    f = convertir(f, str)
    o = convertir(o, str)
    resultado = operaciones_archivos.ver(f=f, o=o)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_archivos_4(request, f, o):
    if request.method == 'GET':
        return _op_archivos_4_0(request, f, o)
    return metodo_no_permitido(('GET',))

urlpatterns = [
    path('api/archivos/estado', _vista_archivos_0),
    path('api/archivos/enlace-de-subida', _vista_archivos_1),
    path('api/archivos/confirmar', _vista_archivos_2),
    re_path(r'^api/archivos/(?P<objeto>.*)/enlace$', _vista_archivos_3),
    re_path(r'^api/archivos/(?P<f>[^/]+)/(?P<o>.*)$', _vista_archivos_4),
]
