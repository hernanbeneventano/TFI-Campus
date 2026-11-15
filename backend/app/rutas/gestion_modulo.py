"""Administración de un módulo por parte de su docente.

Es la contracara de `rutas/cursos.py`: ahí el módulo se lee, acá se arma.
Cubre las tres cosas que el docente necesita hacer sobre su materia:

- **Contenido**: secciones (las "semanas") y lo que va adentro —páginas,
  archivos, trabajos y tableros—, con alta, edición, baja y reordenamiento.
- **Anuncios**: publicar, corregir y dar de baja.
- **Notas**: la grilla de la cursada, una calificación por alumno y trabajo.

Va en un archivo aparte y no dentro de `cursos.py` porque son dos públicos
distintos: todo lo de acá exige ser el docente a cargo, y mezclarlo obligaría
a preguntar el rol en cada función de la pantalla del alumno.

**Quién puede.** El docente a cargo del módulo (`curso["docenteId"]`), y quien
supervise cuando ese rol exista. No alcanza con ser docente: un docente no
administra la materia de otro. Se verifica acá, en cada ruta; que el frontend
esconda el modo editor es una comodidad, no un control.

El contenido de un módulo que nunca se editó se arma al vuelo (ver
`datos.contenido_generico`). La primera edición lo materializa con
`datos.asegurar_contenido`, porque si no el cambio se perdería en el pedido
siguiente.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import cursada as c
from ..servicios import auditoria
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/cursos", tags=["Gestión del módulo"])

TIPOS_ITEM = ("pagina", "archivo", "tarea", "tablero")

# Un título más largo que esto no entra en la fila y no se lee
MAX_TITULO = 120
MAX_DESCRIPCION = 300
MAX_CUERPO = 20_000
MAX_COMENTARIO = 1_000


# ===================== Permisos =====================
def _es_supervisor(persona: dict) -> bool:
    """Todavía no hay rol de administrador. Cuando exista, va acá.

    Es la misma función que en `rutas/gestion_finales.py`: el día que el rol
    exista, hay que cambiar los dos.
    """
    return d.tiene_rol(persona, "Administrador", "Supervisor")


def puede_gestionar(yo: dict, curso: dict) -> bool:
    """Solo el docente a cargo de ese módulo, o quien supervise."""
    if _es_supervisor(yo):
        return True
    return d.tiene_rol(yo, "Docente") and curso.get("docenteId") == yo["id"]


def _curso_que_administra(id_curso: int, yo: dict) -> dict:
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "El módulo no existe")
    if not puede_gestionar(yo, curso):
        raise HTTPException(403, "Solo el docente a cargo puede administrar este módulo")
    return curso


# ===================== Validación =====================
def _texto(valor: Any, campo: str, maximo: int, obligatorio: bool = True) -> str | None:
    if valor is None:
        if obligatorio:
            raise HTTPException(400, f"Falta {campo}")
        return None
    if not isinstance(valor, str):
        raise HTTPException(400, f"{campo} tiene que ser texto")
    limpio = valor.strip()
    if not limpio:
        if obligatorio:
            raise HTTPException(400, f"Falta {campo}")
        return None
    if len(limpio) > maximo:
        raise HTTPException(400, f"{campo} no puede pasar de {maximo} caracteres")
    return limpio


def _buscar_carpeta(carpetas: list[dict], id_carpeta: int) -> dict:
    carpeta = next((c for c in carpetas if c["id"] == id_carpeta), None)
    if not carpeta:
        raise HTTPException(404, "La sección no existe")
    return carpeta


def _buscar_item(carpeta: dict, id_item: str) -> dict:
    item = next((i for i in carpeta["items"] if str(i["id"]) == str(id_item)), None)
    if not item:
        raise HTTPException(404, "El elemento no existe")
    return item


def _mover(lista: list, indice: int, cuerpo: dict) -> None:
    """Reordena un elemento.

    Con `posicion` lo lleva a ese lugar, que es lo que manda el arrastre con
    el mouse. Con `hacia` lo sube o lo baja un lugar, que es lo que manda el
    teclado: arrastrar no se puede hacer sin mouse, así que las dos formas
    tienen que existir.
    """
    posicion = cuerpo.get("posicion")
    if posicion is not None:
        if not isinstance(posicion, int):
            raise HTTPException(400, "La posición tiene que ser un número")
        # Se acota en vez de rechazar: soltar más abajo del último es
        # "ponelo último", no un error.
        destino = max(0, min(posicion, len(lista) - 1))
    else:
        hacia = cuerpo.get("hacia")
        if hacia not in ("arriba", "abajo"):
            raise HTTPException(400, "Falta decir a dónde moverlo")
        destino = indice - 1 if hacia == "arriba" else indice + 1
        if destino < 0 or destino >= len(lista):
            return

    if destino == indice:
        return
    lista.insert(destino, lista.pop(indice))


def _contenido_actualizado(curso: dict) -> dict:
    """Lo que devuelve toda ruta que toca el contenido.

    Se manda el módulo entero y no solo lo que cambió: crear un trabajo toca
    las carpetas y la lista de tareas a la vez, y que la pantalla rearme todo
    de una evita quedar con la mitad vieja.
    """
    return {
        "carpetas": d.carpetas_de_curso(curso),
        "puedeGestionar": True,
    }


# ===================== Secciones =====================
@router.post("/{id_curso}/carpetas", status_code=201, summary="Crear una sección")
def crear_carpeta(id_curso: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    curso = _curso_que_administra(id_curso, yo)
    titulo = _texto(cuerpo.get("titulo"), "el título de la sección", MAX_TITULO)
    descripcion = _texto(
        cuerpo.get("descripcion"), "la descripción", MAX_DESCRIPCION, obligatorio=False
    )

    carpetas = d.asegurar_contenido(curso)
    carpetas.append(
        {
            "id": d.nuevo_id_carpeta(),
            "titulo": titulo,
            "descripcion": descripcion,
            "items": [],
        }
    )
    return _contenido_actualizado(curso)


@router.patch("/{id_curso}/carpetas/{id_carpeta}", summary="Editar una sección")
def editar_carpeta(
    id_curso: int, id_carpeta: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual
):
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.asegurar_contenido(curso)
    carpeta = _buscar_carpeta(carpetas, id_carpeta)

    if "titulo" in cuerpo:
        carpeta["titulo"] = _texto(cuerpo["titulo"], "el título de la sección", MAX_TITULO)
    if "descripcion" in cuerpo:
        carpeta["descripcion"] = _texto(
            cuerpo["descripcion"], "la descripción", MAX_DESCRIPCION, obligatorio=False
        )
    return _contenido_actualizado(curso)


@router.delete("/{id_curso}/carpetas/{id_carpeta}", summary="Borrar una sección")
def borrar_carpeta(id_curso: int, id_carpeta: int, yo: dict = UsuarioActual):
    """Se lleva lo que tiene adentro, incluidos los trabajos.

    Borrar una sección con material adentro es la acción más destructiva de
    esta pantalla, así que la interfaz avisa qué se va antes de llamar acá.
    """
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.asegurar_contenido(curso)
    carpeta = _buscar_carpeta(carpetas, id_carpeta)

    # Las tareas viven en su propia lista: hay que sacarlas también, o quedan
    # colgadas apareciendo en el panel de pendientes del alumno.
    ids_tarea = {i.get("tareaId") for i in carpeta["items"] if i.get("tipo") == "tarea"}
    if ids_tarea:
        d.tareas[:] = [t for t in d.tareas if t["id"] not in ids_tarea]
        d.calificaciones[:] = [c for c in d.calificaciones if c["tareaId"] not in ids_tarea]

    carpetas.remove(carpeta)
    return _contenido_actualizado(curso)


@router.post("/{id_curso}/carpetas/{id_carpeta}/mover", summary="Reordenar una sección")
def mover_carpeta(
    id_curso: int, id_carpeta: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual
):
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.asegurar_contenido(curso)
    carpeta = _buscar_carpeta(carpetas, id_carpeta)
    _mover(carpetas, carpetas.index(carpeta), cuerpo)
    return _contenido_actualizado(curso)


# ===================== Elementos =====================
def _armar_preguntas(crudas) -> list[dict]:
    """Valida las preguntas de un cuestionario.

    Dos opciones es el mínimo para que elegir signifique algo, y seis el
    máximo que entra en pantalla sin que haya que desplazarse.
    """
    if not isinstance(crudas, list):
        raise HTTPException(400, "Las preguntas tienen que venir en una lista")
    if len(crudas) > 50:
        raise HTTPException(400, "Son demasiadas preguntas para un cuestionario")

    preguntas = []
    for n, cruda in enumerate(crudas, start=1):
        if not isinstance(cruda, dict):
            raise HTTPException(400, f"La pregunta {n} no tiene el formato esperado")

        texto = _texto(cruda.get("texto"), f"el enunciado de la pregunta {n}", 500)
        opciones = cruda.get("opciones")
        if not isinstance(opciones, list) or not 2 <= len(opciones) <= 6:
            raise HTTPException(400, f"La pregunta {n} necesita entre 2 y 6 opciones")

        limpias = [_texto(o, f"una opción de la pregunta {n}", 200) for o in opciones]

        correcta = cruda.get("correcta")
        if not isinstance(correcta, int) or not 0 <= correcta < len(limpias):
            raise HTTPException(400, f"Hay que marcar cuál es la correcta en la pregunta {n}")

        puntaje = cruda.get("puntaje", 1)
        if not isinstance(puntaje, int) or not 1 <= puntaje <= 10:
            raise HTTPException(400, f"El puntaje de la pregunta {n} va de 1 a 10")

        preguntas.append(
            {
                "id": n,
                "texto": texto,
                "opciones": limpias,
                "correcta": correcta,
                "puntaje": puntaje,
            }
        )
    return preguntas


def _armar_item(curso: dict, carpeta: dict, cuerpo: dict) -> dict:
    tipo = cuerpo.get("tipo")
    if tipo not in TIPOS_ITEM:
        raise HTTPException(400, "El tipo de elemento no es válido")

    titulo = _texto(cuerpo.get("titulo"), "el título", MAX_TITULO)
    # El id lleva el curso adelante, como los que ya venían en los datos
    item: dict = {
        "id": f"{curso['id']}-{d.nuevo_id_carpeta()}",
        "tipo": tipo,
        "titulo": titulo,
    }

    if tipo == "pagina":
        cuerpo_pagina = cuerpo.get("cuerpo")
        if isinstance(cuerpo_pagina, str):
            cuerpo_pagina = [p.strip() for p in cuerpo_pagina.split("\n\n") if p.strip()]
        if not isinstance(cuerpo_pagina, list) or not cuerpo_pagina:
            raise HTTPException(400, "La página necesita un texto")
        largo = sum(len(p) for p in cuerpo_pagina if isinstance(p, str))
        if largo > MAX_CUERPO:
            raise HTTPException(400, "El texto de la página es demasiado largo")
        item["cuerpo"] = [p for p in cuerpo_pagina if isinstance(p, str)]

    elif tipo == "archivo":
        # Todavía no se sube el archivo: se guarda la ficha. Con Firebase
        # Storage, acá pasa a haber una referencia al bucket.
        item["formato"] = _texto(cuerpo.get("formato"), "el formato", 30) or "PDF"
        item["tamano"] = _texto(cuerpo.get("tamano"), "el tamaño", 30, obligatorio=False) or "—"
        enlace = _texto(cuerpo.get("enlace"), "el enlace", 500, obligatorio=False)
        if enlace:
            if not enlace.startswith(("http://", "https://")):
                raise HTTPException(400, "El enlace tiene que empezar con http:// o https://")
            item["enlace"] = enlace

    elif tipo == "tarea":
        fecha_limite = cuerpo.get("fechaLimite")
        if not isinstance(fecha_limite, str) or not fecha_limite.strip():
            raise HTTPException(400, "El trabajo necesita una fecha de entrega")
        try:
            d.desde_iso(fecha_limite)
        except ValueError:
            raise HTTPException(400, "La fecha de entrega no es válida")

        modalidad = cuerpo.get("modalidad") or "virtual"
        if modalidad not in d.MODALIDADES_TRABAJO:
            raise HTTPException(400, "La modalidad tiene que ser virtual o presencial")

        # Un presencial no tiene formato que elegir: se rinde en el aula y la
        # nota la carga el docente al cerrar.
        if modalidad == "presencial":
            formato = "presencial"
        else:
            formato = cuerpo.get("formato") or "entrega"
            if formato not in ("entrega", "cuestionario"):
                raise HTTPException(400, "El formato tiene que ser entrega o cuestionario")

        preguntas = _armar_preguntas(cuerpo.get("preguntas")) if formato == "cuestionario" else []
        if formato == "cuestionario" and not preguntas:
            raise HTTPException(400, "Un cuestionario necesita al menos una pregunta")

        tarea = {
            "id": d.nuevo_id_tarea(),
            "cursoId": curso["id"],
            "titulo": titulo,
            "publicada": d.iso(d.ahora()),
            "fechaLimite": fecha_limite,
            "entregada": False,
            # None = la fecha manda. True/False = el docente lo cerró o lo
            # reabrió a mano, y eso pesa más que la fecha.
            "cerrada": None,
            "consigna": _texto(cuerpo.get("consigna"), "la consigna", MAX_CUERPO, False),
            "modalidad": modalidad,
            "formato": formato,
            "preguntas": preguntas,
        }
        d.tareas.append(tarea)
        item["tareaId"] = tarea["id"]

    return item


@router.post(
    "/{id_curso}/carpetas/{id_carpeta}/items", status_code=201, summary="Agregar un elemento"
)
def crear_item(
    id_curso: int, id_carpeta: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual
):
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.asegurar_contenido(curso)
    carpeta = _buscar_carpeta(carpetas, id_carpeta)
    carpeta["items"].append(_armar_item(curso, carpeta, cuerpo))
    return _contenido_actualizado(curso)


@router.patch("/{id_curso}/carpetas/{id_carpeta}/items/{id_item}", summary="Editar un elemento")
def editar_item(
    id_curso: int,
    id_carpeta: int,
    id_item: str,
    cuerpo: dict = Body(...),
    yo: dict = UsuarioActual,
):
    """El tipo no se cambia: una página no se convierte en un trabajo.

    Para eso hay que borrarlo y crear el que corresponde, que además deja
    claro que las entregas del trabajo viejo no sobreviven.
    """
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.asegurar_contenido(curso)
    carpeta = _buscar_carpeta(carpetas, id_carpeta)
    item = _buscar_item(carpeta, id_item)

    if "titulo" in cuerpo:
        item["titulo"] = _texto(cuerpo["titulo"], "el título", MAX_TITULO)
        if item["tipo"] == "tarea":
            tarea = d.buscar_tarea(item.get("tareaId"))
            if tarea:
                tarea["titulo"] = item["titulo"]

    if item["tipo"] == "pagina" and "cuerpo" in cuerpo:
        texto = cuerpo["cuerpo"]
        if isinstance(texto, str):
            texto = [p.strip() for p in texto.split("\n\n") if p.strip()]
        if not isinstance(texto, list) or not texto:
            raise HTTPException(400, "La página necesita un texto")
        item["cuerpo"] = [p for p in texto if isinstance(p, str)]

    if item["tipo"] == "archivo":
        if "formato" in cuerpo:
            item["formato"] = _texto(cuerpo["formato"], "el formato", 30)
        if "tamano" in cuerpo:
            item["tamano"] = _texto(cuerpo["tamano"], "el tamaño", 30, obligatorio=False) or "—"

    if item["tipo"] == "tarea":
        tarea = d.buscar_tarea(item.get("tareaId"))
        if tarea and "fechaLimite" in cuerpo:
            try:
                d.desde_iso(cuerpo["fechaLimite"])
            except (ValueError, TypeError, AttributeError):
                raise HTTPException(400, "La fecha de entrega no es válida")
            tarea["fechaLimite"] = cuerpo["fechaLimite"]
        if tarea and "consigna" in cuerpo:
            tarea["consigna"] = _texto(cuerpo["consigna"], "la consigna", MAX_CUERPO, False)
        if tarea and "preguntas" in cuerpo and tarea.get("formato") == "cuestionario":
            nuevas = _armar_preguntas(cuerpo["preguntas"])
            if not nuevas:
                raise HTTPException(400, "Un cuestionario necesita al menos una pregunta")
            # Cambiar las preguntas invalida lo ya respondido: las respuestas
            # viejas apuntaban a otras opciones y su nota dejaría de
            # significar nada.
            if any(r["tareaId"] == tarea["id"] for r in d.respuestas_cuestionario):
                raise HTTPException(
                    409,
                    "Ya hay alumnos que respondieron: no se pueden cambiar las preguntas. "
                    "Creá un cuestionario nuevo.",
                )
            tarea["preguntas"] = nuevas

    return _contenido_actualizado(curso)


@router.delete("/{id_curso}/carpetas/{id_carpeta}/items/{id_item}", summary="Borrar un elemento")
def borrar_item(id_curso: int, id_carpeta: int, id_item: str, yo: dict = UsuarioActual):
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.asegurar_contenido(curso)
    carpeta = _buscar_carpeta(carpetas, id_carpeta)
    item = _buscar_item(carpeta, id_item)

    if item.get("tipo") == "tarea" and item.get("tareaId"):
        id_tarea = item["tareaId"]
        d.tareas[:] = [t for t in d.tareas if t["id"] != id_tarea]
        d.calificaciones[:] = [c for c in d.calificaciones if c["tareaId"] != id_tarea]

    carpeta["items"].remove(item)
    return _contenido_actualizado(curso)


@router.post(
    "/{id_curso}/carpetas/{id_carpeta}/items/{id_item}/mover", summary="Reordenar un elemento"
)
def mover_item(
    id_curso: int,
    id_carpeta: int,
    id_item: str,
    cuerpo: dict = Body(...),
    yo: dict = UsuarioActual,
):
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.asegurar_contenido(curso)
    carpeta = _buscar_carpeta(carpetas, id_carpeta)
    item = _buscar_item(carpeta, id_item)
    _mover(carpeta["items"], carpeta["items"].index(item), cuerpo)
    return _contenido_actualizado(curso)


# ===================== Abrir y cerrar entregas =====================
@router.post("/{id_curso}/tareas/{id_tarea}/entrega", summary="Abrir o cerrar la entrega")
def alternar_entrega(
    id_curso: int, id_tarea: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual
):
    """Cierra un trabajo antes de la fecha, o lo reabre después.

    `abierta` manda sobre la fecha límite: sirve tanto para cortar las
    entregas apenas termina la clase como para darle una prórroga al curso
    sin tener que inventar otra fecha. Con `null` vuelve a mandar la fecha.
    """
    curso = _curso_que_administra(id_curso, yo)
    tarea = d.buscar_tarea(id_tarea)
    if not tarea or tarea["cursoId"] != curso["id"]:
        raise HTTPException(404, "El trabajo no existe en este módulo")

    if "abierta" not in cuerpo:
        raise HTTPException(400, "Falta decir si la entrega queda abierta o cerrada")
    abierta = cuerpo["abierta"]
    if abierta is None:
        tarea["cerrada"] = None
    elif isinstance(abierta, bool):
        tarea["cerrada"] = not abierta
    else:
        raise HTTPException(400, "«abierta» tiene que ser verdadero, falso o nulo")

    return _contenido_actualizado(curso)


# ===================== Anuncios =====================
def _anuncios_de(curso: dict) -> list[dict]:
    """Los anuncios propios del módulo, materializando los genéricos.

    Mismo caso que el contenido: los genéricos se arman al vuelo y hay que
    guardarlos antes de dejar que alguien los edite.
    """
    propios = d.anuncios.get(curso["id"])
    if propios is None:
        propios = d.anuncios_genericos(curso)
        d.anuncios[curso["id"]] = propios
    return propios


@router.post("/{id_curso}/anuncios", status_code=201, summary="Publicar un anuncio")
def crear_anuncio(id_curso: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    curso = _curso_que_administra(id_curso, yo)
    titulo = _texto(cuerpo.get("titulo"), "el título", MAX_TITULO)
    texto = _texto(cuerpo.get("cuerpo"), "el texto del anuncio", MAX_CUERPO)

    anuncios = _anuncios_de(curso)
    anuncio = {
        "id": d.nuevo_id_anuncio(),
        "titulo": titulo,
        "cuerpo": texto,
        "autor": yo["nombre"],
        "autorId": yo["id"],
        "fecha": d.iso(d.ahora()),
    }
    # Los más nuevos arriba: un anuncio recién publicado es el que importa
    anuncios.insert(0, anuncio)
    return {"anuncios": anuncios}


@router.patch("/{id_curso}/anuncios/{id_anuncio}", summary="Editar un anuncio")
def editar_anuncio(
    id_curso: int, id_anuncio: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual
):
    curso = _curso_que_administra(id_curso, yo)
    anuncios = _anuncios_de(curso)
    anuncio = next((a for a in anuncios if a["id"] == id_anuncio), None)
    if not anuncio:
        raise HTTPException(404, "El anuncio no existe")

    if "titulo" in cuerpo:
        anuncio["titulo"] = _texto(cuerpo["titulo"], "el título", MAX_TITULO)
    if "cuerpo" in cuerpo:
        anuncio["cuerpo"] = _texto(cuerpo["cuerpo"], "el texto del anuncio", MAX_CUERPO)
    anuncio["editado"] = d.iso(d.ahora())
    return {"anuncios": anuncios}


@router.delete("/{id_curso}/anuncios/{id_anuncio}", summary="Borrar un anuncio")
def borrar_anuncio(id_curso: int, id_anuncio: int, yo: dict = UsuarioActual):
    curso = _curso_que_administra(id_curso, yo)
    anuncios = _anuncios_de(curso)
    anuncio = next((a for a in anuncios if a["id"] == id_anuncio), None)
    if not anuncio:
        raise HTTPException(404, "El anuncio no existe")
    anuncios.remove(anuncio)
    return {"anuncios": anuncios}


# ===================== Seguimiento del curso =====================
def _alumnos_de(curso: dict) -> list[dict]:
    return [p for p in d.participantes_de_curso(curso) if d.tiene_rol(p, "Estudiante")]


def _completados_de(persona_id: int, curso_id: int) -> set[str]:
    return {
        p["itemId"]
        for p in d.progreso_alumnos
        if p["personaId"] == persona_id and p["cursoId"] == curso_id
    }


def _marcable(item: dict) -> bool:
    """Las tareas no se marcan: se dan por hechas al entregarlas.

    Es la misma regla que aplica el alumno en `services/progreso.js`.
    """
    return item.get("tipo") != "tarea"


@router.get("/{id_curso}/seguimiento", summary="Cómo viene el curso con el material")
def seguimiento(id_curso: int, yo: dict = UsuarioActual):
    """Dos vistas de lo mismo: por sección y por alumno.

    Al docente no le sirve su propio avance —el material lo subió él—, le
    sirve saber **cuántos de sus alumnos completaron cada sección**. Por eso
    en la cabecera de la carpeta, en modo docente, esta cuenta reemplaza a la
    barra de progreso personal.
    """
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.carpetas_de_curso(curso)
    alumnos = _alumnos_de(curso)
    completados = {a["id"]: _completados_de(a["id"], curso["id"]) for a in alumnos}

    def al_dia(alumno_id: int, items: list[dict]) -> bool:
        """Un alumno completó una sección si vio todo lo marcable y entregó
        todos sus trabajos."""
        suyos = completados[alumno_id]
        for item in items:
            if _marcable(item):
                if item["id"] not in suyos:
                    return False
            else:
                tarea = d.buscar_tarea(item.get("tareaId"))
                entregada = any(
                    c["tareaId"] == item.get("tareaId") and c["personaId"] == alumno_id
                    for c in d.calificaciones
                )
                if tarea and not entregada:
                    return False
        return True

    por_seccion = []
    for carpeta in carpetas:
        items = carpeta["items"]
        if not items or not alumnos:
            por_seccion.append(
                {
                    "id": carpeta["id"],
                    "titulo": carpeta["titulo"],
                    "alumnos": len(alumnos),
                    "completaron": 0,
                    "porcentaje": 0,
                    "elementos": len(items),
                }
            )
            continue
        cuantos = sum(1 for a in alumnos if al_dia(a["id"], items))
        por_seccion.append(
            {
                "id": carpeta["id"],
                "titulo": carpeta["titulo"],
                "alumnos": len(alumnos),
                "completaron": cuantos,
                "porcentaje": round(cuantos * 100 / len(alumnos)),
                "elementos": len(items),
            }
        )

    # Todo el material marcable del módulo, para el avance de cada alumno
    todos = [i for c in carpetas for i in c["items"]]
    marcables = [i for i in todos if _marcable(i)]
    trabajos = [t for t in d.tareas if t["cursoId"] == curso["id"]]

    por_alumno = []
    for alumno in alumnos:
        vistos = len([i for i in marcables if i["id"] in completados[alumno["id"]]])
        sus_notas = [
            c
            for c in d.calificaciones
            if c["cursoId"] == curso["id"] and c["personaId"] == alumno["id"]
        ]
        notas = [c["nota"] for c in sus_notas if isinstance(c.get("nota"), (int, float))]
        por_alumno.append(
            {
                "id": alumno["id"],
                "nombre": alumno["nombre"],
                "vistos": vistos,
                "material": len(marcables),
                "porcentaje": round(vistos * 100 / len(marcables)) if marcables else 0,
                "entregados": len(sus_notas),
                "trabajos": len(trabajos),
                "sinCorregir": sum(1 for c in sus_notas if c.get("nota") is None),
                "promedio": round(sum(notas) / len(notas), 2) if notas else None,
            }
        )

    completaron_todo = sum(
        1 for a in alumnos if all(al_dia(a["id"], c["items"]) for c in carpetas if c["items"])
    )

    return {
        "secciones": por_seccion,
        "alumnos": por_alumno,
        "resumen": {
            "alumnos": len(alumnos),
            "completaronTodo": completaron_todo,
            "porcentaje": round(completaron_todo * 100 / len(alumnos)) if alumnos else 0,
            "trabajos": len(trabajos),
            "sinCorregir": sum(
                1
                for c in d.calificaciones
                if c["cursoId"] == curso["id"] and c.get("nota") is None
            ),
        },
    }


@router.get("/{id_curso}/carpetas/{id_carpeta}/entregas", summary="Quién cumplió con una sección")
def entregas_de_seccion(id_curso: int, id_carpeta: int, yo: dict = UsuarioActual):
    """El detalle que hay detrás del porcentaje de la sección.

    Por cada alumno: qué material vio, qué entregó y qué le falta. Es lo que
    el docente necesita para corregir, y lo que el número solo no dice: un
    40% no distingue entre "a casi todos les falta una cosa" y "la mitad no
    abrió nada".
    """
    curso = _curso_que_administra(id_curso, yo)
    carpetas = d.carpetas_de_curso(curso)
    carpeta = _buscar_carpeta(carpetas, id_carpeta)
    alumnos = _alumnos_de(curso)

    material = [i for i in carpeta["items"] if _marcable(i)]
    trabajos = [
        t
        for t in (d.buscar_tarea(i.get("tareaId")) for i in carpeta["items"] if not _marcable(i))
        if t
    ]

    filas = []
    for alumno in alumnos:
        vistos = _completados_de(alumno["id"], curso["id"])
        suyos = []
        for trabajo in trabajos:
            entrega = next(
                (
                    e
                    for e in d.entregas
                    if e["tareaId"] == trabajo["id"] and e["personaId"] == alumno["id"]
                ),
                None,
            )
            nota = next(
                (
                    c
                    for c in d.calificaciones
                    if c["tareaId"] == trabajo["id"] and c["personaId"] == alumno["id"]
                ),
                None,
            )
            atrasada = (
                entrega is not None
                and d.desde_iso(entrega["fecha"]) > d.desde_iso(trabajo["fechaLimite"])
            )
            suyos.append(
                {
                    "tareaId": trabajo["id"],
                    "titulo": trabajo["titulo"],
                    "fechaLimite": trabajo["fechaLimite"],
                    "entregado": entrega is not None,
                    "fecha": entrega["fecha"] if entrega else None,
                    "archivo": entrega.get("archivo") if entrega else None,
                    "comentario": entrega.get("comentario") if entrega else None,
                    "atrasada": atrasada,
                    "nota": nota.get("nota") if nota else None,
                    "estado": nota.get("estado") if nota else None,
                    "devolucion": nota.get("comentario") if nota else None,
                    "corregido": bool(nota and nota.get("nota") is not None),
                }
            )

        vistos_aca = len([i for i in material if i["id"] in vistos])
        entregados = sum(1 for x in suyos if x["entregado"])
        filas.append(
            {
                "id": alumno["id"],
                "nombre": alumno["nombre"],
                "vistos": vistos_aca,
                "material": len(material),
                "entregados": entregados,
                "trabajos": len(trabajos),
                "sinCorregir": sum(1 for x in suyos if x["entregado"] and not x["corregido"]),
                "completo": vistos_aca == len(material) and entregados == len(trabajos),
                "detalle": suyos,
            }
        )

    # Primero los que necesitan atención: algo sin corregir, o incompletos
    filas.sort(key=lambda f: (-f["sinCorregir"], f["completo"], f["nombre"]))

    return {
        "seccion": {"id": carpeta["id"], "titulo": carpeta["titulo"]},
        "material": [{"id": i["id"], "titulo": i["titulo"]} for i in material],
        "trabajos": [{"id": t["id"], "titulo": t["titulo"]} for t in trabajos],
        "alumnos": filas,
        "estados": d.ESTADOS_CALIFICACION,
        "resumen": {
            "alumnos": len(alumnos),
            "completaron": sum(1 for f in filas if f["completo"]),
            "sinCorregir": sum(f["sinCorregir"] for f in filas),
        },
    }


# ===================== Notas =====================


@router.get("/{id_curso}/notas", summary="La grilla de notas del módulo")
def listar_notas(id_curso: int, yo: dict = UsuarioActual):
    """Alumnos por trabajos, con lo cargado hasta ahora.

    Se devuelven las dos listas por separado y las notas sueltas, en vez de
    una matriz ya armada: la pantalla necesita las cabeceras igual, y una
    matriz con huecos es más difícil de leer que una lista de lo que hay.
    """
    curso = _curso_que_administra(id_curso, yo)
    trabajos = [t for t in d.tareas if t["cursoId"] == curso["id"]]
    alumnos = _alumnos_de(curso)
    notas = [c for c in d.calificaciones if c["cursoId"] == curso["id"]]

    cargadas = [x["nota"] for x in notas if isinstance(x.get("nota"), (int, float))]

    # El cierre de cada alumno: promedio, condición y si va a final
    cierres = {a["id"]: c.cierre_de(a["id"], curso["id"]) for a in alumnos}

    return {
        "alumnos": [
            {"id": a["id"], "nombre": a["nombre"], "cierre": cierres[a["id"]]} for a in alumnos
        ],
        "trabajos": [
            {
                "id": t["id"],
                "titulo": t["titulo"],
                "fechaLimite": t["fechaLimite"],
                "cerrada": t.get("cerrada"),
                "modalidad": t.get("modalidad", "virtual"),
                "formato": t.get("formato", "entrega"),
                "preguntas": len(t.get("preguntas") or []),
            }
            for t in trabajos
        ],
        "notas": notas,
        "estados": d.ESTADOS_CALIFICACION,
        "notaParaAprobar": d.NOTA_PARA_APROBAR,
        "resumen": {
            "esperadas": len(alumnos) * len(trabajos),
            "cargadas": len(notas),
            "promedio": round(sum(cargadas) / len(cargadas), 2) if cargadas else None,
            "aprueban": sum(1 for x in cierres.values() if x["condicion"] == c.APROBADA),
            "vanAFinal": sum(1 for x in cierres.values() if x["vaAFinal"]),
        },
    }


@router.put("/{id_curso}/cierre", summary="Fijar a mano la condición de un alumno")
def fijar_cierre(id_curso: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """La condición que decide el docente pesa más que el promedio.

    Hay motivos que el sistema no conoce —una recuperación, una falta
    justificada, un acta ya firmada—. Con `condicion` en null vuelve a mandar
    el cálculo.
    """
    curso = _curso_que_administra(id_curso, yo)

    alumno = d.buscar_persona(cuerpo.get("personaId"))
    if not alumno or not any(a["id"] == alumno["id"] for a in _alumnos_de(curso)):
        raise HTTPException(404, "Esa persona no cursa este módulo")

    condicion = cuerpo.get("condicion")
    if condicion is None:
        return {"cierre": c.soltar_cierre(alumno["id"], curso["id"]), "personaId": alumno["id"]}

    if condicion not in (c.APROBADA, c.VA_A_FINAL):
        raise HTTPException(400, "La condición tiene que ser «Aprobada» o «Va a final»")

    observacion = _texto(cuerpo.get("observacion"), "la observación", MAX_COMENTARIO, False)
    return {
        "cierre": c.fijar_cierre(alumno["id"], curso["id"], condicion, observacion, yo["id"]),
        "personaId": alumno["id"],
    }


@router.get("/{id_curso}/tareas/{id_tarea}/cuestionario", summary="Respuestas de un cuestionario")
def respuestas_del_cuestionario(id_curso: int, id_tarea: int, yo: dict = UsuarioActual):
    """Qué respondió cada alumno, con el detalle por pregunta.

    Un cuestionario se corrige solo, así que esto no es para poner la nota:
    es para ver dónde se traba el curso. Si media clase erró la misma
    pregunta, el problema no es de ellos.
    """
    curso = _curso_que_administra(id_curso, yo)
    tarea = d.buscar_tarea(id_tarea)
    if not tarea or tarea["cursoId"] != curso["id"]:
        raise HTTPException(404, "El trabajo no existe en este módulo")
    if tarea.get("formato") != "cuestionario":
        raise HTTPException(400, "Ese trabajo no es un cuestionario")

    preguntas = tarea.get("preguntas") or []
    alumnos = _alumnos_de(curso)

    filas = []
    for alumno in alumnos:
        respuesta = c.respuesta_de(alumno["id"], id_tarea)
        filas.append(
            {
                "id": alumno["id"],
                "nombre": alumno["nombre"],
                "respondio": respuesta is not None,
                "fecha": respuesta["fecha"] if respuesta else None,
                "nota": respuesta.get("nota") if respuesta else None,
                "detalle": (
                    c.corregir_cuestionario(tarea, respuesta["respuestas"])["detalle"]
                    if respuesta
                    else []
                ),
            }
        )

    # Cuántos acertaron cada pregunta: lo que dice dónde está el problema
    por_pregunta = []
    for pregunta in preguntas:
        aciertos = sum(
            1
            for f in filas
            if any(x["preguntaId"] == pregunta["id"] and x["acerto"] for x in f["detalle"])
        )
        respondieron = sum(1 for f in filas if f["respondio"])
        por_pregunta.append(
            {
                "id": pregunta["id"],
                "texto": pregunta["texto"],
                "opciones": pregunta["opciones"],
                "correcta": pregunta["correcta"],
                "aciertos": aciertos,
                "respondieron": respondieron,
                "porcentaje": round(aciertos * 100 / respondieron) if respondieron else 0,
            }
        )

    return {
        "trabajo": {"id": tarea["id"], "titulo": tarea["titulo"]},
        "preguntas": por_pregunta,
        "alumnos": filas,
        "resumen": {
            "alumnos": len(alumnos),
            "respondieron": sum(1 for f in filas if f["respondio"]),
        },
    }


def _auditar_nota(yo, accion, curso, alumno, tarea, antes, despues, detalle):
    """Un movimiento de la grilla de notas, con la materia puesta.

    La materia es lo que después le permite al docente ver lo suyo en el
    registro y al supervisor filtrar por carrera.
    """
    materia = next((m for m in d.materias_plan if m.get("cursoId") == curso["id"]), None)
    auditoria.registrar(
        yo,
        accion,
        "calificaciones",
        elemento=f"{tarea['titulo']} · {alumno['nombre']}",
        elemento_id=tarea["id"],
        elemento_tipo="calificacion",
        persona_id=alumno["id"],
        materia_id=materia["id"] if materia else None,
        antes=antes,
        despues=despues,
        detalle=detalle,
    )


@router.put("/{id_curso}/notas", summary="Cargar o corregir una nota")
def guardar_nota(id_curso: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Una celda de la grilla. Si ya había nota, se reemplaza.

    Una nota en blanco borra la celda: es la forma de deshacer una carga
    equivocada sin tener otra ruta para eso.
    """
    curso = _curso_que_administra(id_curso, yo)

    tarea = d.buscar_tarea(cuerpo.get("tareaId"))
    if not tarea or tarea["cursoId"] != curso["id"]:
        raise HTTPException(404, "El trabajo no existe en este módulo")

    alumno = d.buscar_persona(cuerpo.get("personaId"))
    if not alumno or not any(a["id"] == alumno["id"] for a in _alumnos_de(curso)):
        raise HTTPException(404, "Esa persona no cursa este módulo")

    nota = cuerpo.get("nota")
    if nota is not None:
        try:
            nota = float(nota)
        except (TypeError, ValueError):
            raise HTTPException(400, "La nota tiene que ser un número")
        if not 1 <= nota <= 10:
            raise HTTPException(400, "La nota va de 1 a 10")
        # 7.5 se guarda como 7.5; 8.0 como 8, que es como se escribe
        nota = int(nota) if nota == int(nota) else round(nota, 2)

    estado = cuerpo.get("estado")
    if estado is not None and estado not in d.ESTADOS_CALIFICACION:
        raise HTTPException(400, "Ese estado de corrección no existe")

    comentario = _texto(cuerpo.get("comentario"), "el comentario", MAX_COMENTARIO, False)

    previa = next(
        (
            c
            for c in d.calificaciones
            if c["tareaId"] == tarea["id"] and c["personaId"] == alumno["id"]
        ),
        None,
    )

    # Sin nota, sin estado y sin comentario, la celda queda vacía
    if nota is None and not estado and not comentario:
        if previa:
            _auditar_nota(
                yo, "baja", curso, alumno, tarea,
                {"nota": previa.get("nota"), "estado": previa.get("estado")},
                None,
                "Borró la calificación",
            )
            d.calificaciones.remove(previa)
        return listar_notas(id_curso, yo)

    if previa:
        antes = {"nota": previa.get("nota"), "estado": previa.get("estado")}
        previa.update(
            {
                "nota": nota,
                "estado": estado or previa.get("estado"),
                "comentario": comentario,
                "docenteId": yo["id"],
                "fecha": d.iso(d.ahora()),
            }
        )
        _auditar_nota(
            yo, "edicion", curso, alumno, tarea,
            antes,
            {"nota": previa["nota"], "estado": previa.get("estado")},
            "Corrigió una calificación ya cargada",
        )
    else:
        d.calificaciones.append(
            {
                "id": d.nuevo_id_calificacion(),
                "cursoId": curso["id"],
                "tareaId": tarea["id"],
                "personaId": alumno["id"],
                "nota": nota,
                "estado": estado or ("Aprobado" if (nota or 0) >= 6 else "Desaprobado"),
                "comentario": comentario,
                "docenteId": yo["id"],
                "fecha": d.iso(d.ahora()),
            }
        )
        _auditar_nota(
            yo, "creacion", curso, alumno, tarea,
            None,
            {"nota": nota, "estado": estado},
            "Cargó una calificación",
        )

    return listar_notas(id_curso, yo)
