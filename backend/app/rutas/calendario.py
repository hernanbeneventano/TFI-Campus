"""Calendario académico: entregas, exámenes, clases y eventos de un rango.

**Lo atiende Django** (`campus_django/calendario.py`, ver `MIGRADOS` en
`despachador.py`). Esta ruta queda para volver atrás sin tocar código:
sacando el prefijo de `MIGRADOS` la vuelve a atender FastAPI. Las dos llaman
a la misma función, `servicios/calendario.del_rango`.
"""

from __future__ import annotations

from ..web import APIRouter

from ..servicios import calendario
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/calendario", tags=["Calendario"])


@router.get("", summary="Todo lo que pasa entre dos fechas")
def listar_calendario(
    desde: str | None = None, hasta: str | None = None, yo: dict = UsuarioActual
):
    return calendario.del_rango(yo, desde, hasta)
