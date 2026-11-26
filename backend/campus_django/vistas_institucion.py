"""Explicit Django views for module institucion."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import institucion as operaciones_institucion
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_institucion_0_0(request):
    yo = identificar(request)
    resultado = operaciones_institucion.catalogo(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_0(request):
    if request.method == 'GET':
        return _op_institucion_0_0(request)
    return metodo_no_permitido(('GET',))

def _op_institucion_1_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.crear_carrera(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_institucion_1(request):
    if request.method == 'POST':
        return _op_institucion_1_0(request)
    return metodo_no_permitido(('POST',))

def _op_institucion_2_0(request, id_carrera):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_carrera = convertir(id_carrera, int)
    resultado = operaciones_institucion.editar_carrera(id_carrera=id_carrera, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_2_1(request, id_carrera):
    yo = identificar(request)
    id_carrera = convertir(id_carrera, int)
    resultado = operaciones_institucion.borrar_carrera(id_carrera=id_carrera, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_2(request, id_carrera):
    if request.method == 'PATCH':
        return _op_institucion_2_0(request, id_carrera)
    if request.method == 'DELETE':
        return _op_institucion_2_1(request, id_carrera)
    return metodo_no_permitido(('DELETE', 'PATCH'))

def _op_institucion_3_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.crear_sede(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_institucion_3(request):
    if request.method == 'POST':
        return _op_institucion_3_0(request)
    return metodo_no_permitido(('POST',))

def _op_institucion_4_0(request, id_sede):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_sede = convertir(id_sede, int)
    resultado = operaciones_institucion.editar_sede(id_sede=id_sede, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_4_1(request, id_sede):
    yo = identificar(request)
    id_sede = convertir(id_sede, int)
    resultado = operaciones_institucion.borrar_sede(id_sede=id_sede, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_4(request, id_sede):
    if request.method == 'PATCH':
        return _op_institucion_4_0(request, id_sede)
    if request.method == 'DELETE':
        return _op_institucion_4_1(request, id_sede)
    return metodo_no_permitido(('DELETE', 'PATCH'))

def _op_institucion_5_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.crear_plan(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_institucion_5(request):
    if request.method == 'POST':
        return _op_institucion_5_0(request)
    return metodo_no_permitido(('POST',))

def _op_institucion_6_0(request, id_plan):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_plan = convertir(id_plan, int)
    resultado = operaciones_institucion.editar_plan(id_plan=id_plan, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_6_1(request, id_plan):
    yo = identificar(request)
    id_plan = convertir(id_plan, int)
    resultado = operaciones_institucion.borrar_plan(id_plan=id_plan, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_6(request, id_plan):
    if request.method == 'PATCH':
        return _op_institucion_6_0(request, id_plan)
    if request.method == 'DELETE':
        return _op_institucion_6_1(request, id_plan)
    return metodo_no_permitido(('DELETE', 'PATCH'))

def _op_institucion_7_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.crear_comision(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_institucion_7(request):
    if request.method == 'POST':
        return _op_institucion_7_0(request)
    return metodo_no_permitido(('POST',))

def _op_institucion_8_0(request, id_comision):
    yo = identificar(request)
    id_comision = convertir(id_comision, int)
    resultado = operaciones_institucion.ver_comision(id_comision=id_comision, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_8_1(request, id_comision):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_comision = convertir(id_comision, int)
    resultado = operaciones_institucion.editar_comision(id_comision=id_comision, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_8_2(request, id_comision):
    yo = identificar(request)
    id_comision = convertir(id_comision, int)
    resultado = operaciones_institucion.borrar_comision(id_comision=id_comision, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_8(request, id_comision):
    if request.method == 'GET':
        return _op_institucion_8_0(request, id_comision)
    if request.method == 'PATCH':
        return _op_institucion_8_1(request, id_comision)
    if request.method == 'DELETE':
        return _op_institucion_8_2(request, id_comision)
    return metodo_no_permitido(('DELETE', 'GET', 'PATCH'))

def _op_institucion_9_0(request, id_comision, id_materia):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_comision = convertir(id_comision, int)
    id_materia = convertir(id_materia, int)
    resultado = operaciones_institucion.configurar_dictado(id_comision=id_comision, id_materia=id_materia, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_9_1(request, id_comision, id_materia):
    yo = identificar(request)
    id_comision = convertir(id_comision, int)
    id_materia = convertir(id_materia, int)
    resultado = operaciones_institucion.quitar_dictado(id_comision=id_comision, id_materia=id_materia, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_9(request, id_comision, id_materia):
    if request.method == 'PUT':
        return _op_institucion_9_0(request, id_comision, id_materia)
    if request.method == 'DELETE':
        return _op_institucion_9_1(request, id_comision, id_materia)
    return metodo_no_permitido(('DELETE', 'PUT'))

def _op_institucion_10_0(request):
    yo = identificar(request)
    carreraId = parametro(request, 'carreraId', int | None, None)
    sedeId = parametro(request, 'sedeId', int | None, None)
    comisionId = parametro(request, 'comisionId', int | None, None)
    sinComision = parametro(request, 'sinComision', bool, False)
    q = parametro(request, 'q', str | None, None)
    resultado = operaciones_institucion.asignaciones(yo=yo, carreraId=carreraId, sedeId=sedeId, comisionId=comisionId, sinComision=sinComision, q=q)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_10_1(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.crear_asignacion(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_institucion_10(request):
    if request.method == 'GET':
        return _op_institucion_10_0(request)
    if request.method == 'POST':
        return _op_institucion_10_1(request)
    return metodo_no_permitido(('GET', 'POST'))

def _op_institucion_11_0(request):
    yo = identificar(request)
    carreraId = parametro(request, 'carreraId', int | None, None)
    resultado = operaciones_institucion.legajo_siguiente(carreraId=carreraId, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_11(request):
    if request.method == 'GET':
        return _op_institucion_11_0(request)
    return metodo_no_permitido(('GET',))

def _op_institucion_12_0(request, id_asociacion):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_asociacion = convertir(id_asociacion, int)
    resultado = operaciones_institucion.editar_asignacion(id_asociacion=id_asociacion, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_12_1(request, id_asociacion):
    yo = identificar(request)
    id_asociacion = convertir(id_asociacion, int)
    resultado = operaciones_institucion.borrar_asignacion(id_asociacion=id_asociacion, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_12(request, id_asociacion):
    if request.method == 'PATCH':
        return _op_institucion_12_0(request, id_asociacion)
    if request.method == 'DELETE':
        return _op_institucion_12_1(request, id_asociacion)
    return metodo_no_permitido(('DELETE', 'PATCH'))

def _op_institucion_13_0(request):
    yo = identificar(request)
    resultado = operaciones_institucion.historial(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_13(request):
    if request.method == 'GET':
        return _op_institucion_13_0(request)
    return metodo_no_permitido(('GET',))

def _op_institucion_14_0(request):
    yo = identificar(request)
    resultado = operaciones_institucion.ver_configuracion(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_14(request):
    if request.method == 'GET':
        return _op_institucion_14_0(request)
    return metodo_no_permitido(('GET',))

def _op_institucion_15_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.cambiar_periodo(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_15(request):
    if request.method == 'PUT':
        return _op_institucion_15_0(request)
    return metodo_no_permitido(('PUT',))

def _op_institucion_16_0(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.cambiar_asistencia(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_16(request):
    if request.method == 'PUT':
        return _op_institucion_16_0(request)
    return metodo_no_permitido(('PUT',))

def _op_institucion_17_0(request):
    yo = identificar(request)
    resultado = operaciones_institucion.listar_eventos(yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_17_1(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.crear_evento(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_institucion_17(request):
    if request.method == 'GET':
        return _op_institucion_17_0(request)
    if request.method == 'POST':
        return _op_institucion_17_1(request)
    return metodo_no_permitido(('GET', 'POST'))

def _op_institucion_18_0(request, id_evento):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_evento = convertir(id_evento, int)
    resultado = operaciones_institucion.editar_evento(id_evento=id_evento, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_18_1(request, id_evento):
    yo = identificar(request)
    id_evento = convertir(id_evento, int)
    resultado = operaciones_institucion.borrar_evento(id_evento=id_evento, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_18(request, id_evento):
    if request.method == 'PUT':
        return _op_institucion_18_0(request, id_evento)
    if request.method == 'DELETE':
        return _op_institucion_18_1(request, id_evento)
    return metodo_no_permitido(('DELETE', 'PUT'))

def _op_institucion_19_0(request):
    yo = identificar(request)
    q = parametro(request, 'q', str | None, None)
    carreraId = parametro(request, 'carreraId', int | None, None)
    planId = parametro(request, 'planId', int | None, None)
    anio = parametro(request, 'anio', int | None, None)
    estado = parametro(request, 'estado', str | None, None)
    orden = parametro(request, 'orden', str | None, None)
    resultado = operaciones_institucion.listar_materias(yo=yo, q=q, carreraId=carreraId, planId=planId, anio=anio, estado=estado, orden=orden)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_19_1(request):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    resultado = operaciones_institucion.crear_materia(cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_institucion_19(request):
    if request.method == 'GET':
        return _op_institucion_19_0(request)
    if request.method == 'POST':
        return _op_institucion_19_1(request)
    return metodo_no_permitido(('GET', 'POST'))

def _op_institucion_20_0(request, id_materia):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_materia = convertir(id_materia, int)
    resultado = operaciones_institucion.editar_materia(id_materia=id_materia, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_institucion_20_1(request, id_materia):
    yo = identificar(request)
    id_materia = convertir(id_materia, int)
    resultado = operaciones_institucion.borrar_materia(id_materia=id_materia, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_institucion_20(request, id_materia):
    if request.method == 'PATCH':
        return _op_institucion_20_0(request, id_materia)
    if request.method == 'DELETE':
        return _op_institucion_20_1(request, id_materia)
    return metodo_no_permitido(('DELETE', 'PATCH'))

urlpatterns = [
    path('api/institucion', _vista_institucion_0),
    path('api/institucion/carreras', _vista_institucion_1),
    path('api/institucion/carreras/<str:id_carrera>', _vista_institucion_2),
    path('api/institucion/sedes', _vista_institucion_3),
    path('api/institucion/sedes/<str:id_sede>', _vista_institucion_4),
    path('api/institucion/planes', _vista_institucion_5),
    path('api/institucion/planes/<str:id_plan>', _vista_institucion_6),
    path('api/institucion/comisiones', _vista_institucion_7),
    path('api/institucion/comisiones/<str:id_comision>', _vista_institucion_8),
    path('api/institucion/comisiones/<str:id_comision>/materias/<str:id_materia>', _vista_institucion_9),
    path('api/institucion/asignaciones', _vista_institucion_10),
    path('api/institucion/legajo-siguiente', _vista_institucion_11),
    path('api/institucion/asignaciones/<str:id_asociacion>', _vista_institucion_12),
    path('api/institucion/historial', _vista_institucion_13),
    path('api/institucion/configuracion', _vista_institucion_14),
    path('api/institucion/configuracion/periodo', _vista_institucion_15),
    path('api/institucion/configuracion/asistencia', _vista_institucion_16),
    path('api/institucion/eventos', _vista_institucion_17),
    path('api/institucion/eventos/<str:id_evento>', _vista_institucion_18),
    path('api/institucion/materias', _vista_institucion_19),
    path('api/institucion/materias/<str:id_materia>', _vista_institucion_20),
]
