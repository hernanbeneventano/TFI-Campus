"""Calendario académico: entregas, exámenes, clases y eventos de un rango.

La vista nativa de Django delega en `servicios/calendario.del_rango`.
"""

from __future__ import annotations


from ..servicios import calendario



def listar_calendario(
    desde: str | None = None, hasta: str | None = None, yo: dict = None
):
    return calendario.del_rango(yo, desde, hasta)
