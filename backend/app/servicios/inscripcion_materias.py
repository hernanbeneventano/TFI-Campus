"""Inscripción a materias: el plan de estudios del alumno y su avance.

Es la parte del estudiante del pedido: ver su plan, entender por qué una
materia está bloqueada y anotarse en las que tiene habilitadas. La inscripción
inicial que hace la institución al ingresar y el panel para administrar planes
y correlatividades son del supervisor y todavía no están: por ahora el plan
viene cargado en `datos_iniciales.json`.

Al confirmar una inscripción la materia **entra sola a Módulos**, que es lo
que se pidió. Si la materia ya tenía un módulo armado se usa ese; si no, se
crea uno con el contenido genérico que arma `datos.contenido_generico`.

Vive acá y no en la ruta para que FastAPI y Django contesten **con la misma
función** mientras dure la migración: cada framework solo la llama. `yo` es
el identificador de quien pregunta, como `IdUsuarioActual`.
"""

from __future__ import annotations

from fastapi import HTTPException

from .. import datos as d
from . import academico as ac
from . import modulos as mod
from . import auditoria

# Los mismos tonos de la familia que ya usan los módulos: oscuros, con
# contraste de sobra contra el texto blanco de la banda.
# Crear el módulo de una materia es cosa de `servicios/modulos.py`: lo
# necesitan también los módulos del docente, y dos copias de la misma función
# terminan dando dos módulos distintos para la misma materia.
_periodo_de = mod.periodo_de


def _materia_con_estado(persona_id: int, materia: dict) -> dict:
    return {**ac.materia_publica(materia), **ac.estado_de_materia(persona_id, materia)}


def listar_materias(yo: int) -> dict:
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

    # Por identificador, no por nombre: el nombre de una carrera puede
    # cambiar y las materias seguirían apuntando a lo mismo.
    del_plan = [
        m
        for m in d.materias_plan
        if m.get("carreraId") == carrera.get("carreraId")
        and m.get("planId") == carrera.get("planId")
    ]
    # Una materia dada de baja se sigue mostrando **si al alumno le toca**:
    # la cursó, la aprobó o está anotado. Si no tuvo nada que ver con ella,
    # no tiene por qué verla: ya no se ofrece y solo haría ruido en el plan.
    del_plan = [
        m
        for m in del_plan
        if m.get("activa", True)
        or d.condicion_en(yo, m["id"])
        or ac.esta_inscripto_en_materia(yo, m["id"])
    ]

    del_plan.sort(key=lambda m: (m["anio"], m["cuatrimestre"], m["codigo"]))

    materias = [_materia_con_estado(yo, m) for m in del_plan]

    def cuantas(estado: str) -> int:
        return sum(1 for m in materias if m["estado"] == estado)

    return {
        "carrera": d.asociacion_completa(carrera),
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



def inscribirse(id_materia: int, yo: int) -> dict:
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
    if not materia.get("activa", True):
        raise HTTPException(403, "Esa materia está dada de baja: no se ofrece este período")
    if (
        materia.get("carreraId") != carrera.get("carreraId")
        or materia.get("planId") != carrera.get("planId")
    ):
        raise HTTPException(403, "Esa materia no pertenece a tu plan de estudios")

    periodo = ac.periodo_materias()
    if not periodo["abierto"]:
        raise HTTPException(403, "El período de inscripción está cerrado")

    # Mirar el estado (cupo, si ya está) y anotar van juntos: ver
    # `academico.inscripciones_a_materias`. El módulo se crea afuera.
    with ac.inscripciones_a_materias:
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

    auditoria.registrar(
        yo,
        "creacion",
        "academico",
        elemento=f"Inscripción a {materia['nombre']}",
        elemento_id=id_materia,
        elemento_tipo="inscripcionMateria",
        persona_id=yo,
        materia_id=id_materia,
        carrera_id=carrera.get("carreraId"),
        sede_id=carrera.get("sedeId"),
        comision_id=carrera.get("comisionId"),
        despues={"estado": "Inscripto"},
        detalle="Se inscribió a una materia",
    )

    # La materia entra a Módulos en el acto
    modulo = mod.modulo_para(materia, por_inscripcion=True)

    # El historial no se toca: queda "Inscripto", no "En curso". Pasar a
    # cursada es un acto de la institución cuando arranca el cuatrimestre,
    # no una consecuencia de anotarse.

    return {
        "materia": _materia_con_estado(yo, materia),
        "modulo": {**modulo, "novedades": d.novedades_de_curso(modulo)},
    }



def dar_de_baja(id_materia: int, yo: int) -> dict:
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

    with ac.inscripciones_a_materias:
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

    carrera = d.carrera_de(yo) or {}
    auditoria.registrar(
        yo,
        "baja",
        "academico",
        elemento=f"Inscripción a {materia['nombre']}",
        elemento_id=id_materia,
        elemento_tipo="inscripcionMateria",
        persona_id=yo,
        materia_id=id_materia,
        carrera_id=carrera.get("carreraId"),
        sede_id=carrera.get("sedeId"),
        comision_id=carrera.get("comisionId"),
        antes={"estado": "Inscripto"},
        detalle="Se dio de baja de una materia",
    )

    # Si el módulo lo creó esta inscripción, se va con ella. Los que ya venían
    # en los datos no se tocan.
    #
    # Y solo si **no queda nadie más**: el módulo lo pudo haber creado este
    # alumno, pero si después se anotaron otros ya no es suyo. Borrarlo al
    # darse de baja lo haría desaparecer de la pantalla de todos los demás.
    # Lo mismo si la cátedra tiene docente a cargo: ese módulo es de ella.
    #
    # «¿Queda alguien?» y borrar van juntos: si no, otro se anota en el medio
    # y queda inscripto sin módulo donde cursar.
    with ac.inscripciones_a_materias:
        curso = d.buscar_curso(materia.get("cursoId"))
        if (
            curso
            and curso.get("creadoPorInscripcion")
            and not curso.get("docenteId")
            and ac.inscriptos_en_materia(id_materia) == 0
        ):
            d.cursos.remove(curso)
            materia["cursoId"] = None

    return _materia_con_estado(yo, materia)
