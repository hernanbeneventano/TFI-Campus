"""Errores de dominio que el backend expone como respuestas HTTP."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any


class ErrorDeAPI(Exception):
    def __init__(
        self,
        estado: int,
        mensaje: Any = None,
        cabeceras: dict[str, str] | None = None,
    ) -> None:
        if mensaje is None:
            mensaje = HTTPStatus(estado).phrase
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje
        self.cabeceras = cabeceras or {}
