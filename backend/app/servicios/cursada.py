"""Cómo se cierra una cursada: el promedio, la condición y el final.

Las reglas, en un solo lugar, porque las consultan tres pantallas distintas:
la grilla del docente, la vista del alumno y el detalle de una sección.

- La **nota final** es el promedio de todas las notas cargadas al alumno en
  ese módulo. Promedio simple: cada instancia pesa lo mismo. Si más adelante
  la cátedra necesita ponderar (parcial 35 %, trabajo práctico 30 %…), el
  lugar donde agregarlo es acá y los trabajos ganan un campo `peso`.
- Se **aprueba con 6**. Con menos, el alumno va a final.
- El docente puede **fijar el cierre a mano**: eso pesa más que el promedio,
  porque hay motivos que el sistema no conoce —una recuperación, una falta
  justificada, un acta ya firmada—. Mientras no lo haga, manda el cálculo.

Un trabajo sin corregir no entra en el promedio. No es lo mismo un cero que
una entrega que el docente todavía no miró, y contarla como cero mostraría
aplazados que no existen.
"""

from __future__ import annotations

from .. import datos as d

APROBADA = "Aprobada"
VA_A_FINAL = "Va a final"
SIN_NOTAS = "Sin notas"


def notas_de(persona_id: int, curso_id: int) -> list[dict]:
    return [
        c
        for c in d.calificaciones
        if c["cursoId"] == curso_id and c["personaId"] == persona_id
    ]


def cierre_fijado(persona_id: int, curso_id: int) -> dict | None:
    """El cierre que puso el docente a mano, si lo puso."""
    return next(
        (
            c
            for c in d.cierres_cursada
            if c["cursoId"] == curso_id and c["personaId"] == persona_id
        ),
        None,
    )


def promedio_de(persona_id: int, curso_id: int) -> float | None:
    """El promedio de lo corregido, o None si todavía no hay nada."""
    valores = [
        c["nota"]
        for c in notas_de(persona_id, curso_id)
        if isinstance(c.get("nota"), (int, float))
    ]
    if not valores:
        return None
    promedio = sum(valores) / len(valores)
    return int(promedio) if promedio == int(promedio) else round(promedio, 2)


def cierre_de(persona_id: int, curso_id: int) -> dict:
    """Cómo cierra la cursada de una persona en un módulo.

    `automatico` dice si lo que se ve sale del cálculo o lo fijó el docente;
    la pantalla lo usa para avisar que una condición está puesta a mano.
    """
    promedio = promedio_de(persona_id, curso_id)
    corregidas = len(
        [c for c in notas_de(persona_id, curso_id) if isinstance(c.get("nota"), (int, float))]
    )

    if promedio is None:
        calculada = SIN_NOTAS
    elif promedio >= d.NOTA_PARA_APROBAR:
        calculada = APROBADA
    else:
        calculada = VA_A_FINAL

    fijado = cierre_fijado(persona_id, curso_id)
    if fijado:
        return {
            "promedio": promedio,
            "corregidas": corregidas,
            "condicion": fijado["condicion"],
            "vaAFinal": fijado["condicion"] == VA_A_FINAL,
            "automatico": False,
            "observacion": fijado.get("observacion"),
            "condicionCalculada": calculada,
        }

    return {
        "promedio": promedio,
        "corregidas": corregidas,
        "condicion": calculada,
        "vaAFinal": calculada == VA_A_FINAL,
        "automatico": True,
        "observacion": None,
        "condicionCalculada": calculada,
    }


def fijar_cierre(
    persona_id: int, curso_id: int, condicion: str, observacion: str | None, docente_id: int
) -> dict:
    """Deja escrita la condición que decidió el docente."""
    previo = cierre_fijado(persona_id, curso_id)
    registro = {
        "cursoId": curso_id,
        "personaId": persona_id,
        "condicion": condicion,
        "observacion": observacion,
        "docenteId": docente_id,
        "fecha": d.iso(d.ahora()),
    }
    if previo:
        previo.update(registro)
    else:
        d.cierres_cursada.append(registro)
    return cierre_de(persona_id, curso_id)


def soltar_cierre(persona_id: int, curso_id: int) -> dict:
    """Saca el cierre manual: vuelve a mandar el promedio."""
    previo = cierre_fijado(persona_id, curso_id)
    if previo:
        d.cierres_cursada.remove(previo)
    return cierre_de(persona_id, curso_id)


# ===================== Cuestionarios =====================
def respuesta_de(persona_id: int, tarea_id: int) -> dict | None:
    return next(
        (
            r
            for r in d.respuestas_cuestionario
            if r["tareaId"] == tarea_id and r["personaId"] == persona_id
        ),
        None,
    )


def corregir_cuestionario(tarea: dict, respuestas: dict) -> dict:
    """Corrige un cuestionario de opción múltiple.

    Devuelve la nota en la misma escala que el resto del campus (1 a 10), y
    el detalle de qué estuvo bien, para poder mostrárselo al alumno.
    """
    preguntas = tarea.get("preguntas") or []
    if not preguntas:
        return {"nota": None, "puntos": 0, "total": 0, "detalle": []}

    total = sum(p.get("puntaje", 1) for p in preguntas)
    puntos = 0
    detalle = []
    for pregunta in preguntas:
        # Las claves llegan como texto desde JSON
        elegida = respuestas.get(str(pregunta["id"]), respuestas.get(pregunta["id"]))
        acerto = elegida is not None and int(elegida) == pregunta["correcta"]
        if acerto:
            puntos += pregunta.get("puntaje", 1)
        detalle.append(
            {
                "preguntaId": pregunta["id"],
                "elegida": None if elegida is None else int(elegida),
                "correcta": pregunta["correcta"],
                "acerto": acerto,
            }
        )

    # De puntos a nota: todo bien es 10, nada bien es 1, como una escala
    # de cátedra. Un cero no existe en el campus.
    proporcion = puntos / total if total else 0
    nota = 1 + proporcion * 9
    nota = int(nota) if nota == int(nota) else round(nota, 2)

    return {"nota": nota, "puntos": puntos, "total": total, "detalle": detalle}
