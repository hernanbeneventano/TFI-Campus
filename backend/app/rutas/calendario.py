"""Calendario académico: entregas, exámenes, clases y eventos de un rango."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from .. import datos as d

router = APIRouter(prefix="/api/calendario", tags=["Calendario"])


def _datos_del_curso(curso_id: int | None) -> dict:
    curso = d.buscar_curso(curso_id) if curso_id is not None else None
    return {
        "curso": curso["nombre"] if curso else None,
        "codigo": curso["codigo"] if curso else None,
        "color": curso["color"] if curso else None,
        "cursoId": curso_id,
    }


def _clases_en_rango(desde: datetime, hasta: datetime) -> list[dict]:
    """Las clases son semanales: se repiten en cada fecha del rango que caiga
    en su día de la semana."""
    expandidas = []
    dia = desde.replace(hour=0, minute=0, second=0, microsecond=0)

    while dia <= hasta:
        # isoweekday() da 1 para lunes, igual que los datos
        dia_semana = dia.isoweekday()

        for clase in (c for c in d.clases if c["dia"] == dia_semana):
            info = _datos_del_curso(clase["cursoId"])
            expandidas.append(
                {
                    "id": f"clase-{clase['cursoId']}-{d.clave_dia(dia)}",
                    "tipo": "clase",
                    "titulo": f"Clase de {info['curso']}",
                    "dia": d.clave_dia(dia),
                    "fecha": d.iso(dia),
                    "desde": clase["desde"],
                    "hasta": clase["hasta"],
                    "lugar": clase["aula"],
                    **info,
                }
            )

        dia += timedelta(days=1)

    return expandidas


def _leer_fecha(texto: str | None) -> datetime | None:
    """Acepta AAAA-MM-DD, que es lo que manda el calendario, y fechas ISO
    completas. Se interpreta en hora local, como las celdas de la pantalla."""
    if not texto:
        return d.ahora()
    try:
        if len(texto) == 10:
            return datetime.strptime(texto, "%Y-%m-%d").astimezone()
        return d.desde_iso(texto).astimezone()
    except ValueError:
        return None


@router.get("", summary="Todo lo que pasa entre dos fechas")
def listar_calendario(desde: str | None = None, hasta: str | None = None):
    inicio = _leer_fecha(desde)
    fin = _leer_fecha(hasta)

    if inicio is None or fin is None or fin < inicio:
        raise HTTPException(400, "Rango de fechas inválido")

    inicio = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = fin.replace(hour=23, minute=59, second=59, microsecond=999000)

    entregas = [
        {
            "id": f"entrega-{t['id']}",
            "tipo": "entrega",
            "titulo": t["titulo"],
            "tareaId": t["id"],
            "entregada": t["entregada"],
            "dia": d.clave_dia(t["fechaLimite"]),
            "fecha": t["fechaLimite"],
            "desde": d.desde_iso(t["fechaLimite"]).astimezone().strftime("%H:%M"),
            **_datos_del_curso(t["cursoId"]),
        }
        for t in d.tareas
    ]

    fijos = [
        {
            **e,
            "id": f"{e['tipo']}-{e['id']}",
            "dia": d.clave_dia(e["fecha"]),
            **(_datos_del_curso(e["cursoId"]) if e.get("cursoId") else {}),
        }
        for e in d.eventos
    ]

    todo = [
        e
        for e in entregas + fijos + _clases_en_rango(inicio, fin)
        if inicio <= d.desde_iso(e["fecha"]).astimezone() <= fin
    ]

    return sorted(todo, key=lambda e: (e["dia"], e.get("desde") or ""))
