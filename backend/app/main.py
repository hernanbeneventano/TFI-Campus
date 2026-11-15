"""Servidor de CampusTFI.

Expone la interfaz de programación que consume el frontend. La documentación
interactiva se genera sola y queda en /docs.
"""

from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import datos as d
from .rutas import biblioteca, calendario, cursos, finales, foro, gestion_finales
from .rutas import gestion_modulo
from .rutas import asistencias as rutas_asistencias
from .rutas import auditoria as rutas_auditoria
from .rutas import panel as rutas_panel
from .servicios import auditoria
from .rutas import institucion, mi_cursada, usuarios
from .rutas import inscripciones
from .rutas import mensajes, novedades, tareas
from .rutas import salud as rutas_salud
from .servicios import certificados
from .servicios.autenticacion import identificar
from .servicios.firestore import inicializar_firestore

load_dotenv()

# Antes de crear cualquier cliente de Google: las bibliotecas leen la
# configuración de certificados una sola vez, al construir su contexto.
certificados.configurar()


@asynccontextmanager
async def lifespan(_: FastAPI):
    inicializar_firestore()
    yield


app = FastAPI(
    title="CampusTFI",
    version="0.1.0",
    description=(
        "Interfaz de programación del campus virtual CampusTFI.\n\n"
        "**Estado actual.** Todavía no hay inicio de sesión: todas las operaciones se "
        "resuelven como si las realizara un usuario de prueba fijo. Los datos residen "
        "en memoria y se reinician al reiniciar el servidor. Firestore está disponible "
        "para la siguiente etapa de migración."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_URL") or "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== Errores =====================
# El frontend espera { error: "..." } con el motivo en castellano, no el
# { detail: ... } que trae FastAPI de fábrica.
@app.exception_handler(StarletteHTTPException)
async def manejar_http(request: Request, exc: StarletteHTTPException):
    detalle = exc.detail
    if exc.status_code == 404 and detalle == "Not Found":
        detalle = "Ruta no encontrada"
    return JSONResponse(status_code=exc.status_code, content={"error": detalle})


@app.exception_handler(RequestValidationError)
async def manejar_validacion(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Los datos enviados no son válidos"})


@app.exception_handler(Exception)
async def manejar_error(request: Request, exc: Exception):
    print(f"Error no previsto: {exc!r}")
    return JSONResponse(status_code=500, content={"error": "Error interno del servidor"})


# ===================== Rutas generales =====================
@app.get("/api/salud", tags=["General"], summary="Comprobar que el servidor responde")
def salud():
    return {"estado": "ok", "app": "CampusTFI"}


@app.get("/api/me", tags=["General"], summary="El usuario que inició sesión")
def obtener_usuario(persona: dict = Depends(identificar)):
    """Sale del token de Firebase que manda el navegador.

    Si no llega token y está permitido el usuario de prueba, devuelve ese.
    """
    nombre = persona.get("nombre", "")
    primero, _, resto = nombre.partition(" ")
    return d.con_presencia(
        {
            **persona,
            # El menú lateral muestra el nombre partido
            "nombre": primero,
            "apellido": resto,
        }
    )


# El perfil propio se edita en PUT /api/usuarios/yo, que trabaja sobre la
# persona de la sesión. Antes había acá un PUT /api/me que escribía sobre el
# usuario de prueba: con login, editar el perfil le cambiaba el nombre a otra
# persona. Ninguna pantalla lo usaba ya.


@app.get("/api/contadores", tags=["General"], summary="Las campanitas del menú")
def contadores(persona: dict = Depends(identificar)):
    """Cuántas cosas nuevas hay en cada apartado, para quien está mirando."""
    return d.resumen_de_novedades(persona["id"])


@app.get("/api/informacion", tags=["General"], summary="Avisos institucionales")
def obtener_informacion():
    avisos = [
        {
            "id": publicacion["id"],
            "categoria": publicacion["categoria"],
            "titulo": publicacion["titulo"],
            "cuerpo": publicacion["cuerpo"],
            "fecha": publicacion["fecha"],
        }
        for publicacion in d.publicaciones
        if publicacion.get("ambito") == "Institucional"
    ]
    return sorted(avisos, key=lambda aviso: d.desde_iso(aviso["fecha"]), reverse=True)


@app.get("/api/actividad", tags=["General"], summary="Actividad agrupada para la interfaz actual")
def obtener_actividad():
    grupos = {"importante": [], "proximo": [], "hoy": [], "reciente": []}
    ahora = d.ahora()

    for tarea in d.tareas:
        if tarea.get("entregada"):
            continue

        fecha = d.desde_iso(tarea["fechaLimite"])
        grupo = (
            "importante"
            if fecha < ahora
            else "hoy"
            if fecha.astimezone().date() == ahora.date()
            else "proximo"
        )
        curso = d.buscar_curso(tarea["cursoId"])
        grupos[grupo].append(
            {
                "id": f"tarea-{tarea['id']}",
                "tipo": "entrega",
                "titulo": tarea["titulo"],
                "curso": curso["nombre"] if curso else "Campus",
                "fecha": tarea["fechaLimite"],
            }
        )

    for publicacion in d.publicaciones:
        curso = d.buscar_curso(publicacion.get("cursoId"))
        grupos["reciente"].append(
            {
                "id": f"novedad-{publicacion['id']}",
                "tipo": "anuncio",
                "titulo": publicacion["titulo"],
                "curso": curso["nombre"] if curso else publicacion.get("ambito", "Campus"),
                "fecha": publicacion["fecha"],
            }
        )

    for elementos in grupos.values():
        elementos.sort(key=lambda elemento: d.desde_iso(elemento["fecha"]), reverse=True)
    return grupos


# ===================== Routers =====================
# ===================== La petición, para la auditoría =====================
# Deja el `Request` a mano de `servicios/auditoria.registrar`, que lo usa para
# anotar la dirección IP. Sin esto, cada ruta del campus tendría que recibir
# el `Request` y pasarlo solo para eso.
@app.middleware("http")
async def recordar_peticion(peticion, seguir):
    marca = auditoria.peticion_actual.set(peticion)
    try:
        return await seguir(peticion)
    finally:
        auditoria.peticion_actual.reset(marca)


app.include_router(cursos.router)
app.include_router(tareas.router)
app.include_router(mensajes.router)
app.include_router(novedades.router)
app.include_router(calendario.router)
app.include_router(foro.router)
app.include_router(biblioteca.router)
app.include_router(finales.router)
# La gestión docente va después de la mitad del alumno: tiene su propio
# prefijo (/api/finales/gestion), así que el orden no las pisa.
app.include_router(gestion_finales.router)
app.include_router(gestion_modulo.router)
app.include_router(mi_cursada.router)
app.include_router(institucion.router)
app.include_router(usuarios.router)
app.include_router(rutas_asistencias.router)
app.include_router(inscripciones.router)
app.include_router(rutas_auditoria.router)
app.include_router(rutas_panel.router)
app.include_router(rutas_salud.router)


def arrancar() -> None:
    """Punto de entrada para `python -m app.main`."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT") or 3000),
        reload=True,
    )


if __name__ == "__main__":
    arrancar()
