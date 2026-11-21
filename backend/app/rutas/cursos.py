"""Módulos del estudiante y todo el contenido de la pantalla de un módulo."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import modulos as mod
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/cursos", tags=["Cursos"])

# Se importa acá y no arriba porque `gestion_modulo` declara su router con
# el mismo prefijo y los dos se registran en `main`: importarlo al principio
# no rompe, pero deja el orden de carga menos obvio de lo necesario.
from . import gestion_modulo  # noqa: E402


# El horario semanal lo arma `servicios/modulos.py`: lo necesita también la
# gestión del módulo, y dos copias terminarían mostrando cosas distintas.
_cursada_de = mod.cursada_de


def puede_ver(yo: dict, curso: dict) -> bool:
    """Si esa persona tiene algo que hacer en ese módulo.

    Es la misma regla con la que `listar_cursos` arma la grilla, puesta en un
    solo lugar: quien administra o supervisa ve todo el campus, el docente lo
    que dicta y el estudiante aquello en lo que está inscripto.

    Sin esto, el contenido, los anuncios y la lista de participantes de
    cualquier materia salían con solo cambiar el número en la dirección.
    """
    if d.tiene_rol(yo, "Administrador", "Supervisor"):
        return True
    if curso.get("docenteId") == yo["id"]:
        return True
    return any(p["id"] == yo["id"] for p in d.participantes_de_curso(curso))


def _curso_mio(id_curso: int, yo: dict) -> dict:
    """El módulo, si le corresponde a quien pregunta.

    Fuera de alcance responde **404 y no 403**, como en Biblioteca, Finales y
    Auditoría: un 403 ya confirma que ese módulo existe.
    """
    curso = d.buscar_curso(id_curso)
    if not curso or not puede_ver(yo, curso):
        raise HTTPException(404, "Curso no encontrado")
    return curso


def es_favorito(persona_id: int, curso_id: int) -> bool:
    return any(
        f["personaId"] == persona_id and f["cursoId"] == curso_id for f in d.favoritos_modulo
    )


def _proximas_de(curso_id: int, persona_id=None) -> list[dict]:
    """Lo que se viene en este módulo: entregas sin hacer y exámenes, de lo más
    cercano a lo más lejano.

    En las carpetas están, pero hay que abrirlas una por una para enterarse.

    "Sin hacer" es **de quien mira**: antes salía de un booleano del trabajo,
    igual para todo el curso, así que una entrega hecha por otro desaparecía
    de los pendientes de todos.
    """
    ahora = d.ahora()

    entregas = [
        {"tipo": "entrega", "titulo": t["titulo"], "fecha": t["fechaLimite"], "tareaId": t["id"]}
        for t in d.tareas
        if t["cursoId"] == curso_id
        and not d.entrego(persona_id, t)
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

    Viajan también el **año y el cuatrimestre del plan**, que es como la
    pantalla separa los módulos. El `periodo` del módulo ("2026 – 2.º
    cuatrimestre") no alcanza: junta en un mismo grupo el segundo cuatrimestre
    de primero con el de segundo año, que es justo lo que hay que distinguir.
    """
    materia = next((m for m in d.materias_plan if m.get("cursoId") == curso_id), None)
    if not materia:
        return {"carreraId": None, "carrera": None, "anio": None, "cuatrimestre": None}
    carrera = d.buscar_en(d.carreras_institucion, materia.get("carreraId"))
    return {
        "carreraId": materia.get("carreraId"),
        "carrera": carrera["nombre"] if carrera else None,
        "anio": materia.get("anio"),
        "cuatrimestre": materia.get("cuatrimestre"),
    }


@router.get("", summary="Listar los módulos de quien consulta")
def listar_cursos(yo: dict = UsuarioActual):
    """Los módulos propios, que no son los mismos según quién pregunte.

    - **Administrador y supervisor**: todos. No cursan ni dictan nada, así que
      con la regla de los demás la pantalla les quedaba vacía, y justamente
      son quienes tienen que poder mirar cualquier materia de cualquier
      carrera.
    - **Docente**: los de las materias que tiene asignadas, aunque todavía no
      tengan a nadie inscripto ni contenido cargado. No los de otra cátedra:
      un docente no dicta la materia de otro y verla en su grilla solo lo
      haría buscar la suya entre materias ajenas.
    - **Estudiante**: aquellos en los que está inscripto.

    Lo usa tanto la pantalla Módulos como la lista que cuelga del menú
    lateral, así que las dos quedan consistentes con una sola regla.
    """
    if d.tiene_rol(yo, "Administrador", "Supervisor"):
        # Los de todo el campus, **creándolos si faltan**: el módulo existe
        # desde que se le asigna la materia a un docente, no desde que ese
        # docente entra a verla. Sin esto la secretaría veía "0 módulos" con
        # el plan cargado y los dictados puestos.
        mod.modulos_con_catedra()
        mios = list(d.cursos)
    elif d.tiene_rol(yo, "Docente"):
        # Los módulos de lo que dicta, **creándolos si hace falta**: el
        # docente tiene que poder cargar contenido el día que le asignan la
        # materia, no el día que se anota el primer alumno.
        mod.modulos_que_dicta(yo["id"])
        mios = [c for c in d.cursos if c.get("docenteId") == yo["id"]]
    else:
        # Los de las materias a las que está inscripto, **creándolos si hace
        # falta**: a una inscripción se llega por varios caminos —se anota él,
        # o la institución lo pone en una comisión— y si uno de ellos no creó
        # el módulo, el alumno queda inscripto y con la pantalla vacía.
        mod.modulos_en_los_que_cursa(yo["id"])
        mios = [
            c for c in d.cursos if any(p["id"] == yo["id"] for p in d.participantes_de_curso(c))
        ]

    # Cada curso viaja con sus novedades, para la campanita de la tarjeta, con
    # su carrera, que es como se agrupan en la pantalla, y con **su** estrella:
    # el favorito es de cada persona, no del módulo.
    return [
        {
            **curso,
            "favorito": es_favorito(yo["id"], curso["id"]),
            "novedades": d.novedades_de_curso(curso),
            **_carrera_de_curso(curso["id"]),
        }
        for curso in mios
    ]


@router.get("/{id_curso}", summary="Obtener un módulo")
def obtener_curso(id_curso: int, yo: dict = UsuarioActual):
    curso = _curso_mio(id_curso, yo)
    return {**curso, "favorito": es_favorito(yo["id"], curso["id"])}


@router.get("/{id_curso}/modulo", summary="Todo el contenido de la pantalla de un módulo")
def obtener_modulo(id_curso: int, yo: dict = UsuarioActual):
    """El curso, sus carpetas de contenido, los anuncios y la gente inscripta.

    Va en una sola consulta: resolverlo con cuatro multiplicaba los estados
    intermedios de carga en la pantalla.
    """
    curso = _curso_mio(id_curso, yo)

    return {
        "curso": {**curso, "favorito": es_favorito(yo["id"], curso["id"])},
        # Si quien mira es el docente a cargo, la pantalla ofrece el modo
        # editor. Es solo para no mostrar botones que no van: cada ruta de
        # `rutas/gestion_modulo.py` lo vuelve a comprobar por su cuenta.
        "puedeGestionar": gestion_modulo.puede_gestionar(yo, curso),
        "cursada": _cursada_de(id_curso),
        "proximas": _proximas_de(id_curso, yo["id"]),
        # Con quién mira: "entregada" es de cada uno, no del curso
        "carpetas": d.carpetas_de_curso(curso, yo["id"]),
        "anuncios": d.anuncios.get(id_curso) or d.anuncios_genericos(curso),
        # El último acceso y el estado de presencia se calculan ahora
        "participantes": [d.con_presencia(p) for p in d.participantes_de_curso(curso)],
    }


# ===================== El tablero de consultas =====================
# Un elemento de tipo tablero es el lugar donde se pregunta: columnas con
# publicaciones cortas. El botón «+ Publicar» estaba dibujado y **no hacía
# nada** —no había ruta—, así que la única forma de agregarle algo era tocar
# la base. Un tablero al que no se puede escribir no es un tablero.
MAXIMO_PUBLICACION = 1000


def _tablero_de(curso: dict, id_item: str) -> dict:
    """El tablero vivo, el de `datos.contenidos`.

    No sirve el que devuelve `carpetas_de_curso`: ahí los elementos vienen
    resueltos para la pantalla —copias—, y escribir en una copia se pierde al
    responder. Un módulo sin contenido propio no tiene tableros que valgan:
    lo que se le escribiera no quedaría guardado en ningún lado.
    """
    propias = d.contenidos.get(curso["id"])
    if not propias:
        raise HTTPException(404, "Ese tablero no existe en este módulo")

    for carpeta in propias:
        for item in carpeta.get("items") or []:
            if str(item.get("id")) == str(id_item):
                if item.get("tipo") != "tablero":
                    raise HTTPException(400, "Ese elemento no es un tablero")
                return item
    raise HTTPException(404, "Ese tablero no existe en este módulo")


@router.post(
    "/{id_curso}/tableros/{id_item}/publicaciones",
    status_code=201,
    summary="Publicar en el tablero de consultas",
)
def publicar_en_tablero(
    id_curso: int, id_item: str, cuerpo: dict = Body(default={}), yo: dict = UsuarioActual
):
    """Escribe **cualquiera del módulo**, no solo la cátedra.

    El tablero es donde se pregunta: limitarlo al docente lo dejaría sin uso.
    Lo que sí hace falta es estar en el módulo, que es lo que comprueba
    `_curso_mio`.
    """
    curso = _curso_mio(id_curso, yo)
    tablero = _tablero_de(curso, id_item)

    texto = str(cuerpo.get("texto") or "").strip()
    if not texto:
        raise HTTPException(400, "La consulta no puede estar vacía")
    if len(texto) > MAXIMO_PUBLICACION:
        raise HTTPException(400, f"La consulta no puede pasar de {MAXIMO_PUBLICACION} caracteres")

    buscada = str(cuerpo.get("columna") or "").strip()
    columna = next((c for c in tablero["columnas"] if c["titulo"] == buscada), None)
    if columna is None:
        raise HTTPException(404, "Ese tablero no tiene esa columna")

    columna.setdefault("publicaciones", [])
    usados = [
        p["id"]
        for c in tablero["columnas"]
        for p in (c.get("publicaciones") or [])
        if isinstance(p.get("id"), int)
    ]
    publicacion = {
        "id": max(usados, default=0) + 1,
        "autor": yo["nombre"],
        # El id además del nombre: el nombre se puede repetir y además cambia
        # si alguien corrige cómo se escribe.
        "autorId": yo["id"],
        "fecha": d.iso(d.ahora()),
        "texto": texto,
    }
    columna["publicaciones"].append(publicacion)
    return publicacion


@router.post("/{id_curso}/favorito", summary="Marcar o desmarcar un módulo como favorito")
def alternar_favorito(id_curso: int, yo: dict = UsuarioActual):
    """La estrella es **de quien la pone**, no del módulo.

    Antes era un booleano adentro del curso: marcar Programación II se la
    dejaba marcada a todo el campus, y la ruta ni siquiera pedía sesión.
    """
    curso = _curso_mio(id_curso, yo)

    marcado = next(
        (
            f
            for f in d.favoritos_modulo
            if f["personaId"] == yo["id"] and f["cursoId"] == curso["id"]
        ),
        None,
    )
    if marcado:
        d.favoritos_modulo.remove(marcado)
    else:
        d.favoritos_modulo.append({"personaId": yo["id"], "cursoId": curso["id"]})

    return {
        **curso,
        "favorito": marcado is None,
        "novedades": d.novedades_de_curso(curso),
        **_carrera_de_curso(curso["id"]),
    }
