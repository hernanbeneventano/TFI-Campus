"""Inscripción a materias: el plan de estudios del alumno y su avance.

Las vistas nativas de Django delegan en estas funciones y en
`servicios/inscripcion_materias.py`.
"""

from __future__ import annotations


from ..servicios import inscripcion_materias as servicio



def listar_materias(yo: int ):
    return servicio.listar_materias(yo)


def inscribirse(id_materia: int, yo: int ):
    return servicio.inscribirse(id_materia, yo)


def dar_de_baja(id_materia: int, yo: int ):
    return servicio.dar_de_baja(id_materia, yo)
