"""El panel de control de la institución.

Dos consultas y nada más: los números con sus distribuciones, y las alertas.
Es de **solo lectura**: todo lo que se ve acá se resuelve en la pantalla a la
que lleva cada alerta, no desde el panel. Un tablero que además escribe
termina siendo una copia de las otras pantallas.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import datos as d
from ..servicios import auditoria, panel as p
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/panel", tags=["Panel"])


def _exigir_acceso(yo: dict) -> None:
    if not p.es_supervisor(yo):
        raise HTTPException(
            403, "El panel de control es para la administración y la supervisión"
        )


@router.get("", summary="Los números y las distribuciones de la institución")
def ver_panel(yo: dict = UsuarioActual):
    """Todo en una sola consulta.

    Son ocho cuentas chicas sobre datos que ya están en memoria: partirlo en
    cinco llamadas solo multiplicaría los estados de carga de la pantalla.
    """
    _exigir_acceso(yo)

    return {
        "indicadores": p.indicadores(),
        "distribuciones": p.distribuciones(),
        "proximos": p._proximos_examenes()[:6],
        # La actividad reciente sale del registro central de auditoría, no de
        # una lista aparte: es el mismo dato mirado desde el panel.
        "actividad": [
            auditoria.con_nombres(e)
            for e in auditoria.buscar({}, None if p.es_administrador(yo) else
                                      {"academico", "asistencias", "calificaciones",
                                       "finales", "biblioteca", "modulos"})[:8]
        ],
        "esAdministrador": p.es_administrador(yo),
    }


@router.get("/alertas", summary="Lo que hay que atender")
def ver_alertas(yo: dict = UsuarioActual):
    """Cada alerta dice qué pasa, cuántos son y adónde ir a resolverlo.

    Las que no tienen nada que atender no vienen: un tablero lleno de ceros en
    verde enseña a no mirarlo.
    """
    _exigir_acceso(yo)
    lista = p.alertas(yo)

    return {
        "alertas": lista,
        "cuantas": sum(a["cantidad"] for a in lista),
        "urgentes": sum(a["cantidad"] for a in lista if a["nivel"] == "alta"),
    }
