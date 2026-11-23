"""Finales: mesas de examen, inscripción del alumno y sus resultados.

Es la mitad del alumno del apartado Finales. La gestión del docente —crear
mesas, ver inscriptos, cargar notas— todavía no está: estas rutas solo leen
las mesas que vienen en los datos y dejan que el estudiante se anote o se dé
de baja.

A diferencia del resto de los apartados, acá quien consulta sale de la sesión
(`IdUsuarioActual`) y no de una constante de módulo: es código nuevo y no hay
motivo para arrastrar el usuario de prueba fijo. Mientras no haya token, el
servicio de autenticación devuelve igual al usuario de prueba, así que se
comporta como el resto.

Vive acá y no en la ruta para que FastAPI y Django contesten **con la misma
función** mientras dure la migración: cada framework solo la llama. `yo` es
el identificador de quien pregunta, como `IdUsuarioActual`.
"""

from __future__ import annotations

from fastapi import HTTPException

from .. import datos as d
from . import academico as ac
from . import auditoria


def _mesa_con_estado(persona_id: int, mesa: dict) -> dict:
    return {**ac.mesa_publica(mesa), **ac.estado_de_mesa(persona_id, mesa)}


def listar_mesas(yo: int) -> dict:
    """Todas las mesas, de la más cercana a la más lejana.

    Van todas y no solo las que puede rendir: ver que la mesa de una materia
    que está cursando existe, y por qué todavía no puede anotarse, vale más
    que no verla.
    """
    mesas = sorted(d.mesas_examen, key=lambda m: d.desde_iso(m["fecha"]))
    return {
        "mesas": [_mesa_con_estado(yo, m) for m in mesas],
        "habilitadas": sum(
            1 for m in mesas if ac.habilitado_para_rendir(yo, m["materiaId"])
        ),
    }


def proximas(yo: int) -> dict:
    """Lo que se viene: solo las mesas que todavía no pasaron.

    Las que el alumno ya tiene tomadas vienen marcadas con `inscripto`, que es
    lo que la pantalla destaca.
    """
    ahora = d.ahora()
    futuras = [m for m in d.mesas_examen if d.desde_iso(m["fecha"]) >= ahora]
    futuras.sort(key=lambda m: d.desde_iso(m["fecha"]))

    salida = []
    for mesa in futuras:
        estado = ac.estado_de_mesa(yo, mesa)
        salida.append(
            {
                **ac.mesa_publica(mesa),
                **estado,
                "inscripto": estado["estado"] == ac.MESA_INSCRIPTO,
                "dia": d.clave_dia(mesa["fecha"]),
            }
        )
    return {"mesas": salida, "inscripto": sum(1 for m in salida if m["inscripto"])}


def resultados(yo: int) -> dict:
    """Los finales rendidos, del más reciente al más viejo, con el resumen."""
    mios = [r for r in d.resultados_finales if r["personaId"] == yo]
    mios.sort(key=lambda r: d.desde_iso(r["fecha"]), reverse=True)

    salida = []
    for registro in mios:
        materia = d.buscar_materia(registro["materiaId"])
        salida.append(
            {
                "id": registro["id"],
                "materiaId": registro["materiaId"],
                "materia": materia["nombre"] if materia else "Materia sin datos",
                "codigo": materia["codigo"] if materia else None,
                "anio": materia["anio"] if materia else None,
                "fecha": registro["fecha"],
                "nota": registro["nota"],
                "condicion": registro["condicion"],
                "llamado": registro.get("llamado"),
            }
        )

    aprobados = [r for r in salida if r["condicion"] == "Aprobado"]
    notas = [r["nota"] for r in aprobados if r["nota"] is not None]

    return {
        "resultados": salida,
        "resumen": {
            "rendidos": len(salida),
            "aprobados": len(aprobados),
            "desaprobados": sum(1 for r in salida if r["condicion"] == "Desaprobado"),
            "ausentes": sum(1 for r in salida if r["condicion"] == "Ausente"),
            # Promedio de los aprobados, con un decimal
            "promedio": round(sum(notas) / len(notas), 2) if notas else None,
        },
    }


def inscribirse(id_mesa: int, yo: int) -> dict:
    """Las mismas comprobaciones que hace la pantalla, pero acá mandan.

    La interfaz esconde el botón cuando no corresponde; esconderlo no es
    controlar. Cualquiera puede llamar a esta ruta a mano.
    """
    mesa = d.buscar_mesa(id_mesa)
    if not mesa:
        raise HTTPException(404, "La mesa de examen no existe")

    # Mirar el estado (cupo, si ya está, si se canceló) y anotar van juntos:
    # ver `academico.inscripciones_a_mesas`.
    with ac.inscripciones_a_mesas:
        estado = ac.estado_de_mesa(yo, mesa)
        if estado["estado"] == ac.MESA_INSCRIPTO:
            raise HTTPException(409, "Ya estás inscripto en esta mesa")
        if not estado["puedeInscribirse"]:
            raise HTTPException(403, estado["motivo"] or "No podés inscribirte a esta mesa")

        # Si había una baja anterior se reutiliza el registro, así no quedan dos
        # filas de la misma persona en la misma mesa.
        previa = ac.cancelacion_en_mesa(yo, id_mesa)
        if previa:
            previa["estado"] = ac.MESA_INSCRIPTO
            previa["fecha"] = d.iso(d.ahora())
        else:
            d.inscripciones_finales.append(
                {
                    "id": d.nuevo_id_inscripcion_final(),
                    "personaId": yo,
                    "mesaId": id_mesa,
                    "fecha": d.iso(d.ahora()),
                    "estado": ac.MESA_INSCRIPTO,
                }
            )

    materia = d.buscar_materia(mesa["materiaId"])
    auditoria.registrar(
        yo,
        "creacion",
        "finales",
        elemento=f"Inscripción a {materia['nombre'] if materia else 'un final'} ({mesa.get('llamado')})",
        elemento_id=mesa["id"],
        elemento_tipo="inscripcionFinal",
        persona_id=yo,
        materia_id=mesa["materiaId"],
        despues={"estado": ac.MESA_INSCRIPTO, "fecha": mesa.get("fecha")},
        detalle="Se inscribió a una mesa de examen",
    )
    return _mesa_con_estado(yo, mesa)


def cancelar(id_mesa: int, yo: int) -> dict:
    """Se puede mientras el período de inscripción siga abierto.

    La baja no se borra: queda con estado `Cancelado`, porque la institución
    necesita saber que esa inscripción existió.
    """
    mesa = d.buscar_mesa(id_mesa)
    if not mesa:
        raise HTTPException(404, "La mesa de examen no existe")

    with ac.inscripciones_a_mesas:
        inscripcion = ac.inscripcion_en_mesa(yo, id_mesa)
        if not inscripcion:
            raise HTTPException(409, "No estás inscripto en esta mesa")

        ahora = d.ahora()
        if not (
            d.desde_iso(mesa["inscripcionDesde"]) <= ahora <= d.desde_iso(mesa["inscripcionHasta"])
        ):
            raise HTTPException(403, "El período de inscripción está cerrado: no se puede dar de baja")

        inscripcion["estado"] = ac.MESA_CANCELADO
        inscripcion["canceladaEl"] = d.iso(ahora)

    materia = d.buscar_materia(mesa["materiaId"])
    auditoria.registrar(
        yo,
        "baja",
        "finales",
        elemento=f"Inscripción a {materia['nombre'] if materia else 'un final'} ({mesa.get('llamado')})",
        elemento_id=mesa["id"],
        elemento_tipo="inscripcionFinal",
        persona_id=yo,
        materia_id=mesa["materiaId"],
        antes={"estado": ac.MESA_INSCRIPTO},
        despues={"estado": ac.MESA_CANCELADO},
        detalle="Se dio de baja de una mesa de examen",
    )
    return _mesa_con_estado(yo, mesa)
