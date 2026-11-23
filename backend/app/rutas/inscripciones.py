"""Inscripción a materias: el plan de estudios del alumno y su avance.

**Lo atiende Django** (`campus_django/inscripciones.py`, ver `MIGRADOS` en
`despachador.py`). Estas rutas quedan para volver atrás sin tocar código. Las
tres llaman a las mismas funciones de `servicios/inscripcion_materias.py`,
con la misma firma de siempre (las pruebas de concurrencia las llaman así).
"""

from __future__ import annotations

from fastapi import APIRouter

from ..servicios import inscripcion_materias as servicio
from ..servicios.autenticacion import IdUsuarioActual

router = APIRouter(prefix="/api/inscripciones", tags=["Inscripciones"])


@router.get("/materias", summary="El plan de estudios del alumno, con el estado de cada materia")
def listar_materias(yo: int = IdUsuarioActual):
    return servicio.listar_materias(yo)


@router.post("/materias/{id_materia}", status_code=201, summary="Inscribirse a una materia")
def inscribirse(id_materia: int, yo: int = IdUsuarioActual):
    return servicio.inscribirse(id_materia, yo)


@router.delete("/materias/{id_materia}", summary="Dar de baja la inscripción a una materia")
def dar_de_baja(id_materia: int, yo: int = IdUsuarioActual):
    return servicio.dar_de_baja(id_materia, yo)
