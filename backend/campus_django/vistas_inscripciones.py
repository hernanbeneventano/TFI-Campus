"""Explicit Django views for module inscripciones."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import inscripciones as operaciones_inscripciones
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_inscripciones_0_0(request):
    yo = identificar_id(request)
    resultado = operaciones_inscripciones.listar_materias(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_inscripciones_0(request):
    if request.method == 'GET':
        return _op_inscripciones_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_inscripciones_1_0(request, id_materia):
    yo = identificar_id(request)
    id_materia = convertir(id_materia, int)
    resultado = operaciones_inscripciones.inscribirse(id_materia=id_materia, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _op_inscripciones_1_1(request, id_materia):
    yo = identificar_id(request)
    id_materia = convertir(id_materia, int)
    resultado = operaciones_inscripciones.dar_de_baja(id_materia=id_materia, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_inscripciones_1(request, id_materia):
    if request.method == 'POST':
        return _op_inscripciones_1_0(request, id_materia)
    if request.method == 'DELETE':
        return _op_inscripciones_1_1(request, id_materia)
    return metodo_no_permitido(('DELETE', 'POST'))

urlpatterns = [
    path('api/inscripciones/materias', _vista_inscripciones_0),
    path('api/inscripciones/materias/<str:id_materia>', _vista_inscripciones_1),
]
