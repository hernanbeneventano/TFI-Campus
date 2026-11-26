"""El panel de control de la institución.

Dos consultas y nada más: los números con sus distribuciones, y las alertas.
Es de **solo lectura**: todo lo que se ve acá se resuelve en la pantalla a la
que lleva cada alerta, no desde el panel. Un tablero que además escribe
termina siendo una copia de las otras pantallas.

Las vistas de Django delegan en estas funciones y en
`servicios/panel.py`.
"""

from __future__ import annotations


from ..servicios import panel as p



def ver_panel(yo: dict ):
    return p.tablero(yo)


def ver_alertas(yo: dict ):
    return p.resumen_de_alertas(yo)
