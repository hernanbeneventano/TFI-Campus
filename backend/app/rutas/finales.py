"""Finales: mesas de examen, inscripción del alumno y sus resultados.

Es la mitad del alumno del apartado Finales; la de la cátedra está en
`rutas/gestion_finales.py`.

Las vistas de Django delegan en estas funciones y en
`servicios/finales_alumno.py`. Las pruebas de concurrencia también ejercitan
las funciones de servicio directamente.
"""

from __future__ import annotations


from ..servicios import finales_alumno as servicio



def listar_mesas(yo: int ):
    return servicio.listar_mesas(yo)


def proximas(yo: int ):
    return servicio.proximas(yo)


def resultados(yo: int ):
    return servicio.resultados(yo)


def inscribirse(id_mesa: int, yo: int ):
    return servicio.inscribirse(id_mesa, yo)


def cancelar(id_mesa: int, yo: int ):
    return servicio.cancelar(id_mesa, yo)
