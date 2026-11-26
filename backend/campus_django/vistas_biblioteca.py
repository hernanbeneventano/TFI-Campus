"""Explicit Django views for module biblioteca."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import biblioteca as operaciones_biblioteca
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_biblioteca_0_0(request):
    yo = identificar(request)
    resultado = operaciones_biblioteca.opciones_biblioteca(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_0(request):
    if request.method == 'GET':
        return _op_biblioteca_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_biblioteca_1_0(request):
    yo = identificar(request)
    resultado = operaciones_biblioteca.mis_aportes(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_1(request):
    if request.method == 'GET':
        return _op_biblioteca_1_0(request)
    return metodo_no_permitido(('GET',))

def _op_biblioteca_2_0(request):
    yo = identificar(request)
    resultado = operaciones_biblioteca.pendientes(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_2(request):
    if request.method == 'GET':
        return _op_biblioteca_2_0(request)
    return metodo_no_permitido(('GET',))

def _op_biblioteca_3_0(request):
    yo = identificar(request)
    resultado = operaciones_biblioteca.obtener_favoritos(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_3(request):
    if request.method == 'GET':
        return _op_biblioteca_3_0(request)
    return metodo_no_permitido(('GET',))

def _op_biblioteca_4_0(request):
    yo = identificar(request)
    request = request
    resultado = async_to_sync(operaciones_biblioteca.listar_materiales)(request=request, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_biblioteca_4_1(request):
    cuerpo = leer_cuerpo(request, dict[str, typing.Any], {})
    yo = identificar(request)
    resultado = operaciones_biblioteca.crear_material(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_biblioteca_4(request):
    if request.method == 'GET':
        return _op_biblioteca_4_0(request)
    if request.method == 'POST':
        return _op_biblioteca_4_1(request)
    return metodo_no_permitido(('GET', 'POST'))

def _op_biblioteca_5_0(request, id_material):
    cuerpo = leer_cuerpo(request, dict[str, typing.Any], {})
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = operaciones_biblioteca.subir_archivo(id_material=id_material, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _op_biblioteca_5_1(request, id_material):
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = operaciones_biblioteca.descargar_archivo(id_material=id_material, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_5(request, id_material):
    if request.method == 'POST':
        return _op_biblioteca_5_0(request, id_material)
    if request.method == 'GET':
        return _op_biblioteca_5_1(request, id_material)
    return metodo_no_permitido(('GET', 'POST'))

def _op_biblioteca_6_0(request, id_material):
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = operaciones_biblioteca.aprobar_material(id_material=id_material, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_6(request, id_material):
    if request.method == 'POST':
        return _op_biblioteca_6_0(request, id_material)
    return metodo_no_permitido(('POST',))

def _op_biblioteca_7_0(request, id_material):
    cuerpo = leer_cuerpo(request, dict[str, typing.Any], {})
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = operaciones_biblioteca.rechazar_material(id_material=id_material, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_7(request, id_material):
    if request.method == 'POST':
        return _op_biblioteca_7_0(request, id_material)
    return metodo_no_permitido(('POST',))

def _op_biblioteca_8_0(request, id_material):
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = operaciones_biblioteca.agregar_favorito(id_material=id_material, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _op_biblioteca_8_1(request, id_material):
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = operaciones_biblioteca.quitar_favorito(id_material=id_material, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_8(request, id_material):
    if request.method == 'POST':
        return _op_biblioteca_8_0(request, id_material)
    if request.method == 'DELETE':
        return _op_biblioteca_8_1(request, id_material)
    return metodo_no_permitido(('DELETE', 'POST'))

def _op_biblioteca_9_0(request, id_material):
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = async_to_sync(operaciones_biblioteca.obtener_material)(id_material=id_material, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_biblioteca_9_1(request, id_material):
    cuerpo = leer_cuerpo(request, dict[str, typing.Any], {})
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = operaciones_biblioteca.editar_material(id_material=id_material, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_biblioteca_9_2(request, id_material):
    yo = identificar(request)
    id_material = convertir(id_material, str)
    resultado = operaciones_biblioteca.borrar_material(id_material=id_material, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_biblioteca_9(request, id_material):
    if request.method == 'GET':
        return _op_biblioteca_9_0(request, id_material)
    if request.method == 'PATCH':
        return _op_biblioteca_9_1(request, id_material)
    if request.method == 'DELETE':
        return _op_biblioteca_9_2(request, id_material)
    return metodo_no_permitido(('DELETE', 'GET', 'PATCH'))

urlpatterns = [
    path('api/biblioteca/opciones', _vista_biblioteca_0),
    path('api/biblioteca/mis-aportes', _vista_biblioteca_1),
    path('api/biblioteca/pendientes', _vista_biblioteca_2),
    path('api/biblioteca/favoritos', _vista_biblioteca_3),
    path('api/biblioteca', _vista_biblioteca_4),
    re_path(r'^api/biblioteca/(?P<id_material>.*)/archivo$', _vista_biblioteca_5),
    re_path(r'^api/biblioteca/(?P<id_material>.*)/aprobar$', _vista_biblioteca_6),
    re_path(r'^api/biblioteca/(?P<id_material>.*)/rechazar$', _vista_biblioteca_7),
    re_path(r'^api/biblioteca/(?P<id_material>.*)/favorito$', _vista_biblioteca_8),
    re_path(r'^api/biblioteca/(?P<id_material>.*)$', _vista_biblioteca_9),
]
