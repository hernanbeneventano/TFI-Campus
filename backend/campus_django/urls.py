"""Las rutas que atiende Django.

**En la fase 0 no hay ninguna.** El despachador manda todo a FastAPI, y Django
solo está montado para poder probarlo.

Cuando se migre un módulo, sus rutas se agregan acá con el **mismo camino y en
el mismo orden** que en `app/main.py`. El orden importa por dos motivos: las
rutas con nombre fijo (`/contactos`, `/favoritos`) van antes que las que
toman un identificador, y `cursos` y `gestion_modulo` comparten el prefijo
`/api/cursos`.

Los parámetros de camino van siempre como `<str:...>` —o `<path:...>` donde
FastAPI usa `:path`—, **nunca** `<int:...>`: con `<int:>` un identificador no
numérico daría 404, y hoy da 400 con «Los datos enviados no son válidos». La
conversión la hace `adaptadores.entero`, dentro de la vista y después de
comprobar la sesión, que es el orden en que lo hace FastAPI.
"""

from __future__ import annotations

urlpatterns: list = []

handler404 = "campus_django.vistas.no_encontrada"
