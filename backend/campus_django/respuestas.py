"""Utilidades pequeñas de respuesta para las vistas Django del campus."""

from __future__ import annotations

import datetime
import json
from collections import deque
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
from uuid import UUID

from django.http import HttpResponse


def _jsonable(valor):
    if isinstance(valor, (str, int, float, type(None))):
        return valor
    if isinstance(valor, (bytes, memoryview)):
        return bytes(valor).decode("utf-8")
    if isinstance(valor, Enum):
        return _jsonable(valor.value)
    if isinstance(valor, dict):
        return {_jsonable(clave): _jsonable(contenido) for clave, contenido in valor.items()}
    if isinstance(valor, (list, tuple, set, frozenset, deque)):
        return [_jsonable(elemento) for elemento in valor]
    if isinstance(valor, datetime.datetime):
        return valor.isoformat()
    if isinstance(valor, (datetime.date, datetime.time)):
        return valor.isoformat()
    if isinstance(valor, datetime.timedelta):
        return valor.total_seconds()
    if isinstance(valor, Decimal):
        return int(valor) if valor.as_tuple().exponent >= 0 else float(valor)
    if isinstance(valor, (UUID, PurePath)):
        return str(valor)
    raise TypeError(f"No se puede serializar {type(valor).__name__} como JSON")


def json_respuesta(valor, estado: int = 200, cabeceras: dict[str, str] | None = None) -> HttpResponse:
    contenido = json.dumps(
        _jsonable(valor),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    respuesta = HttpResponse(contenido, status=estado, content_type="application/json")
    if not (estado < 200 or estado in (204, 304)):
        respuesta["Content-Length"] = str(len(contenido))
    for nombre, valor_cabecera in (cabeceras or {}).items():
        respuesta[nombre] = valor_cabecera
    return respuesta


def error_json(mensaje: str, estado: int) -> HttpResponse:
    return json_respuesta({"error": mensaje}, estado)


def metodo_no_permitido(_permitidos: tuple[str, ...]) -> HttpResponse:
    return error_json("Method Not Allowed", 405)


def error_datos() -> HttpResponse:
    return error_json("Los datos enviados no son válidos", 400)


def descargar(contenido: bytes, tipo: str, cabeceras: dict[str, str] | None = None) -> HttpResponse:
    respuesta = HttpResponse(contenido, content_type=tipo)
    respuesta["Content-Length"] = str(len(contenido))
    for nombre, valor in (cabeceras or {}).items():
        respuesta[nombre] = valor
    return respuesta
