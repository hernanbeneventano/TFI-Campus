"""Comprobaciones de la aplicación y las vistas nativas de Django."""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

from django.urls import Resolver404, resolve

from app.main import ARRANQUE
from app.servicios import autenticacion, frenos
from . import escenario
from .cliente import como, crear_cliente, sin_suplantar

SANTIAGO = 1
ORIGEN = "http://localhost:5173"


def comprobar(nombre: str, condicion: bool, detalle=None) -> None:
    if condicion:
        print(f"  ok     {nombre}")
        return
    print(f"  FALLA  {nombre}" + (f" -> {detalle}" if detalle is not None else ""))
    raise AssertionError(nombre)


def _rutas_historicas() -> list[tuple[str, str]]:
    archivo = Path(__file__).with_name("banco") / "grabaciones" / "fastapi.json.gz"
    with gzip.open(archivo, "rt", encoding="utf-8") as fuente:
        return [tuple(ruta) for ruta in json.load(fuente)["rutas"]]


def correr() -> int:
    escenario.cargar()
    frenos.olvidar_todo()
    cliente = crear_cliente()

    print("Vistas y middleware Django nativos\n")
    sin_suplantar()
    respuesta = cliente.get("/api/me")
    comprobar("rechaza la sesión ausente", respuesta.status_code == 401, respuesta.status_code)

    respuesta = cliente.post(
        "/api/usuarios",
        content=b"{roto",
        headers={"content-type": "application/json"},
    )
    comprobar("valida el JSON antes de autenticar", respuesta.status_code == 400, respuesta.status_code)

    como(SANTIAGO)
    respuesta = cliente.get("/api/salud")
    esperado = (
        '{"estado":"ok","app":"CampusTFI","instancia":"' + ARRANQUE + '"}'
    ).encode("utf-8")
    comprobar(
        "conserva la respuesta JSON de salud",
        (respuesta.status_code, respuesta.content, respuesta.headers.get("content-type"))
        == (200, esperado, "application/json"),
        respuesta.content,
    )

    respuesta = cliente.get("/api/me")
    comprobar(
        "resuelve la sesión desde HttpRequest",
        respuesta.status_code == 200 and respuesta.json()["id"] == SANTIAGO,
        respuesta.content,
    )

    respuesta = cliente.head("/api/salud")
    comprobar("rechaza HEAD en una ruta GET", respuesta.status_code == 405, respuesta.status_code)
    comprobar("el 405 no agrega Allow", "allow" not in respuesta.headers)

    respuesta = cliente.get("/api/__no_existe", headers={"origin": ORIGEN})
    comprobar(
        "formatea el 404 en JSON",
        respuesta.status_code == 404 and respuesta.json() == {"error": "Ruta no encontrada"},
        (respuesta.status_code, respuesta.content),
    )
    comprobar(
        "el 404 de una petición del frontend lleva CORS",
        respuesta.headers.get("access-control-allow-origin") == ORIGEN,
    )

    rutas = _rutas_historicas()
    no_resueltas = []
    for metodo, plantilla in rutas:
        camino = re.sub(r"{[^}:]+:path}", "muestra/archivo", plantilla)
        camino = re.sub(r"{[^}]+}", "1", camino)
        try:
            resolve(camino)
        except Resolver404:
            no_resueltas.append((metodo, plantilla))
    comprobar("resuelve los 169 contratos históricos", len(rutas) == 169 and not no_resueltas, no_resueltas[:5])

    como(None)
    sin_suplantar()
    print("\nComprobaciones Django nativo completas.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(correr())
    except AssertionError:
        sys.exit(1)
