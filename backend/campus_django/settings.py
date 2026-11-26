"""Configuración de Django para el campus.

Es la mínima a propósito. Django vale por su ORM, su panel de administración
y sus migraciones, y el campus no usa ninguna de las tres: los datos viven en
Firestore y en la memoria del servidor, y la administración es la de React.
Todo lo que se agregue acá es algo que puede cambiar una respuesta, así que
solo está lo que hace falta para que Django funcione como enrutador.

Variables de entorno
--------------------
Ninguna es obligatoria para desarrollar. Están documentadas en
`.env.example`.

DJANGO_SECRET_KEY
    Django no arranca sin una. El campus no la usa para nada —no hay
    sesiones, ni CSRF, ni firmas de Django—, así que si falta se sortea una al
    arrancar, en vez de dejar una escrita en el repositorio, que sería un
    secreto publicado. En producción conviene fijarla igual, para que no
    cambie entre reinicios si algún día se usa.

DJANGO_DEBUG
    Apagado salvo que diga «si». Con `DEBUG` encendido, un error muestra la
    traza y la configuración en la respuesta: es el descuido más caro de
    Django en producción. Los errores públicos y los internos se formatean
    con el middleware del campus.

DJANGO_ALLOWED_HOSTS
    Separados por comas. Con un host que no esté en la lista, Django contesta
    400 a todo. Por omisión: los de desarrollo y `testserver`, que es el que
    usan los clientes de prueba.
"""

from __future__ import annotations

import os
import secrets

from app.servicios import frenos


def _si(valor: str | None) -> bool:
    return (valor or "").strip().lower() in ("si", "sí", "1", "true")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50)

DEBUG = _si(os.environ.get("DJANGO_DEBUG"))

ALLOWED_HOSTS = [
    h.strip()
    for h in (
        os.environ.get("DJANGO_ALLOWED_HOSTS") or "localhost,127.0.0.1,testserver"
    ).split(",")
    if h.strip()
]

# ===================== Sin base de datos =====================
# Ni ORM ni módulos de `contrib`: `auth`, `sessions` y `admin` piden una base,
# y el campus no la tiene. Firestore se usa a través de `app/servicios/`.
INSTALLED_APPS: list[str] = []
DATABASES: dict = {}

# ===================== Middleware =====================
# El orden conserva la política de respuesta: el freno ocurre antes de CORS;
# los errores de las vistas pasan por CORS y los errores internos no.
MIDDLEWARE = [
    "campus_django.middleware.ErrorInternoMiddleware",
    "campus_django.middleware.FrenoMiddleware",
    "campus_django.middleware.GuardadoMiddleware",
    "campus_django.middleware.IPMiddleware",
    "campus_django.middleware.CorsMiddleware",
    "campus_django.middleware.ErrorDeAPIMiddleware",
]

ROOT_URLCONF = "campus_django.urls"

# Django middleware serializa los errores públicos del campus; los errores
# inesperados se registran y responden como 500 sin exponer la traza.
DEBUG_PROPAGATE_EXCEPTIONS = False

# ===================== El tamaño de lo que llega =====================
# Por omisión Django rechaza cuerpos de más de 2,5 MB con un 400 propio. Los
# archivos viajan en base64 adentro del JSON, así que eso cortaría casi todas
# las subidas. El tope lo pone el freno del campus, con su 413 y su mensaje:
# Django tiene que aceptar exactamente hasta donde el freno deja pasar.
DATA_UPLOAD_MAX_MEMORY_SIZE = frenos.MAXIMO_BYTES

# Django corta por omisión una consulta de más de 1000 parámetros
# (`?a=1&b=2…`). El tamaño máximo total ya lo controla el freno del campus, así
# que el número de campos no necesita otro tope.
DATA_UPLOAD_MAX_NUMBER_FIELDS = None

# La barra final se resuelve en `vistas.no_encontrada` con un 307.
APPEND_SLASH = False

# ===================== El registro =====================
# Django anota cada 404 en su propio registro. El servidor ya anota cada
# petición, así que eso solo duplicaría las líneas de la consola.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {"django.request": {"level": "ERROR"}},
}

USE_TZ = True
