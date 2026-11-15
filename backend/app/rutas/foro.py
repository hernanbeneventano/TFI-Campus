"""Foro de consultas por asignatura.

Quién publica sale de la **sesión**: cada ruta recibe `yo` del token de
Firebase que verifica `servicios/autenticacion.py`. Antes había una constante
de módulo con el usuario de prueba, de cuando no había login; con sesiones de
verdad, eso hacía que cada consulta y cada respuesta salieran a nombre de la
misma persona.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios.autenticacion import IdUsuarioActual

router = APIRouter(prefix="/api/foro", tags=["Foro"])


def _autor_de(id_persona: int) -> dict | None:
    persona = d.buscar_persona(id_persona)
    return (
        {"id": persona["id"], "nombre": persona["nombre"], "rol": d.rol_principal(persona)}
        if persona
        else None
    )


def _curso_de(id_curso: Any) -> dict | None:
    curso = d.buscar_curso(id_curso)
    return (
        {
            "id": curso["id"],
            "nombre": curso["nombre"],
            "codigo": curso["codigo"],
            "color": curso["color"],
        }
        if curso
        else None
    )


def _con_votos(mensaje: dict, yo: int) -> dict:
    """Los votos salen contados, nunca con la lista de quiénes fueron: igual
    que las reacciones de Novedades."""
    votos = mensaje.get("votos") or []
    resto = {k: v for k, v in mensaje.items() if k != "votos"}
    return {**resto, "utiles": len(votos), "loVote": yo in votos}


def _resumir(tema: dict) -> dict:
    """En la lista no hacen falta los mensajes, solo cuántos hay y cuándo fue
    el último."""
    mensajes = tema["mensajes"]
    ultimo = mensajes[-1] if mensajes else None
    return {
        "id": tema["id"],
        "titulo": tema["titulo"],
        "curso": _curso_de(tema["cursoId"]),
        "autor": _autor_de(tema["autorId"]),
        "fecha": tema["fecha"],
        "respuestas": max(len(mensajes) - 1, 0),
        "ultimaActividad": ultimo["fecha"] if ultimo else tema["fecha"],
        "ultimoAutor": _autor_de(ultimo["autorId"]) if ultimo else None,
    }


def _detalle_de(tema: dict, yo: int) -> dict:
    siguen = tema.get("siguen") or []
    return {
        "id": tema["id"],
        "titulo": tema["titulo"],
        "curso": _curso_de(tema["cursoId"]),
        "autor": _autor_de(tema["autorId"]),
        "fecha": tema["fecha"],
        "siguiendo": yo in siguen,
        "seguidores": len(siguen),
        "mensajes": [
            {**_con_votos(m, yo), "autor": _autor_de(m["autorId"])} for m in tema["mensajes"]
        ],
    }


def _buscar_tema(id_tema: int) -> dict:
    tema = next((t for t in d.temas_foro if t["id"] == id_tema), None)
    if not tema:
        raise HTTPException(404, "Tema no encontrado")
    return tema


@router.get("", summary="Los temas y las asignaturas que tienen alguno")
def listar_temas():
    temas = sorted(
        (_resumir(t) for t in d.temas_foro),
        key=lambda t: d.desde_iso(t["ultimaActividad"]),
        reverse=True,
    )

    asignaturas = []
    for curso in d.cursos:
        cuantos = sum(1 for t in temas if t["curso"] and t["curso"]["id"] == curso["id"])
        if cuantos > 0:
            asignaturas.append({**_curso_de(curso["id"]), "temas": cuantos})

    return {"temas": temas, "asignaturas": asignaturas}


@router.post("", status_code=201, summary="Abrir un tema")
def crear_tema(cuerpo: dict[str, Any] = Body(default={}), yo: int = IdUsuarioActual):
    curso = _curso_de(cuerpo.get("cursoId"))
    titulo = str(cuerpo.get("titulo") or "").strip()
    texto = str(cuerpo.get("texto") or "").strip()

    if not curso:
        raise HTTPException(400, "Hay que elegir una asignatura")
    if not titulo or not texto:
        raise HTTPException(400, "El tema necesita un título y una consulta")

    ahora = d.iso(d.ahora())
    tema = {
        "id": d.nuevo_id_tema(),
        "cursoId": curso["id"],
        "titulo": titulo,
        "autorId": yo,
        "fecha": ahora,
        "siguen": [yo],
        "mensajes": [
            {
                "id": d.nuevo_id_mensaje_foro(),
                "autorId": yo,
                "texto": texto,
                "fecha": ahora,
                "votos": [],
            }
        ],
    }
    d.temas_foro.append(tema)

    return _resumir(tema)


@router.get("/{id_tema}", summary="Abrir un tema con sus respuestas")
def obtener_tema(id_tema: int, yo: int = IdUsuarioActual):
    return _detalle_de(_buscar_tema(id_tema), yo)


@router.post("/{id_tema}", status_code=201, summary="Responder un tema")
def responder(
    id_tema: int, cuerpo: dict[str, Any] = Body(default={}), yo: int = IdUsuarioActual
):
    tema = _buscar_tema(id_tema)

    texto = str(cuerpo.get("texto") or "").strip()
    if not texto:
        raise HTTPException(400, "La respuesta no puede estar vacía")

    mensaje = {
        "id": d.nuevo_id_mensaje_foro(),
        "autorId": yo,
        "texto": texto,
        "fecha": d.iso(d.ahora()),
        "votos": [],
    }
    tema["mensajes"].append(mensaje)

    return {**_con_votos(mensaje, yo), "autor": _autor_de(yo)}


@router.post("/{id_tema}/seguir", summary="Seguir el tema, o dejar de seguirlo")
def seguir(id_tema: int, yo: int = IdUsuarioActual):
    """Por ahora solo se guarda: los avisos van a llegar cuando haya
    notificaciones de verdad."""
    tema = _buscar_tema(id_tema)

    siguen = tema.setdefault("siguen", [])
    tema["siguen"] = [i for i in siguen if i != yo] if yo in siguen else [*siguen, yo]

    return _detalle_de(tema, yo)


@router.post("/{id_tema}/mensajes/{id_mensaje}/voto", summary="Marcar una respuesta como útil")
def votar(id_tema: int, id_mensaje: int, yo: int = IdUsuarioActual):
    """O sacar el voto, si ya estaba puesto."""
    tema = next((t for t in d.temas_foro if t["id"] == id_tema), None)
    mensaje = (
        next((m for m in tema["mensajes"] if m["id"] == id_mensaje), None) if tema else None
    )
    if not mensaje:
        raise HTTPException(404, "Mensaje no encontrado")

    votos = mensaje.setdefault("votos", [])
    mensaje["votos"] = [i for i in votos if i != yo] if yo in votos else [*votos, yo]

    return {**_con_votos(mensaje, yo), "autor": _autor_de(mensaje["autorId"])}
