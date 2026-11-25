"""Middleware nativo de Django para errores, límites, auditoría y CORS."""

from __future__ import annotations

import logging

from asgiref.sync import markcoroutinefunction
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from app.errores import ErrorDeAPI
from app.servicios import auditoria, frenos, persistencia

from .respuestas import error_json, json_respuesta

logger = logging.getLogger(__name__)

METODOS_CORS = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")


class ErrorDeAPIMiddleware(MiddlewareMixin):
    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        if not isinstance(exception, ErrorDeAPI):
            return None
        return json_respuesta(
            {"error": exception.mensaje},
            exception.estado,
            exception.cabeceras,
        )


class ErrorInternoMiddleware(MiddlewareMixin):
    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse:
        logger.exception("Error no previsto al atender %s %s", request.method, request.path)
        return error_json("Error interno del servidor", 500)


class FrenoMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        if frenos.demasiado_grande(request):
            return error_json(
                f"El envío supera los {frenos.MAXIMO_MB} MB.",
                413,
            )
        if frenos.excede(request):
            respuesta = error_json(
                "Demasiadas peticiones seguidas. Esperá un momento.",
                429,
            )
            respuesta["Retry-After"] = str(frenos.VENTANA_SEGUNDOS)
            return respuesta
        return None


class GuardadoMiddleware(MiddlewareMixin):
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if response.status_code < 500 and persistencia.activo():
            persistencia.guardar_cambios()
        return response


class IPMiddleware:
    sync_capable = False
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        marca = auditoria.peticion_actual.set(request)
        try:
            return await self.get_response(request)
        finally:
            auditoria.peticion_actual.reset(marca)


class CorsMiddleware(MiddlewareMixin):
    sync_capable = False
    async_capable = True

    def __init__(self, get_response):
        super().__init__(get_response)
        markcoroutinefunction(self)
        import os

        self.origenes = {os.environ.get("FRONTEND_URL") or "http://localhost:5173"}

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        origen = request.headers.get("origin")
        preflight = (
            request.method == "OPTIONS"
            and request.headers.get("access-control-request-method") is not None
        )
        if preflight and origen is not None:
            respuesta = HttpResponse("OK", content_type="text/plain")
            respuesta["Vary"] = "Origin"
            respuesta["Access-Control-Allow-Methods"] = ", ".join(METODOS_CORS)
            respuesta["Access-Control-Max-Age"] = "600"
            fallas = []
            if origen in self.origenes:
                respuesta["Access-Control-Allow-Origin"] = origen
            else:
                fallas.append("origin")
            if request.headers["access-control-request-method"] not in METODOS_CORS:
                fallas.append("method")
            pedidas = request.headers.get("access-control-request-headers")
            if pedidas is not None:
                respuesta["Access-Control-Allow-Headers"] = pedidas
            if fallas:
                respuesta = HttpResponse(
                    "Disallowed CORS " + ", ".join(fallas),
                    status=400,
                    content_type="text/plain",
                )
                respuesta["Vary"] = "Origin"
                respuesta["Access-Control-Allow-Methods"] = ", ".join(METODOS_CORS)
                respuesta["Access-Control-Max-Age"] = "600"
                if origen in self.origenes:
                    respuesta["Access-Control-Allow-Origin"] = origen
                if pedidas is not None:
                    respuesta["Access-Control-Allow-Headers"] = pedidas
            return respuesta

        respuesta = await self.get_response(request)
        if origen in self.origenes and respuesta.status_code < 500:
            respuesta["Access-Control-Allow-Origin"] = origen
            vary = respuesta.headers.get("Vary")
            if vary is None:
                respuesta["Vary"] = "Origin"
            elif "origin" not in {parte.strip().lower() for parte in vary.split(",")}:
                respuesta["Vary"] = vary + ", Origin"
        return respuesta
