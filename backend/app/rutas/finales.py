"""Finales: mesas de examen, inscripción del alumno y sus resultados.

Es la mitad del alumno del apartado Finales; la de la cátedra está en
`rutas/gestion_finales.py`.

**Lo atiende Django** (`campus_django/finales.py`, ver `MIGRADOS` en
`despachador.py`). Estas rutas quedan para volver atrás sin tocar código. Las
cinco llaman a las mismas funciones de `servicios/finales_alumno.py`, con la
misma firma de siempre (las pruebas de concurrencia las llaman así).
"""

from __future__ import annotations

from ..web import APIRouter

from ..servicios import finales_alumno as servicio
from ..servicios.autenticacion import IdUsuarioActual

router = APIRouter(prefix="/api/finales", tags=["Finales"])


@router.get("/mesas", summary="Las mesas de examen y en qué situación está el alumno")
def listar_mesas(yo: int = IdUsuarioActual):
    return servicio.listar_mesas(yo)


@router.get("/proximas", summary="Las próximas mesas, en orden cronológico")
def proximas(yo: int = IdUsuarioActual):
    return servicio.proximas(yo)


@router.get("/resultados", summary="El historial de finales del alumno")
def resultados(yo: int = IdUsuarioActual):
    return servicio.resultados(yo)


@router.post(
    "/mesas/{id_mesa}/inscripcion",
    status_code=201,
    summary="Inscribirse a una mesa de examen",
)
def inscribirse(id_mesa: int, yo: int = IdUsuarioActual):
    return servicio.inscribirse(id_mesa, yo)


@router.delete("/mesas/{id_mesa}/inscripcion", summary="Dar de baja la inscripción")
def cancelar(id_mesa: int, yo: int = IdUsuarioActual):
    return servicio.cancelar(id_mesa, yo)
