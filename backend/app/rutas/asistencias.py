"""Asistencias: tomar lista, planificar las clases y justificar faltas.

Dos públicos sobre los mismos datos, como en Finales:

- **El docente** toma lista en sus materias, planifica cuántas clases va a
  dar, corrige registros y resuelve las justificaciones de sus alumnos.
- **El alumno** ve lo suyo y pide que le justifiquen una falta.

Todo pasa por el curso: no hay forma de pedir asistencias "de todos". Las
rutas del docente exigen ser el responsable de esa materia y las del alumno
sacan de quién son los datos de la sesión, nunca de la pantalla.

**Administrador y Supervisor todavía no existen** en `personas`. Hasta que
existan, administra el docente a cargo, que es quien responde por su materia.
Está en una sola función —`puede_administrar`—: el día que el rol exista, se
cambia ahí y nada más.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import asistencias as asis
from ..servicios import auditoria
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api", tags=["Asistencias"])

MAX_TEMA = 200
MAX_MOTIVO = 1000
MAX_OBSERVACION = 500


# ===================== Permisos =====================
def _es_supervisor(persona: dict) -> bool:
    """Todavía no hay rol de administrador ni de supervisor."""
    return d.tiene_rol(persona, "Administrador", "Supervisor")


def puede_administrar(yo: dict, curso: dict) -> bool:
    """Quién maneja las asistencias de una materia: su docente a cargo."""
    if _es_supervisor(yo):
        return True
    return d.tiene_rol(yo, "Docente") and curso.get("docenteId") == yo["id"]


def _curso_que_administra(id_curso: int, yo: dict) -> dict:
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "El módulo no existe")
    if not puede_administrar(yo, curso):
        raise HTTPException(403, "Solo el docente a cargo maneja las asistencias de este módulo")
    return curso


def _curso_en_el_que_estoy(id_curso: int, yo: dict) -> dict:
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "El módulo no existe")
    if not any(p["id"] == yo["id"] for p in d.participantes_de_curso(curso)):
        raise HTTPException(403, "No cursás este módulo")
    return curso


def _alumnos_de(curso: dict) -> list[dict]:
    return [p for p in d.participantes_de_curso(curso) if d.tiene_rol(p, "Estudiante")]


def _texto(valor, campo: str, maximo: int, obligatorio: bool = True) -> str | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            raise HTTPException(400, f"Falta {campo}")
        return None
    if not isinstance(valor, str):
        raise HTTPException(400, f"{campo} tiene que ser texto")
    limpio = valor.strip()
    if len(limpio) > maximo:
        raise HTTPException(400, f"{campo} no puede pasar de {maximo} caracteres")
    return limpio


def _buscar_clase(id_clase: int, curso_id: int) -> dict:
    clase = next(
        (c for c in d.clases_asistencia if c["id"] == id_clase and c["cursoId"] == curso_id),
        None,
    )
    if not clase:
        raise HTTPException(404, "La clase no existe en este módulo")
    return clase


# ===================== Planificación =====================
@router.get("/cursos/{id_curso}/asistencias/planificacion", summary="Las clases previstas")
def ver_planificacion(id_curso: int, yo: dict = UsuarioActual):
    """Cuántas clases hay previstas y cuántas se dictaron.

    La ven docente y alumno: el alumno necesita saber desde el primer día
    cuántas faltas puede acumular. Modificarla es otra ruta.
    """
    curso = d.buscar_curso(id_curso)
    if not curso:
        raise HTTPException(404, "El módulo no existe")
    if not puede_administrar(yo, curso) and not any(
        p["id"] == yo["id"] for p in d.participantes_de_curso(curso)
    ):
        raise HTTPException(403, "No tenés acceso a este módulo")

    plan = asis.planificacion_de(id_curso)
    dictadas = asis.clases_de(id_curso, solo_dictadas=True)
    limites = asis.limite_de_inasistencias(
        plan["clasesPlanificadas"], plan["minimoAsistencia"]
    )
    quien = d.buscar_persona(plan.get("actualizadoPor"))

    return {
        "curso": {"id": curso["id"], "codigo": curso["codigo"], "nombre": curso["nombre"]},
        "clasesPlanificadas": plan["clasesPlanificadas"],
        "clasesDictadas": len(dictadas),
        "clasesPendientes": (
            None
            if not plan["clasesPlanificadas"]
            else max(plan["clasesPlanificadas"] - len(dictadas), 0)
        ),
        "minimoAsistencia": plan["minimoAsistencia"],
        **limites,
        "actualizadoPor": quien["nombre"] if quien else None,
        "fecha": plan.get("fecha"),
        "puedeEditar": puede_administrar(yo, curso),
    }


@router.put("/cursos/{id_curso}/asistencias/planificacion", summary="Fijar las clases previstas")
def guardar_planificacion(id_curso: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Lo único que decide la cátedra es cuántas clases va a dar.

    El porcentaje mínimo lo fija la institución (75 %) y no se toca desde
    acá: si cada materia pudiera poner el suyo, dejaría de ser un mínimo.
    """
    curso = _curso_que_administra(id_curso, yo)

    total = cuerpo.get("clasesPlanificadas")
    if not isinstance(total, int) or not 1 <= total <= 300:
        raise HTTPException(400, "Las clases previstas tienen que ser un número de 1 a 300")

    dictadas = len(asis.clases_de(id_curso, solo_dictadas=True))
    if total < dictadas:
        raise HTTPException(
            400,
            f"Ya se dictaron {dictadas} clases: no se pueden planificar menos.",
        )

    previa = next(
        (p for p in d.planificacion_asistencia if p["cursoId"] == id_curso), None
    )
    registro = {
        "cursoId": id_curso,
        "clasesPlanificadas": total,
        "actualizadoPor": yo["id"],
        "fecha": d.iso(d.ahora()),
    }
    if previa:
        anterior = previa.get("clasesPlanificadas")
        previa.update(registro)
        # Queda el rastro de quién cambió el total y desde qué valor
        d.historial_asistencia.append(
            {
                "id": d.nuevo_id_historial_asistencia(),
                "claseId": None,
                "personaId": None,
                "de": str(anterior),
                "a": str(total),
                "quien": yo["id"],
                "cuando": d.iso(d.ahora()),
                "motivo": "Cambio en las clases planificadas",
            }
        )
        _auditar(
            yo,
            "edicion",
            id_curso,
            elemento=f"Clases previstas de {curso['nombre']}",
            antes={"clasesPlanificadas": anterior},
            despues={"clasesPlanificadas": total},
            detalle="Cambió el total de clases previstas",
        )
    else:
        d.planificacion_asistencia.append(registro)
        _auditar(
            yo,
            "creacion",
            id_curso,
            elemento=f"Clases previstas de {curso['nombre']}",
            despues={"clasesPlanificadas": total},
            detalle="Planificó el total de clases",
        )

    return ver_planificacion(id_curso, yo)


def _auditar(yo, accion, curso_id, **extra):
    """Un movimiento de Asistencias, con la materia puesta.

    La materia es lo que después le permite al docente ver lo suyo y al
    supervisor filtrar: vale la pena resolverla acá y no en cada llamada.
    """
    materia = asis.materia_del_curso(curso_id)
    auditoria.registrar(
        yo,
        accion,
        "asistencias",
        elemento_tipo=extra.pop("elemento_tipo", "asistencias"),
        materia_id=materia["id"] if materia else None,
        **extra,
    )


# ===================== Las clases y la lista =====================
@router.get("/cursos/{id_curso}/asistencias/clases", summary="Las clases de la materia")
def listar_clases(id_curso: int, yo: dict = UsuarioActual):
    """Las clases con cuántos presentes tuvo cada una, de la última a la
    primera: el docente casi siempre viene a tomar la de hoy."""
    curso = _curso_que_administra(id_curso, yo)
    alumnos = _alumnos_de(curso)
    clases = asis.clases_de(id_curso)
    clases.reverse()

    return {
        "curso": {"id": curso["id"], "codigo": curso["codigo"], "nombre": curso["nombre"]},
        "clases": [
            {
                **{k: v for k, v in c.items() if k != "registradaEl"},
                "resumen": asis.resumen_de_clase(c, alumnos),
            }
            for c in clases
        ],
        "alumnos": len(alumnos),
    }


@router.post("/cursos/{id_curso}/asistencias/clases", status_code=201, summary="Registrar una clase")
def crear_clase(id_curso: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Da de alta una clase para poder tomarle lista.

    Una clase **suspendida** se registra igual: deja constancia de por qué no
    hubo clase y, al no contar como dictada, no le genera una falta a nadie.
    """
    curso = _curso_que_administra(id_curso, yo)

    fecha = cuerpo.get("fecha")
    if not isinstance(fecha, str) or not fecha.strip():
        raise HTTPException(400, "Falta la fecha de la clase")
    try:
        cuando = d.desde_iso(fecha)
    except ValueError:
        raise HTTPException(400, "La fecha no es válida")
    if cuando > d.ahora():
        raise HTTPException(400, "No se puede tomar lista de una clase que todavía no pasó")

    # Una sola clase por materia y día: si no, la misma clase cargada dos
    # veces le cuenta doble falta al que no fue.
    dia = d.clave_dia(fecha)
    if any(d.clave_dia(c["fecha"]) == dia for c in asis.clases_de(id_curso)):
        raise HTTPException(409, "Ya hay una clase registrada para ese día")

    estado = cuerpo.get("estado") or "dictada"
    if estado not in ("dictada", "suspendida"):
        raise HTTPException(400, "La clase es dictada o suspendida")

    clase = {
        "id": d.nuevo_id_clase_asistencia(),
        "cursoId": id_curso,
        "fecha": fecha,
        "tema": _texto(cuerpo.get("tema"), "el tema", MAX_TEMA, obligatorio=False),
        "estado": estado,
        "docenteId": yo["id"],
        "cerrada": False,
        "registradaEl": d.iso(d.ahora()),
        "motivo": _texto(cuerpo.get("motivo"), "el motivo", MAX_OBSERVACION, obligatorio=False),
    }
    d.clases_asistencia.append(clase)
    return listar_clases(id_curso, yo)


@router.get("/cursos/{id_curso}/asistencias/clases/{id_clase}", summary="La lista de una clase")
def ver_clase(id_curso: int, id_clase: int, yo: dict = UsuarioActual):
    """Los alumnos de la materia con lo que tenga cada uno en esa clase.

    Van todos, con o sin registro: tomar lista es completar la lista entera,
    no agregar de a uno.
    """
    curso = _curso_que_administra(id_curso, yo)
    clase = _buscar_clase(id_clase, id_curso)
    alumnos = _alumnos_de(curso)

    filas = []
    for alumno in alumnos:
        registro = asis.registro_de(id_clase, alumno["id"])
        situacion = asis.situacion_de(alumno["id"], id_curso)
        justificacion = asis.justificacion_de(alumno["id"], id_clase)
        filas.append(
            {
                "id": alumno["id"],
                "nombre": alumno["nombre"],
                "estado": registro["estado"] if registro else None,
                "observacion": registro.get("observacion") if registro else None,
                "porcentaje": situacion["porcentaje"],
                "situacion": situacion["estado"],
                "justificacion": (
                    {"estado": justificacion["estado"], "motivo": justificacion["motivo"]}
                    if justificacion
                    else None
                ),
            }
        )

    return {
        "curso": {"id": curso["id"], "codigo": curso["codigo"], "nombre": curso["nombre"]},
        "clase": clase,
        "alumnos": filas,
        "estados": d.ESTADOS_ASISTENCIA,
        "resumen": asis.resumen_de_clase(clase, alumnos),
    }


@router.put("/cursos/{id_curso}/asistencias/clases/{id_clase}", summary="Guardar la lista")
def guardar_lista(
    id_curso: int, id_clase: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual
):
    """Guarda la asistencia de toda la clase de una vez.

    Se valida entera antes de escribir nada: o se guarda todo o no se guarda
    nada. Una lista a medias es peor que no haberla tomado, porque parece
    completa.
    """
    curso = _curso_que_administra(id_curso, yo)
    clase = _buscar_clase(id_clase, id_curso)

    if clase["estado"] == "suspendida":
        raise HTTPException(400, "La clase está suspendida: no hay lista que tomar")

    # Un registro cerrado solo lo corrige quien tiene permiso, y dejando el
    # motivo: es lo que convierte una corrección en algo auditable.
    corrigiendo = bool(clase.get("cerrada"))
    motivo = _texto(cuerpo.get("motivo"), "el motivo de la corrección", MAX_OBSERVACION,
                    obligatorio=corrigiendo)

    registros = cuerpo.get("asistencias")
    if not isinstance(registros, list) or not registros:
        raise HTTPException(400, "Falta la lista")

    alumnos = {a["id"]: a for a in _alumnos_de(curso)}
    validados = []
    for fila in registros:
        if not isinstance(fila, dict):
            raise HTTPException(400, "La lista no tiene el formato esperado")
        persona_id = fila.get("personaId")
        if persona_id not in alumnos:
            raise HTTPException(400, "Hay alguien en la lista que no cursa este módulo")
        estado = fila.get("estado")
        if estado not in d.ESTADOS_ASISTENCIA:
            raise HTTPException(400, f"«{estado}» no es un estado de asistencia válido")
        validados.append(
            {
                "personaId": persona_id,
                "estado": estado,
                "observacion": _texto(
                    fila.get("observacion"), "la observación", MAX_OBSERVACION, obligatorio=False
                ),
            }
        )

    if len({f["personaId"] for f in validados}) != len(validados):
        raise HTTPException(400, "Hay un alumno repetido en la lista")

    # Recién ahora se escribe
    for fila in validados:
        previo = asis.registro_de(id_clase, fila["personaId"])
        if previo:
            asis.anotar_cambio(
                id_clase, fila["personaId"], previo["estado"], fila["estado"], yo["id"], motivo
            )
            previo.update(
                {
                    "estado": fila["estado"],
                    "observacion": fila["observacion"],
                    "registradoPor": yo["id"],
                    "fecha": d.iso(d.ahora()),
                }
            )
        else:
            d.asistencias.append(
                {
                    "id": d.nuevo_id_asistencia(),
                    "claseId": id_clase,
                    "personaId": fila["personaId"],
                    "estado": fila["estado"],
                    "observacion": fila["observacion"],
                    "registradoPor": yo["id"],
                    "fecha": d.iso(d.ahora()),
                }
            )

    if cuerpo.get("cerrar"):
        clase["cerrada"] = True

    return ver_clase(id_curso, id_clase, yo)


# ===================== El curso visto por el docente =====================
@router.get("/cursos/{id_curso}/asistencias/alumnos", summary="Cómo viene cada alumno")
def asistencia_por_alumno(id_curso: int, yo: dict = UsuarioActual):
    """El porcentaje de cada alumno, los que están en riesgo primero."""
    curso = _curso_que_administra(id_curso, yo)
    alumnos = _alumnos_de(curso)
    filas = [{**asis.situacion_de(a["id"], id_curso), "nombre": a["nombre"]} for a in alumnos]

    orden = {asis.POR_DEBAJO: 0, asis.EN_RIESGO: 1, asis.AL_DIA: 2, asis.SIN_CLASES: 3}
    filas.sort(key=lambda f: (orden.get(f["estado"], 9), -(f["inasistencias"] or 0)))

    dictadas = asis.clases_de(id_curso, solo_dictadas=True)
    porcentajes = [f["porcentaje"] for f in filas if f["porcentaje"] is not None]

    return {
        "curso": {"id": curso["id"], "codigo": curso["codigo"], "nombre": curso["nombre"]},
        "alumnos": filas,
        "resumen": {
            "alumnos": len(filas),
            "clasesDictadas": len(dictadas),
            "promedio": round(sum(porcentajes) / len(porcentajes), 1) if porcentajes else None,
            "enRiesgo": sum(1 for f in filas if f["estado"] == asis.EN_RIESGO),
            "porDebajo": sum(1 for f in filas if f["estado"] == asis.POR_DEBAJO),
        },
    }


# ===================== Lo que ve el alumno =====================
@router.get("/asistencias/mi-situacion", summary="Mis asistencias en todas mis materias")
def mi_situacion(yo: dict = UsuarioActual):
    """Una fila por materia, con lo suyo y nada de nadie más.

    De quién son los datos sale de la sesión: no hay parámetro que permita
    pedir los de otro.
    """
    mios = [
        c
        for c in d.cursos
        if any(p["id"] == yo["id"] for p in d.participantes_de_curso(c))
    ]

    materias = []
    for curso in mios:
        situacion = asis.situacion_de(yo["id"], curso["id"])
        materias.append(
            {
                **situacion,
                "codigo": curso["codigo"],
                "nombre": curso["nombre"],
                "color": curso.get("color"),
            }
        )

    con_clases = [m for m in materias if m["registradas"] > 0]
    porcentajes = [m["porcentaje"] for m in con_clases if m["porcentaje"] is not None]

    return {
        "materias": materias,
        "minimoAsistencia": asis.minimo_exigido(),
        "resumen": {
            "materias": len(materias),
            "promedio": round(sum(porcentajes) / len(porcentajes), 1) if porcentajes else None,
            "enRiesgo": sum(1 for m in materias if m["estado"] == asis.EN_RIESGO),
            "porDebajo": sum(1 for m in materias if m["estado"] == asis.POR_DEBAJO),
        },
    }


@router.get("/cursos/{id_curso}/asistencias/mi-detalle", summary="Mi asistencia en una materia")
def mi_detalle(id_curso: int, yo: dict = UsuarioActual):
    """Clase por clase, con el estado de cada una y si pedí justificarla."""
    curso = _curso_en_el_que_estoy(id_curso, yo)
    clases = asis.clases_de(id_curso)
    clases.reverse()

    detalle = []
    for clase in clases:
        registro = asis.registro_de(clase["id"], yo["id"])
        justificacion = asis.justificacion_de(yo["id"], clase["id"])
        detalle.append(
            {
                "claseId": clase["id"],
                "fecha": clase["fecha"],
                "tema": clase.get("tema"),
                "suspendida": clase["estado"] == "suspendida",
                "estado": registro["estado"] if registro else None,
                "observacion": registro.get("observacion") if registro else None,
                "justificacion": (
                    {
                        "id": justificacion["id"],
                        "estado": justificacion["estado"],
                        "motivo": justificacion["motivo"],
                        "observacion": justificacion.get("observacion"),
                    }
                    if justificacion
                    else None
                ),
                # Solo tiene sentido pedir justificación de una falta propia
                "puedeJustificar": (
                    registro is not None
                    and registro["estado"] == asis.AUSENTE
                    and justificacion is None
                    and clase["estado"] == "dictada"
                ),
            }
        )

    return {
        "curso": {"id": curso["id"], "codigo": curso["codigo"], "nombre": curso["nombre"]},
        "situacion": asis.situacion_de(yo["id"], id_curso),
        "clases": detalle,
    }


# ===================== Justificaciones =====================
@router.get("/asistencias/justificaciones", summary="Las justificaciones que me tocan")
def listar_justificaciones(yo: dict = UsuarioActual):
    """Al alumno, las suyas. Al docente, las de sus materias.

    Las pendientes primero: son las que hay que resolver.
    """
    if d.tiene_rol(yo, "Docente") or _es_supervisor(yo):
        mios = {c["id"] for c in d.cursos if puede_administrar(yo, c)}
        propias = [j for j in d.justificaciones if j["cursoId"] in mios]
        soy_quien_resuelve = True
    else:
        propias = [j for j in d.justificaciones if j["personaId"] == yo["id"]]
        soy_quien_resuelve = False

    salida = []
    for j in propias:
        curso = d.buscar_curso(j["cursoId"])
        clase = next((c for c in d.clases_asistencia if c["id"] == j["claseId"]), None)
        alumno = d.buscar_persona(j["personaId"])
        revisor = d.buscar_persona(j.get("revisadoPor"))
        salida.append(
            {
                **j,
                "alumno": alumno["nombre"] if alumno else "—",
                "curso": curso["nombre"] if curso else "—",
                "codigo": curso["codigo"] if curso else None,
                "fechaClase": clase["fecha"] if clase else None,
                "tema": clase.get("tema") if clase else None,
                "revisor": revisor["nombre"] if revisor else None,
            }
        )

    orden = {"Pendiente": 0, "Aprobada": 1, "Rechazada": 2}
    salida.sort(key=lambda j: (orden.get(j["estado"], 9), -d.desde_iso(j["fecha"]).timestamp()))

    return {
        "justificaciones": salida,
        "puedeResolver": soy_quien_resuelve,
        "pendientes": sum(1 for j in salida if j["estado"] == "Pendiente"),
    }


@router.post("/asistencias/justificaciones", status_code=201, summary="Pedir una justificación")
def pedir_justificacion(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Un alumno pide que le justifiquen una falta.

    Solo de una falta propia y real: si no faltó, o ya pidió por esa clase,
    no hay nada que justificar.
    """
    id_clase = cuerpo.get("claseId")
    clase = next((c for c in d.clases_asistencia if c["id"] == id_clase), None)
    if not clase:
        raise HTTPException(404, "La clase no existe")

    curso = _curso_en_el_que_estoy(clase["cursoId"], yo)

    registro = asis.registro_de(id_clase, yo["id"])
    if not registro or registro["estado"] != asis.AUSENTE:
        raise HTTPException(400, "Esa clase no figura como una falta tuya")
    if asis.justificacion_de(yo["id"], id_clase):
        raise HTTPException(409, "Ya pediste justificar esa falta")

    motivo = _texto(cuerpo.get("motivo"), "el motivo", MAX_MOTIVO)
    archivo = _texto(cuerpo.get("archivo"), "el archivo", 200, obligatorio=False)

    justificacion = {
        "id": d.nuevo_id_justificacion(),
        "personaId": yo["id"],
        "cursoId": curso["id"],
        "claseId": id_clase,
        "motivo": motivo,
        "archivo": archivo,
        "estado": "Pendiente",
        "revisadoPor": None,
        "fechaResolucion": None,
        "observacion": None,
        "fecha": d.iso(d.ahora()),
    }
    d.justificaciones.append(justificacion)

    # No hay mails: el aviso es un mensaje del campus, como en Finales
    docente = d.buscar_persona(curso.get("docenteId"))
    if docente:
        d.avisar_por_mensaje(
            yo["id"],
            docente["id"],
            f"Pedí justificar la falta del {d.clave_dia(clase['fecha'])} "
            f"en {curso['nombre']}: {motivo}",
        )

    return listar_justificaciones(yo)


@router.put("/asistencias/justificaciones/{id_justificacion}", summary="Resolver una justificación")
def resolver_justificacion(
    id_justificacion: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual
):
    """Aprobar o rechazar.

    **Rechazar exige motivo**: sin eso, el alumno no sabe qué pasó ni qué
    corregir. Aprobar marca la falta como justificada, pero —salvo que la
    institución lo configure— **no le devuelve el porcentaje**: deja
    constancia de por qué faltó, no borra la falta.
    """
    justificacion = next(
        (j for j in d.justificaciones if j["id"] == id_justificacion), None
    )
    if not justificacion:
        raise HTTPException(404, "La justificación no existe")

    curso = _curso_que_administra(justificacion["cursoId"], yo)

    estado = cuerpo.get("estado")
    if estado not in ("Aprobada", "Rechazada"):
        raise HTTPException(400, "La justificación se aprueba o se rechaza")

    observacion = _texto(
        cuerpo.get("observacion"),
        "el motivo del rechazo",
        MAX_OBSERVACION,
        obligatorio=estado == "Rechazada",
    )

    justificacion.update(
        {
            "estado": estado,
            "revisadoPor": yo["id"],
            "fechaResolucion": d.iso(d.ahora()),
            "observacion": observacion,
        }
    )

    # Aprobar cambia el estado del registro a "justificada"
    if estado == "Aprobada":
        registro = asis.registro_de(justificacion["claseId"], justificacion["personaId"])
        if registro:
            asis.anotar_cambio(
                justificacion["claseId"],
                justificacion["personaId"],
                registro["estado"],
                asis.JUSTIFICADA,
                yo["id"],
                "Se aprobó la justificación",
            )
            registro["estado"] = asis.JUSTIFICADA

    clase = next(
        (c for c in d.clases_asistencia if c["id"] == justificacion["claseId"]), None
    )
    d.avisar_por_mensaje(
        yo["id"],
        justificacion["personaId"],
        f"Tu justificación de {curso['nombre']} "
        f"({d.clave_dia(clase['fecha']) if clase else 'una clase'}) quedó "
        f"{estado.lower()}." + (f" {observacion}" if observacion else ""),
    )

    return listar_justificaciones(yo)


# ===================== Historial de cambios =====================
@router.get("/cursos/{id_curso}/asistencias/historial", summary="Quién cambió qué")
def historial(id_curso: int, yo: dict = UsuarioActual):
    """Las correcciones hechas sobre los registros de la materia."""
    _curso_que_administra(id_curso, yo)
    clases = {c["id"] for c in asis.clases_de(id_curso)}

    salida = []
    for h in d.historial_asistencia:
        if h.get("claseId") is not None and h["claseId"] not in clases:
            continue
        if h.get("claseId") is None and h.get("motivo") != "Cambio en las clases planificadas":
            continue
        quien = d.buscar_persona(h.get("quien"))
        alumno = d.buscar_persona(h.get("personaId"))
        clase = next((c for c in d.clases_asistencia if c["id"] == h.get("claseId")), None)
        salida.append(
            {
                **h,
                "quienNombre": quien["nombre"] if quien else "—",
                "alumnoNombre": alumno["nombre"] if alumno else None,
                "fechaClase": clase["fecha"] if clase else None,
            }
        )

    salida.sort(key=lambda h: d.desde_iso(h["cuando"]), reverse=True)
    return {"historial": salida}
