"""Las rutas que atiende Django.

Cada módulo migrado tiene su archivo con su `urlpatterns`, y se suma acá. El
despachador solo le manda a Django lo que está en `MIGRADOS`: una ruta que
esté acá y no allá no la ve nadie.

Migrados: el calendario, el panel, las tareas pendientes, la auditoría, la
inscripción a materias, la mitad del alumno de Finales y los archivos.

Cuando se migre un módulo, sus rutas se agregan con el **mismo camino y en
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

from . import archivos, auditoria, calendario, finales, inscripciones, panel, tareas

urlpatterns: list = [
    *calendario.urlpatterns,
    *panel.urlpatterns,
    *tareas.urlpatterns,
    *auditoria.urlpatterns,
    *inscripciones.urlpatterns,
    *finales.urlpatterns,
    *archivos.urlpatterns,
]

handler404 = "campus_django.vistas.no_encontrada"
