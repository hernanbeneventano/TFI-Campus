"""Comprobaciones de disponibilidad del backend y Firestore."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..servicios.firestore import verificar_conexion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/salud", tags=["General"])


@router.get("/firestore", summary="Comprobar el acceso a Firestore")
def salud_firestore():
    try:
        verificar_conexion()
    except Exception as error:
        logger.exception("No se pudo comprobar la conexión con Firestore")
        raise HTTPException(503, "Firestore no está disponible") from error
    return {"estado": "ok", "firestore": "conectado"}
