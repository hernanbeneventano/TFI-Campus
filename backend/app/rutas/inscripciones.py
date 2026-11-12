"""Inscripción a materias: el plan de estudios del alumno y su avance.

Es la parte del estudiante del pedido: ver su plan, entender por qué una
materia está bloqueada y anotarse en las que tiene habilitadas. La inscripción
inicial que hace la institución al ingresar y el panel para administrar planes
y correlatividades son del supervisor y todavía no están: por ahora el plan
viene cargado en `datos_iniciales.json`.

Al confirmar una inscripción la materia **entra sola a Módulos**, que es lo
que se pidió. Si la materia ya tenía un módulo armado se usa ese; si no, se
crea uno con el contenido genérico que arma `datos.contenido_generico`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import datos as d
from ..servicios import academico as ac
from ..servicios.autenticacion import IdUsuarioActual

router = APIRouter(prefix="/api/inscripciones", tags=["Inscripciones"])

# Los mismos tonos de la familia que ya usan los módulos: oscuros, con
# contraste de sobra contra el texto blanco de la banda.
COLORES = ["#2E4057", "#8A1C3B", "#3F5E7A", "#6B2E4A", "#44506B", "#A4193D"]

ORDINAL = {1: "1.er", 2: "2.º"}


def _periodo_de(materia: dict) -> str:
    """"2026 – 1.er cuatrimestre", con el mismo formato que los módulos."""
    anio = d.ahora().year
    return f"{anio} – {ORDINAL.get(materia['cuatrimestre'], '1.er')} cuatrimestre"


def _modulo_para(materia: dict) -> dict:
    """El módulo de la materia. Si no existe, se crea.

    Queda marcado con `creadoPorInscripcion` para poder darlo de baja si el
    alumno se arrepiente: los módulos que ya venían en los datos no se tocan.
    """
    existente = d.buscar_curso(materia.get("cursoId"))
    if existente:
        return existente

    docente = d.buscar_persona(materia.get("docenteId"))
    nuevo = {
        "id": max((c["id"] for c in d.cursos), default=0) + 1,
        "codigo": materia["codigo"],
        "nombre": materia["nombre"],
        "docente": docente["nombre"] if docente else "Sin asignar",
        "docenteId": materia.get("docenteId"),
        "periodo": _periodo_de(materia),
        "color": COLORES[materia["id"] % len(COLORES)],
        "favorito": False,
        "creadoPorInscripcion": True,
    }
    d.cursos.append(nuevo)
    materia["cursoId"] = nuevo["id"]
    return nuevo


def _materia_con_estado(persona_id: int, materia: dict) -> dict:
    return {**ac.materia_publica(materia), **ac.estado_de_materia(persona_id, materia)}


@router.get("/materias", summary="El plan de estudios del alumno, con el estado de cada materia")
def listar_materias(yo: int = IdUsuarioActual):
    """Todo el plan, no solo lo que puede cursar.

    Ver la carrera entera —lo aprobado, lo que está cursando y lo que le falta
    con el motivo— es justamente lo que hace entendible el sistema de
    correlatividades.
    """
    carrera = d.carrera_de(yo)
    if not carrera:
        # Pasa si la institución todavía no lo inscribió a la carrera
        raise HTTPException(
            404,
            "Todavía no estás inscripto a una carrera. Acercate a la secretaría para el alta.",
        )

    del_plan = [
        m
        for m in d.materias_plan
        if m["carrera"] == carrera["carrera"] and m["plan"] == carrera["plan"]
    ]
    del_plan.sort(key=lambda m: (m["anio"], m["cuatrimestre"], m["codigo"]))

    materias = [_materia_con_estado(yo, m) for m in del_plan]

    def cuantas(estado: str) -> int:
        return sum(1 for m in materias if m["estado"] == estado)

    return {
        "carrera": carrera,
        "periodo": ac.periodo_materias(),
        "materias": materias,
        "resumen": {
            "total": len(materias),
            "aprobadas": cuantas(ac.APROBADA),
            "regulares": cuantas(ac.REGULAR),
            "enCurso": cuantas(ac.EN_CURSO),
            "inscripto": cuantas(ac.INSCRIPTO),
            "habilitadas": cuantas(ac.HABILITADA),
            "bloqueadas": cuantas(ac.BLOQUEADA),
        },
    }


@router.post("/materias/{id_materia}", status_code=201, summary="Inscribirse a una materia")
def inscribirse(id_materia: int, yo: int = IdUsuarioActual):
    """Valida correlatividades, cupo, período y duplicados antes de anotar.

    Lo mismo que muestra la pantalla, pero decidido acá: ocultar un botón no
    es un control de acceso.
    """
    carrera = d.carrera_de(yo)
    if not carrera:
        raise HTTPException(403, "No estás inscripto a ninguna carrera")

    materia = d.buscar_materia(id_materia)
    if not materia:
        raise HTTPException(404, "La materia no existe")
    if materia["carrera"] != carrera["carrera"] or materia["plan"] != carrera["plan"]:
        raise HTTPException(403, "Esa materia no pertenece a tu plan de estudios")

    periodo = ac.periodo_materias()
    if not periodo["abierto"]:
        raise HTTPException(403, "El período de inscripción está cerrado")

    estado = ac.estado_de_materia(yo, materia)
    if estado["estado"] == ac.INSCRIPTO:
        raise HTTPException(409, "Ya estás inscripto a esta materia")
    if not estado["puedeInscribirse"]:
        raise HTTPException(403, estado["motivo"] or "No podés inscribirte a esta materia")

    d.inscripciones_materias.append(
        {
            "id": d.nuevo_id_inscripcion_materia(),
            "personaId": yo,
            "materiaId": id_materia,
            "fecha": d.iso(d.ahora()),
        }
    )

    # La materia entra a Módulos en el acto
    modulo = _modulo_para(materia)

    # El historial no se toca: queda "Inscripto", no "En curso". Pasar a
    # cursada es un acto de la institución cuando arranca el cuatrimestre,
    # no una consecuencia de anotarse.

    return {
        "materia": _materia_con_estado(yo, materia),
        "modulo": {**modulo, "novedades": d.novedades_de_curso(modulo)},
    }


@router.delete("/materias/{id_materia}", summary="Dar de baja la inscripción a una materia")
def dar_de_baja(id_materia: int, yo: int = IdUsuarioActual):
    """Mientras el período siga abierto.

    No estaba en el pedido, pero una inscripción sin vuelta atrás deja al
    alumno atado a un error de un clic, y el período de inscripción existe
    justamente para poder rearmar la cursada.
    """
    materia = d.buscar_materia(id_materia)
    if not materia:
        raise HTTPException(404, "La materia no existe")

    if not ac.periodo_materias()["abierto"]:
        raise HTTPException(403, "El período de inscripción está cerrado")

    inscripcion = next(
        (
            i
            for i in d.inscripciones_materias
            if i["personaId"] == yo and i["materiaId"] == id_materia
        ),
        None,
    )
    if not inscripcion:
        raise HTTPException(409, "No estás inscripto a esta materia")

    d.inscripciones_materias.remove(inscripcion)

    # Si el módulo lo creó esta inscripción, se va con ella. Los que ya venían
    # en los datos no se tocan.
    curso = d.buscar_curso(materia.get("cursoId"))
    if curso and curso.get("creadoPorInscripcion"):
        d.cursos.remove(curso)
        materia["cursoId"] = None

    return _materia_con_estado(yo, materia)
