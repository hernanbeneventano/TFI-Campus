"""Reglas académicas: correlatividades, cupos y períodos de inscripción.

Vive acá y no en las rutas porque la comparten los dos apartados nuevos:
Finales (`rutas/finales.py`) e Inscripciones a materias
(`rutas/inscripciones.py`). Las rutas se limitan a pedir el estado y a
rechazar lo que no corresponde.

**El plan de estudios no está escrito en el código.** Las correlatividades de
cada materia son la lista `correlativas` de `datos_iniciales.json`: cambiar un
requisito es cambiar un dato, no tocar el servidor. Eso es lo que va a
administrar el panel de la institución cuando exista.

Condiciones de cursada que maneja el historial:

- `Aprobada`  — rindió el final y lo aprobó. Habilita las correlativas.
- `Regular`   — aprobó la cursada pero le falta el final. **Es la condición
                que habilita a inscribirse a una mesa de examen.**
- `En curso`  — la está cursando ahora.
- `Libre`     — perdió la cursada.

`Regular` no figuraba en la lista de estados del pedido, pero sin esa
distinción no se puede decidir quién puede rendir un final: aprobar la cursada
y aprobar la materia son dos cosas distintas.
"""

from __future__ import annotations

from .. import datos as d

# ===================== Estados =====================
# Los de una materia en la pantalla de inscripción.
APROBADA = "Aprobada"
REGULAR = "Regular"
EN_CURSO = "En curso"
INSCRIPTO = "Inscripto"
BLOQUEADA = "Bloqueada por correlatividad"
SIN_CUPO = "Sin cupos disponibles"
HABILITADA = "Habilitada"

# Los de una mesa de examen.
MESA_NO_HABILITADO = "No habilitado"
MESA_INSCRIPTO = "Inscripto"
MESA_PENDIENTE = "Pendiente"
MESA_CERRADA = "Cerrada"
MESA_CANCELADO = "Cancelado"
MESA_SIN_CUPO = "Sin cupos disponibles"
MESA_DISPONIBLE = "Disponible"
# La cátedra puede cancelar una mesa desde la gestión docente
# (`rutas/gestion_finales.py`). Pesa más que cualquier otro estado: una
# mesa que no se va a tomar no se rinde ni se discute el cupo.
MESA_SUSPENDIDA = "Mesa cancelada"


# ===================== Materias =====================
def materia_publica(materia: dict) -> dict:
    """La ficha de una materia con sus correlativas ya resueltas a nombres.

    El frontend muestra "Programación I", no el número 103.
    """
    docente = d.buscar_persona(materia.get("docenteId")) if materia.get("docenteId") else None
    return {
        "id": materia["id"],
        "codigo": materia["codigo"],
        "nombre": materia["nombre"],
        "carrera": materia["carrera"],
        "plan": materia["plan"],
        "anio": materia["anio"],
        "cuatrimestre": materia["cuatrimestre"],
        "cupo": materia["cupo"],
        "comision": materia.get("comision"),
        "horario": materia.get("horario"),
        "cursoId": materia.get("cursoId"),
        "docente": docente["nombre"] if docente else None,
        "correlativas": [
            {
                "id": c["id"],
                "codigo": c["codigo"],
                "nombre": c["nombre"],
            }
            for c in (d.buscar_materia(i) for i in materia.get("correlativas", []))
            if c
        ],
    }


def inscriptos_en_materia(materia_id: int) -> int:
    return sum(1 for i in d.inscripciones_materias if i["materiaId"] == materia_id)


def esta_inscripto_en_materia(persona_id: int, materia_id: int) -> bool:
    return any(
        i["personaId"] == persona_id and i["materiaId"] == materia_id
        for i in d.inscripciones_materias
    )


def correlativas_faltantes(persona_id: int, materia: dict) -> list[dict]:
    """Las materias que hay que aprobar antes y todavía no están aprobadas.

    Se devuelven enteras para poder decir *cuál* falta: un "no podés
    inscribirte" sin el motivo no le sirve a nadie.
    """
    faltan = []
    for id_correlativa in materia.get("correlativas", []):
        if d.condicion_en(persona_id, id_correlativa) == APROBADA:
            continue
        requisito = d.buscar_materia(id_correlativa)
        if requisito:
            faltan.append(
                {
                    "id": requisito["id"],
                    "codigo": requisito["codigo"],
                    "nombre": requisito["nombre"],
                    "condicion": d.condicion_en(persona_id, id_correlativa) or "Sin cursar",
                }
            )
    return faltan


def periodo_materias() -> dict:
    """El período general de inscripción a materias, y si está abierto."""
    periodo = d.periodo_inscripcion_materias
    ahora = d.ahora()
    desde = d.desde_iso(periodo["desde"])
    hasta = d.desde_iso(periodo["hasta"])
    return {
        "desde": periodo["desde"],
        "hasta": periodo["hasta"],
        "abierto": desde <= ahora <= hasta,
    }


def estado_de_materia(persona_id: int, materia: dict) -> dict:
    """En qué situación está la persona frente a una materia.

    El orden importa: lo que ya cursó pesa más que los cupos, y la
    correlatividad pesa más que el cupo (si no puede cursarla, que sobren
    lugares no cambia nada).
    """
    condicion = d.condicion_en(persona_id, materia["id"])
    inscriptos = inscriptos_en_materia(materia["id"])
    cupo = materia["cupo"]
    faltantes = correlativas_faltantes(persona_id, materia)

    base = {
        "inscriptos": inscriptos,
        "cupo": cupo,
        "lugares": max(cupo - inscriptos, 0),
        "faltantes": faltantes,
        "puedeInscribirse": False,
        "motivo": None,
    }

    if condicion == APROBADA:
        return {**base, "estado": APROBADA, "motivo": "Ya la aprobaste."}
    if condicion == REGULAR:
        return {
            **base,
            "estado": REGULAR,
            "motivo": "Aprobaste la cursada. Te falta rendir el final.",
        }
    if condicion == EN_CURSO:
        return {**base, "estado": EN_CURSO, "motivo": "La estás cursando."}

    if esta_inscripto_en_materia(persona_id, materia["id"]):
        return {**base, "estado": INSCRIPTO, "motivo": "Ya estás inscripto."}

    if faltantes:
        nombres = ", ".join(f["nombre"] for f in faltantes)
        return {
            **base,
            "estado": BLOQUEADA,
            "motivo": f"Te falta aprobar {nombres}.",
        }

    if inscriptos >= cupo:
        return {**base, "estado": SIN_CUPO, "motivo": "No quedan lugares."}

    abierto = periodo_materias()["abierto"]
    return {
        **base,
        "estado": HABILITADA,
        "puedeInscribirse": abierto,
        "motivo": None if abierto else "El período de inscripción está cerrado.",
    }


# ===================== Mesas de examen =====================
def inscripcion_en_mesa(persona_id: int, mesa_id: int) -> dict | None:
    """La inscripción vigente de la persona en esa mesa, si la hay.

    Una cancelada no cuenta: queda registrada, pero deja el lugar libre y
    permite volver a anotarse mientras el período siga abierto.
    """
    return next(
        (
            i
            for i in d.inscripciones_finales
            if i["personaId"] == persona_id
            and i["mesaId"] == mesa_id
            and i["estado"] == MESA_INSCRIPTO
        ),
        None,
    )


def cancelacion_en_mesa(persona_id: int, mesa_id: int) -> dict | None:
    return next(
        (
            i
            for i in d.inscripciones_finales
            if i["personaId"] == persona_id
            and i["mesaId"] == mesa_id
            and i["estado"] == MESA_CANCELADO
        ),
        None,
    )


def inscriptos_en_mesa(mesa_id: int) -> int:
    return sum(
        1
        for i in d.inscripciones_finales
        if i["mesaId"] == mesa_id and i["estado"] == MESA_INSCRIPTO
    )


def habilitado_para_rendir(persona_id: int, materia_id: int) -> bool:
    """Para rendir el final hay que tener la cursada aprobada."""
    return d.condicion_en(persona_id, materia_id) == REGULAR


def estado_de_mesa(persona_id: int, mesa: dict) -> dict:
    """La situación de la persona frente a una mesa de examen."""
    ahora = d.ahora()
    abre = d.desde_iso(mesa["inscripcionDesde"])
    cierra = d.desde_iso(mesa["inscripcionHasta"])
    inscriptos = inscriptos_en_mesa(mesa["id"])
    # El cupo puede venir vacío: en la gestión docente, una mesa sin cupo es
    # una mesa sin límite de inscriptos. Entonces no hay lugares que contar y
    # nunca se queda sin lugar.
    cupo = mesa.get("cupo")

    base = {
        "inscriptos": inscriptos,
        "cupo": cupo,
        "lugares": None if cupo is None else max(cupo - inscriptos, 0),
        "puedeInscribirse": False,
        "puedeCancelar": False,
        "motivo": None,
    }

    if mesa.get("estado") == "cancelada":
        return {
            **base,
            "estado": MESA_SUSPENDIDA,
            "motivo": mesa.get("motivoCancelacion") or "La cátedra canceló esta mesa.",
        }

    condicion = d.condicion_en(persona_id, mesa["materiaId"])
    if condicion != REGULAR:
        if condicion == APROBADA:
            motivo = "Ya aprobaste esta materia."
        elif condicion == EN_CURSO:
            motivo = "Todavía la estás cursando: podés rendirla cuando apruebes la cursada."
        else:
            motivo = "Necesitás tener la cursada aprobada para rendir."
        return {**base, "estado": MESA_NO_HABILITADO, "motivo": motivo}

    inscripcion = inscripcion_en_mesa(persona_id, mesa["id"])
    if inscripcion:
        # Se puede dar de baja mientras el período siga abierto
        return {
            **base,
            "estado": MESA_INSCRIPTO,
            "puedeCancelar": abre <= ahora <= cierra,
            "inscriptoEl": inscripcion["fecha"],
            "motivo": None
            if abre <= ahora <= cierra
            else "El período cerró: ya no se puede dar de baja.",
        }

    if ahora < abre:
        return {
            **base,
            "estado": MESA_PENDIENTE,
            "motivo": "La inscripción todavía no abrió.",
        }
    if ahora > cierra:
        return {**base, "estado": MESA_CERRADA, "motivo": "La inscripción cerró."}
    if cupo is not None and inscriptos >= cupo:
        return {**base, "estado": MESA_SIN_CUPO, "motivo": "No quedan lugares."}

    if cancelacion_en_mesa(persona_id, mesa["id"]):
        return {
            **base,
            "estado": MESA_CANCELADO,
            "puedeInscribirse": True,
            "motivo": "Diste de baja la inscripción. Podés volver a anotarte.",
        }

    return {**base, "estado": MESA_DISPONIBLE, "puedeInscribirse": True}


def mesa_publica(mesa: dict) -> dict:
    """La ficha de una mesa con la materia y el tribunal ya resueltos."""
    materia = d.buscar_materia(mesa["materiaId"])
    tribunal = [d.buscar_persona(i) for i in mesa.get("tribunal", [])]
    return {
        "id": mesa["id"],
        "materiaId": mesa["materiaId"],
        "materia": materia["nombre"] if materia else "Materia sin datos",
        "codigo": materia["codigo"] if materia else None,
        "cursoId": materia.get("cursoId") if materia else None,
        "llamado": mesa.get("llamado"),
        "fecha": mesa["fecha"],
        "desde": mesa["desde"],
        "hasta": mesa["hasta"],
        "modalidad": mesa["modalidad"],
        "lugar": mesa["lugar"],
        "inscripcionDesde": mesa["inscripcionDesde"],
        "inscripcionHasta": mesa["inscripcionHasta"],
        "tribunal": [p["nombre"] for p in tribunal if p],
        "cupo": mesa.get("cupo"),
        "cancelada": mesa.get("estado") == "cancelada",
        "motivoCancelacion": mesa.get("motivoCancelacion"),
    }
