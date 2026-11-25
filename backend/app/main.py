"""Servidor de CampusTFI.

Expone la interfaz de programación que consume el frontend. La atiende
Django (`campus_django/`): este archivo es la configuración del campus —qué
pasa al arrancar y al cerrar, qué módulos de rutas hay y en qué orden— y el
punto de entrada, `python -m app.main`.

Hasta la migración esto era una aplicación de FastAPI. Ya no hay FastAPI: las
rutas de `app/rutas/` se anotan con `app/web.py` y las atiende Django por el
puente (`campus_django/puente.py`); las capas que las envuelven están en
`campus_django/asgi.py`.
"""

from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv

from . import datos as d
from .rutas import biblioteca, calendario, cursos, finales, foro, gestion_finales
from .rutas import gestion_modulo
from .rutas import archivos as rutas_archivos
from .rutas import asistencias as rutas_asistencias
from .rutas import auditoria as rutas_auditoria
from .rutas import panel as rutas_panel
from .rutas import institucion, mi_cursada, usuarios
from .rutas import inscripciones
from .rutas import mensajes, novedades, tareas
from .rutas import salud as rutas_salud
from .servicios import certificados
from .servicios.autenticacion import identificar
from .servicios.firestore import inicializar_firestore
from .servicios import almacenamiento, general, legajos, persistencia
from .web import APIRouter, Depends

load_dotenv()

# Antes de crear cualquier cliente de Google: las bibliotecas leen la
# configuración de certificados una sola vez, al construir su contexto.
certificados.configurar()


# ===================== El arranque y el cierre =====================
def al_arrancar() -> None:
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


def al_cerrar() -> None:
    """Lo último que se haya hecho, antes de cerrar."""
    persistencia.guardar_cambios()


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

router = APIRouter()


@router.get("/api/salud", tags=["General"], summary="Comprobar que el servidor responde")
def salud():
    return {"estado": "ok", "app": "CampusTFI", "instancia": ARRANQUE}


@router.get("/api/me", tags=["General"], summary="El usuario que inició sesión")
def obtener_usuario(persona: dict = Depends(identificar)):
    """Sale del token de Firebase que manda el navegador."""
    return general.yo_mismo(persona)


# `PUT /api/me` **se eliminó**. No pedía sesión y escribía sobre
# `d.usuario_actual` —el usuario de prueba— en vez de sobre quien llamaba, así
# que ni editaba el perfil de nadie ni tenía por qué dejar escribir a
# cualquiera. El perfil propio se edita en `PUT /api/usuarios/yo`, que sí
# comprueba la sesión y guarda donde corresponde.


@router.get("/api/contadores", tags=["General"], summary="Las campanitas del menú")
def contadores(persona: dict = Depends(identificar)):
    """Cuántas cosas nuevas hay en cada apartado, para quien pregunta."""
    return general.contadores(persona)


# `GET /api/informacion` y `GET /api/actividad` **se eliminaron**. Ninguna
# pantalla las usaba: la primera repetía las novedades institucionales, que ya
# salen de `/api/novedades` con el control de alcance puesto, y la segunda
# quedó de la pantalla «Actividad» que reemplazó el Calendario —leía
# `tarea["entregada"]`, un campo que dejó de existir cuando la entrega pasó a
# ser de cada alumno—. Las dos respondían sin pedir sesión.


# ===================== Los módulos, en orden =====================
# El orden en que se miran las rutas, el mismo que tenía FastAPI: importa
# cuando dos rutas coinciden en camino (ver `adaptadores.como_starlette`).
# La gestión docente de finales va después de la mitad del alumno: tiene su
# propio prefijo (/api/finales/gestion), así que el orden no las pisa.
MODULOS = {
    "main": router,
    "archivos": rutas_archivos.router,
    "cursos": cursos.router,
    "tareas": tareas.router,
    "mensajes": mensajes.router,
    "novedades": novedades.router,
    "calendario": calendario.router,
    "foro": foro.router,
    "biblioteca": biblioteca.router,
    "finales": finales.router,
    "gestion_finales": gestion_finales.router,
    "gestion_modulo": gestion_modulo.router,
    "mi_cursada": mi_cursada.router,
    "institucion": institucion.router,
    "usuarios": usuarios.router,
    "asistencias": rutas_asistencias.router,
    "inscripciones": inscripciones.router,
    "auditoria": rutas_auditoria.router,
    "panel": rutas_panel.router,
    "salud": rutas_salud.router,
}


def todas_las_rutas() -> list:
    """Todas las rutas anotadas, en el orden en que se miran."""
    return [ruta for r in MODULOS.values() for ruta in r.rutas]


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

    uvicorn.run(
        "campus_django.asgi:aplicacion",
        host=host,
        port=int(os.environ.get("PORT") or 3000),
        reload=recarga,
        workers=1,
    )


if __name__ == "__main__":
    arrancar()
