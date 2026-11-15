"""Las cuentas de asistencia: porcentajes, límites y situación del alumno.

Están acá y no en las rutas porque las consultan tres pantallas: la del
docente cuando toma lista, la del alumno cuando mira cómo viene, y el panel
que resume todas sus materias.

**Lo que se cuenta.** Solo las clases **dictadas**. Una clase suspendida no
existió para nadie: no suma a las dictadas ni genera inasistencias. Por eso
el total de clases dictadas no es el de clases planificadas ni el de filas
en la tabla.

**Cómo pesa cada estado**, según la configuración de la cátedra:

- `presente`     cuenta como asistencia
- `ausente`      inasistencia
- `justificada`  inasistencia, salvo que la institución decida que descuenta
                 (`justificadaDescuenta`). El pliego pide que por defecto
                 **no** descuente: aprobar una justificación no le devuelve
                 el porcentaje al alumno, deja constancia de por qué faltó.

**El límite de inasistencias** sale de las clases planificadas y del mínimo
exigido, no de las dictadas: el alumno tiene que saber desde el primer día
cuántas puede faltar en todo el cuatrimestre. Las asistencias mínimas se
redondean **hacia arriba**, para que nadie quede por debajo del porcentaje
por un decimal.
"""

from __future__ import annotations

import math

from .. import datos as d
from . import auditoria

buscar_en = d.buscar_en

PRESENTE = "presente"
AUSENTE = "ausente"
JUSTIFICADA = "justificada"

# Cómo viene el alumno, para el semáforo
AL_DIA = "al día"
EN_RIESGO = "en riesgo"
POR_DEBAJO = "por debajo"
SIN_CLASES = "sin clases"


def configuracion() -> dict:
    return d.CONFIG_ASISTENCIA


def minimo_exigido() -> int:
    """El porcentaje que la institución exige para regularizar: 75 %.

    Es el mismo para todas las materias y no lo cambia la cátedra. Vive en la
    configuración y no escrito en el código para que, el día que la facultad
    lo cambie, sea un dato y no una búsqueda por todo el repositorio.
    """
    return d.CONFIG_ASISTENCIA["minimoPorDefecto"]


def planificacion_de(curso_id: int) -> dict:
    """La planificación de la materia, o una vacía si todavía no se cargó.

    Lo único que decide la cátedra es **cuántas clases va a dar**. El mínimo
    de asistencia lo pone la institución y se agrega acá para que las
    pantallas lo tengan junto con el resto.
    """
    guardada = next(
        (p for p in d.planificacion_asistencia if p["cursoId"] == curso_id), None
    )
    base = {
        "cursoId": curso_id,
        "clasesPlanificadas": None,
        "actualizadoPor": None,
        "fecha": None,
    }
    if guardada:
        base = {**base, **guardada}
    return {**base, "minimoAsistencia": minimo_exigido()}


def clases_de(curso_id: int, solo_dictadas: bool = False) -> list[dict]:
    clases = [c for c in d.clases_asistencia if c["cursoId"] == curso_id]
    if solo_dictadas:
        clases = [c for c in clases if c["estado"] == "dictada"]
    return sorted(clases, key=lambda c: d.desde_iso(c["fecha"]))


def registros_de_clase(clase_id: int) -> list[dict]:
    return [a for a in d.asistencias if a["claseId"] == clase_id]


def registro_de(clase_id: int, persona_id: int) -> dict | None:
    return next(
        (a for a in d.asistencias if a["claseId"] == clase_id and a["personaId"] == persona_id),
        None,
    )


def limite_de_inasistencias(clases_planificadas: int | None, minimo: int) -> dict:
    """Cuántas faltas tolera el alumno en todo el período.

    Con 40 clases y 75 %: necesita 30 presentes, así que puede faltar 10.
    """
    if not clases_planificadas:
        return {"minimasNecesarias": None, "maximoInasistencias": None}
    minimas = math.ceil(clases_planificadas * minimo / 100)
    return {
        "minimasNecesarias": minimas,
        "maximoInasistencias": max(clases_planificadas - minimas, 0),
    }


def situacion_de(persona_id: int, curso_id: int) -> dict:
    """Cómo viene una persona en una materia.

    Devuelve todo junto —lo contado, lo planificado y lo que le queda— porque
    las tres pantallas necesitan lo mismo y repartirlo obligaría a rehacer la
    cuenta en cada una.
    """
    config = configuracion()
    plan = planificacion_de(curso_id)
    dictadas = clases_de(curso_id, solo_dictadas=True)

    cuenta = {PRESENTE: 0, AUSENTE: 0, JUSTIFICADA: 0}
    sin_registrar = 0
    for clase in dictadas:
        registro = registro_de(clase["id"], persona_id)
        if registro is None:
            sin_registrar += 1
            continue
        cuenta[registro["estado"]] = cuenta.get(registro["estado"], 0) + 1

    registradas = len(dictadas) - sin_registrar

    # Las inasistencias que pesan: las ausencias y, si la institución no las
    # descuenta, también las justificadas.
    inasistencias = cuenta[AUSENTE]
    if not config.get("justificadaDescuenta"):
        inasistencias += cuenta[JUSTIFICADA]

    asistidas = max(registradas - inasistencias, 0)
    porcentaje = round(asistidas * 100 / registradas, 1) if registradas else None

    limites = limite_de_inasistencias(plan["clasesPlanificadas"], plan["minimoAsistencia"])
    maximo = limites["maximoInasistencias"]
    disponibles = None if maximo is None else max(maximo - inasistencias, 0)

    # El semáforo mira **las faltas que le quedan del cupo del período**, no
    # el porcentaje de lo dictado hasta hoy. Son cosas distintas: con 40
    # clases planificadas y 8 faltas de 10, el alumno va por debajo del 75 %
    # *ahora*, pero asistiendo al resto termina regular. Decirle "estás por
    # debajo" cuando todavía puede recuperarse es desinformarlo.
    #
    # Sin planificación cargada no hay cupo que mirar, así que ahí sí se cae
    # al porcentaje de lo que se lleva dictado.
    if registradas == 0:
        estado = SIN_CLASES
    elif maximo is None:
        estado = (
            POR_DEBAJO
            if porcentaje is not None and porcentaje < plan["minimoAsistencia"]
            else AL_DIA
        )
    elif inasistencias > maximo:
        estado = POR_DEBAJO
    elif disponibles <= max(1, round(maximo * 0.25)):
        estado = EN_RIESGO
    else:
        estado = AL_DIA

    return {
        "cursoId": curso_id,
        "personaId": persona_id,
        "clasesPlanificadas": plan["clasesPlanificadas"],
        "clasesDictadas": len(dictadas),
        "clasesPendientes": (
            None
            if not plan["clasesPlanificadas"]
            else max(plan["clasesPlanificadas"] - len(dictadas), 0)
        ),
        "registradas": registradas,
        "sinRegistrar": sin_registrar,
        "presentes": cuenta[PRESENTE],
        "ausentes": cuenta[AUSENTE],
        "justificadas": cuenta[JUSTIFICADA],
        "inasistencias": inasistencias,
        "porcentaje": porcentaje,
        "minimoAsistencia": plan["minimoAsistencia"],
        "minimasNecesarias": limites["minimasNecesarias"],
        "maximoInasistencias": maximo,
        "inasistenciasDisponibles": disponibles,
        "estado": estado,
    }


def resumen_de_clase(clase: dict, alumnos: list[dict]) -> dict:
    """Cuántos de cada estado tiene una clase, para la lista del docente."""
    cuenta = {PRESENTE: 0, AUSENTE: 0, JUSTIFICADA: 0}
    registrados = 0
    for alumno in alumnos:
        registro = registro_de(clase["id"], alumno["id"])
        if registro:
            cuenta[registro["estado"]] = cuenta.get(registro["estado"], 0) + 1
            registrados += 1
    return {
        **{k: v for k, v in cuenta.items()},
        "registrados": registrados,
        "total": len(alumnos),
        "tomada": registrados > 0,
    }


def justificacion_de(persona_id: int, clase_id: int) -> dict | None:
    return next(
        (
            j
            for j in d.justificaciones
            if j["personaId"] == persona_id and j["claseId"] == clase_id
        ),
        None,
    )


def materia_del_curso(curso_id) -> dict | None:
    """La materia del plan que corresponde a ese módulo, si la hay.

    La necesita la auditoría para saber de qué materia es un movimiento: así
    el docente ve lo suyo sin que haya que adivinarlo después.
    """
    return next((m for m in d.materias_plan if m.get("cursoId") == curso_id), None)


def anotar_cambio(clase_id: int, persona_id: int, antes: str | None, despues: str,
                  quien: int, motivo: str | None = None) -> None:
    """Deja asentado quién cambió un registro y cuándo.

    Solo se anota si algo cambió de verdad: tomar lista por primera vez no es
    una modificación, y anotarla llenaría el historial de ruido.

    Escribe en los dos lados a propósito: en `historialAsistencia`, que es
    **dato del apartado** —el tribunal ve la corrección al mirar la clase—, y
    en la auditoría, que es el registro central del campus.
    """
    if antes == despues:
        return
    d.historial_asistencia.append(
        {
            "id": d.nuevo_id_historial_asistencia(),
            "claseId": clase_id,
            "personaId": persona_id,
            "de": antes,
            "a": despues,
            "quien": quien,
            "cuando": d.iso(d.ahora()),
            "motivo": motivo,
        }
    )

    clase = buscar_en(d.clases_asistencia, clase_id) if clase_id else None
    materia = materia_del_curso(clase.get("cursoId")) if clase else None
    alumno = d.buscar_persona(persona_id)

    auditoria.registrar(
        quien,
        "edicion",
        "asistencias",
        elemento=(
            f"Asistencia de {alumno['nombre']}" if alumno else "Registro de asistencia"
        ),
        elemento_id=clase_id,
        elemento_tipo="asistencia",
        persona_id=persona_id,
        materia_id=materia["id"] if materia else None,
        antes={"asistencia": antes or "sin registrar"},
        despues={"asistencia": despues},
        detalle=motivo or "Corrección de asistencia",
    )
