"""Tareas pendientes y atrasadas.

**Lo atiende Django** (`campus_django/tareas.py`, ver `MIGRADOS_EXACTOS` en
`despachador.py`). Esta ruta queda para volver atrás sin tocar código. Las dos
llaman a la misma función, `servicios/tareas.pendientes_de`.

Ojo con el prefijo: `/api/tareas/{id}/...` es de `mi_cursada`, que sigue en
FastAPI. Por eso esta ruta se migra por su camino **exacto**, no por prefijo.
"""

from __future__ import annotations

from ..web import APIRouter

from ..servicios import tareas
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/tareas", tags=["Tareas"])


@router.get("/pendientes", summary="Tareas sin entregar, próximas y atrasadas")
def listar_pendientes(yo: dict = UsuarioActual):
    return tareas.pendientes_de(yo)
