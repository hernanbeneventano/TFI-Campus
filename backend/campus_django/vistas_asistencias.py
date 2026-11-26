"""Explicit Django views for module asistencias."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import asistencias as operaciones_asistencias
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_asistencias_0_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_asistencias.ver_planificacion(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_asistencias_0_1(request, id_curso):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_asistencias.guardar_planificacion(id_curso=id_curso, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_asistencias_0(request, id_curso):
    if request.method == 'GET':
        return _op_asistencias_0_0(request, id_curso)
    if request.method == 'PUT':
        return _op_asistencias_0_1(request, id_curso)
    return metodo_no_permitido(('GET', 'PUT'))

def _op_asistencias_1_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_asistencias.listar_clases(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_asistencias_1_1(request, id_curso):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_asistencias.crear_clase(id_curso=id_curso, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_asistencias_1(request, id_curso):
    if request.method == 'GET':
        return _op_asistencias_1_0(request, id_curso)
    if request.method == 'POST':
        return _op_asistencias_1_1(request, id_curso)
    return metodo_no_permitido(('GET', 'POST'))

def _op_asistencias_2_0(request, id_curso, id_clase):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_clase = convertir(id_clase, int)
    resultado = operaciones_asistencias.ver_clase(id_curso=id_curso, id_clase=id_clase, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_asistencias_2_1(request, id_curso, id_clase):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_clase = convertir(id_clase, int)
    resultado = operaciones_asistencias.guardar_lista(id_curso=id_curso, id_clase=id_clase, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_asistencias_2(request, id_curso, id_clase):
    if request.method == 'GET':
        return _op_asistencias_2_0(request, id_curso, id_clase)
    if request.method == 'PUT':
        return _op_asistencias_2_1(request, id_curso, id_clase)
    return metodo_no_permitido(('GET', 'PUT'))

def _op_asistencias_3_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_asistencias.asistencia_por_alumno(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_asistencias_3(request, id_curso):
    if request.method == 'GET':
        return _op_asistencias_3_0(request, id_curso)
    return metodo_no_permitido(('GET',))

def _op_asistencias_4_0(request):
    yo = identificar(request)
    resultado = operaciones_asistencias.mi_situacion(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_asistencias_4(request):
    if request.method == 'GET':
        return _op_asistencias_4_0(request)
    return metodo_no_permitido(('GET',))

def _op_asistencias_5_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_asistencias.mi_detalle(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_asistencias_5(request, id_curso):
    if request.method == 'GET':
        return _op_asistencias_5_0(request, id_curso)
    return metodo_no_permitido(('GET',))

def _op_asistencias_6_0(request):
    yo = identificar(request)
    resultado = operaciones_asistencias.listar_justificaciones(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_asistencias_6_1(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_asistencias.pedir_justificacion(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_asistencias_6(request):
    if request.method == 'GET':
        return _op_asistencias_6_0(request)
    if request.method == 'POST':
        return _op_asistencias_6_1(request)
    return metodo_no_permitido(('GET', 'POST'))

def _op_asistencias_7_0(request, id_justificacion):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_justificacion = convertir(id_justificacion, int)
    resultado = operaciones_asistencias.resolver_justificacion(id_justificacion=id_justificacion, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_asistencias_7(request, id_justificacion):
    if request.method == 'PUT':
        return _op_asistencias_7_0(request, id_justificacion)
    return metodo_no_permitido(('PUT',))

def _op_asistencias_8_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_asistencias.historial(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_asistencias_8(request, id_curso):
    if request.method == 'GET':
        return _op_asistencias_8_0(request, id_curso)
    return metodo_no_permitido(('GET',))

urlpatterns = [
    path('api/cursos/<str:id_curso>/asistencias/planificacion', _vista_asistencias_0),
    path('api/cursos/<str:id_curso>/asistencias/clases', _vista_asistencias_1),
    path('api/cursos/<str:id_curso>/asistencias/clases/<str:id_clase>', _vista_asistencias_2),
    path('api/cursos/<str:id_curso>/asistencias/alumnos', _vista_asistencias_3),
    path('api/asistencias/mi-situacion', _vista_asistencias_4),
    path('api/cursos/<str:id_curso>/asistencias/mi-detalle', _vista_asistencias_5),
    path('api/asistencias/justificaciones', _vista_asistencias_6),
    path('api/asistencias/justificaciones/<str:id_justificacion>', _vista_asistencias_7),
    path('api/cursos/<str:id_curso>/asistencias/historial', _vista_asistencias_8),
]
