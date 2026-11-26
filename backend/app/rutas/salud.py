"""Comprobaciones de disponibilidad del backend y Firestore."""

from __future__ import annotations

import logging

from app.errores import ErrorDeAPI

from .. import datos as d
from ..servicios.firestore import verificar_conexion

logger = logging.getLogger(__name__)


def salud_firestore(yo: dict ):
    """La mira quien administra el campus, no cualquiera.

    Que la base esté o no esté es información del servidor: a un visitante no
    le sirve para nada y a quien está probando el campus le dice qué hay
    detrás. `GET /api/salud`, que solo responde que el servidor está vivo,
    sigue abierta: es lo que mira el navegador para saber si se reinició.
    """
    if not d.tiene_rol(yo, "Administrador", "Supervisor"):
        raise ErrorDeAPI(403, "Solo la administración del campus puede ver esto")

    try:
        verificar_conexion()
    except Exception as error:
        logger.exception("No se pudo comprobar la conexión con Firestore")
        raise ErrorDeAPI(503, "Firestore no está disponible") from error
    return {"estado": "ok", "firestore": "conectado"}
