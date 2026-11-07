"""Tareas pendientes y atrasadas."""

from __future__ import annotations

from fastapi import APIRouter

from .. import datos as d

router = APIRouter(prefix="/api/tareas", tags=["Tareas"])


def _apartado_de(curso: dict, tarea_id: int) -> dict | None:
    """La carpeta donde vive una tarea, con todo lo que hay que completar
    adentro.

    El frontend lo usa para mostrar el "1 de 2" del apartado: cuenta los
    recursos que el alumno marcó más las tareas que ya entregó.
    """
    for carpeta in d.carpetas_de_curso(curso):
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


@router.get("/pendientes", summary="Tareas sin entregar, próximas y atrasadas")
def listar_pendientes():
    ahora = d.ahora()

    pendientes = []
    for tarea in d.tareas:
        if tarea["entregada"]:
            continue
        curso = d.buscar_curso(tarea["cursoId"])
        pendientes.append(
            {
                **tarea,
                "curso": curso["nombre"] if curso else None,
                "color": curso["color"] if curso else None,
                "apartado": _apartado_de(curso, tarea["id"]) if curso else None,
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
