"""Explicit Django views for module cursos."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import cursos as operaciones_cursos
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_cursos_0_0(request):
    yo = identificar(request)
    resultado = operaciones_cursos.listar_cursos(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_cursos_0(request):
    if request.method == 'GET':
        return _op_cursos_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_cursos_1_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_cursos.obtener_curso(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_cursos_1(request, id_curso):
    if request.method == 'GET':
        return _op_cursos_1_0(request, id_curso)
    return metodo_no_permitido(('GET',))

def _op_cursos_2_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_cursos.obtener_modulo(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_cursos_2(request, id_curso):
    if request.method == 'GET':
        return _op_cursos_2_0(request, id_curso)
    return metodo_no_permitido(('GET',))

def _op_cursos_3_0(request, id_curso, id_item):
    cuerpo = leer_cuerpo(request, dict, {})
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_item = convertir(id_item, str)
    resultado = operaciones_cursos.publicar_en_tablero(id_curso=id_curso, id_item=id_item, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_cursos_3(request, id_curso, id_item):
    if request.method == 'POST':
        return _op_cursos_3_0(request, id_curso, id_item)
    return metodo_no_permitido(('POST',))

def _op_cursos_4_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_cursos.alternar_favorito(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_cursos_4(request, id_curso):
    if request.method == 'POST':
        return _op_cursos_4_0(request, id_curso)
    return metodo_no_permitido(('POST',))

urlpatterns = [
    path('api/cursos', _vista_cursos_0),
    path('api/cursos/<str:id_curso>', _vista_cursos_1),
    path('api/cursos/<str:id_curso>/modulo', _vista_cursos_2),
    path('api/cursos/<str:id_curso>/tableros/<str:id_item>/publicaciones', _vista_cursos_3),
    path('api/cursos/<str:id_curso>/favorito', _vista_cursos_4),
]
