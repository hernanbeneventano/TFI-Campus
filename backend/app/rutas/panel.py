"""El panel de control de la institución.

Dos consultas y nada más: los números con sus distribuciones, y las alertas.
Es de **solo lectura**: todo lo que se ve acá se resuelve en la pantalla a la
que lleva cada alerta, no desde el panel. Un tablero que además escribe
termina siendo una copia de las otras pantallas.

**Lo atiende Django** (`campus_django/panel.py`, ver `MIGRADOS` en
`despachador.py`). Estas rutas quedan para volver atrás sin tocar código:
sacando el prefijo de `MIGRADOS` las vuelve a atender FastAPI. Las dos llaman
a las mismas funciones de `servicios/panel.py`.
"""

from __future__ import annotations

from ..web import APIRouter

from ..servicios import panel as p
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/panel", tags=["Panel"])


@router.get("", summary="Los números y las distribuciones de la institución")
def ver_panel(yo: dict = UsuarioActual):
    return p.tablero(yo)


@router.get("/alertas", summary="Lo que hay que atender")
def ver_alertas(yo: dict = UsuarioActual):
    return p.resumen_de_alertas(yo)
