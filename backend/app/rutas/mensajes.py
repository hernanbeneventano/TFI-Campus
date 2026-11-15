"""Mensajería interna: conversaciones de a dos.

Quién escribe sale de la **sesión**, no de una constante de módulo: cada ruta
recibe `yo` del token de Firebase que verifica `servicios/autenticacion.py`.
Antes había una constante con el usuario de prueba, de cuando no había login;
con sesiones de verdad eso hacía que todos los mensajes salieran a nombre de
la misma persona por más que hubiera iniciado sesión otra.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios.autenticacion import IdUsuarioActual

router = APIRouter(prefix="/api/mensajes", tags=["Mensajes"])


def _es_mia(conversacion: dict, yo: int) -> bool:
    return yo in conversacion["entre"]


def _el_otro(conversacion: dict, yo: int) -> dict | None:
    """La otra persona de la conversación, con su estado de presencia."""
    otro_id = next((i for i in conversacion["entre"] if i != yo), None)
    persona = d.buscar_persona(otro_id)
    return d.con_presencia(persona) if persona else None


def _sin_leer(conversacion: dict, yo: int) -> int:
    return sum(1 for m in conversacion["mensajes"] if m["deId"] != yo and not m["leido"])


def _resumir(conversacion: dict, yo: int) -> dict:
    mensajes = conversacion["mensajes"]
    return {
        "id": conversacion["id"],
        "con": _el_otro(conversacion, yo),
        "ultimo": mensajes[-1] if mensajes else None,
        "sinLeer": _sin_leer(conversacion, yo),
    }


def _buscar(id_conversacion: int, yo: int) -> dict:
    conversacion = next((c for c in d.conversaciones if c["id"] == id_conversacion), None)
    # Una conversación ajena no existe para quien pregunta: un 403 confirmaría
    # que está y con quién
    if not conversacion or not _es_mia(conversacion, yo):
        raise HTTPException(404, "Conversación no encontrada")
    return conversacion


@router.get("", summary="Las conversaciones del usuario y el total sin leer")
def listar_conversaciones(yo: int = IdUsuarioActual):
    lista = sorted(
        (_resumir(c, yo) for c in d.conversaciones if _es_mia(c, yo)),
        key=lambda c: d.desde_iso(c["ultimo"]["fecha"]) if c["ultimo"] else d.desde_iso("1970-01-01T00:00:00.000Z"),
        reverse=True,
    )
    return {"conversaciones": lista, "sinLeer": sum(c["sinLeer"] for c in lista)}


@router.get("/contactos", summary="Gente de tus módulos con la que podés hablar")
def listar_contactos(yo: int = IdUsuarioActual):
    """Va declarada antes que /{id}: si no, "contactos" se tomaría como un
    identificador."""
    return [{**d.con_presencia(c), "modulos": c["modulos"]} for c in d.contactos_de(yo)]


@router.get("/{id_conversacion}", summary="Abrir una conversación y darla por leída")
def obtener_conversacion(id_conversacion: int, yo: int = IdUsuarioActual):
    conversacion = _buscar(id_conversacion, yo)

    for mensaje in conversacion["mensajes"]:
        if mensaje["deId"] != yo:
            mensaje["leido"] = True

    return {
        "id": conversacion["id"],
        "con": _el_otro(conversacion, yo),
        "mensajes": conversacion["mensajes"],
    }


@router.post("/{id_conversacion}", status_code=201, summary="Enviar un mensaje")
def enviar_mensaje(
    id_conversacion: int,
    cuerpo: dict[str, Any] = Body(default={}),
    yo: int = IdUsuarioActual,
):
    conversacion = _buscar(id_conversacion, yo)

    texto = str(cuerpo.get("texto") or "").strip()

    # Por ahora de los adjuntos solo se guarda el nombre y el tamaño: todavía
    # no hay dónde subir el archivo, eso llega con Firebase Storage.
    recibidos = cuerpo.get("adjuntos")
    adjuntos = []
    if isinstance(recibidos, list):
        for a in recibidos[:5]:
            nombre = str((a or {}).get("nombre") or "")[:120]
            if not nombre:
                continue
            try:
                tamano = int((a or {}).get("tamano") or 0)
            except (TypeError, ValueError):
                tamano = 0
            adjuntos.append({"nombre": nombre, "tamano": tamano})

    if not texto and not adjuntos:
        raise HTTPException(400, "El mensaje no puede estar vacío")

    mensaje = {
        "id": d.nuevo_id_mensaje(),
        "deId": yo,
        "texto": texto,
        "adjuntos": adjuntos,
        "fecha": d.iso(d.ahora()),
        "leido": True,
    }
    conversacion["mensajes"].append(mensaje)

    return mensaje


@router.post("", summary="Abrir la conversación con alguien, o crearla")
def abrir_conversacion(cuerpo: dict[str, Any] = Body(default={}), yo: int = IdUsuarioActual):
    try:
        para_id = int(cuerpo.get("paraId"))
    except (TypeError, ValueError):
        raise HTTPException(400, "No se puede abrir una conversación con esa persona")

    persona = d.buscar_persona(para_id)
    if not persona or para_id == yo:
        raise HTTPException(400, "No se puede abrir una conversación con esa persona")

    conversacion = next(
        (c for c in d.conversaciones if _es_mia(c, yo) and para_id in c["entre"]), None
    )
    if not conversacion:
        conversacion = {"id": d.nuevo_id_conversacion(), "entre": [yo, para_id], "mensajes": []}
        d.conversaciones.append(conversacion)

    return {
        "id": conversacion["id"],
        "con": _el_otro(conversacion, yo),
        "mensajes": conversacion["mensajes"],
    }
