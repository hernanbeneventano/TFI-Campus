"""Registro de las rutas del campus."""

from __future__ import annotations

from . import (
    comunicacion,
    general,
    vistas_archivos,
    vistas_asistencias,
    vistas_auditoria,
    vistas_biblioteca,
    vistas_calendario,
    vistas_cursos,
    vistas_finales,
    vistas_gestion_finales,
    vistas_gestion_modulo,
    vistas_inscripciones,
    vistas_institucion,
    vistas_mi_cursada,
    vistas_panel,
    vistas_salud,
    vistas_tareas,
    vistas_usuarios,
)

urlpatterns = [
    *general.urlpatterns,
    *vistas_salud.urlpatterns,
    *vistas_archivos.urlpatterns,
    *vistas_cursos.urlpatterns,
    *vistas_tareas.urlpatterns,
    *comunicacion.urlpatterns,
    *vistas_calendario.urlpatterns,
    *vistas_biblioteca.urlpatterns,
    *vistas_finales.urlpatterns,
    *vistas_gestion_finales.urlpatterns,
    *vistas_gestion_modulo.urlpatterns,
    *vistas_mi_cursada.urlpatterns,
    *vistas_institucion.urlpatterns,
    *vistas_usuarios.urlpatterns,
    *vistas_asistencias.urlpatterns,
    *vistas_inscripciones.urlpatterns,
    *vistas_auditoria.urlpatterns,
    *vistas_panel.urlpatterns,
]

handler404 = "campus_django.vistas.no_encontrada"
