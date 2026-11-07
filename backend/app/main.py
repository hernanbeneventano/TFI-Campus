"""Servidor de CampusTFI.

Expone la interfaz de programación que consume el frontend. La documentación
interactiva se genera sola y queda en /docs.
"""

from __future__ import annotations

import os
import re
from typing import Any

from dotenv import load_dotenv
from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import datos as d
from .rutas import biblioteca, calendario, cursos, foro, mensajes, novedades, tareas

load_dotenv()

app = FastAPI(
    title="CampusTFI",
    version="0.1.0",
    description=(
        "Interfaz de programación del campus virtual CampusTFI.\n\n"
        "**Estado actual.** Todavía no hay inicio de sesión: todas las operaciones se "
        "resuelven como si las realizara un usuario de prueba fijo. Los datos residen "
        "en memoria y se reinician al reiniciar el servidor."
    ),
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
def obtener_usuario():
    """Por ahora fijo, hasta que esté el login."""
    return d.con_presencia(d.usuario_actual)


@app.put("/api/me", tags=["General"], summary="Editar el perfil propio")
def editar_usuario(cuerpo: dict[str, Any] = Body(default={})):
    """El rol no se toca desde acá: lo define la facultad, no la persona."""
    nombre = str(cuerpo.get("nombre") or "").strip()
    apellido = str(cuerpo.get("apellido") or "").strip()
    correo = str(cuerpo.get("correo") or "").strip()

    if not nombre or not apellido:
        return JSONResponse(
            status_code=400, content={"error": "El nombre y el apellido no pueden estar vacíos"}
        )
    if correo and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", correo):
        return JSONResponse(status_code=400, content={"error": "Ese correo no parece válido"})

    d.usuario_actual["nombre"] = nombre
    d.usuario_actual["apellido"] = apellido
    d.usuario_actual["correo"] = correo

    # La lista de personas tiene el nombre completo: hay que mantenerla igual
    persona = d.buscar_persona(d.usuario_actual["id"])
    if persona:
        persona["nombre"] = f"{nombre} {apellido}"

    return d.con_presencia(d.usuario_actual)


@app.get("/api/contadores", tags=["General"], summary="Las campanitas del menú")
def contadores():
    """Cuántas cosas nuevas hay en cada apartado."""
    return d.resumen_de_novedades(d.usuario_actual["id"])


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
app.include_router(cursos.router)
app.include_router(tareas.router)
app.include_router(mensajes.router)
app.include_router(novedades.router)
app.include_router(calendario.router)
app.include_router(foro.router)
app.include_router(biblioteca.router)


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
