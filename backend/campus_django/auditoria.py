"""El registro de auditoría, atendido por Django.

Las vistas leen los parámetros y llaman a las mismas funciones que FastAPI
(`servicios/consulta_auditoria`): los permisos, los filtros, la paginación y
la exportación están una sola vez.
"""

from __future__ import annotations

from django.urls import path

from app.servicios import consulta_auditoria as consulta

from .adaptadores import con_sesion, descargar, entero, parametros, responder, rutas


@con_sesion
def opciones(request, yo):
    return responder(consulta.opciones(yo))


@con_sesion
def mis_materias(request, yo):
    return responder(consulta.mis_materias(yo, parametros(request)))


@con_sesion
def exportar(request, yo):
    archivo = consulta.exportar(yo, parametros(request))
    return descargar(archivo.contenido, archivo.tipo, archivo.cabeceras)


@con_sesion
def listar(request, yo):
    return responder(consulta.listar(yo, parametros(request)))


@con_sesion
def ver(request, yo, id_evento):
    return responder(consulta.ver(yo, entero(id_evento)))


# Las de nombre fijo antes que /<id>, como en FastAPI
urlpatterns = [
    path("api/auditoria", rutas(get=listar)),
    path("api/auditoria/opciones", rutas(get=opciones)),
    path("api/auditoria/mis-materias", rutas(get=mis_materias)),
    path("api/auditoria/exportar", rutas(get=exportar)),
    path("api/auditoria/<str:id_evento>", rutas(get=ver)),
]
