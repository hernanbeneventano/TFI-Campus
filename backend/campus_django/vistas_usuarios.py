"""Explicit Django views for module usuarios."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import usuarios as operaciones_usuarios
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_usuarios_0_0(request):
    yo = identificar(request)
    resultado = operaciones_usuarios.mi_perfil(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_usuarios_0_1(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_usuarios.editar_mi_perfil(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_usuarios_0(request):
    if request.method == 'GET':
        return _op_usuarios_0_0(request)
    if request.method == 'PUT':
        return _op_usuarios_0_1(request)
    return metodo_no_permitido(('GET', 'PUT'))

def _op_usuarios_1_0(request):
    yo = identificar(request)
    resultado = operaciones_usuarios.mi_acceso(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_usuarios_1(request):
    if request.method == 'GET':
        return _op_usuarios_1_0(request)
    return metodo_no_permitido(('GET',))

def _op_usuarios_2_0(request):
    yo = identificar(request)
    resultado = operaciones_usuarios.cerrar_mis_sesiones(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_usuarios_2(request):
    if request.method == 'POST':
        return _op_usuarios_2_0(request)
    return metodo_no_permitido(('POST',))

def _op_usuarios_3_0(request):
    yo = identificar(request)
    q = parametro(request, 'q', str | None, None)
    rol = parametro(request, 'rol', str | None, None)
    resultado = operaciones_usuarios.listar(yo=yo, q=q, rol=rol)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_usuarios_3_1(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_usuarios.crear(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_usuarios_3(request):
    if request.method == 'GET':
        return _op_usuarios_3_0(request)
    if request.method == 'POST':
        return _op_usuarios_3_1(request)
    return metodo_no_permitido(('GET', 'POST'))

def _op_usuarios_4_0(request):
    yo = identificar(request)
    resultado = operaciones_usuarios.historial(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_usuarios_4(request):
    if request.method == 'GET':
        return _op_usuarios_4_0(request)
    return metodo_no_permitido(('GET',))

def _op_usuarios_5_0(request, id_persona):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_persona = convertir(id_persona, int)
    resultado = operaciones_usuarios.administrar(id_persona=id_persona, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_usuarios_5(request, id_persona):
    if request.method == 'PATCH':
        return _op_usuarios_5_0(request, id_persona)
    return metodo_no_permitido(('PATCH',))

def _op_usuarios_6_0(request, id_persona):
    yo = identificar(request)
    id_persona = convertir(id_persona, int)
    resultado = operaciones_usuarios.restablecer_contrasena(id_persona=id_persona, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_usuarios_6(request, id_persona):
    if request.method == 'POST':
        return _op_usuarios_6_0(request, id_persona)
    return metodo_no_permitido(('POST',))

def _op_usuarios_7_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_usuarios.subir_mi_foto(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_usuarios_7_1(request):
    yo = identificar(request)
    resultado = operaciones_usuarios.quitar_mi_foto(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_usuarios_7(request):
    if request.method == 'POST':
        return _op_usuarios_7_0(request)
    if request.method == 'DELETE':
        return _op_usuarios_7_1(request)
    return metodo_no_permitido(('DELETE', 'POST'))

def _op_usuarios_8_0(request, id_persona):
    id_persona = convertir(id_persona, int)
    f = parametro(request, 'f', str, '')
    resultado = operaciones_usuarios.ver_foto(id_persona=id_persona, f=f)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_usuarios_8(request, id_persona):
    if request.method == 'GET':
        return _op_usuarios_8_0(request, id_persona)
    return metodo_no_permitido(('GET',))

urlpatterns = [
    path('api/usuarios/yo', _vista_usuarios_0),
    path('api/usuarios/yo/acceso', _vista_usuarios_1),
    path('api/usuarios/yo/cerrar-sesiones', _vista_usuarios_2),
    path('api/usuarios', _vista_usuarios_3),
    path('api/usuarios/historial', _vista_usuarios_4),
    path('api/usuarios/<str:id_persona>', _vista_usuarios_5),
    path('api/usuarios/<str:id_persona>/contrasena', _vista_usuarios_6),
    path('api/usuarios/yo/foto', _vista_usuarios_7),
    path('api/usuarios/<str:id_persona>/foto', _vista_usuarios_8),
]
