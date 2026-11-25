"""Las tareas pendientes de quien pregunta: próximas y atrasadas."""

from __future__ import annotations

from .. import datos as d


def _apartado_de(curso: dict, tarea_id: int, persona_id=None) -> dict | None:
    """La carpeta donde vive una tarea, con todo lo que hay que completar
    adentro.

    El frontend lo usa para mostrar el "1 de 2" del apartado: cuenta los
    recursos que el alumno marcó más las tareas que ya entregó.
    """
    for carpeta in d.carpetas_de_curso(curso, persona_id):
        if not any(
            i.get("tipo") == "tarea" and i.get("tareaId") == tarea_id for i in carpeta["items"]
        ):
            continue
        return {
            "titulo": carpeta["titulo"],
            "items": [
                (
                    {"id": i["id"], "tipo": i["tipo"], "entregada": i.get("entregada")}
                    if i.get("tipo") == "tarea"
                    else {"id": i["id"], "tipo": i["tipo"]}
                )
                for i in carpeta["items"]
            ],
        }
    return None


def pendientes_de(yo: dict) -> dict:
    """Las **propias**: las de los módulos que cursa quien pregunta.

    Antes recorría todas las tareas del campus y miraba un booleano del
    trabajo, igual para todo el curso. Con un módulo y un alumno de prueba no
    se notaba; con el campus cargado, cada uno veía las entregas de materias
    que no cursa, y una entrega hecha por otro le desaparecía de la lista.
    """
    ahora = d.ahora()
    mios = {
        c["id"]
        for c in d.cursos
        if any(p["id"] == yo["id"] for p in d.participantes_de_curso(c))
    }

    pendientes = []
    for tarea in d.tareas:
        if tarea["cursoId"] not in mios:
            continue
        if d.entrego(yo["id"], tarea):
            continue
        curso = d.buscar_curso(tarea["cursoId"])
        pendientes.append(
            {
                **tarea,
                "entregada": False,
                "curso": curso["nombre"] if curso else None,
                "color": curso["color"] if curso else None,
                "apartado": _apartado_de(curso, tarea["id"], yo["id"]) if curso else None,
            }
        )

    por_fecha = lambda t: d.desde_iso(t["fechaLimite"])  # noqa: E731

    recientes = sorted(
        (t for t in pendientes if d.desde_iso(t["fechaLimite"]) >= ahora), key=por_fecha
    )
    atrasadas = sorted(
        (t for t in pendientes if d.desde_iso(t["fechaLimite"]) < ahora), key=por_fecha
    )

    return {"recientes": recientes, "atrasadas": atrasadas}
