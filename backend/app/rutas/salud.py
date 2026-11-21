"""Comprobaciones de disponibilidad del backend y Firestore."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from .. import datos as d
from ..servicios.autenticacion import UsuarioActual
from ..servicios.firestore import verificar_conexion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/salud", tags=["General"])


@router.get("/firestore", summary="Comprobar el acceso a Firestore")
def salud_firestore(yo: dict = UsuarioActual):
    """La mira quien administra el campus, no cualquiera.

    Que la base esté o no esté es información del servidor: a un visitante no
    le sirve para nada y a quien está probando el campus le dice qué hay
    detrás. `GET /api/salud`, que solo responde que el servidor está vivo,
    sigue abierta: es lo que mira el navegador para saber si se reinició.
    """
    if not d.tiene_rol(yo, "Administrador", "Supervisor"):
        raise HTTPException(403, "Solo la administración del campus puede ver esto")

    try:
        verificar_conexion()
    except Exception as error:
        logger.exception("No se pudo comprobar la conexión con Firestore")
        raise HTTPException(503, "Firestore no está disponible") from error
    return {"estado": "ok", "firestore": "conectado"}
