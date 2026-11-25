"""El registro de auditoría: consultarlo y exportarlo.

**No hay POST, ni PUT, ni DELETE.** Es a propósito: los eventos los escribe
`servicios/auditoria.registrar` desde cada módulo, y desde afuera el registro
solo se lee. Que no exista la ruta es más fuerte que prohibirla.

Las vistas nativas de Django delegan en estas funciones y en
`servicios/consulta_auditoria.py`.
"""

from __future__ import annotations

from campus_django.respuestas import descargar
from django.http import HttpRequest as Request

from ..servicios import consulta_auditoria as consulta



# ===================== Rutas con nombre fijo =====================
# Antes de /{id}, si no "opciones" se tomaría como el id de un evento.


def opciones(yo: dict ):
    return consulta.opciones(yo)


def mis_materias(request: Request, yo: dict ):
    return consulta.mis_materias(yo, request.GET.dict())


def exportar(request: Request, yo: dict ):
    archivo = consulta.exportar(yo, request.GET.dict())
    return descargar(archivo.contenido, archivo.tipo, archivo.cabeceras)


# ===================== El registro =====================
def listar(request: Request, yo: dict ):
    return consulta.listar(yo, request.GET.dict())


def ver(id_evento: int, yo: dict ):
    return consulta.ver(yo, id_evento)
