"""Explicit Django views for module gestion_modulo."""

from __future__ import annotations

import typing
from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.urls import path, re_path
from app.rutas import gestion_modulo as operaciones_gestion_modulo
from app.servicios.autenticacion import identificar, identificar_id
from campus_django.respuestas import json_respuesta, metodo_no_permitido
from campus_django.validacion import OBLIGATORIO, convertir, cuerpo as leer_cuerpo, parametro

def _op_gestion_modulo_0_0(request, id_curso):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_gestion_modulo.crear_carpeta(id_curso=id_curso, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_gestion_modulo_0(request, id_curso):
    if request.method == 'POST':
        return _op_gestion_modulo_0_0(request, id_curso)
    return metodo_no_permitido(('POST',))

def _op_gestion_modulo_1_0(request, id_curso, id_carpeta):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    resultado = operaciones_gestion_modulo.editar_carpeta(id_curso=id_curso, id_carpeta=id_carpeta, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_gestion_modulo_1_1(request, id_curso, id_carpeta):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    resultado = operaciones_gestion_modulo.borrar_carpeta(id_curso=id_curso, id_carpeta=id_carpeta, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_1(request, id_curso, id_carpeta):
    if request.method == 'PATCH':
        return _op_gestion_modulo_1_0(request, id_curso, id_carpeta)
    if request.method == 'DELETE':
        return _op_gestion_modulo_1_1(request, id_curso, id_carpeta)
    return metodo_no_permitido(('DELETE', 'PATCH'))

def _op_gestion_modulo_2_0(request, id_curso, id_carpeta):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    resultado = operaciones_gestion_modulo.mover_carpeta(id_curso=id_curso, id_carpeta=id_carpeta, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_2(request, id_curso, id_carpeta):
    if request.method == 'POST':
        return _op_gestion_modulo_2_0(request, id_curso, id_carpeta)
    return metodo_no_permitido(('POST',))

def _op_gestion_modulo_3_0(request, id_curso, id_carpeta):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    resultado = operaciones_gestion_modulo.crear_item(id_curso=id_curso, id_carpeta=id_carpeta, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_gestion_modulo_3(request, id_curso, id_carpeta):
    if request.method == 'POST':
        return _op_gestion_modulo_3_0(request, id_curso, id_carpeta)
    return metodo_no_permitido(('POST',))

def _op_gestion_modulo_4_0(request, id_curso, id_carpeta, id_item):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    id_item = convertir(id_item, str)
    resultado = operaciones_gestion_modulo.editar_item(id_curso=id_curso, id_carpeta=id_carpeta, id_item=id_item, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_gestion_modulo_4_1(request, id_curso, id_carpeta, id_item):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    id_item = convertir(id_item, str)
    resultado = operaciones_gestion_modulo.borrar_item(id_curso=id_curso, id_carpeta=id_carpeta, id_item=id_item, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_4(request, id_curso, id_carpeta, id_item):
    if request.method == 'PATCH':
        return _op_gestion_modulo_4_0(request, id_curso, id_carpeta, id_item)
    if request.method == 'DELETE':
        return _op_gestion_modulo_4_1(request, id_curso, id_carpeta, id_item)
    return metodo_no_permitido(('DELETE', 'PATCH'))

def _op_gestion_modulo_5_0(request, id_curso, id_carpeta, id_item):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    id_item = convertir(id_item, str)
    resultado = operaciones_gestion_modulo.mover_item(id_curso=id_curso, id_carpeta=id_carpeta, id_item=id_item, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_5(request, id_curso, id_carpeta, id_item):
    if request.method == 'POST':
        return _op_gestion_modulo_5_0(request, id_curso, id_carpeta, id_item)
    return metodo_no_permitido(('POST',))

def _op_gestion_modulo_6_0(request, id_curso, id_tarea):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_tarea = convertir(id_tarea, int)
    resultado = operaciones_gestion_modulo.alternar_entrega(id_curso=id_curso, id_tarea=id_tarea, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_6(request, id_curso, id_tarea):
    if request.method == 'POST':
        return _op_gestion_modulo_6_0(request, id_curso, id_tarea)
    return metodo_no_permitido(('POST',))

def _op_gestion_modulo_7_0(request, id_curso):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_gestion_modulo.crear_anuncio(id_curso=id_curso, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_gestion_modulo_7(request, id_curso):
    if request.method == 'POST':
        return _op_gestion_modulo_7_0(request, id_curso)
    return metodo_no_permitido(('POST',))

def _op_gestion_modulo_8_0(request, id_curso, id_anuncio):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_anuncio = convertir(id_anuncio, int)
    resultado = operaciones_gestion_modulo.editar_anuncio(id_curso=id_curso, id_anuncio=id_anuncio, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_gestion_modulo_8_1(request, id_curso, id_anuncio):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_anuncio = convertir(id_anuncio, int)
    resultado = operaciones_gestion_modulo.borrar_anuncio(id_curso=id_curso, id_anuncio=id_anuncio, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_8(request, id_curso, id_anuncio):
    if request.method == 'PATCH':
        return _op_gestion_modulo_8_0(request, id_curso, id_anuncio)
    if request.method == 'DELETE':
        return _op_gestion_modulo_8_1(request, id_curso, id_anuncio)
    return metodo_no_permitido(('DELETE', 'PATCH'))

def _op_gestion_modulo_9_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_gestion_modulo.seguimiento(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_9(request, id_curso):
    if request.method == 'GET':
        return _op_gestion_modulo_9_0(request, id_curso)
    return metodo_no_permitido(('GET',))

def _op_gestion_modulo_10_0(request, id_curso, id_tarea):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_tarea = convertir(id_tarea, int)
    resultado = operaciones_gestion_modulo.entregas_de_tarea(id_curso=id_curso, id_tarea=id_tarea, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_10(request, id_curso, id_tarea):
    if request.method == 'GET':
        return _op_gestion_modulo_10_0(request, id_curso, id_tarea)
    return metodo_no_permitido(('GET',))

def _op_gestion_modulo_11_0(request, id_curso, id_carpeta):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    resultado = operaciones_gestion_modulo.entregas_de_seccion(id_curso=id_curso, id_carpeta=id_carpeta, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_11(request, id_curso, id_carpeta):
    if request.method == 'GET':
        return _op_gestion_modulo_11_0(request, id_curso, id_carpeta)
    return metodo_no_permitido(('GET',))

def _op_gestion_modulo_12_0(request, id_curso):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_gestion_modulo.listar_notas(id_curso=id_curso, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _op_gestion_modulo_12_1(request, id_curso):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_gestion_modulo.guardar_nota(id_curso=id_curso, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_12(request, id_curso):
    if request.method == 'GET':
        return _op_gestion_modulo_12_0(request, id_curso)
    if request.method == 'PUT':
        return _op_gestion_modulo_12_1(request, id_curso)
    return metodo_no_permitido(('GET', 'PUT'))

def _op_gestion_modulo_13_0(request, id_curso):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_gestion_modulo.fijar_cierre(id_curso=id_curso, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_13(request, id_curso):
    if request.method == 'PUT':
        return _op_gestion_modulo_13_0(request, id_curso)
    return metodo_no_permitido(('PUT',))

def _op_gestion_modulo_14_0(request, id_curso, id_tarea):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_tarea = convertir(id_tarea, int)
    resultado = operaciones_gestion_modulo.respuestas_del_cuestionario(id_curso=id_curso, id_tarea=id_tarea, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_14(request, id_curso, id_tarea):
    if request.method == 'GET':
        return _op_gestion_modulo_14_0(request, id_curso, id_tarea)
    return metodo_no_permitido(('GET',))

def _op_gestion_modulo_15_0(request, id_curso, id_carpeta, id_item):
    cuerpo = leer_cuerpo(request, dict, {})
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    id_item = convertir(id_item, str)
    resultado = operaciones_gestion_modulo.subir_archivo_item(id_curso=id_curso, id_carpeta=id_carpeta, id_item=id_item, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _op_gestion_modulo_15_1(request, id_curso, id_carpeta, id_item):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    id_carpeta = convertir(id_carpeta, int)
    id_item = convertir(id_item, str)
    ver = parametro(request, 'ver', bool, False)
    resultado = operaciones_gestion_modulo.descargar_archivo_item(id_curso=id_curso, id_carpeta=id_carpeta, id_item=id_item, ver=ver, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_15(request, id_curso, id_carpeta, id_item):
    if request.method == 'POST':
        return _op_gestion_modulo_15_0(request, id_curso, id_carpeta, id_item)
    if request.method == 'GET':
        return _op_gestion_modulo_15_1(request, id_curso, id_carpeta, id_item)
    return metodo_no_permitido(('GET', 'POST'))

def _op_gestion_modulo_16_0(request, id_curso):
    cuerpo = leer_cuerpo(request, dict, OBLIGATORIO)
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    resultado = operaciones_gestion_modulo.agregar_dia_de_clase(id_curso=id_curso, cuerpo=cuerpo, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=201)

def _vista_gestion_modulo_16(request, id_curso):
    if request.method == 'POST':
        return _op_gestion_modulo_16_0(request, id_curso)
    return metodo_no_permitido(('POST',))

def _op_gestion_modulo_17_0(request, id_curso, dia, desde):
    yo = identificar(request)
    id_curso = convertir(id_curso, int)
    dia = convertir(dia, int)
    desde = convertir(desde, str)
    resultado = operaciones_gestion_modulo.quitar_dia_de_clase(id_curso=id_curso, dia=dia, desde=desde, yo=yo)
    if isinstance(resultado, HttpResponse):
        return resultado
    return json_respuesta(resultado, estado=200)

def _vista_gestion_modulo_17(request, id_curso, dia, desde):
    if request.method == 'DELETE':
        return _op_gestion_modulo_17_0(request, id_curso, dia, desde)
    return metodo_no_permitido(('DELETE',))

urlpatterns = [
    path('api/cursos/<str:id_curso>/carpetas', _vista_gestion_modulo_0),
    path('api/cursos/<str:id_curso>/carpetas/<str:id_carpeta>', _vista_gestion_modulo_1),
    path('api/cursos/<str:id_curso>/carpetas/<str:id_carpeta>/mover', _vista_gestion_modulo_2),
    path('api/cursos/<str:id_curso>/carpetas/<str:id_carpeta>/items', _vista_gestion_modulo_3),
    path('api/cursos/<str:id_curso>/carpetas/<str:id_carpeta>/items/<str:id_item>', _vista_gestion_modulo_4),
    path('api/cursos/<str:id_curso>/carpetas/<str:id_carpeta>/items/<str:id_item>/mover', _vista_gestion_modulo_5),
    path('api/cursos/<str:id_curso>/tareas/<str:id_tarea>/entrega', _vista_gestion_modulo_6),
    path('api/cursos/<str:id_curso>/anuncios', _vista_gestion_modulo_7),
    path('api/cursos/<str:id_curso>/anuncios/<str:id_anuncio>', _vista_gestion_modulo_8),
    path('api/cursos/<str:id_curso>/seguimiento', _vista_gestion_modulo_9),
    path('api/cursos/<str:id_curso>/tareas/<str:id_tarea>/entregas', _vista_gestion_modulo_10),
    path('api/cursos/<str:id_curso>/carpetas/<str:id_carpeta>/entregas', _vista_gestion_modulo_11),
    path('api/cursos/<str:id_curso>/notas', _vista_gestion_modulo_12),
    path('api/cursos/<str:id_curso>/cierre', _vista_gestion_modulo_13),
    path('api/cursos/<str:id_curso>/tareas/<str:id_tarea>/cuestionario', _vista_gestion_modulo_14),
    path('api/cursos/<str:id_curso>/carpetas/<str:id_carpeta>/items/<str:id_item>/archivo', _vista_gestion_modulo_15),
    path('api/cursos/<str:id_curso>/clases', _vista_gestion_modulo_16),
    path('api/cursos/<str:id_curso>/clases/<str:dia>/<str:desde>', _vista_gestion_modulo_17),
]
