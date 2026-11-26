"""Tareas pendientes y atrasadas.

Las vistas de Django delegan en estas funciones y en
`servicios/tareas.pendientes_de`.

Las rutas de entrega `/api/tareas/{id}/...` también están registradas
explícitamente en el URLconf de Django.
"""

from __future__ import annotations


from ..servicios import tareas



def listar_pendientes(yo: dict ):
    return tareas.pendientes_de(yo)
