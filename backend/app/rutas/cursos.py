"""Módulos del estudiante y todo el contenido de la pantalla de un módulo."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import datos as d

router = APIRouter(prefix="/api/cursos", tags=["Cursos"])

DIAS = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _cursada_de(curso_id: int) -> list[dict]:
    """El horario semanal del módulo: no aparece en ninguna otra parte de la
    pantalla, hay que ir al calendario para verlo."""
    return [
        {"dia": DIAS[c["dia"]], "desde": c["desde"], "hasta": c["hasta"], "aula": c["aula"]}
        for c in d.clases
        if c["cursoId"] == curso_id
    ]


def _proximas_de(curso_id: int) -> list[dict]:
    """Lo que se viene en este módulo: entregas sin hacer y exámenes, de lo más
    cercano a lo más lejano.

    En las carpetas están, pero hay que abrirlas una por una para enterarse.
    """
    ahora = d.ahora()

    entregas = [
        {"tipo": "entrega", "titulo": t["titulo"], "fecha": t["fechaLimite"], "tareaId": t["id"]}
        for t in d.tareas
        if t["cursoId"] == curso_id
        and not t["entregada"]
        and d.desde_iso(t["fechaLimite"]) >= ahora
    ]

    examenes = [
        {"tipo": "examen", "titulo": e["titulo"], "fecha": e["fecha"], "lugar": e.get("lugar")}
        for e in d.eventos
        if e.get("cursoId") == curso_id
        and e.get("tipo") == "examen"
        and d.desde_iso(e["fecha"]) >= ahora
    ]

    return sorted(entregas + examenes, key=lambda x: d.desde_iso(x["fecha"]))[:4]


@router.get("", summary="Listar los módulos del estudiante")
def listar_cursos():
    # Cada curso viaja con sus novedades, para la campanita de la tarjeta
    return [{**curso, "novedades": d.novedades_de_curso(curso)} for curso in d.cursos]


@router.get("/{id_curso}", summary="Obtener un módulo")
def obtener_curso(id_curso: int):
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")
    return curso


@router.get("/{id_curso}/modulo", summary="Todo el contenido de la pantalla de un módulo")
def obtener_modulo(id_curso: int):
    """El curso, sus carpetas de contenido, los anuncios y la gente inscripta.

    Va en una sola consulta: resolverlo con cuatro multiplicaba los estados
    intermedios de carga en la pantalla.
    """
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")

    return {
        "curso": curso,
        "cursada": _cursada_de(id_curso),
        "proximas": _proximas_de(id_curso),
        "carpetas": d.carpetas_de_curso(curso),
        "anuncios": d.anuncios.get(id_curso) or d.anuncios_genericos(curso),
        # El último acceso y el estado de presencia se calculan ahora
        "participantes": [d.con_presencia(p) for p in d.participantes_de_curso(curso)],
    }


@router.post("/{id_curso}/favorito", summary="Marcar o desmarcar un módulo como favorito")
def alternar_favorito(id_curso: int):
    """Hoy queda en memoria, como el resto de los datos; con Firestore pasa a
    ser por usuario."""
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")

    curso["favorito"] = not curso["favorito"]
    return {**curso, "novedades": d.novedades_de_curso(curso)}
