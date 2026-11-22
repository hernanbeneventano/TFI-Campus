"""El calendario académico, atendido por Django.

Lee los parámetros como FastAPI y llama a la misma función que él
(`servicios/calendario.del_rango`): la lógica no está copiada, está una vez.
"""

from __future__ import annotations

from django.urls import path

from app.servicios import calendario

from .adaptadores import con_sesion, consulta, responder, rutas


@con_sesion
def listar(request, yo):
    desde = consulta(request, "desde", str | None, None)
    hasta = consulta(request, "hasta", str | None, None)
    return responder(calendario.del_rango(yo, desde, hasta))


urlpatterns = [
    path("api/calendario", rutas(get=listar)),
]
