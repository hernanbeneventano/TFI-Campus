"""Lo que el alumno ve de su propia cursada: sus notas y sus cuestionarios.

**Cada uno ve lo suyo y nada más.** Las rutas de acá nunca reciben de quién
son las notas que se piden: salen de la sesión. Un alumno no puede pedir las
de un compañero porque no hay forma de nombrarlo. La grilla con todo el curso
existe —`rutas/gestion_modulo.py`— pero exige ser el docente a cargo.

De un cuestionario, el alumno recibe las preguntas **sin cuál es la
correcta**: mandarlas y esconderlas en la pantalla sería regalar las
respuestas a cualquiera que abra las herramientas del navegador. Las ve
recién después de responder.
"""

from __future__ import annotations

from app.errores import ErrorDeAPI

from .. import datos as d
from ..servicios import almacenamiento as alm
from ..servicios import archivos, auditoria, fotos
from ..servicios import cursada as c



def _curso_en_el_que_estoy(id_curso: int, yo: dict) -> dict:
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise ErrorDeAPI(404, "El módulo no existe")
    if not any(p["id"] == yo["id"] for p in d.participantes_de_curso(curso)):
        raise ErrorDeAPI(403, "No cursás este módulo")
    return curso


def mis_notas(id_curso: int, yo: dict ):
    """Las notas propias, con el promedio y la condición.

    No hay forma de pedir las de otro: de quién son sale de la sesión.
    """
    curso = _curso_en_el_que_estoy(id_curso, yo)
    trabajos = [t for t in d.tareas if t["cursoId"] == curso["id"]]
    mias = c.notas_de(yo["id"], curso["id"])

    filas = []
    for trabajo in trabajos:
        nota = next((x for x in mias if x["tareaId"] == trabajo["id"]), None)
        entrega = next(
            (
                e
                for e in d.entregas
                if e["tareaId"] == trabajo["id"] and e["personaId"] == yo["id"]
            ),
            None,
        )
        respuesta = c.respuesta_de(yo["id"], trabajo["id"])
        filas.append(
            {
                "tareaId": trabajo["id"],
                "titulo": trabajo["titulo"],
                "fechaLimite": trabajo["fechaLimite"],
                "modalidad": trabajo.get("modalidad", "virtual"),
                "formato": trabajo.get("formato", "entrega"),
                "entregado": entrega is not None or respuesta is not None,
                "fecha": (entrega or respuesta or {}).get("fecha"),
                "nota": nota.get("nota") if nota else (respuesta or {}).get("nota"),
                "estado": nota.get("estado") if nota else None,
                # La devolución del docente: es lo que explica la nota
                "devolucion": nota.get("comentario") if nota else None,
            }
        )

    return {
        "curso": {"id": curso["id"], "codigo": curso["codigo"], "nombre": curso["nombre"]},
        "trabajos": filas,
        "cierre": c.cierre_de(yo["id"], curso["id"]),
        "notaParaAprobar": d.NOTA_PARA_APROBAR,
    }


def abrir_cuestionario(id_tarea: int, yo: dict ):
    """Las preguntas, sin decir cuál es la correcta.

    Si ya lo respondió, vienen la nota y el detalle: ahí sí se muestra qué
    estaba bien, que es de lo que se aprende.
    """
    tarea = d.buscar_tarea(id_tarea)
    if not tarea:
        raise ErrorDeAPI(404, "El trabajo no existe")
    _curso_en_el_que_estoy(tarea["cursoId"], yo)

    if tarea.get("formato") != "cuestionario":
        raise ErrorDeAPI(400, "Ese trabajo no es un cuestionario")

    respuesta = c.respuesta_de(yo["id"], id_tarea)
    abierto = _entrega_abierta(tarea)

    preguntas = [
        {
            "id": p["id"],
            "texto": p["texto"],
            "opciones": p["opciones"],
            "puntaje": p.get("puntaje", 1),
        }
        for p in (tarea.get("preguntas") or [])
    ]

    salida = {
        "trabajo": {
            "id": tarea["id"],
            "titulo": tarea["titulo"],
            "consigna": tarea.get("consigna"),
            "fechaLimite": tarea["fechaLimite"],
        },
        "preguntas": preguntas,
        "abierto": abierto,
        "respondido": respuesta is not None,
    }

    if respuesta:
        corregido = c.corregir_cuestionario(tarea, respuesta["respuestas"])
        salida["resultado"] = {
            "nota": respuesta.get("nota"),
            "puntos": corregido["puntos"],
            "total": corregido["total"],
            "fecha": respuesta["fecha"],
            "detalle": corregido["detalle"],
        }

    return salida


def _entrega_abierta(tarea: dict) -> bool:
    """`cerrada` pesa más que la fecha: el docente puede cortar antes o dar
    prórroga."""
    if tarea.get("cerrada") is True:
        return False
    if tarea.get("cerrada") is False:
        return True
    return d.desde_iso(tarea["fechaLimite"]) >= d.ahora()


# ===================== Lo que ya vi del módulo =====================
# Qué material marcó como visto cada alumno. Vivía en `localStorage`, así que
# se perdía al cambiar de navegador o de equipo y el docente —que mira esto
# para saber cómo viene el curso— veía siempre cero.
def _mi_progreso(persona_id: int) -> list[str]:
    return [p["itemId"] for p in d.progreso_alumnos if p["personaId"] == persona_id]


def _marca_de(persona_id: int, curso_id: int, item_id: str) -> dict | None:
    return next(
        (
            p
            for p in d.progreso_alumnos
            if p["personaId"] == persona_id
            and p["cursoId"] == curso_id
            and p["itemId"] == item_id
        ),
        None,
    )


def ver_mi_progreso(yo: dict ):
    """Los identificadores de **todos** los módulos, no de uno.

    El panel de tareas pendientes cruza módulos —muestra lo que falta en la
    carpeta de cada tarea, de la materia que sea— así que pedirlo por módulo
    lo obligaría a hacer una consulta por materia para dibujar una barra.
    Los identificadores ya traen el módulo adentro (`2-107`), así que una
    lista sola alcanza.
    """
    return {"completados": _mi_progreso(yo["id"])}


def marcar_visto(id_curso: int, id_item: str, yo: dict ):
    """Solo material que existe en ese módulo y que se pueda marcar.

    Sin esa comprobación cualquiera podría mandar identificadores inventados
    y llenarse la barra de avance; peor, le ensuciaría al docente la cuenta
    de quién vio qué, que es lo que mira para saber cómo viene el curso.
    """
    _curso_en_el_que_estoy(id_curso, yo)

    item = d.buscar_item_de_curso(id_curso, id_item)
    if not item:
        raise ErrorDeAPI(404, "Ese material no existe en el módulo")
    if not d.es_marcable(item):
        raise ErrorDeAPI(400, "Las tareas se dan por hechas al entregarlas")

    if not _marca_de(yo["id"], id_curso, id_item):
        d.progreso_alumnos.append(
            {
                "personaId": yo["id"],
                "cursoId": id_curso,
                "itemId": id_item,
                "fecha": d.iso(d.ahora()),
            }
        )
    return {"completados": _mi_progreso(yo["id"])}


def desmarcar(id_curso: int, id_item: str, yo: dict ):
    """Se puede desmarcar siempre: marcar algo por error no puede ser
    definitivo, y esto no es una entrega sino una nota para uno mismo."""
    _curso_en_el_que_estoy(id_curso, yo)
    marca = _marca_de(yo["id"], id_curso, id_item)
    if marca:
        d.progreso_alumnos.remove(marca)
    return {"completados": _mi_progreso(yo["id"])}


def importar_progreso(cuerpo: dict , yo: dict ):
    """Trae de una vez lo que el alumno había marcado cuando esto vivía en el
    navegador.

    Existe para no hacerle perder lo que ya tenía al pasar al servidor. Se
    ignora en silencio lo que no corresponda —material borrado, de un módulo
    que ya no cursa, o identificadores inventados—: es un arrastre de datos
    viejos, no una operación que deba fallar entera por una línea mala.
    """
    ids = cuerpo.get("completados")
    if not isinstance(ids, list):
        raise ErrorDeAPI(400, "Falta la lista de material visto")

    mios = {
        c["id"]
        for c in d.cursos
        if any(p["id"] == yo["id"] for p in d.participantes_de_curso(c))
    }

    sumados = 0
    for item_id in ids[:2000]:
        item_id = str(item_id)
        for curso_id in mios:
            item = d.buscar_item_de_curso(curso_id, item_id)
            if not item or not d.es_marcable(item):
                continue
            if not _marca_de(yo["id"], curso_id, item_id):
                d.progreso_alumnos.append(
                    {
                        "personaId": yo["id"],
                        "cursoId": curso_id,
                        "itemId": item_id,
                        "fecha": d.iso(d.ahora()),
                    }
                )
                sumados += 1
            break

    return {"sumados": sumados, "completados": _mi_progreso(yo["id"])}


# ===================== Entregar un trabajo =====================
# Cuánto puede pesar lo que entrega un alumno. Más generoso que un avatar
# —un trabajo puede traer capturas o un informe largo— y más chico que la
# Biblioteca, que aloja libros enteros.
ENTREGA_MAX_MB = 20

# Qué se acepta. Deliberadamente corto: el docente corrige lo que puede
# abrir, y cada formato que se suma es uno más que el servidor tiene que
# saber reconocer por sus bytes. Nada que el navegador pueda ejecutar.
FORMATOS_ENTREGA = {"pdf", "docx", "png", "jpg", "jpeg"}


def _entrega_de(persona_id: int, tarea_id: int) -> dict | None:
    return next(
        (e for e in d.entregas if e["tareaId"] == tarea_id and e["personaId"] == persona_id),
        None,
    )


def _entrega_publica(entrega: dict | None, tarea: dict) -> dict | None:
    """Lo que la pantalla necesita para mostrar lo entregado."""
    if not entrega:
        return None
    archivo = entrega.get("archivo")
    # Las entregas viejas guardaban solo el nombre del archivo, como texto
    if isinstance(archivo, str):
        archivo = {"nombre": archivo}
    if archivo and archivo.get("objectKey"):
        archivo = {**archivo, "url": fotos.direccion_de_archivo(archivo["objectKey"])}
    return {
        "fecha": entrega["fecha"],
        "comentario": entrega.get("comentario"),
        "archivo": archivo,
        # Entregar tarde no se impide —el docente decide si lo toma— pero se
        # dice, porque es lo que mira al corregir.
        "tarde": d.desde_iso(entrega["fecha"]) > d.desde_iso(tarea["fechaLimite"]),
    }


def _trabajo_entregable(id_tarea: int, yo: dict) -> tuple[dict, dict]:
    """La tarea y su módulo, comprobando que esa persona pueda entregarla."""
    tarea = d.buscar_tarea(id_tarea)
    if not tarea:
        raise ErrorDeAPI(404, "El trabajo no existe")
    curso = _curso_en_el_que_estoy(tarea["cursoId"], yo)

    if tarea.get("formato") == "cuestionario":
        raise ErrorDeAPI(400, "Ese trabajo se responde en pantalla, no se sube")
    if tarea.get("modalidad") == "presencial":
        raise ErrorDeAPI(400, "Ese trabajo es presencial: no hay nada que subir")

    # Entrega quien cursa, no quien dicta. La cátedra figura entre los
    # participantes del módulo —por eso pasa el control de arriba— y sin esto
    # el docente podía entregarse su propio trabajo y aparecer en su propia
    # planilla de corrección.
    if curso.get("docenteId") == yo["id"] or not d.tiene_rol(yo, "Estudiante"):
        raise ErrorDeAPI(403, "Los trabajos los entregan los estudiantes")
    return tarea, curso


def ver_mi_entrega(id_tarea: int, yo: dict ):
    tarea, _curso = _trabajo_entregable(id_tarea, yo)
    return {
        "entrega": _entrega_publica(_entrega_de(yo["id"], id_tarea), tarea),
        "abierta": _entrega_abierta(tarea),
        "fechaLimite": tarea["fechaLimite"],
        "maximoMb": ENTREGA_MAX_MB,
        "formatos": sorted(FORMATOS_ENTREGA),
    }


def entregar(id_tarea: int, cuerpo: dict , yo: dict ):
    """Sube el archivo y deja la entrega hecha.

    **Se puede volver a entregar**, y la nueva reemplaza a la anterior: vale
    la última, como dice la pantalla. Es lo contrario del cuestionario, que
    se responde una sola vez porque repetirlo lo dejaría sin medir nada; acá
    lo que se corrige es un trabajo, y corregir una versión vieja porque
    alguien se equivocó de archivo no le sirve a nadie.

    El archivo anterior se borra: dos archivos para una entrega que apunta a
    uno solo es basura pagando lugar.
    """
    tarea, curso = _trabajo_entregable(id_tarea, yo)

    if not _entrega_abierta(tarea):
        raise ErrorDeAPI(403, "La entrega está cerrada")

    contenido, ficha = archivos.leer_subida(
        cuerpo, permitidos=FORMATOS_ENTREGA, max_mb=ENTREGA_MAX_MB
    )

    comentario = str(cuerpo.get("comentario") or "").strip()[:500] or None
    previa = _entrega_de(yo["id"], id_tarea)

    objeto = alm.clave(alm.ENTREGAS, curso["id"], id_tarea, yo["id"], nombre=ficha["nombre"])

    # Primero el archivo y después la ficha: si no se pudo guardar, la
    # entrega queda como estaba en vez de prometer algo que no está.
    try:
        alm.subir(objeto, contenido, ficha["tipo"])
    except Exception as error:  # noqa: BLE001
        raise ErrorDeAPI(502, f"No se pudo guardar la entrega: {error}")

    anterior = ((previa or {}).get("archivo") or {})
    if isinstance(anterior, dict) and anterior.get("objectKey") and anterior["objectKey"] != objeto:
        alm.olvidar(anterior["objectKey"])

    alm.registrar(
        objeto,
        nombre=ficha["nombre"],
        tipo=ficha["tipo"],
        tamano=ficha["tamano"],
        persona_id=yo["id"],
        modulo=alm.ENTREGAS,
        registro_id=id_tarea,
    )

    archivo = {**ficha, "objectKey": objeto}
    if previa:
        previa.update({"fecha": d.iso(d.ahora()), "archivo": archivo, "comentario": comentario})
        entrega = previa
    else:
        entrega = {
            "id": d.nuevo_id_entrega(),
            "tareaId": id_tarea,
            "personaId": yo["id"],
            "fecha": d.iso(d.ahora()),
            "archivo": archivo,
            "comentario": comentario,
        }
        d.entregas.append(entrega)

    auditoria.registrar(
        yo,
        "edicion" if previa else "creacion",
        "modulos",
        elemento=f"{tarea['titulo']} · {curso['nombre']}",
        elemento_id=id_tarea,
        elemento_tipo="entrega",
        materia_id=None,
        detalle="Volvió a entregar un trabajo" if previa else "Entregó un trabajo",
    )

    return {"entrega": _entrega_publica(entrega, tarea), "abierta": True}


def retirar_entrega(id_tarea: int, yo: dict ):
    """Solo mientras la entrega siga abierta.

    Después de cerrada no se retira: el docente ya pudo haberla corregido, y
    sacarla le dejaría una nota sin trabajo al lado.
    """
    tarea, curso = _trabajo_entregable(id_tarea, yo)
    entrega = _entrega_de(yo["id"], id_tarea)
    if not entrega:
        raise ErrorDeAPI(409, "No entregaste nada en este trabajo")
    if not _entrega_abierta(tarea):
        raise ErrorDeAPI(403, "La entrega está cerrada: ya no se puede retirar")

    archivo = entrega.get("archivo")
    if isinstance(archivo, dict) and archivo.get("objectKey"):
        alm.olvidar(archivo["objectKey"])
    d.entregas.remove(entrega)

    auditoria.registrar(
        yo, "baja", "modulos",
        elemento=f"{tarea['titulo']} · {curso['nombre']}",
        elemento_id=id_tarea, elemento_tipo="entrega",
        detalle="Retiró su entrega",
    )
    return {"entrega": None, "abierta": True}


def responder(id_tarea: int, cuerpo: dict , yo: dict ):
    """Se responde una sola vez y se corrige en el acto.

    Una sola vez porque, pudiendo repetir, el cuestionario deja de medir
    nada: se prueba hasta acertar. Si hay que volver a tomarlo, el docente
    crea otro.
    """
    tarea = d.buscar_tarea(id_tarea)
    if not tarea:
        raise ErrorDeAPI(404, "El trabajo no existe")
    curso = _curso_en_el_que_estoy(tarea["cursoId"], yo)

    if tarea.get("formato") != "cuestionario":
        raise ErrorDeAPI(400, "Ese trabajo no es un cuestionario")
    if c.respuesta_de(yo["id"], id_tarea):
        raise ErrorDeAPI(409, "Ya respondiste este cuestionario")
    if not _entrega_abierta(tarea):
        raise ErrorDeAPI(403, "El cuestionario está cerrado")

    respuestas = cuerpo.get("respuestas")
    if not isinstance(respuestas, dict) or not respuestas:
        raise ErrorDeAPI(400, "Falta responder")

    preguntas = tarea.get("preguntas") or []
    if len(respuestas) < len(preguntas):
        raise ErrorDeAPI(400, "Quedaron preguntas sin responder")

    corregido = c.corregir_cuestionario(tarea, respuestas)

    d.respuestas_cuestionario.append(
        {
            "id": d.nuevo_id_respuesta(),
            "tareaId": id_tarea,
            "personaId": yo["id"],
            "fecha": d.iso(d.ahora()),
            "respuestas": {str(k): int(v) for k, v in respuestas.items()},
            "nota": corregido["nota"],
        }
    )

    # La nota entra en la cursada como cualquier otra: el promedio no
    # distingue de dónde salió.
    d.calificaciones.append(
        {
            "id": d.nuevo_id_calificacion(),
            "cursoId": curso["id"],
            "tareaId": id_tarea,
            "personaId": yo["id"],
            "nota": corregido["nota"],
            "estado": "Aprobado" if corregido["nota"] >= d.NOTA_PARA_APROBAR else "Desaprobado",
            "comentario": "Corrección automática del cuestionario.",
            "docenteId": None,
            "fecha": d.iso(d.ahora()),
        }
    )

    return {
        "resultado": {
            "nota": corregido["nota"],
            "puntos": corregido["puntos"],
            "total": corregido["total"],
            "detalle": corregido["detalle"],
        },
        "cierre": c.cierre_de(yo["id"], curso["id"]),
    }
