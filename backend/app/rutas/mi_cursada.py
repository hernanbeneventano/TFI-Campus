"""Lo que el alumno ve de su propia cursada: sus notas y sus cuestionarios.

**Cada uno ve lo suyo y nada más.** Las rutas de acá nunca reciben de quién
son las notas que se piden: salen de la sesión. Un alumno no puede pedir las
de un compañero porque no hay forma de nombrarlo. La grilla con todo el curso
existe —`rutas/gestion_modulo.py`— pero exige ser el docente a cargo.

De un cuestionario, el alumno recibe las preguntas **sin cuál es la
correcta**: mandarlas y esconderlas en la pantalla sería regalar las
respuestas a cualquiera que abra las herramientas del navegador. Las ve
recién después de responder.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import cursada as c
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api", tags=["Mi cursada"])


def _curso_en_el_que_estoy(id_curso: int, yo: dict) -> dict:
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "El módulo no existe")
    if not any(p["id"] == yo["id"] for p in d.participantes_de_curso(curso)):
        raise HTTPException(403, "No cursás este módulo")
    return curso


@router.get("/cursos/{id_curso}/mis-notas", summary="Mis notas en un módulo")
def mis_notas(id_curso: int, yo: dict = UsuarioActual):
    """Las notas propias, con el promedio y la condición.

    No hay forma de pedir las de otro: de quién son sale de la sesión.
    """
    curso = _curso_en_el_que_estoy(id_curso, yo)
    trabajos = [t for t in d.tareas if t["cursoId"] == curso["id"]]
    mias = c.notas_de(yo["id"], curso["id"])

    filas = []
    for trabajo in trabajos:
        nota = next((x for x in mias if x["tareaId"] == trabajo["id"]), None)
        entrega = next(
            (
                e
                for e in d.entregas
                if e["tareaId"] == trabajo["id"] and e["personaId"] == yo["id"]
            ),
            None,
        )
        respuesta = c.respuesta_de(yo["id"], trabajo["id"])
        filas.append(
            {
                "tareaId": trabajo["id"],
                "titulo": trabajo["titulo"],
                "fechaLimite": trabajo["fechaLimite"],
                "modalidad": trabajo.get("modalidad", "virtual"),
                "formato": trabajo.get("formato", "entrega"),
                "entregado": entrega is not None or respuesta is not None,
                "fecha": (entrega or respuesta or {}).get("fecha"),
                "nota": nota.get("nota") if nota else (respuesta or {}).get("nota"),
                "estado": nota.get("estado") if nota else None,
                # La devolución del docente: es lo que explica la nota
                "devolucion": nota.get("comentario") if nota else None,
            }
        )

    return {
        "curso": {"id": curso["id"], "codigo": curso["codigo"], "nombre": curso["nombre"]},
        "trabajos": filas,
        "cierre": c.cierre_de(yo["id"], curso["id"]),
        "notaParaAprobar": d.NOTA_PARA_APROBAR,
    }


@router.get("/tareas/{id_tarea}/cuestionario", summary="Abrir un cuestionario")
def abrir_cuestionario(id_tarea: int, yo: dict = UsuarioActual):
    """Las preguntas, sin decir cuál es la correcta.

    Si ya lo respondió, vienen la nota y el detalle: ahí sí se muestra qué
    estaba bien, que es de lo que se aprende.
    """
    tarea = d.buscar_tarea(id_tarea)
    if not tarea:
        raise HTTPException(404, "El trabajo no existe")
    _curso_en_el_que_estoy(tarea["cursoId"], yo)

    if tarea.get("formato") != "cuestionario":
        raise HTTPException(400, "Ese trabajo no es un cuestionario")

    respuesta = c.respuesta_de(yo["id"], id_tarea)
    abierto = _entrega_abierta(tarea)

    preguntas = [
        {
            "id": p["id"],
            "texto": p["texto"],
            "opciones": p["opciones"],
            "puntaje": p.get("puntaje", 1),
        }
        for p in (tarea.get("preguntas") or [])
    ]

    salida = {
        "trabajo": {
            "id": tarea["id"],
            "titulo": tarea["titulo"],
            "consigna": tarea.get("consigna"),
            "fechaLimite": tarea["fechaLimite"],
        },
        "preguntas": preguntas,
        "abierto": abierto,
        "respondido": respuesta is not None,
    }

    if respuesta:
        corregido = c.corregir_cuestionario(tarea, respuesta["respuestas"])
        salida["resultado"] = {
            "nota": respuesta.get("nota"),
            "puntos": corregido["puntos"],
            "total": corregido["total"],
            "fecha": respuesta["fecha"],
            "detalle": corregido["detalle"],
        }

    return salida


def _entrega_abierta(tarea: dict) -> bool:
    """`cerrada` pesa más que la fecha: el docente puede cortar antes o dar
    prórroga."""
    if tarea.get("cerrada") is True:
        return False
    if tarea.get("cerrada") is False:
        return True
    return d.desde_iso(tarea["fechaLimite"]) >= d.ahora()


@router.post("/tareas/{id_tarea}/respuestas", status_code=201, summary="Responder un cuestionario")
def responder(id_tarea: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Se responde una sola vez y se corrige en el acto.

    Una sola vez porque, pudiendo repetir, el cuestionario deja de medir
    nada: se prueba hasta acertar. Si hay que volver a tomarlo, el docente
    crea otro.
    """
    tarea = d.buscar_tarea(id_tarea)
    if not tarea:
        raise HTTPException(404, "El trabajo no existe")
    curso = _curso_en_el_que_estoy(tarea["cursoId"], yo)

    if tarea.get("formato") != "cuestionario":
        raise HTTPException(400, "Ese trabajo no es un cuestionario")
    if c.respuesta_de(yo["id"], id_tarea):
        raise HTTPException(409, "Ya respondiste este cuestionario")
    if not _entrega_abierta(tarea):
        raise HTTPException(403, "El cuestionario está cerrado")

    respuestas = cuerpo.get("respuestas")
    if not isinstance(respuestas, dict) or not respuestas:
        raise HTTPException(400, "Falta responder")

    preguntas = tarea.get("preguntas") or []
    if len(respuestas) < len(preguntas):
        raise HTTPException(400, "Quedaron preguntas sin responder")

    corregido = c.corregir_cuestionario(tarea, respuestas)

    d.respuestas_cuestionario.append(
        {
            "id": d.nuevo_id_respuesta(),
            "tareaId": id_tarea,
            "personaId": yo["id"],
            "fecha": d.iso(d.ahora()),
            "respuestas": {str(k): int(v) for k, v in respuestas.items()},
            "nota": corregido["nota"],
        }
    )

    # La nota entra en la cursada como cualquier otra: el promedio no
    # distingue de dónde salió.
    d.calificaciones.append(
        {
            "id": d.nuevo_id_calificacion(),
            "cursoId": curso["id"],
            "tareaId": id_tarea,
            "personaId": yo["id"],
            "nota": corregido["nota"],
            "estado": "Aprobado" if corregido["nota"] >= d.NOTA_PARA_APROBAR else "Desaprobado",
            "comentario": "Corrección automática del cuestionario.",
            "docenteId": None,
            "fecha": d.iso(d.ahora()),
        }
    )

    return {
        "resultado": {
            "nota": corregido["nota"],
            "puntos": corregido["puntos"],
            "total": corregido["total"],
            "detalle": corregido["detalle"],
        },
        "cierre": c.cierre_de(yo["id"], curso["id"]),
    }
