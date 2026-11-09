"""Inicialización y acceso al cliente de Cloud Firestore."""

from __future__ import annotations

import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

RUTA_CLAVE_POR_DEFECTO = Path(__file__).resolve().parents[2] / "firebase-key.json"
_cliente: Client | None = None


def _ruta_credenciales() -> Path:
    configurada = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    ruta = Path(configurada).expanduser() if configurada else RUTA_CLAVE_POR_DEFECTO
    ruta = ruta.resolve()
    if not ruta.is_file():
        raise FileNotFoundError(
            "No se encontró la clave de Firebase. Guardala en "
            f"{RUTA_CLAVE_POR_DEFECTO} o configurá GOOGLE_APPLICATION_CREDENTIALS."
        )
    return ruta


def inicializar_firestore() -> Client:
    """Crea el cliente de Firestore una vez por proceso."""
    global _cliente
    if _cliente is not None:
        return _cliente

    clave = credentials.Certificate(str(_ruta_credenciales()))
    aplicacion = firebase_admin.initialize_app(
        clave,
        options={"projectId": clave.project_id},
    )
    _cliente = firestore.client(app=aplicacion)
    return _cliente


def obtener_firestore() -> Client:
    if _cliente is None:
        raise RuntimeError("Firestore no fue inicializado durante el arranque.")
    return _cliente


def verificar_conexion() -> None:
    """Hace una consulta vacía para comprobar acceso sin crear ni modificar datos."""
    obtener_firestore().collection("campustfi_healthcheck").limit(1).get()
