"""Servidor de CampusTFI.

Expone la interfaz de programación que consume el frontend. Django registra y
atiende las rutas mediante `campus_django/urls.py`; este módulo prepara los
servicios del campus al iniciar y cerrar, y ofrece el punto de entrada
`python -m app.main`.
"""

from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv

from . import datos as d
from .servicios.firestore import inicializar_firestore
from .servicios import almacenamiento, legajos, persistencia
from .servicios import certificados

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


# Cambia en cada arranque del servidor. El navegador lo compara con el que
# tenía guardado y, si no coincide, cierra la sesión y manda al login.
ARRANQUE = secrets.token_hex(8)


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
