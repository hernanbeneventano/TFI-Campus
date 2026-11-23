"""Mensajería interna: conversaciones de a dos."""

from __future__ import annotations

import secrets
import threading
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import almacenamiento as alm
from ..servicios import archivos, fotos
from ..servicios.autenticacion import IdUsuarioActual

router = APIRouter(prefix="/api/mensajes", tags=["Mensajes"])

# Mientras no haya login, el que escribe es siempre el usuario de prueba.
# Una conversación es **de las dos personas que están en ella y de nadie
# más**. No hay forma de leer la de otro: ni un administrador ni un supervisor
# aparecen en `entre`, así que para ellos esa conversación no existe —
# `_buscar` responde 404, no 403: un 403 ya confirmaría que existe y con
# quién—.
#
# Es una decisión y no un olvido: la administración puede ver *que* hubo
# actividad en la auditoría, nunca *qué* se dijeron.


def _es_mia(conversacion: dict, yo: int) -> bool:
    return yo in conversacion["entre"]


def _el_otro(conversacion: dict, yo: int) -> dict | None:
    """La otra persona de la conversación, con su estado de presencia."""
    otro_id = next((i for i in conversacion["entre"] if i != yo), None)
    persona = d.buscar_persona(otro_id)
    return d.con_presencia(persona) if persona else None


def _sin_leer(conversacion: dict, yo: int) -> int:
    return sum(
        1 for m in conversacion["mensajes"] if m["deId"] != yo and not m["leido"]
    )


def _adjunto_visible(adjunto: dict) -> dict:
    """El adjunto con su dirección **recién armada**.

    La dirección va firmada, y la firma depende del secreto y de la forma de
    la ruta. Guardarla dentro del mensaje la congela: el día que cambia
    cualquiera de las dos, todas las fotos del campus dejan de cargar y el
    chat queda lleno de recuadros rotos. Lo que no cambia es la clave del
    objeto, así que se guarda esa y la dirección se arma al leer.

    Sin `objectKey` no hay nada que ofrecer: son los mensajes de cuando el
    archivo vivía en la memoria del servidor y se perdió al reiniciar. El
    chat los muestra como "ya no disponible", que es la verdad.
    """
    visible = {clave: valor for clave, valor in adjunto.items() if clave != "url"}
    if adjunto.get("objectKey"):
        visible["url"] = fotos.direccion_de_archivo(adjunto["objectKey"])
    return visible


def _visible(mensaje: dict | None) -> dict | None:
    if not mensaje or not mensaje.get("adjuntos"):
        return mensaje
    return {**mensaje, "adjuntos": [_adjunto_visible(a) for a in mensaje["adjuntos"]]}


def _resumir(conversacion: dict, yo: int) -> dict:
    mensajes = conversacion["mensajes"]
    return {
        "id": conversacion["id"],
        "con": _el_otro(conversacion, yo),
        "ultimo": _visible(mensajes[-1]) if mensajes else None,
        "sinLeer": _sin_leer(conversacion, yo),
    }


def _buscar(id_conversacion: int, yo: int) -> dict:
    conversacion = next((c for c in d.conversaciones if c["id"] == id_conversacion), None)
    if not conversacion or not _es_mia(conversacion, yo):
        raise HTTPException(404, "Conversación no encontrada")
    return conversacion


@router.get("", summary="Las conversaciones del usuario y el total sin leer")
def listar_conversaciones(yo: int = IdUsuarioActual):
    lista = sorted(
        (_resumir(c, yo) for c in d.conversaciones if _es_mia(c, yo)),
        key=lambda c: d.desde_iso(c["ultimo"]["fecha"]) if c["ultimo"] else d.desde_iso("1970-01-01T00:00:00.000Z"),
        reverse=True,
    )
    return {"conversaciones": lista, "sinLeer": sum(c["sinLeer"] for c in lista)}


@router.get("/contactos", summary="Gente de tus módulos con la que podés hablar")
def listar_contactos(yo: int = IdUsuarioActual):
    """Va declarada antes que /{id}: si no, "contactos" se tomaría como un
    identificador."""
    return [{**d.con_presencia(c), "modulos": c["modulos"]} for c in d.contactos_de(yo)]


@router.get("/{id_conversacion}", summary="Abrir una conversación y darla por leída")
def obtener_conversacion(id_conversacion: int, yo: int = IdUsuarioActual):
    conversacion = _buscar(id_conversacion, yo)

    for mensaje in conversacion["mensajes"]:
        if mensaje["deId"] != yo:
            mensaje["leido"] = True

    return {
        "id": conversacion["id"],
        "con": _el_otro(conversacion, yo),
        "mensajes": [_visible(m) for m in conversacion["mensajes"]],
        # El mensaje fijado, si hay alguno. Uno solo por conversación: con
        # varios deja de ser «lo importante» y vuelve a ser la conversación.
        "fijado": conversacion.get("fijado"),
    }


# Lo mismo que cualquier otra imagen del campus: un chat no es el lugar para
# mandar un libro —para eso está la Biblioteca—, pero una foto sacada con el
# celular tiene que entrar.
ADJUNTO_MAX_MB = archivos.IMAGENES_MAX_MB


def _guardar_adjunto(crudo: dict, conversacion: dict, yo: int) -> dict:
    """Escribe el archivo y devuelve lo que se guarda dentro del mensaje."""
    contenido, ficha = archivos.leer_subida(crudo, max_mb=ADJUNTO_MAX_MB)

    # Un tramo al azar para que dos archivos con el mismo nombre en la misma
    # conversación no se pisen: "foto.jpg" lo manda todo el mundo.
    objeto = alm.clave(alm.MENSAJES, conversacion["id"], secrets.token_hex(4),
                       nombre=ficha["nombre"])
    try:
        alm.subir(objeto, contenido, ficha["tipo"])
    except Exception as error:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo guardar «{ficha['nombre']}»: {error}")

    alm.registrar(
        objeto,
        nombre=ficha["nombre"],
        tipo=ficha["tipo"],
        tamano=ficha["tamano"],
        persona_id=yo,
        modulo=alm.MENSAJES,
        registro_id=conversacion["id"],
    )

    return {
        "nombre": ficha["nombre"],
        "tamano": ficha["tamano"],
        "tipo": ficha["tipo"],
        # Se guarda la clave, no la dirección: la arma `_adjunto_visible`
        # cada vez que se lee (ver ahí el porqué).
        "objectKey": objeto,
        # Para que el chat sepa si puede mostrarlo o solo ofrecer la descarga
        "esImagen": ficha["tipo"].startswith("image/"),
    }


@router.post("/{id_conversacion}", status_code=201, summary="Enviar un mensaje")
def enviar_mensaje(
    id_conversacion: int, cuerpo: dict[str, Any] = Body(default={}), yo: int = IdUsuarioActual
):
    conversacion = _buscar(id_conversacion, yo)

    texto = str(cuerpo.get("texto") or "").strip()

    # Los adjuntos van a Cloudflare R2 como todo lo demás. Antes se guardaba
    # solo el nombre y el tamaño: el chat mostraba "foto.jpg · 41 KB" y no
    # había foto, que es peor que no poder adjuntar.
    #
    # Se escriben **antes** de anotar el mensaje: si uno falla, la ruta corta
    # con error y no queda un mensaje prometiendo un archivo que no está.
    recibidos = cuerpo.get("adjuntos")
    adjuntos = []
    if isinstance(recibidos, list):
        for a in recibidos[:5]:
            adjuntos.append(_guardar_adjunto(a or {}, conversacion, yo))

    if not texto and not adjuntos:
        raise HTTPException(400, "El mensaje no puede estar vacío")

    mensaje = {
        "id": d.nuevo_id_mensaje(),
        "deId": yo,
        "texto": texto,
        "adjuntos": adjuntos,
        "fecha": d.iso(d.ahora()),
        "leido": True,
    }
    conversacion["mensajes"].append(mensaje)

    return _visible(mensaje)


def _buscar_mensaje(conversacion: dict, id_mensaje: int) -> dict:
    mensaje = next((m for m in conversacion["mensajes"] if m["id"] == id_mensaje), None)
    if not mensaje:
        raise HTTPException(404, "Ese mensaje no existe")
    return mensaje


@router.patch("/{id_conversacion}/mensajes/{id_mensaje}", summary="Editar un mensaje propio")
def editar_mensaje(
    id_conversacion: int,
    id_mensaje: int,
    cuerpo: dict[str, Any] = Body(default={}),
    yo: int = IdUsuarioActual,
):
    """Solo el texto, y solo el propio.

    No se edita el mensaje de otro: en una conversación de a dos, poder
    cambiar lo que dijo el otro convierte el chat en algo que no se puede
    usar como constancia de nada.

    Queda marcado como editado. Ocultar que se cambió es peor que no poder
    cambiarlo: el otro leyó una cosa y después ve otra.
    """
    conversacion = _buscar(id_conversacion, yo)
    mensaje = _buscar_mensaje(conversacion, id_mensaje)
    if mensaje["deId"] != yo:
        raise HTTPException(403, "Solo podés editar tus propios mensajes")

    texto = str(cuerpo.get("texto") or "").strip()
    if not texto and not mensaje.get("adjuntos"):
        raise HTTPException(400, "El mensaje no puede quedar vacío")

    mensaje["texto"] = texto
    mensaje["editado"] = d.iso(d.ahora())
    return _visible(mensaje)


@router.delete("/{id_conversacion}/mensajes/{id_mensaje}", summary="Eliminar un mensaje propio")
def eliminar_mensaje(id_conversacion: int, id_mensaje: int, yo: int = IdUsuarioActual):
    """Se borra el propio, y se borra de verdad: también su archivo.

    Dejar el archivo en el almacenamiento después de borrar el mensaje es
    pagar lugar por algo que ya nadie puede ver, y es justamente lo que
    alguien quiso sacar.
    """
    conversacion = _buscar(id_conversacion, yo)
    mensaje = _buscar_mensaje(conversacion, id_mensaje)
    if mensaje["deId"] != yo:
        raise HTTPException(403, "Solo podés eliminar tus propios mensajes")

    for adjunto in mensaje.get("adjuntos") or []:
        if adjunto.get("objectKey"):
            alm.olvidar(adjunto["objectKey"])

    conversacion["mensajes"].remove(mensaje)
    if conversacion.get("fijado") == id_mensaje:
        conversacion["fijado"] = None
    return {"eliminado": id_mensaje}


@router.post("/{id_conversacion}/mensajes/{id_mensaje}/fijar", summary="Fijar o soltar un mensaje")
def fijar_mensaje(id_conversacion: int, id_mensaje: int, yo: int = IdUsuarioActual):
    """Uno solo por conversación, y lo puede fijar cualquiera de los dos.

    Sirve para lo que hay que tener a mano: la fecha de un parcial, un aula.
    Que sea uno solo es a propósito: con varios deja de ser "lo importante"
    y vuelve a ser la conversación entera.

    Se puede fijar el mensaje del otro: lo que importa tener a la vista
    normalmente lo dijo el docente, no uno.
    """
    conversacion = _buscar(id_conversacion, yo)
    _buscar_mensaje(conversacion, id_mensaje)
    # Tocar el que ya estaba fijado lo suelta
    conversacion["fijado"] = None if conversacion.get("fijado") == id_mensaje else id_mensaje
    return {"fijado": conversacion.get("fijado")}


_abriendo = threading.Lock()


@router.post("", summary="Abrir la conversación con alguien, o crearla")
def abrir_conversacion(cuerpo: dict[str, Any] = Body(default={}), yo: int = IdUsuarioActual):
    try:
        para_id = int(cuerpo.get("paraId"))
    except (TypeError, ValueError):
        raise HTTPException(400, "No se puede abrir una conversación con esa persona")

    persona = d.buscar_persona(para_id)
    if not persona or para_id == yo:
        raise HTTPException(400, "No se puede abrir una conversación con esa persona")

    # «¿Ya hay una? → si no, crearla» va junto: dos que se escriben a la vez,
    # o un doble clic, creaban dos conversaciones de la misma pareja
    # (`pruebas/concurrencia.py`). En memoria y sin nada más adentro.
    with _abriendo:
        conversacion = next(
            (c for c in d.conversaciones if _es_mia(c, yo) and para_id in c["entre"]), None
        )
        if not conversacion:
            conversacion = {
                "id": d.nuevo_id_conversacion(),
                "entre": [yo, para_id],
                "mensajes": [],
            }
            d.conversaciones.append(conversacion)

    return {
        "id": conversacion["id"],
        "con": _el_otro(conversacion, yo),
        "mensajes": [_visible(m) for m in conversacion["mensajes"]],
        # El mensaje fijado, si hay alguno. Uno solo por conversación: con
        # varios deja de ser «lo importante» y vuelve a ser la conversación.
        "fijado": conversacion.get("fijado"),
    }
