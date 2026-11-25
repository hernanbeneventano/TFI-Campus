"""Explicit Django views for module mi_cursada."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import mi_cursada as operaciones_mi_cursada
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_mi_cursada_0_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_mi_cursada.mis_notas(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_mi_cursada_0(request, id_curso):
    if request.method == 'GET':
        return _op_mi_cursada_0_0(request, id_curso)
    return metodo_no_permitido(('GET',))

def _op_mi_cursada_1_0(request, id_tarea):
    yo = identificar(request)
    id_tarea = convertir(id_tarea, int)
    resultado = operaciones_mi_cursada.abrir_cuestionario(id_tarea=id_tarea, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_mi_cursada_1(request, id_tarea):
    if request.method == 'GET':
        return _op_mi_cursada_1_0(request, id_tarea)
    return metodo_no_permitido(('GET',))

def _op_mi_cursada_2_0(request):
    yo = identificar(request)
    resultado = operaciones_mi_cursada.ver_mi_progreso(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_mi_cursada_2(request):
    if request.method == 'GET':
        return _op_mi_cursada_2_0(request)
    return metodo_no_permitido(('GET',))

def _op_mi_cursada_3_0(request, id_curso, id_item):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_item = convertir(id_item, str)
    resultado = operaciones_mi_cursada.marcar_visto(id_curso=id_curso, id_item=id_item, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_mi_cursada_3_1(request, id_curso, id_item):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_item = convertir(id_item, str)
    resultado = operaciones_mi_cursada.desmarcar(id_curso=id_curso, id_item=id_item, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_mi_cursada_3(request, id_curso, id_item):
    if request.method == 'PUT':
        return _op_mi_cursada_3_0(request, id_curso, id_item)
    if request.method == 'DELETE':
        return _op_mi_cursada_3_1(request, id_curso, id_item)
    return metodo_no_permitido(('DELETE', 'PUT'))

def _op_mi_cursada_4_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_mi_cursada.importar_progreso(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_mi_cursada_4(request):
    if request.method == 'POST':
        return _op_mi_cursada_4_0(request)
    return metodo_no_permitido(('POST',))

def _op_mi_cursada_5_0(request, id_tarea):
    yo = identificar(request)
    id_tarea = convertir(id_tarea, int)
    resultado = operaciones_mi_cursada.ver_mi_entrega(id_tarea=id_tarea, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_mi_cursada_5_1(request, id_tarea):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_tarea = convertir(id_tarea, int)
    resultado = operaciones_mi_cursada.entregar(id_tarea=id_tarea, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _op_mi_cursada_5_2(request, id_tarea):
    yo = identificar(request)
    id_tarea = convertir(id_tarea, int)
    resultado = operaciones_mi_cursada.retirar_entrega(id_tarea=id_tarea, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_mi_cursada_5(request, id_tarea):
    if request.method == 'GET':
        return _op_mi_cursada_5_0(request, id_tarea)
    if request.method == 'POST':
        return _op_mi_cursada_5_1(request, id_tarea)
    if request.method == 'DELETE':
        return _op_mi_cursada_5_2(request, id_tarea)
    return metodo_no_permitido(('DELETE', 'GET', 'POST'))

def _op_mi_cursada_6_0(request, id_tarea):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_tarea = convertir(id_tarea, int)
    resultado = operaciones_mi_cursada.responder(id_tarea=id_tarea, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_mi_cursada_6(request, id_tarea):
    if request.method == 'POST':
        return _op_mi_cursada_6_0(request, id_tarea)
    return metodo_no_permitido(('POST',))

urlpatterns = [
    path('api/cursos/<str:id_curso>/mis-notas', _vista_mi_cursada_0),
    path('api/tareas/<str:id_tarea>/cuestionario', _vista_mi_cursada_1),
    path('api/mi-progreso', _vista_mi_cursada_2),
    path('api/cursos/<str:id_curso>/mi-progreso/<str:id_item>', _vista_mi_cursada_3),
    path('api/mi-progreso/importar', _vista_mi_cursada_4),
    path('api/tareas/<str:id_tarea>/mi-entrega', _vista_mi_cursada_5),
    path('api/tareas/<str:id_tarea>/respuestas', _vista_mi_cursada_6),
]
