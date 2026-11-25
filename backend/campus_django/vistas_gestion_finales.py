"""Explicit Django views for module gestion_finales."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import gestion_finales as operaciones_gestion_finales
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_gestion_finales_0_0(request):
    yo = identificar(request)
    resultado = operaciones_gestion_finales.opciones(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_finales_0(request):
    if request.method == 'GET':
        return _op_gestion_finales_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_gestion_finales_1_0(request):
    yo = identificar(request)
    materiaId = parametro(request, 'materiaId', int | None, None)
    resultado = operaciones_gestion_finales.listar_mesas(yo=yo, materiaId=materiaId)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_gestion_finales_1_1(request):
    cuerpo = leer_cuerpo(request, dict[str, typing.Any], {})
    yo = identificar(request)
    resultado = operaciones_gestion_finales.crear_mesa(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_gestion_finales_1(request):
    if request.method == 'GET':
        return _op_gestion_finales_1_0(request)
    if request.method == 'POST':
        return _op_gestion_finales_1_1(request)
    return metodo_no_permitido(('GET', 'POST'))

def _op_gestion_finales_2_0(request):
    yo = identificar(request)
    materiaId = parametro(request, 'materiaId', int | None, None)
    mesaId = parametro(request, 'mesaId', int | None, None)
    comision = parametro(request, 'comision', str | None, None)
    resultado = operaciones_gestion_finales.listar_inscriptos(yo=yo, materiaId=materiaId, mesaId=mesaId, comision=comision)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_finales_2(request):
    if request.method == 'GET':
        return _op_gestion_finales_2_0(request)
    return metodo_no_permitido(('GET',))

def _op_gestion_finales_3_0(request, id_mesa):
    yo = identificar(request)
    id_mesa = convertir(id_mesa, int)
    resultado = operaciones_gestion_finales.obtener_mesa(id_mesa=id_mesa, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_gestion_finales_3_1(request, id_mesa):
    cuerpo = leer_cuerpo(request, dict[str, typing.Any], {})
    yo = identificar(request)
    id_mesa = convertir(id_mesa, int)
    resultado = operaciones_gestion_finales.editar_mesa(id_mesa=id_mesa, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_finales_3(request, id_mesa):
    if request.method == 'GET':
        return _op_gestion_finales_3_0(request, id_mesa)
    if request.method == 'PUT':
        return _op_gestion_finales_3_1(request, id_mesa)
    return metodo_no_permitido(('GET', 'PUT'))

def _op_gestion_finales_4_0(request, id_mesa):
    cuerpo = leer_cuerpo(request, dict[str, typing.Any], {})
    yo = identificar(request)
    id_mesa = convertir(id_mesa, int)
    resultado = operaciones_gestion_finales.cancelar_mesa(id_mesa=id_mesa, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_finales_4(request, id_mesa):
    if request.method == 'POST':
        return _op_gestion_finales_4_0(request, id_mesa)
    return metodo_no_permitido(('POST',))

def _op_gestion_finales_5_0(request, id_mesa):
    cuerpo = leer_cuerpo(request, dict[str, typing.Any], {})
    yo = identificar(request)
    id_mesa = convertir(id_mesa, int)
    resultado = operaciones_gestion_finales.guardar_resultados(id_mesa=id_mesa, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_finales_5(request, id_mesa):
    if request.method == 'PUT':
        return _op_gestion_finales_5_0(request, id_mesa)
    return metodo_no_permitido(('PUT',))

def _op_gestion_finales_6_0(request, id_mesa):
    yo = identificar(request)
    id_mesa = convertir(id_mesa, int)
    resultado = operaciones_gestion_finales.cerrar_acta(id_mesa=id_mesa, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_finales_6(request, id_mesa):
    if request.method == 'POST':
        return _op_gestion_finales_6_0(request, id_mesa)
    return metodo_no_permitido(('POST',))

urlpatterns = [
    path('api/finales/gestion/opciones', _vista_gestion_finales_0),
    path('api/finales/gestion/mesas', _vista_gestion_finales_1),
    path('api/finales/gestion/inscriptos', _vista_gestion_finales_2),
    path('api/finales/gestion/mesas/<str:id_mesa>', _vista_gestion_finales_3),
    path('api/finales/gestion/mesas/<str:id_mesa>/cancelar', _vista_gestion_finales_4),
    path('api/finales/gestion/mesas/<str:id_mesa>/resultados', _vista_gestion_finales_5),
    path('api/finales/gestion/mesas/<str:id_mesa>/cerrar-acta', _vista_gestion_finales_6),
]
