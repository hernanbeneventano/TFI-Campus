"""Servidor de CampusTFI.

Expone la interfaz de programación que consume el frontend. La documentación
interactiva se genera sola y queda en /docs.
"""

from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import datos as d
from .rutas import biblioteca, calendario, cursos, finales, foro, gestion_finales
from .rutas import gestion_modulo
from .rutas import archivos as rutas_archivos
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
from .servicios import almacenamiento, frenos, legajos, persistencia

load_dotenv()

# Antes de crear cualquier cliente de Google: las bibliotecas leen la
# configuración de certificados una sola vez, al construir su contexto.
certificados.configurar()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Al arrancar: conectar con Firestore y traer el campus.

    Si no hay credenciales o Firestore no responde, el servidor **levanta
    igual** y trabaja en memoria: que la base no esté disponible no tiene por
    qué dejar a la facultad sin campus. Lo que no puede pasar es que no se
    note, así que se dice en el arranque.
    """
    try:
        inicializar_firestore()
    except Exception as error:  # noqa: BLE001
        print(f"[firestore] sin conexión: {error}")
    print(f"[datos] {persistencia.iniciar()}")

    # Al personal que todavía no tiene legajo del campus se le asigna uno.
    # Pasa con las cuentas creadas antes de que existieran los legajos, y con
    # cualquiera que cambie de rol: un docente nuevo necesita su número para
    # firmar un acta, y no hay dónde pedirlo a mano.
    sin_legajo = [p for p in d.personas if not p.get("legajo")]
    nuevos = [p for p in sin_legajo if legajos.asegurar_institucional(p)]
    if nuevos:
        print(f"[legajos] asignados a {len(nuevos)} personas del personal")

    print(f"[archivos] {almacenamiento.iniciar()}")
    yield
    # Lo último que se haya hecho, antes de cerrar
    persistencia.guardar_cambios()


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
# Cambia en cada arranque del servidor. El navegador lo compara con el que
# tenía guardado y, si no coincide, cierra la sesión y manda al login.
#
# Hace falta porque la sesión de Firebase vive en el navegador: reiniciar el
# backend no la toca, y se seguía entrando como quien hubiera quedado logueado
# la última vez. Para probar los roles eso es un estorbo —uno quiere arrancar
# siempre desde el login— y, con el campus en desarrollo, también evita quedar
# con media pantalla de datos viejos de antes del reinicio.
ARRANQUE = secrets.token_hex(8)


@app.get("/api/salud", tags=["General"], summary="Comprobar que el servidor responde")
def salud():
    return {"estado": "ok", "app": "CampusTFI", "instancia": ARRANQUE}


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
            # La foto la pone `con_presencia`, que la firma a partir de la
            # clave del archivo. Ponerla también acá la firmaba sobre el
            # diccionario ya modificado —es decir, sobre la dirección— y la
            # firma no validaba.
        }
    )


# `PUT /api/me` **se eliminó**. No pedía sesión y escribía sobre
# `d.usuario_actual` —el usuario de prueba— en vez de sobre quien llamaba, así
# que ni editaba el perfil de nadie ni tenía por qué dejar escribir a
# cualquiera. El perfil propio se edita en `PUT /api/usuarios/yo`, que sí
# comprueba la sesión y guarda donde corresponde.


@app.get("/api/contadores", tags=["General"], summary="Las campanitas del menú")
def contadores(persona: dict = Depends(identificar)):
    """Cuántas cosas nuevas hay en cada apartado, **para quien pregunta**.

    Contaba siempre sobre `d.usuario_actual`, el usuario de prueba: todos
    veían los mismos números y no eran los suyos. Es de lo poco que se mira
    en cada pantalla, así que equivocarse ahí se nota en todo el campus.
    """
    return d.resumen_de_novedades(persona["id"])


# `GET /api/informacion` y `GET /api/actividad` **se eliminaron**. Ninguna
# pantalla las usaba: la primera repetía las novedades institucionales, que ya
# salen de `/api/novedades` con el control de alcance puesto, y la segunda
# quedó de la pantalla «Actividad» que reemplazó el Calendario —leía
# `tarea["entregada"]`, un campo que dejó de existir cuando la entrega pasó a
# ser de cada alumno—. Las dos respondían sin pedir sesión.



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


# ===================== Guardar lo que cambió =====================
# Después de cada petición se compara la memoria con lo último que se escribió
# y se manda a Firestore la diferencia. Ver `servicios/persistencia.py`: se
# hace acá, en un solo lugar, para que ninguna ruta tenga que acordarse de
# guardar y un módulo nuevo quede persistido por usar `datos.py` y nada más.
#
# Va también en las consultas, no solo en las que escriben: varias de lectura
# dejan rastro —la auditoría anota los ingresos, y abrir Módulos crea los
# módulos que falten—, así que mirar el método daría por no guardado algo que
# sí cambió.
@app.middleware("http")
async def guardar_lo_que_cambio(peticion, seguir):
    respuesta = await seguir(peticion)
    if persistencia.activo():
        await run_in_threadpool(persistencia.guardar_cambios)
    return respuesta


# ===================== Los frenos =====================
# Van declarados al final de los middlewares a propósito: Starlette los corre
# en orden inverso al que se agregan, así que este es el **primero** que ve la
# petición. Tiene que serlo: frenar después de identificar, auditar y leer el
# cuerpo es hacer todo el trabajo que se quería evitar.
@app.middleware("http")
async def frenar_lo_que_sobra(peticion, seguir):
    if frenos.demasiado_grande(peticion):
        return JSONResponse(
            status_code=413,
            content={"error": f"El envío supera los {frenos.MAXIMO_MB} MB."},
        )
    if frenos.excede(peticion):
        return JSONResponse(
            status_code=429,
            content={"error": "Demasiadas peticiones seguidas. Esperá un momento."},
            headers={"Retry-After": str(frenos.VENTANA_SEGUNDOS)},
        )
    return await seguir(peticion)


app.include_router(rutas_archivos.router)
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


# ===================== Arranque =====================
# **Un solo proceso, siempre.** La memoria del servidor es la copia de
# trabajo del campus y lo que cambia se guarda por diferencia después de cada
# petición (ver `servicios/persistencia.py`). Con dos procesos cada uno
# tendría su propio campus en memoria y el último que respondiera pisaría en
# Firestore lo que hubiera hecho el otro, **sin que se note**: es la peor
# forma de perder datos.
#
# Por eso acá no hay `workers`, y si alguien lo pide por la variable de
# entorno que usan los servidores de siempre, se avisa y se ignora. El día
# que haga falta escalar, lo que hay que cambiar es la persistencia —escribir
# en el momento, no por diferencia—, no la cantidad de procesos.
def _un_solo_proceso() -> None:
    pedidos = os.environ.get("WEB_CONCURRENCY") or os.environ.get("UVICORN_WORKERS")
    if pedidos and pedidos.strip() not in ("", "1"):
        print(f"[arranque] Se pidieron {pedidos} procesos y se va a levantar UNO.")
        print("           El campus vive en la memoria de un proceso y se guarda por")
        print("           diferencia: con varios, cada uno pisa lo del otro en silencio.")


def arrancar() -> None:
    """Punto de entrada para `python -m app.main`."""
    import uvicorn

    _un_solo_proceso()

    # `reload` levanta un vigilante que reinicia el servidor al guardar un
    # archivo: comodísimo mientras se desarrolla y nada que deba correr en la
    # facultad. Se apaga solo si no se pide.
    recarga = (os.environ.get("RECARGA_AUTOMATICA") or "si").strip().lower() in (
        "si", "1", "true",
    )
    # Por defecto solo escucha desde esta máquina. Para publicarlo hay que
    # decirlo a propósito, no que pase por olvido.
    host = (os.environ.get("HOST") or "127.0.0.1").strip()

    # Se sirve el despachador y no `app` directo: es el que reparte cada
    # petición entre FastAPI y Django durante la migración. Mientras su lista
    # de módulos migrados esté vacía, le pasa todo a esta misma `app` sin
    # tocarlo —incluido el `lifespan` de arriba—, así que el campus se
    # comporta exactamente igual. Ver `backend/despachador.py`.
    uvicorn.run(
        "despachador:aplicacion",
        host=host,
        port=int(os.environ.get("PORT") or 3000),
        reload=recarga,
        workers=1,
    )


if __name__ == "__main__":
    arrancar()
