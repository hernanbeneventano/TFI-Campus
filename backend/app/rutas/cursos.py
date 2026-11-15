"""Módulos del estudiante y todo el contenido de la pantalla de un módulo."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import datos as d
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/cursos", tags=["Cursos"])

# Se importa acá y no arriba porque `gestion_modulo` declara su router con
# el mismo prefijo y los dos se registran en `main`: importarlo al principio
# no rompe, pero deja el orden de carga menos obvio de lo necesario.
from . import gestion_modulo  # noqa: E402

DIAS = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _cursada_de(curso_id: int) -> list[dict]:
    """El horario semanal del módulo: no aparece en ninguna otra parte de la
    pantalla, hay que ir al calendario para verlo."""
    return [
        {"dia": DIAS[c["dia"]], "desde": c["desde"], "hasta": c["hasta"], "aula": c["aula"]}
        for c in d.clases
        if c["cursoId"] == curso_id
    ]


def _proximas_de(curso_id: int) -> list[dict]:
    """Lo que se viene en este módulo: entregas sin hacer y exámenes, de lo más
    cercano a lo más lejano.

    En las carpetas están, pero hay que abrirlas una por una para enterarse.
    """
    ahora = d.ahora()

    entregas = [
        {"tipo": "entrega", "titulo": t["titulo"], "fecha": t["fechaLimite"], "tareaId": t["id"]}
        for t in d.tareas
        if t["cursoId"] == curso_id
        and not t["entregada"]
        and d.desde_iso(t["fechaLimite"]) >= ahora
    ]

    examenes = [
        {"tipo": "examen", "titulo": e["titulo"], "fecha": e["fecha"], "lugar": e.get("lugar")}
        for e in d.eventos
        if e.get("cursoId") == curso_id
        and e.get("tipo") == "examen"
        and d.desde_iso(e["fecha"]) >= ahora
    ]

    return sorted(entregas + examenes, key=lambda x: d.desde_iso(x["fecha"]))[:4]


def _carrera_de_curso(curso_id: int) -> dict:
    """La carrera a la que pertenece un módulo.

    El módulo no la guarda: la sabe la materia del plan que apunta a él con
    `cursoId`. Se resuelve acá y no en la pantalla porque es la misma vuelta
    que haría cada una por su cuenta.

    Un módulo sin materia en el plan —los de prueba, o uno creado a mano— se
    queda sin carrera y la pantalla lo agrupa aparte.
    """
    materia = next((m for m in d.materias_plan if m.get("cursoId") == curso_id), None)
    if not materia:
        return {"carreraId": None, "carrera": None}
    carrera = d.buscar_en(d.carreras_institucion, materia.get("carreraId"))
    return {
        "carreraId": materia.get("carreraId"),
        "carrera": carrera["nombre"] if carrera else None,
    }


@router.get("", summary="Listar los módulos de quien consulta")
def listar_cursos(yo: dict = UsuarioActual):
    """Los módulos propios, que no son los mismos según quién pregunte.

    - **Administrador y supervisor**: todos. No cursan ni dictan nada, así que
      con la regla de los demás la pantalla les quedaba vacía, y justamente
      son quienes tienen que poder mirar cualquier materia de cualquier
      carrera.
    - **Docente**: los que tiene a cargo. No los que cursa nadie más: un
      docente no dicta la materia de otro y verla en su grilla solo lo haría
      buscar la suya entre materias ajenas.
    - **Estudiante**: aquellos en los que está inscripto.

    Lo usa tanto la pantalla Módulos como la lista que cuelga del menú
    lateral, así que las dos quedan consistentes con una sola regla.
    """
    if d.tiene_rol(yo, "Administrador", "Supervisor"):
        mios = list(d.cursos)
    elif d.tiene_rol(yo, "Docente"):
        mios = [c for c in d.cursos if c.get("docenteId") == yo["id"]]
    else:
        mios = [
            c for c in d.cursos if any(p["id"] == yo["id"] for p in d.participantes_de_curso(c))
        ]

    # Cada curso viaja con sus novedades, para la campanita de la tarjeta, y
    # con su carrera, que es como se agrupan en la pantalla.
    return [
        {**curso, "novedades": d.novedades_de_curso(curso), **_carrera_de_curso(curso["id"])}
        for curso in mios
    ]


@router.get("/{id_curso}", summary="Obtener un módulo")
def obtener_curso(id_curso: int):
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")
    return curso


@router.get("/{id_curso}/modulo", summary="Todo el contenido de la pantalla de un módulo")
def obtener_modulo(id_curso: int, yo: dict = UsuarioActual):
    """El curso, sus carpetas de contenido, los anuncios y la gente inscripta.

    Va en una sola consulta: resolverlo con cuatro multiplicaba los estados
    intermedios de carga en la pantalla.
    """
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")

    return {
        "curso": curso,
        # Si quien mira es el docente a cargo, la pantalla ofrece el modo
        # editor. Es solo para no mostrar botones que no van: cada ruta de
        # `rutas/gestion_modulo.py` lo vuelve a comprobar por su cuenta.
        "puedeGestionar": gestion_modulo.puede_gestionar(yo, curso),
        "cursada": _cursada_de(id_curso),
        "proximas": _proximas_de(id_curso),
        "carpetas": d.carpetas_de_curso(curso),
        "anuncios": d.anuncios.get(id_curso) or d.anuncios_genericos(curso),
        # El último acceso y el estado de presencia se calculan ahora
        "participantes": [d.con_presencia(p) for p in d.participantes_de_curso(curso)],
    }


@router.post("/{id_curso}/favorito", summary="Marcar o desmarcar un módulo como favorito")
def alternar_favorito(id_curso: int):
    """Hoy queda en memoria, como el resto de los datos; con Firestore pasa a
    ser por usuario."""
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "Curso no encontrado")

    curso["favorito"] = not curso["favorito"]
    return {**curso, "novedades": d.novedades_de_curso(curso)}
