"""Lo poco de la web que el campus necesita, sin FastAPI ni Starlette.

El campus usaba de FastAPI un puñado de piezas: declarar rutas
(`APIRouter`), marcar de dónde sale cada parámetro (`Body`, `Query`,
`Depends`), cortar con un error (`HTTPException`), devolver un archivo
(`Response`) y armar el JSON. Este archivo las reemplaza **con los mismos
nombres**, así que las rutas de `app/rutas/` solo cambiaron la línea del
import: la lógica no se tocó.

Lo que importa es que contesten **igual que antes**, byte por byte: las
reglas de las cabeceras, del JSON y del CORS están portadas de Starlette
(licencia BSD) y verificadas contra lo que grabó FastAPI antes de irse
(`pruebas/banco/grabaciones/`).

Las rutas no se atienden acá: este archivo solo las **anota**. Las atiende
Django, con las vistas que arma `campus_django/puente.py` leyendo estas
anotaciones.
"""

from __future__ import annotations

import datetime
import http
import json
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
from typing import Any, Callable
from uuid import UUID


# ===================== Los errores =====================
class HTTPException(Exception):
    """Cortar con un código y un motivo: lo que el frontend ve como
    `{"error": "..."}`. Sin motivo, la frase del código («Not Found»)."""

    def __init__(self, status_code: int, detail: Any = None, headers: dict | None = None) -> None:
        if detail is None:
            detail = http.HTTPStatus(status_code).phrase
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

    def __str__(self) -> str:
        return f"{self.status_code}: {self.detail}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code!r}, detail={self.detail!r})"


class ErrorDeValidacion(Exception):
    """Un dato que no tiene la forma que la ruta declara: 400 con «Los datos
    enviados no son válidos», sea cual sea el dato."""


# ===================== Declarar los parámetros =====================
@dataclass
class _Marca:
    default: Any = ...  # `...` = obligatorio, como en FastAPI

    @property
    def obligatorio(self) -> bool:
        return self.default is ...


class _Cuerpo(_Marca):
    pass


class _Consulta(_Marca):
    pass


def Body(default: Any = ..., **_: Any) -> Any:  # noqa: N802 - el nombre de siempre
    """El cuerpo de la petición. `Body(...)` obligatorio, `Body(default={})` no."""
    return _Cuerpo(default)


def Query(default: Any = ..., **_: Any) -> Any:  # noqa: N802
    """Un parámetro de la consulta (`?pagina=2`)."""
    return _Consulta(default)


@dataclass
class _Dependencia:
    funcion: Callable


def Depends(funcion: Callable) -> Any:  # noqa: N802
    """Lo que se resuelve antes de la ruta: en el campus, quién pregunta."""
    return _Dependencia(funcion)


# La petición entera, para las rutas que leen la consulta suelta. Es la que
# arma `campus_django/asgi.py` (ver `Peticion` allá).
Request = Any


# ===================== Las rutas =====================
@dataclass
class Ruta:
    """Una ruta anotada: qué camino, qué método, qué función, qué código."""

    camino: str
    metodo: str
    funcion: Callable
    estado: int | None = None

    @property
    def endpoint(self) -> Callable:
        return self.funcion


@dataclass
class APIRouter:
    """Anota las rutas de un módulo. No las atiende: solo las registra, en el
    orden en que se declaran, para que las lea el puente de Django."""

    prefix: str = ""
    tags: list = field(default_factory=list)
    rutas: list[Ruta] = field(default_factory=list)

    def _anotar(self, metodo: str, camino: str, status_code: int | None = None, **_: Any):
        def decorador(funcion: Callable) -> Callable:
            self.rutas.append(Ruta(self.prefix + camino, metodo, funcion, status_code))
            return funcion

        return decorador

    def get(self, camino: str, **opciones: Any):
        return self._anotar("GET", camino, **opciones)

    def post(self, camino: str, **opciones: Any):
        return self._anotar("POST", camino, **opciones)

    def put(self, camino: str, **opciones: Any):
        return self._anotar("PUT", camino, **opciones)

    def patch(self, camino: str, **opciones: Any):
        return self._anotar("PATCH", camino, **opciones)

    def delete(self, camino: str, **opciones: Any):
        return self._anotar("DELETE", camino, **opciones)


# ===================== Las respuestas =====================
class Response:
    """Una respuesta con su cuerpo y sus cabeceras, armadas como Starlette.

    El cuerpo: `bytes` tal cual, texto en UTF-8. Las cabeceras: las que se
    pasan, más `content-length` (salvo en 1xx, 204 y 304) y `content-type`
    —con `; charset=utf-8` si es `text/*` y no lo trae— si no vinieron.
    """

    media_type: str | None = None
    charset = "utf-8"

    def __init__(self, content: Any = None, status_code: int = 200,
                 headers: dict | None = None, media_type: str | None = None) -> None:
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.body = self.render(content)
        self.cabeceras = self._cabeceras(headers)

    def render(self, content: Any) -> bytes:
        if content is None:
            return b""
        if isinstance(content, (bytes, memoryview)):
            return bytes(content)
        return content.encode(self.charset)

    def _cabeceras(self, headers: dict | None) -> list[tuple[str, str]]:
        crudas = [(k.lower(), v) for k, v in (headers or {}).items()]
        claves = [k for k, _ in crudas]
        if "content-length" not in claves and not (
            self.status_code < 200 or self.status_code in (204, 304)
        ):
            crudas.append(("content-length", str(len(self.body))))
        tipo = self.media_type
        if tipo is not None and "content-type" not in claves:
            if tipo.startswith("text/") and "charset=" not in tipo.lower():
                tipo += "; charset=" + self.charset
            crudas.append(("content-type", tipo))
        return crudas


class JSONResponse(Response):
    """El JSON como lo escribía FastAPI: sin espacios y con los acentos tal cual."""

    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content, ensure_ascii=False, allow_nan=False, indent=None, separators=(",", ":")
        ).encode("utf-8")


class PlainTextResponse(Response):
    media_type = "text/plain"


# ===================== Lo que se puede devolver =====================
def _decimal(valor: Decimal) -> int | float:
    return int(valor) if valor.as_tuple().exponent >= 0 else float(valor)


_POR_TIPO: dict[type, Callable[[Any], Any]] = {
    bytes: lambda o: o.decode(),
    datetime.date: lambda o: o.isoformat(),
    datetime.datetime: lambda o: o.isoformat(),
    datetime.time: lambda o: o.isoformat(),
    datetime.timedelta: lambda o: o.total_seconds(),
    Decimal: _decimal,
    Enum: lambda o: o.value,
    frozenset: list,
    deque: list,
    set: list,
    UUID: str,
    PurePath: str,
}


def a_json(valor: Any) -> Any:
    """Lo que devuelve una ruta, pasado a algo que `json` sabe escribir.

    Es lo que hacía `jsonable_encoder` de FastAPI con los tipos que aparecen
    en el campus: diccionarios, listas, tuplas y conjuntos se recorren; las
    fechas van en ISO; un `Decimal` entero queda entero.
    """
    if isinstance(valor, (str, int, float, type(None))):
        return valor
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, dict):
        return {a_json(k): a_json(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple, set, frozenset, deque)):
        return [a_json(v) for v in valor]
    for tipo, convertir in _POR_TIPO.items():
        if isinstance(valor, tipo):
            return a_json(convertir(valor))
    if hasattr(valor, "__dict__"):
        return a_json(vars(valor))
    raise ValueError(f"No se sabe pasar a JSON un {type(valor).__name__}")
