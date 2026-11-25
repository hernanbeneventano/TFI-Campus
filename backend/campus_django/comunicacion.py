"""Vistas Django nativas para Mensajes, Foro y Novedades."""

from __future__ import annotations

import json
from email.message import Message

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path

from app.errores import ErrorDeAPI
from app.rutas import foro as operaciones_foro
from app.rutas import mensajes as operaciones_mensajes
from app.rutas import novedades as operaciones_novedades
from app.servicios.autenticacion import identificar, identificar_id


def _json(datos, estado: int = 200) -> JsonResponse:
    respuesta = JsonResponse(
        datos,
        status=estado,
        safe=False,
        json_dumps_params={"ensure_ascii": False, "separators": (",", ":")},
    )
    respuesta["Content-Length"] = str(len(respuesta.content))
    return respuesta


def _error(error: ErrorDeAPI) -> JsonResponse:
    detalle = error.mensaje
    if error.estado == 404 and detalle == "Not Found":
        detalle = "Ruta no encontrada"
    return _json({"error": detalle}, error.estado)


def _no_permitido(permitidos: tuple[str, ...]) -> JsonResponse:
    del permitidos
    return _json({"error": "Method Not Allowed"}, 405)


def _cuerpo(request: HttpRequest, requerido: bool = False) -> dict:
    crudo = request.body
    if not crudo:
        if requerido:
            raise ValueError
        return {}

    tipo = request.headers.get("content-type")
    if tipo:
        mensaje = Message()
        mensaje["content-type"] = tipo
        if mensaje.get_content_maintype() != "application":
            raise ValueError
        subtipo = mensaje.get_content_subtype()
        if subtipo != "json" and not subtipo.endswith("+json"):
            raise ValueError

    try:
        valor = json.loads(crudo)
    except (UnicodeDecodeError, ValueError):
        raise ValueError from None
    if valor is None and not requerido:
        return {}
    if not isinstance(valor, dict):
        raise ValueError
    return valor


def _id(valor: str) -> int:
    try:
        return int(valor)
    except ValueError:
        raise ValueError from None


def _invalido() -> JsonResponse:
    return _json({"error": "Los datos enviados no son válidos"}, 400)


def conversaciones(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        try:
            return _json(operaciones_mensajes.listar_conversaciones(identificar_id(request)))
        except ErrorDeAPI as error:
            return _error(error)
    if request.method == "POST":
        try:
            cuerpo = _cuerpo(request)
        except ValueError:
            return _invalido()
        try:
            yo = identificar_id(request)
            return _json(operaciones_mensajes.abrir_conversacion(cuerpo, yo))
        except ErrorDeAPI as error:
            return _error(error)
    return _no_permitido(("GET", "POST"))


def contactos(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return conversacion(request, "contactos")
    if request.method != "GET":
        return _no_permitido(("GET", "POST"))
    try:
        return _json(operaciones_mensajes.listar_contactos(identificar_id(request)))
    except ErrorDeAPI as error:
        return _error(error)


def conversacion(request: HttpRequest, id_conversacion: str) -> HttpResponse:
    if request.method == "GET":
        try:
            yo = identificar_id(request)
        except ErrorDeAPI as error:
            return _error(error)
        try:
            identificador = _id(id_conversacion)
        except ValueError:
            return _invalido()
        try:
            return _json(
                operaciones_mensajes.obtener_conversacion(identificador, yo)
            )
        except ErrorDeAPI as error:
            return _error(error)
    if request.method == "POST":
        try:
            cuerpo = _cuerpo(request)
        except ValueError:
            return _invalido()
        try:
            yo = identificar_id(request)
        except ErrorDeAPI as error:
            return _error(error)
        try:
            identificador = _id(id_conversacion)
        except ValueError:
            return _invalido()
        try:
            return _json(
                operaciones_mensajes.enviar_mensaje(identificador, cuerpo, yo),
                201,
            )
        except ErrorDeAPI as error:
            return _error(error)
    return _no_permitido(("GET", "POST"))


def mensaje(request: HttpRequest, id_conversacion: str, id_mensaje: str) -> HttpResponse:
    if request.method == "PATCH":
        try:
            cuerpo = _cuerpo(request)
        except ValueError:
            return _invalido()
        try:
            yo = identificar_id(request)
        except ErrorDeAPI as error:
            return _error(error)
        try:
            conversacion_id = _id(id_conversacion)
            mensaje_id = _id(id_mensaje)
        except ValueError:
            return _invalido()
        try:
            return _json(
                operaciones_mensajes.editar_mensaje(
                    conversacion_id, mensaje_id, cuerpo, yo
                )
            )
        except ErrorDeAPI as error:
            return _error(error)
    if request.method == "DELETE":
        try:
            yo = identificar_id(request)
        except ErrorDeAPI as error:
            return _error(error)
        try:
            conversacion_id = _id(id_conversacion)
            mensaje_id = _id(id_mensaje)
        except ValueError:
            return _invalido()
        try:
            return _json(
                operaciones_mensajes.eliminar_mensaje(
                    conversacion_id, mensaje_id, yo
                )
            )
        except ErrorDeAPI as error:
            return _error(error)
    return _no_permitido(("DELETE", "PATCH"))


def fijar_mensaje(
    request: HttpRequest, id_conversacion: str, id_mensaje: str
) -> HttpResponse:
    if request.method != "POST":
        return _no_permitido(("POST",))
    try:
        yo = identificar_id(request)
    except ErrorDeAPI as error:
        return _error(error)
    try:
        conversacion_id = _id(id_conversacion)
        mensaje_id = _id(id_mensaje)
    except ValueError:
        return _invalido()
    try:
        return _json(
            operaciones_mensajes.fijar_mensaje(conversacion_id, mensaje_id, yo)
        )
    except ErrorDeAPI as error:
        return _error(error)


def foro(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        try:
            return _json(operaciones_foro.listar_temas(identificar(request)))
        except ErrorDeAPI as error:
            return _error(error)
    if request.method == "POST":
        try:
            cuerpo = _cuerpo(request)
        except ValueError:
            return _invalido()
        try:
            yo = identificar(request)
            return _json(operaciones_foro.crear_tema(cuerpo, yo), 201)
        except ErrorDeAPI as error:
            return _error(error)
    return _no_permitido(("GET", "POST"))


def tema(request: HttpRequest, id_tema: str) -> HttpResponse:
    if request.method == "GET":
        try:
            yo = identificar(request)
        except ErrorDeAPI as error:
            return _error(error)
        try:
            identificador = _id(id_tema)
        except ValueError:
            return _invalido()
        try:
            return _json(operaciones_foro.obtener_tema(identificador, yo))
        except ErrorDeAPI as error:
            return _error(error)
    if request.method in {"POST", "DELETE"}:
        try:
            cuerpo = _cuerpo(request)
        except ValueError:
            return _invalido()
        try:
            yo = identificar(request)
        except ErrorDeAPI as error:
            return _error(error)
        try:
            identificador = _id(id_tema)
        except ValueError:
            return _invalido()
        try:
            if request.method == "POST":
                return _json(operaciones_foro.responder(identificador, cuerpo, yo), 201)
            return _json(operaciones_foro.retirar_tema(identificador, cuerpo, yo))
        except ErrorDeAPI as error:
            return _error(error)
    return _no_permitido(("DELETE", "GET", "POST"))


def seguir_tema(request: HttpRequest, id_tema: str) -> HttpResponse:
    if request.method != "POST":
        return _no_permitido(("POST",))
    try:
        yo = identificar(request)
    except ErrorDeAPI as error:
        return _error(error)
    try:
        identificador = _id(id_tema)
    except ValueError:
        return _invalido()
    try:
        return _json(operaciones_foro.seguir(identificador, yo))
    except ErrorDeAPI as error:
        return _error(error)


def voto_foro(
    request: HttpRequest, id_tema: str, id_mensaje: str
) -> HttpResponse:
    if request.method != "POST":
        return _no_permitido(("POST",))
    try:
        yo = identificar(request)
    except ErrorDeAPI as error:
        return _error(error)
    try:
        tema_id = _id(id_tema)
        mensaje_id = _id(id_mensaje)
    except ValueError:
        return _invalido()
    try:
        return _json(operaciones_foro.votar(tema_id, mensaje_id, yo))
    except ErrorDeAPI as error:
        return _error(error)


def respuesta_foro(
    request: HttpRequest, id_tema: str, id_mensaje: str
) -> HttpResponse:
    if request.method != "DELETE":
        return _no_permitido(("DELETE",))
    try:
        cuerpo = _cuerpo(request)
    except ValueError:
        return _invalido()
    try:
        yo = identificar(request)
    except ErrorDeAPI as error:
        return _error(error)
    try:
        tema_id = _id(id_tema)
        mensaje_id = _id(id_mensaje)
    except ValueError:
        return _invalido()
    try:
        return _json(
            operaciones_foro.retirar_respuesta(tema_id, mensaje_id, cuerpo, yo)
        )
    except ErrorDeAPI as error:
        return _error(error)


def novedades(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        try:
            return _json(operaciones_novedades.listar_publicaciones(identificar(request)))
        except ErrorDeAPI as error:
            return _error(error)
    if request.method == "POST":
        try:
            cuerpo = _cuerpo(request)
        except ValueError:
            return _invalido()
        try:
            yo = identificar(request)
            return _json(operaciones_novedades.crear_publicacion(cuerpo, yo), 201)
        except ErrorDeAPI as error:
            return _error(error)
    return _no_permitido(("GET", "POST"))


def novedad(request: HttpRequest, id_publicacion: str) -> HttpResponse:
    if request.method not in {"PUT", "DELETE"}:
        return _no_permitido(("DELETE", "PUT"))
    try:
        cuerpo = _cuerpo(request)
    except ValueError:
        return _invalido()
    try:
        yo = identificar(request)
    except ErrorDeAPI as error:
        return _error(error)
    try:
        identificador = _id(id_publicacion)
    except ValueError:
        return _invalido()
    try:
        if request.method == "PUT":
            return _json(
                operaciones_novedades.editar_publicacion(identificador, cuerpo, yo)
            )
        return _json(
            operaciones_novedades.retirar_publicacion(identificador, cuerpo, yo)
        )
    except ErrorDeAPI as error:
        return _error(error)


def imagen_novedad(
    request: HttpRequest, id_publicacion: str
) -> HttpResponse:
    if request.method not in {"POST", "DELETE"}:
        return _no_permitido(("DELETE", "POST"))
    if request.method == "POST":
        try:
            cuerpo = _cuerpo(request, requerido=True)
        except ValueError:
            return _invalido()
    else:
        cuerpo = {}
    try:
        yo = identificar(request)
    except ErrorDeAPI as error:
        return _error(error)
    try:
        identificador = _id(id_publicacion)
    except ValueError:
        return _invalido()
    try:
        if request.method == "POST":
            return _json(
                operaciones_novedades.subir_imagen(identificador, cuerpo, yo)
            )
        return _json(operaciones_novedades.quitar_imagen(identificador, yo))
    except ErrorDeAPI as error:
        return _error(error)


def reaccion_novedad(
    request: HttpRequest, id_publicacion: str
) -> HttpResponse:
    if request.method != "POST":
        return _no_permitido(("POST",))
    try:
        cuerpo = _cuerpo(request)
    except ValueError:
        return _invalido()
    try:
        yo = identificar(request)
    except ErrorDeAPI as error:
        return _error(error)
    try:
        identificador = _id(id_publicacion)
    except ValueError:
        return _invalido()
    try:
        return _json(
            operaciones_novedades.reaccionar(identificador, cuerpo, yo)
        )
    except ErrorDeAPI as error:
        return _error(error)


urlpatterns = [
    path("api/mensajes", conversaciones),
    path("api/mensajes/contactos", contactos),
    path("api/mensajes/<str:id_conversacion>", conversacion),
    path(
        "api/mensajes/<str:id_conversacion>/mensajes/<str:id_mensaje>/fijar",
        fijar_mensaje,
    ),
    path(
        "api/mensajes/<str:id_conversacion>/mensajes/<str:id_mensaje>",
        mensaje,
    ),
    path("api/foro", foro),
    path("api/foro/<str:id_tema>/seguir", seguir_tema),
    path(
        "api/foro/<str:id_tema>/mensajes/<str:id_mensaje>/voto",
        voto_foro,
    ),
    path(
        "api/foro/<str:id_tema>/mensajes/<str:id_mensaje>",
        respuesta_foro,
    ),
    path("api/foro/<str:id_tema>", tema),
    path("api/novedades", novedades),
    path("api/novedades/<str:id_publicacion>/imagen", imagen_novedad),
    path("api/novedades/<str:id_publicacion>/reaccion", reaccion_novedad),
    path("api/novedades/<str:id_publicacion>", novedad),
]
