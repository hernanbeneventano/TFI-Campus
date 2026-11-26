"""Validación de parámetros y cuerpos usados por las vistas Django."""

from __future__ import annotations

import copy
import email.message
import json
from typing import Any

from django.http import HttpRequest
from pydantic import TypeAdapter, ValidationError

from app.errores import ErrorDeAPI

OBLIGATORIO = object()


def convertir(valor: Any, tipo: Any) -> Any:
    try:
        return TypeAdapter(tipo).validate_python(valor)
    except ValidationError:
        raise ErrorDeAPI(400, "Los datos enviados no son válidos") from None


def parametro(request: HttpRequest, nombre: str, tipo: Any, defecto: Any = OBLIGATORIO) -> Any:
    if nombre not in request.GET:
        if defecto is OBLIGATORIO:
            raise ErrorDeAPI(400, "Los datos enviados no son válidos")
        return copy.deepcopy(defecto)
    return convertir(request.GET.get(nombre), tipo)


def _es_json(request: HttpRequest) -> bool:
    tipo = request.headers.get("content-type")
    if not tipo:
        return True
    mensaje = email.message.Message()
    mensaje["content-type"] = tipo
    if mensaje.get_content_maintype() != "application":
        return False
    subtipo = mensaje.get_content_subtype()
    return subtipo == "json" or subtipo.endswith("+json")


def cuerpo(request: HttpRequest, tipo: Any, defecto: Any = OBLIGATORIO) -> Any:
    crudo = request.body
    if not crudo:
        if defecto is OBLIGATORIO:
            raise ErrorDeAPI(400, "Los datos enviados no son válidos")
        return copy.deepcopy(defecto)

    valor: Any = crudo
    if _es_json(request):
        try:
            valor = json.loads(crudo)
        except (UnicodeDecodeError, ValueError):
            raise ErrorDeAPI(400, "Los datos enviados no son válidos") from None
        if valor is None:
            if defecto is OBLIGATORIO:
                raise ErrorDeAPI(400, "Los datos enviados no son válidos")
            return copy.deepcopy(defecto)
    return convertir(valor, tipo)
