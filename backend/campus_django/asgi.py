"""Aplicación ASGI de Django con gestión de arranque y cierre del campus."""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_django.settings")

from asgiref.sync import sync_to_async
from django.core.asgi import get_asgi_application

from app import main

_django = get_asgi_application()


async def aplicacion(scope, receive, send):
    if scope["type"] != "lifespan":
        await _django(scope, receive, send)
        return

    while True:
        mensaje = await receive()
        if mensaje["type"] == "lifespan.startup":
            try:
                await sync_to_async(main.al_arrancar, thread_sensitive=True)()
            except Exception as error:
                await send(
                    {
                        "type": "lifespan.startup.failed",
                        "message": repr(error),
                    }
                )
                raise
            await send({"type": "lifespan.startup.complete"})
        elif mensaje["type"] == "lifespan.shutdown":
            await sync_to_async(main.al_cerrar, thread_sensitive=True)()
            await send({"type": "lifespan.shutdown.complete"})
            return
