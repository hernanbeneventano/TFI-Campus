"""La estructura académica de la institución y quién está dentro de ella.

Dos responsabilidades distintas, y a propósito con permisos distintos:

- **El administrador construye la estructura**: carreras, sedes, planes de
  estudio y comisiones. Nada de eso está escrito en el código; todo se crea
  desde acá.
- **El supervisor distribuye estudiantes** dentro de esa estructura: los
  inscribe en una carrera, los asigna a una comisión, los cambia de una a
  otra. No puede crear ni modificar carreras, sedes, planes ni comisiones:
  trabaja con lo que ya existe.

El administrador también puede hacer lo del supervisor, porque tiene todo.
Al revés no.

**Nada se borra del todo.** Una carrera con estudiantes o materias no se
elimina: se da de baja. Borrarla dejaría inscripciones apuntando al vacío y
un historial que ya no se puede leer.
"""

from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import academico as ac
from ..servicios import legajos
from ..servicios import auditoria
from ..servicios import modulos as mod
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/institucion", tags=["Institución"])

MAX_NOMBRE = 150
MAX_CODIGO = 20


# ===================== Permisos =====================
def es_administrador(yo: dict) -> bool:
    """Quien construye la estructura."""
    return d.tiene_rol(yo, "Administrador")


def es_supervisor(yo: dict) -> bool:
    """Quien distribuye estudiantes. El administrador también puede."""
    return d.tiene_rol(yo, "Supervisor", "Administrador")


def _exigir_administrador(yo: dict) -> None:
    if not es_administrador(yo):
        raise HTTPException(
            403,
            "Solo el administrador puede modificar la estructura académica.",
        )


def _exigir_supervisor(yo: dict) -> None:
    if not es_supervisor(yo):
        raise HTTPException(403, "Solo el supervisor puede asignar estudiantes.")


def _exigir_que_administre_lo_academico(yo: dict) -> None:
    """El período de inscripción, el mínimo de asistencia y los eventos.

    Los cambia **quien supervisa**, no solo quien administra. Abrir y cerrar
    el cuatrimestre, cargar las jornadas y fijar el mínimo es el trabajo
    diario de la secretaría: dejarlo del lado del administrador obligaba a
    pedirle a otra persona que apretara el botón, y la fecha se termina
    cambiando igual, tarde y por otro camino.

    La estructura —carreras, planes, materias— sigue siendo del
    administrador: eso define qué es la facultad, no cuándo abre.
    """
    if not es_supervisor(yo):
        raise HTTPException(
            403,
            "Solo la administración de la facultad cambia la configuración académica.",
        )


# ===================== Validación =====================
def _fecha_de(valor, que: str):
    """Una fecha que mandó la pantalla, o un error que diga cuál falta.

    Acepta tanto la fecha sola (`2026-03-01`, que es lo que manda un
    `<input type="date">`) como una fecha con hora. La primera se toma como
    el comienzo del día: un período que abre el 1 de marzo abre a las 00:00,
    no a las 00:00 de mañana.
    """
    texto = str(valor or "").strip()
    if not texto:
        raise HTTPException(400, f"Falta {que}")
    try:
        if len(texto) == 10:  # AAAA-MM-DD
            return d.desde_iso(texto + "T00:00:00").astimezone()
        return d.desde_iso(texto)
    except (ValueError, TypeError):
        raise HTTPException(400, f"{que.capitalize()} no es una fecha válida")


def _sin_tildes(texto) -> str:
    """Para buscar sin que importen las tildes ni las mayúsculas."""
    sin = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in sin if unicodedata.category(c) != "Mn").lower()


def _texto(valor, campo: str, maximo: int = MAX_NOMBRE, obligatorio: bool = True) -> str | None:
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


def _referencia(coleccion: list[dict], valor, que: str) -> dict:
    encontrado = d.buscar_en(coleccion, valor)
    if not encontrado:
        raise HTTPException(400, f"{que} no existe")
    return encontrado


def _vincular_con_las_materias(persona_id: int, comision_id: int | None) -> list[str]:
    """Inscribe al estudiante en las materias que se dictan en su comisión.

    Es lo que evita tener que anotarlo a mano en cada una: si la comisión ya
    tiene su cuadro de materias armado, pertenecer a la comisión *es* cursar
    esas materias.

    Tres cuidados: no duplica lo que ya tenía, **no toca lo que el alumno ya
    cursó o aprobó** —si tiene condición en el historial, esa materia no se
    vuelve a inscribir— y **saltea las materias dadas de baja**. Esto último
    importa: la comisión conserva su cuadro de materias aunque una se dé de
    baja, y sin esta comprobación una materia que el campus ya no ofrece
    volvería a aparecer en el plan de cada estudiante nuevo. Devuelve los
    nombres de lo que agregó, para poder decírselo a quien hizo la asignación.
    """
    if not comision_id:
        return []

    agregadas = []
    for dictado in d.dictados_de_comision(comision_id):
        materia = d.buscar_materia(dictado["materiaId"])
        if not materia:
            continue
        if not materia.get("activa", True):
            continue
        # «¿Ya está?» y anotar van juntos: el alumno se puede estar anotando
        # solo a la misma materia en ese momento. Ver
        # `academico.inscripciones_a_materias`.
        with ac.inscripciones_a_materias:
            # Ya inscripto, o ya cursada: no se toca
            if any(
                i["personaId"] == persona_id and i["materiaId"] == materia["id"]
                for i in d.inscripciones_materias
            ):
                continue
            if d.condicion_en(persona_id, materia["id"]):
                continue

            d.inscripciones_materias.append(
                {
                    "id": d.nuevo_id_inscripcion_materia(),
                    "personaId": persona_id,
                    "materiaId": materia["id"],
                    "fecha": d.iso(d.ahora()),
                    "porComision": comision_id,
                }
            )
        # Y la materia entra a Módulos, igual que cuando el estudiante se
        # anota por su cuenta. Sin esto quedaba inscripto a seis materias y
        # su pantalla de Módulos vacía: la inscripción existía pero el módulo
        # donde cursarla, no.
        #
        # Va sin `por_inscripcion`: lo armó la institución al ponerlo en la
        # comisión, así que es la cursada de la cátedra y no se borra porque
        # un estudiante se dé de baja.
        mod.modulo_para(materia)
        agregadas.append(materia["nombre"])
    return agregadas


# De lo que se anota a la acción del vocabulario de auditoría. La frase que
# escribe cada ruta ("carrera creada", "plan dado de baja") ya dice qué pasó:
# alcanza con mirar su última palabra.
_ACCION_POR_PALABRA = {
    "creada": "creacion", "creado": "creacion", "creadas": "creacion",
    "editada": "edicion", "editado": "edicion", "configurado": "edicion",
    "baja": "baja", "eliminada": "baja", "eliminado": "baja",
    "estado": "estado", "roles": "roles", "cuenta": "estado",
    "asignado": "asignacion", "asignada": "asignacion",
    "reasignado": "reasignacion", "cambiada": "reasignacion",
}


def _accion_de(que: str) -> str:
    for palabra in reversed(que.lower().split()):
        if palabra in _ACCION_POR_PALABRA:
            return _ACCION_POR_PALABRA[palabra]
    return "edicion"


def _anotar(
    yo: dict,
    que: str,
    detalle: str,
    persona_id: int | None = None,
    *,
    antes=None,
    despues=None,
    elemento_id=None,
    **alcance,
) -> None:
    """Deja registro de los cambios sobre la estructura o la gente.

    Sin esto, "¿quién sacó a este alumno de la comisión?" no tiene respuesta.
    Escribe en el registro **central** (`servicios/auditoria`): antes cada
    apartado tenía el suyo y había que preguntarle a cada uno por separado.
    """
    auditoria.registrar(
        yo,
        _accion_de(que),
        "academico",
        elemento=detalle,
        elemento_id=elemento_id,
        elemento_tipo=que,
        persona_id=persona_id,
        antes=antes,
        despues=despues,
        detalle=que,
        **alcance,
    )


# ===================== El catálogo =====================
@router.get("", summary="Toda la estructura académica")
def catalogo(yo: dict = UsuarioActual):
    """Carreras, sedes, planes y comisiones, con lo que cada uno tiene colgando.

    La lee cualquiera que haya iniciado sesión: un alumno necesita ver el
    nombre de su carrera y su comisión. Modificarla es otra cosa, y para eso
    están `puedeAdministrar` y `puedeAsignar`.
    """
    def usos_de_carrera(carrera_id: int) -> dict:
        return {
            "planes": sum(1 for p in d.planes_estudio if p["carreraId"] == carrera_id),
            "comisiones": sum(1 for c in d.comisiones if c["carreraId"] == carrera_id),
            "materias": sum(1 for m in d.materias_plan if m.get("carreraId") == carrera_id),
            "estudiantes": sum(
                1 for a in d.asociaciones_academicas if a["carreraId"] == carrera_id
            ),
        }

    return {
        "carreras": [{**c, "usos": usos_de_carrera(c["id"])} for c in d.carreras_institucion],
        "sedes": [
            {
                **s,
                "comisiones": sum(1 for c in d.comisiones if c["sedeId"] == s["id"]),
            }
            for s in d.sedes
        ],
        "planes": [
            {
                **p,
                "carrera": (d.buscar_en(d.carreras_institucion, p["carreraId"]) or {}).get(
                    "nombre"
                ),
                "materias": sum(1 for m in d.materias_plan if m.get("planId") == p["id"]),
            }
            for p in d.planes_estudio
        ],
        "comisiones": [
            {
                **c,
                "carrera": (d.buscar_en(d.carreras_institucion, c["carreraId"]) or {}).get(
                    "nombre"
                ),
                "sede": (d.buscar_en(d.sedes, c["sedeId"]) or {}).get("nombre"),
                "estudiantes": sum(
                    1 for a in d.asociaciones_academicas if a.get("comisionId") == c["id"]
                ),
            }
            for c in d.comisiones
        ],
        "turnos": d.TURNOS,
        "roles": d.ROLES,
        "puedeAdministrar": es_administrador(yo),
        "puedeAsignar": es_supervisor(yo),
    }


# ===================== Carreras =====================
@router.post("/carreras", status_code=201, summary="Crear una carrera")
def crear_carrera(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    nombre = _texto(cuerpo.get("nombre"), "el nombre de la carrera")
    if any(c["nombre"].lower() == nombre.lower() for c in d.carreras_institucion):
        raise HTTPException(409, "Ya existe una carrera con ese nombre")

    carrera = {
        "id": d.nuevo_id_carrera(),
        "nombre": nombre,
        "codigo": _texto(cuerpo.get("codigo"), "el código", MAX_CODIGO, obligatorio=False),
        "activa": True,
        "creada": d.iso(d.ahora()),
    }
    d.carreras_institucion.append(carrera)
    _anotar(yo, "carrera creada", nombre)
    return catalogo(yo)


@router.patch("/carreras/{id_carrera}", summary="Editar una carrera")
def editar_carrera(id_carrera: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    carrera = _referencia(d.carreras_institucion, id_carrera, "La carrera")

    if "nombre" in cuerpo:
        nombre = _texto(cuerpo["nombre"], "el nombre de la carrera")
        if any(
            c["nombre"].lower() == nombre.lower() and c["id"] != carrera["id"]
            for c in d.carreras_institucion
        ):
            raise HTTPException(409, "Ya existe otra carrera con ese nombre")
        carrera["nombre"] = nombre
    if "codigo" in cuerpo:
        carrera["codigo"] = _texto(cuerpo["codigo"], "el código", MAX_CODIGO, obligatorio=False)
    if "activa" in cuerpo:
        carrera["activa"] = bool(cuerpo["activa"])

    _anotar(yo, "carrera editada", carrera["nombre"])
    return catalogo(yo)


@router.delete("/carreras/{id_carrera}", summary="Dar de baja una carrera")
def borrar_carrera(id_carrera: int, yo: dict = UsuarioActual):
    """Se elimina solo si no la usa nadie; si no, se da de baja.

    Borrar una carrera con estudiantes dejaría sus inscripciones apuntando a
    algo que ya no existe.
    """
    _exigir_administrador(yo)
    carrera = _referencia(d.carreras_institucion, id_carrera, "La carrera")

    en_uso = (
        any(a["carreraId"] == id_carrera for a in d.asociaciones_academicas)
        or any(m.get("carreraId") == id_carrera for m in d.materias_plan)
        or any(c["carreraId"] == id_carrera for c in d.comisiones)
    )
    if en_uso:
        carrera["activa"] = False
        _anotar(yo, "carrera dada de baja", carrera["nombre"])
    else:
        d.carreras_institucion.remove(carrera)
        d.planes_estudio[:] = [p for p in d.planes_estudio if p["carreraId"] != id_carrera]
        _anotar(yo, "carrera eliminada", carrera["nombre"])

    return catalogo(yo)


# ===================== Sedes =====================
@router.post("/sedes", status_code=201, summary="Crear una sede")
def crear_sede(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    nombre = _texto(cuerpo.get("nombre"), "el nombre de la sede")
    if any(s["nombre"].lower() == nombre.lower() for s in d.sedes):
        raise HTTPException(409, "Ya existe una sede con ese nombre")

    d.sedes.append(
        {
            "id": d.nuevo_id_sede(),
            "nombre": nombre,
            "ciudad": _texto(cuerpo.get("ciudad"), "la ciudad", obligatorio=False),
            "activa": True,
        }
    )
    _anotar(yo, "sede creada", nombre)
    return catalogo(yo)


@router.patch("/sedes/{id_sede}", summary="Editar una sede")
def editar_sede(id_sede: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    sede = _referencia(d.sedes, id_sede, "La sede")
    if "nombre" in cuerpo:
        sede["nombre"] = _texto(cuerpo["nombre"], "el nombre de la sede")
    if "ciudad" in cuerpo:
        sede["ciudad"] = _texto(cuerpo["ciudad"], "la ciudad", obligatorio=False)
    if "activa" in cuerpo:
        sede["activa"] = bool(cuerpo["activa"])
    _anotar(yo, "sede editada", sede["nombre"])
    return catalogo(yo)


@router.delete("/sedes/{id_sede}", summary="Dar de baja una sede")
def borrar_sede(id_sede: int, yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    sede = _referencia(d.sedes, id_sede, "La sede")
    if any(c["sedeId"] == id_sede for c in d.comisiones):
        sede["activa"] = False
        _anotar(yo, "sede dada de baja", sede["nombre"])
    else:
        d.sedes.remove(sede)
        _anotar(yo, "sede eliminada", sede["nombre"])
    return catalogo(yo)


# ===================== Planes de estudio =====================
@router.post("/planes", status_code=201, summary="Crear un plan de estudio")
def crear_plan(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Un plan es siempre de una carrera: la misma carrera puede tener el
    plan 2008 y el 2023 conviviendo."""
    _exigir_administrador(yo)
    carrera = _referencia(d.carreras_institucion, cuerpo.get("carreraId"), "La carrera")
    nombre = _texto(cuerpo.get("nombre"), "el nombre del plan")

    if any(
        p["carreraId"] == carrera["id"] and p["nombre"].lower() == nombre.lower()
        for p in d.planes_estudio
    ):
        raise HTTPException(409, "Esa carrera ya tiene un plan con ese nombre")

    anio = cuerpo.get("anio")
    if anio is not None and (not isinstance(anio, int) or not 1950 <= anio <= 2100):
        raise HTTPException(400, "El año del plan no es válido")

    d.planes_estudio.append(
        {
            "id": d.nuevo_id_plan(),
            "carreraId": carrera["id"],
            "nombre": nombre,
            "anio": anio,
            "activo": True,
            "creado": d.iso(d.ahora()),
        }
    )
    _anotar(yo, "plan creado", f"{nombre} ({carrera['nombre']})")
    return catalogo(yo)


@router.patch("/planes/{id_plan}", summary="Editar un plan")
def editar_plan(id_plan: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    plan = _referencia(d.planes_estudio, id_plan, "El plan")
    if "nombre" in cuerpo:
        plan["nombre"] = _texto(cuerpo["nombre"], "el nombre del plan")
    if "activo" in cuerpo:
        plan["activo"] = bool(cuerpo["activo"])
    _anotar(yo, "plan editado", plan["nombre"])
    return catalogo(yo)


@router.delete("/planes/{id_plan}", summary="Dar de baja un plan")
def borrar_plan(id_plan: int, yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    plan = _referencia(d.planes_estudio, id_plan, "El plan")
    en_uso = any(m.get("planId") == id_plan for m in d.materias_plan) or any(
        a.get("planId") == id_plan for a in d.asociaciones_academicas
    )
    if en_uso:
        plan["activo"] = False
        _anotar(yo, "plan dado de baja", plan["nombre"])
    else:
        d.planes_estudio.remove(plan)
        _anotar(yo, "plan eliminado", plan["nombre"])
    return catalogo(yo)


# ===================== Comisiones =====================
@router.post("/comisiones", status_code=201, summary="Crear una comisión")
def crear_comision(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Una comisión es de una carrera **y** de una sede.

    La misma sede dicta varias carreras, y la misma carrera se dicta en
    varias sedes: sin las dos referencias no se sabe de cuál se habla.
    """
    _exigir_administrador(yo)
    carrera = _referencia(d.carreras_institucion, cuerpo.get("carreraId"), "La carrera")
    sede = _referencia(d.sedes, cuerpo.get("sedeId"), "La sede")
    nombre = _texto(cuerpo.get("nombre"), "el nombre de la comisión")

    if any(
        c["carreraId"] == carrera["id"]
        and c["sedeId"] == sede["id"]
        and c["nombre"].lower() == nombre.lower()
        for c in d.comisiones
    ):
        raise HTTPException(409, "Ya existe esa comisión en esa carrera y sede")

    turno = cuerpo.get("turno")
    if turno is not None and turno not in d.TURNOS:
        raise HTTPException(400, "Ese turno no existe")

    anio = cuerpo.get("anio")
    if anio is not None and (not isinstance(anio, int) or not 1 <= anio <= 10):
        raise HTTPException(400, "El año de la comisión no es válido")

    # La comisión es de un plan: la misma carrera puede tener el 2008 y el
    # 2023 conviviendo, con materias distintas.
    plan = None
    if cuerpo.get("planId"):
        plan = _referencia(d.planes_estudio, cuerpo["planId"], "El plan")
        if plan["carreraId"] != carrera["id"]:
            raise HTTPException(400, "Ese plan no es de esa carrera")

    d.comisiones.append(
        {
            "id": d.nuevo_id_comision(),
            "carreraId": carrera["id"],
            "sedeId": sede["id"],
            "planId": plan["id"] if plan else None,
            "nombre": nombre,
            "anio": anio,
            "turno": turno,
            "activa": True,
            "creada": d.iso(d.ahora()),
        }
    )
    _anotar(yo, "comisión creada", f"{nombre} · {carrera['nombre']} · {sede['nombre']}")
    return catalogo(yo)


@router.get("/comisiones/{id_comision}", summary="Una comisión con sus materias")
def ver_comision(id_comision: int, yo: dict = UsuarioActual):
    """La comisión, qué materias se dictan en ella y quién las da.

    Se listan **todas las materias del plan**, no solo las que ya tienen
    dictado: el administrador necesita ver qué le falta configurar, y una
    lista con solo lo hecho esconde justamente lo que hay que hacer.
    """
    comision = _referencia(d.comisiones, id_comision, "La comisión")
    carrera = d.buscar_en(d.carreras_institucion, comision["carreraId"])
    sede = d.buscar_en(d.sedes, comision["sedeId"])
    plan = d.buscar_en(d.planes_estudio, comision.get("planId"))

    del_plan = [
        m
        for m in d.materias_plan
        if m.get("carreraId") == comision["carreraId"]
        and (not comision.get("planId") or m.get("planId") == comision["planId"])
    ]
    del_plan.sort(key=lambda m: (m["anio"], m["cuatrimestre"], m["codigo"]))

    materias = []
    for materia in del_plan:
        dictado = next(
            (x for x in d.dictados_de_comision(id_comision) if x["materiaId"] == materia["id"]),
            None,
        )
        docentes = [d.buscar_persona(x) for x in (dictado or {}).get("docentes", [])]
        materias.append(
            {
                "id": materia["id"],
                "codigo": materia["codigo"],
                "nombre": materia["nombre"],
                "anio": materia["anio"],
                "cuatrimestre": materia["cuatrimestre"],
                "seDicta": dictado is not None,
                "dictadoId": (dictado or {}).get("id"),
                "horario": (dictado or {}).get("horario"),
                "docentes": [
                    {"id": x["id"], "nombre": x["nombre"]} for x in docentes if x
                ],
            }
        )

    return {
        "comision": {
            **comision,
            "carrera": carrera["nombre"] if carrera else None,
            "sede": sede["nombre"] if sede else None,
            "plan": plan["nombre"] if plan else None,
        },
        "materias": materias,
        "docentesDisponibles": [
            {"id": p["id"], "nombre": p["nombre"]}
            for p in d.personas
            if d.tiene_rol(p, "Docente")
        ],
        "estudiantes": sum(
            1 for a in d.asociaciones_academicas if a.get("comisionId") == id_comision
        ),
        "puedeAdministrar": es_administrador(yo),
    }


@router.put("/comisiones/{id_comision}/materias/{id_materia}", summary="Dictar una materia")
def configurar_dictado(
    id_comision: int, id_materia: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual
):
    """Pone una materia a dictarse en la comisión y le asigna docentes.

    Una materia puede tener **más de un docente** —cátedras compartidas, un
    titular y un adjunto— y un docente puede estar en varias materias y
    comisiones. Por eso `docentes` es una lista y no un campo.
    """
    _exigir_administrador(yo)
    comision = _referencia(d.comisiones, id_comision, "La comisión")
    materia = d.buscar_materia(id_materia)
    if not materia:
        raise HTTPException(404, "La materia no existe")
    if materia.get("carreraId") != comision["carreraId"]:
        raise HTTPException(400, "Esa materia no es de la carrera de la comisión")

    docentes = cuerpo.get("docentes") or []
    if not isinstance(docentes, list):
        raise HTTPException(400, "Los docentes tienen que venir en una lista")
    for persona_id in docentes:
        persona = d.buscar_persona(persona_id)
        if not persona:
            raise HTTPException(400, "Una de las personas elegidas no existe")
        if not d.tiene_rol(persona, "Docente"):
            raise HTTPException(
                400, f"{persona['nombre']} no tiene el rol de docente"
            )

    horario = _texto(cuerpo.get("horario"), "el horario", 120, obligatorio=False)

    dictado = next(
        (x for x in d.dictados_de_comision(id_comision) if x["materiaId"] == id_materia),
        None,
    )

    def nombres(ids):
        return [p["nombre"] for i in ids if (p := d.buscar_persona(i))]

    if dictado:
        # Reasignar un docente conserva quién estaba antes: es la pregunta que
        # se hace después ("¿quién daba esto el cuatrimestre pasado?").
        antes = {
            "docentes": nombres(dictado.get("docentes") or []),
            "horario": dictado.get("horario"),
        }
        dictado["docentes"] = list(dict.fromkeys(docentes))
        dictado["horario"] = horario
    else:
        antes = None
        d.dictados.append(
            {
                "id": d.nuevo_id_dictado(),
                "comisionId": id_comision,
                "materiaId": id_materia,
                "docentes": list(dict.fromkeys(docentes)),
                "horario": horario,
                "creado": d.iso(d.ahora()),
            }
        )

    # El módulo tiene que seguir al dictado, o quien dejó la materia la sigue
    # viendo y quien la tomó no la ve aparecer.
    mod.sincronizar_docente(materia)

    despues = {"docentes": nombres(docentes), "horario": horario}
    _anotar(
        yo,
        "docentes reasignados" if antes else "dictado asignado",
        f"{materia['nombre']} en {comision['nombre']}",
        antes=antes,
        despues=despues,
        elemento_id=id_materia,
        carrera_id=comision.get("carreraId"),
        sede_id=comision.get("sedeId"),
        comision_id=id_comision,
        materia_id=id_materia,
    )
    return ver_comision(id_comision, yo)


@router.delete("/comisiones/{id_comision}/materias/{id_materia}", summary="Dejar de dictarla")
def quitar_dictado(id_comision: int, id_materia: int, yo: dict = UsuarioActual):
    """La materia deja de dictarse en esa comisión.

    No toca a los alumnos ya inscriptos: lo que cursaron, cursaron. Deja de
    ofrecerse de ahí en adelante.
    """
    _exigir_administrador(yo)
    comision = _referencia(d.comisiones, id_comision, "La comisión")
    dictado = next(
        (x for x in d.dictados_de_comision(id_comision) if x["materiaId"] == id_materia),
        None,
    )
    if not dictado:
        raise HTTPException(404, "Esa materia no se dicta en esta comisión")
    d.dictados.remove(dictado)
    materia = d.buscar_materia(id_materia)
    if materia:
        mod.sincronizar_docente(materia)
    _anotar(
        yo,
        "dictado eliminado",
        f"{materia['nombre'] if materia else '—'} en {comision['nombre']}",
        antes={"docentes": [
            p["nombre"] for i in (dictado.get("docentes") or []) if (p := d.buscar_persona(i))
        ]},
        elemento_id=id_materia,
        carrera_id=comision.get("carreraId"),
        sede_id=comision.get("sedeId"),
        comision_id=id_comision,
        materia_id=id_materia,
    )
    return ver_comision(id_comision, yo)


@router.patch("/comisiones/{id_comision}", summary="Editar una comisión")
def editar_comision(id_comision: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    comision = _referencia(d.comisiones, id_comision, "La comisión")
    if "nombre" in cuerpo:
        comision["nombre"] = _texto(cuerpo["nombre"], "el nombre de la comisión")
    if "turno" in cuerpo:
        if cuerpo["turno"] not in d.TURNOS:
            raise HTTPException(400, "Ese turno no existe")
        comision["turno"] = cuerpo["turno"]
    if "sedeId" in cuerpo:
        comision["sedeId"] = _referencia(d.sedes, cuerpo["sedeId"], "La sede")["id"]
    if "activa" in cuerpo:
        comision["activa"] = bool(cuerpo["activa"])
    _anotar(yo, "comisión editada", comision["nombre"])
    return catalogo(yo)


@router.delete("/comisiones/{id_comision}", summary="Dar de baja una comisión")
def borrar_comision(id_comision: int, yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    comision = _referencia(d.comisiones, id_comision, "La comisión")
    if any(a.get("comisionId") == id_comision for a in d.asociaciones_academicas):
        comision["activa"] = False
        _anotar(yo, "comisión dada de baja", comision["nombre"])
    else:
        d.comisiones.remove(comision)
        _anotar(yo, "comisión eliminada", comision["nombre"])
    return catalogo(yo)


# ===================== Distribución de estudiantes =====================
@router.get("/asignaciones", summary="Quién está en cada carrera y comisión")
def asignaciones(
    yo: dict = UsuarioActual,
    carreraId: int | None = None,
    sedeId: int | None = None,
    comisionId: int | None = None,
    sinComision: bool = False,
    q: str | None = None,
):
    """La distribución de estudiantes, para el supervisor.

    Se puede recortar por carrera, sede y comisión —que es como se mira la
    distribución de verdad: "los de primero de la noche en Goya"— y buscar
    a una persona por nombre, correo o legajo, que es la otra forma de usar
    esta pantalla: encontrar a alguien y ver dónde está.

    Con `sinComision` quedan los que están en una carrera pero todavía no
    tienen comisión: son los que hay que ubicar.
    """
    _exigir_supervisor(yo)

    buscado = _sin_tildes(q)

    filas = []
    for asociacion in d.asociaciones_academicas:
        if carreraId and asociacion["carreraId"] != carreraId:
            continue
        if sedeId and asociacion.get("sedeId") != sedeId:
            continue
        if comisionId and asociacion.get("comisionId") != comisionId:
            continue
        if sinComision and asociacion.get("comisionId"):
            continue
        persona = d.buscar_persona(asociacion["personaId"])
        if not persona:
            continue
        if buscado and not any(
            buscado in _sin_tildes(x)
            for x in (persona["nombre"], persona.get("correo"), asociacion.get("legajo"))
        ):
            continue
        filas.append(
            {
                **d.asociacion_completa(asociacion),
                "nombre": persona["nombre"],
                "correo": persona.get("correo"),
            }
        )

    filas.sort(key=lambda f: (f["carrera"] or "", f["comision"] or "", f["nombre"]))

    return {
        "asignaciones": filas,
        "sinComision": sum(1 for f in filas if not f.get("comisionId")),
        "puedeAsignar": es_supervisor(yo),
    }


@router.get("/legajo-siguiente", summary="El legajo que le tocaría a quien se inscriba")
def legajo_siguiente(carreraId: int | None = None, yo: dict = UsuarioActual):
    """Para mostrarlo en el formulario **antes** de inscribir.

    Quien carga ve el número que le va a quedar, en vez de un campo vacío
    que dice «se genera solo»: el legajo es con lo que después se busca a esa
    persona, y saberlo recién al final obliga a volver a buscarla.

    Es una **vista previa, no una reserva**. El legajo definitivo lo arma el
    servidor al guardar, con los datos de ese momento: si entre que se abre
    el formulario y se aprieta Inscribir alguien más se anota, el número que
    se vio ya no es el libre, y el bueno es el del final. Por eso la pantalla
    lo muestra y no lo manda de vuelta.
    """
    _exigir_supervisor(yo)
    carrera = _referencia(d.carreras_institucion, carreraId, "La carrera")
    anio = d.ahora().year
    return {
        "legajo": legajos.proximo_de_carrera(carrera["id"], anio),
        "carrera": carrera["nombre"],
        "anio": anio,
    }


@router.post("/asignaciones", status_code=201, summary="Inscribir a un estudiante")
def crear_asignacion(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Mete a un estudiante en una carrera, con su sede, comisión y plan.

    Es lo que hace el supervisor al ingreso. La comisión puede quedar vacía
    si todavía no se decidió: después se asigna.
    """
    _exigir_supervisor(yo)

    persona = d.buscar_persona(cuerpo.get("personaId"))
    if not persona:
        raise HTTPException(404, "Esa persona no existe")
    if not d.tiene_rol(persona, "Estudiante"):
        raise HTTPException(400, "Solo se inscribe a quien tenga el rol de estudiante")

    carrera = _referencia(d.carreras_institucion, cuerpo.get("carreraId"), "La carrera")
    if not carrera["activa"]:
        raise HTTPException(400, "Esa carrera está dada de baja")

    sede = _referencia(d.sedes, cuerpo.get("sedeId"), "La sede")
    plan = _referencia(d.planes_estudio, cuerpo.get("planId"), "El plan")
    if plan["carreraId"] != carrera["id"]:
        raise HTTPException(400, "Ese plan no es de esa carrera")

    comision = None
    if cuerpo.get("comisionId"):
        comision = _referencia(d.comisiones, cuerpo["comisionId"], "La comisión")
        if comision["carreraId"] != carrera["id"] or comision["sedeId"] != sede["id"]:
            raise HTTPException(400, "Esa comisión no es de esa carrera y sede")

    # Comprobar, numerar y anotar van juntos (ver `legajos.py`): dos
    # inscripciones a la vez sacaban el mismo legajo, y la misma persona
    # mandada dos veces pasaba dos veces por «todavía no está inscripta».
    with legajos.inscripciones_a_carrera:
        # Una persona no se inscribe dos veces a la misma carrera
        if any(
            a["personaId"] == persona["id"] and a["carreraId"] == carrera["id"]
            for a in d.asociaciones_academicas
        ):
            raise HTTPException(409, "Esa persona ya está inscripta en esa carrera")

        asociacion = {
            "id": d.nuevo_id_asociacion(),
            "personaId": persona["id"],
            "carreraId": carrera["id"],
            "sedeId": sede["id"],
            "comisionId": comision["id"] if comision else None,
            "planId": plan["id"],
            # Si no lo escriben, lo arma el sistema: es un contador por carrera
            # y nadie que carga tiene cómo saber cuál fue el último.
            "legajo": _texto(cuerpo.get("legajo"), "el legajo", 40, obligatorio=False)
            or legajos.proximo_de_carrera(carrera["id"], d.ahora().year),
            "estado": "activa",
            "desde": d.iso(d.ahora()),
            "ingreso": d.ahora().year,
        }
        d.asociaciones_academicas.append(asociacion)

    # Pertenecer a la comisión es cursar sus materias: no hace falta
    # inscribirlo a una por una.
    materias = _vincular_con_las_materias(persona["id"], asociacion["comisionId"])

    _anotar(
        yo,
        "estudiante inscripto",
        f"{persona['nombre']} en {carrera['nombre']}"
        + (f" · {len(materias)} materias" if materias else ""),
        persona["id"],
    )
    return {
        "asociacion": d.asociacion_completa(asociacion),
        "materiasVinculadas": materias,
    }


@router.patch("/asignaciones/{id_asociacion}", summary="Cambiar de comisión o de plan")
def editar_asignacion(id_asociacion: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Cambios de comisión, de plan o de estado.

    La carrera no se cambia: cambiar de carrera es otra inscripción, con su
    propio historial. Mutarla acá borraría de dónde viene el alumno.
    """
    _exigir_supervisor(yo)
    asociacion = _referencia(d.asociaciones_academicas, id_asociacion, "La asignación")
    persona = d.buscar_persona(asociacion["personaId"])
    antes = d.asociacion_completa(asociacion)
    # Lo que se le agregue al cambiarlo de comisión
    materias: list[str] = []

    if "comisionId" in cuerpo:
        if cuerpo["comisionId"] is None:
            asociacion["comisionId"] = None
        else:
            comision = _referencia(d.comisiones, cuerpo["comisionId"], "La comisión")
            if comision["carreraId"] != asociacion["carreraId"]:
                raise HTTPException(400, "Esa comisión no es de la carrera del estudiante")
            asociacion["comisionId"] = comision["id"]
            asociacion["sedeId"] = comision["sedeId"]
            # Al cambiarlo de comisión queda en las materias de la nueva
            materias = _vincular_con_las_materias(asociacion["personaId"], comision["id"])


    if "planId" in cuerpo:
        plan = _referencia(d.planes_estudio, cuerpo["planId"], "El plan")
        if plan["carreraId"] != asociacion["carreraId"]:
            raise HTTPException(400, "Ese plan no es de la carrera del estudiante")
        asociacion["planId"] = plan["id"]

    if "estado" in cuerpo:
        if cuerpo["estado"] not in d.ESTADOS_ASOCIACION:
            raise HTTPException(400, "Ese estado no existe")
        asociacion["estado"] = cuerpo["estado"]

    if "legajo" in cuerpo:
        asociacion["legajo"] = _texto(cuerpo["legajo"], "el legajo", 40, obligatorio=False)

    despues = d.asociacion_completa(asociacion)
    cambios = [
        f"{campo}: {antes[campo]} → {despues[campo]}"
        for campo in ("comision", "plan", "estado")
        if antes[campo] != despues[campo]
    ]
    if cambios:
        _anotar(
            yo,
            "asignación modificada",
            f"{persona['nombre'] if persona else '—'} · " + "; ".join(cambios),
            asociacion["personaId"],
        )

    return {"asociacion": despues, "materiasVinculadas": materias}


@router.delete("/asignaciones/{id_asociacion}", summary="Dar de baja una inscripción")
def borrar_asignacion(id_asociacion: int, yo: dict = UsuarioActual):
    """Se marca como suspendida, no se borra: el alumno cursó, y eso pasó.

    Para sacarlo definitivamente habría que borrar también sus notas y sus
    asistencias, que es justamente lo que no se quiere.
    """
    _exigir_supervisor(yo)
    asociacion = _referencia(d.asociaciones_academicas, id_asociacion, "La asignación")
    persona = d.buscar_persona(asociacion["personaId"])
    asociacion["estado"] = "suspendida"
    _anotar(
        yo,
        "inscripción suspendida",
        persona["nombre"] if persona else "—",
        asociacion["personaId"],
    )
    return {"asociacion": d.asociacion_completa(asociacion)}


# ===================== Historial =====================
@router.get("/historial", summary="Los cambios sobre la estructura y la gente")
def historial(yo: dict = UsuarioActual):
    """Los últimos movimientos académicos.

    Es una vista del **registro central** de auditoría, no un historial
    aparte: el apartado completo, con todos sus filtros, está en
    `/api/auditoria`.
    """
    _exigir_supervisor(yo)
    eventos = auditoria.buscar({"modulo": "academico"})
    return {
        "historial": [
            {
                **auditoria.con_nombres(e),
                # Los nombres que esperaba la pantalla que ya existía
                "que": e.get("elementoTipo") or e["accion"],
                "detalle": e.get("elemento"),
                "quienNombre": e["quien"],
            }
            for e in eventos[:200]
        ]
    }


# ===================== Materias =====================
# Una materia es del **plan**, no de la comisión: el plan dice qué hay que
# cursar y en qué orden, y la comisión dice quién la dicta y cuándo. Por eso
# las correlatividades viven acá y no en el dictado.


def _grupo_de_correlativas(cuerpo, clave: str, materia_id, plan_id) -> dict:
    """Valida y arma uno de los dos grupos de requisitos.

    Las reglas son las de cualquier plan de estudios:

    - **Una materia no puede ser correlativa de sí misma.** Nadie podría
      cursarla nunca.
    - **Del mismo plan.** Pedir una materia de otro plan deja al estudiante
      con un requisito que no puede cumplir desde su carrera.
    - **Sin ciclos.** Si A pide B y B pide A, ninguna de las dos se puede
      cursar jamás. Se comprueba el camino entero, no solo el paso directo.
    """
    grupo = (cuerpo.get("correlativas") or {}).get(clave) or {}
    modo = grupo.get("modo") or "todas"
    if modo not in d.MODOS_CORRELATIVA:
        raise HTTPException(400, "Ese modo de correlatividad no existe")

    salida = []
    vistos = set()
    for r in grupo.get("requisitos") or []:
        try:
            otra_id = int(r.get("materiaId"))
        except (TypeError, ValueError):
            raise HTTPException(400, "Una correlativa no tiene materia")

        condicion = r.get("condicion") or "Aprobada"
        if condicion not in d.CONDICIONES_CORRELATIVA:
            raise HTTPException(400, f"La condición «{condicion}» no existe")

        if materia_id is not None and otra_id == materia_id:
            raise HTTPException(400, "Una materia no puede ser correlativa de sí misma")

        otra = d.buscar_materia(otra_id)
        if not otra:
            raise HTTPException(400, "Una de las correlativas no existe")
        if otra.get("planId") != plan_id:
            raise HTTPException(
                400,
                f"«{otra['nombre']}» es de otro plan de estudio: no puede ser correlativa",
            )

        if otra_id in vistos:
            continue  # la misma materia dos veces en el grupo es una sola
        vistos.add(otra_id)
        salida.append({"materiaId": otra_id, "condicion": condicion})

    if materia_id is not None:
        for r in salida:
            if _hay_ciclo(materia_id, r["materiaId"], clave):
                otra = d.buscar_materia(r["materiaId"])
                raise HTTPException(
                    400,
                    f"«{otra['nombre']}» ya depende de esta materia: quedarían encadenadas "
                    "y ninguna de las dos se podría cursar.",
                )

    return {"modo": modo, "requisitos": salida}


def _hay_ciclo(materia_id: int, desde_id: int, clave: str) -> bool:
    """Si llegando desde `desde_id` se vuelve a `materia_id`."""
    por_ver = [desde_id]
    vistos = set()
    while por_ver:
        actual = por_ver.pop()
        if actual == materia_id:
            return True
        if actual in vistos:
            continue
        vistos.add(actual)
        otra = d.buscar_materia(actual)
        if not otra:
            continue
        for r in ac.requisitos_de(otra, clave)["requisitos"]:
            por_ver.append(r.get("materiaId"))
    return False


def _leer_materia(cuerpo: dict, materia_id=None) -> dict:
    nombre = _texto(cuerpo.get("nombre"), "el nombre de la materia")
    codigo = _texto(cuerpo.get("codigo"), "el código", MAX_CODIGO)

    carrera = _referencia(d.carreras_institucion, cuerpo.get("carreraId"), "La carrera")
    plan = _referencia(d.planes_estudio, cuerpo.get("planId"), "El plan de estudio")
    if plan.get("carreraId") != carrera["id"]:
        raise HTTPException(400, "Ese plan no es de la carrera elegida")

    # El código identifica a la materia dentro de su plan: repetido, dos
    # materias distintas se confunden en los listados y en las actas.
    repetido = any(
        m["id"] != materia_id
        and m.get("planId") == plan["id"]
        and (m.get("codigo") or "").lower() == codigo.lower()
        for m in d.materias_plan
    )
    if repetido:
        raise HTTPException(409, "Ya hay una materia con ese código en este plan")

    anio = cuerpo.get("anio")
    if not isinstance(anio, int) or not 1 <= anio <= 7:
        raise HTTPException(400, "El año de cursado va de 1 a 7")

    cuatrimestre = cuerpo.get("cuatrimestre")
    if cuatrimestre not in (1, 2, 3):
        raise HTTPException(400, "El cuatrimestre es 1, 2 o 3 (anual)")

    horas = cuerpo.get("cargaHoraria")
    if horas is not None and (not isinstance(horas, int) or not 1 <= horas <= 1000):
        raise HTTPException(400, "La carga horaria no es válida")

    modalidad = cuerpo.get("modalidad") or d.MODALIDADES_MATERIA[0]
    if modalidad not in d.MODALIDADES_MATERIA:
        raise HTTPException(400, "Esa modalidad no existe")

    # Vacío es **sin límite**, la misma regla que el cupo de una mesa: poner
    # un número por defecto sería inventar un tope que nadie configuró.
    cupo = cuerpo.get("cupo")
    if cupo is not None and (not isinstance(cupo, int) or not 1 <= cupo <= 1000):
        raise HTTPException(400, "El cupo va de 1 a 1000")

    return {
        "nombre": nombre,
        "codigo": codigo,
        "descripcion": _texto(cuerpo.get("descripcion"), "la descripción", 600, False),
        "carreraId": carrera["id"],
        "planId": plan["id"],
        "anio": anio,
        "cuatrimestre": cuatrimestre,
        "cargaHoraria": horas,
        "modalidad": modalidad,
        "cupo": cupo,
        "activa": bool(cuerpo.get("activa", True)),
        "correlativas": {
            "cursar": _grupo_de_correlativas(cuerpo, "cursar", materia_id, plan["id"]),
            "rendir": _grupo_de_correlativas(cuerpo, "rendir", materia_id, plan["id"]),
        },
    }


def _actividad_de_materia(materia: dict) -> dict:
    """Qué tiene colgando una materia. Decide si se puede borrar o solo dar
    de baja: la información académica no se tira."""
    curso_id = materia.get("cursoId")
    return {
        "inscriptos": sum(
            1 for i in d.inscripciones_materias if i["materiaId"] == materia["id"]
        ),
        "historial": sum(
            1 for h in d.historial_academico if h["materiaId"] == materia["id"]
        ),
        "mesas": sum(1 for m in d.mesas_examen if m["materiaId"] == materia["id"]),
        "dictados": len(d.dictados_de_materia(materia["id"])),
        "esCorrelativaDe": [
            m["nombre"]
            for m in d.materias_plan
            if m["id"] != materia["id"]
            and any(
                r.get("materiaId") == materia["id"]
                for clave in ("cursar", "rendir")
                for r in ac.requisitos_de(m, clave)["requisitos"]
            )
        ],
        "tieneModulo": bool(d.buscar_curso(curso_id)),
    }


def _materia_completa(materia: dict) -> dict:
    """La ficha para el panel: la materia con todo lo que cuelga de ella."""
    carrera = d.buscar_en(d.carreras_institucion, materia.get("carreraId"))
    plan = d.buscar_en(d.planes_estudio, materia.get("planId"))
    comisiones = []
    for dictado in d.dictados_de_materia(materia["id"]):
        comision = d.buscar_en(d.comisiones, dictado["comisionId"])
        if not comision:
            continue
        comisiones.append(
            {
                "id": comision["id"],
                "nombre": comision["nombre"],
                "turno": comision.get("turno"),
                "docentes": [
                    p["nombre"]
                    for p in (d.buscar_persona(i) for i in dictado.get("docentes") or [])
                    if p
                ],
            }
        )

    return {
        **ac.materia_publica(materia),
        "carrera": carrera["nombre"] if carrera else None,
        "plan": plan["nombre"] if plan else None,
        "comisiones": comisiones,
        "actividad": _actividad_de_materia(materia),
    }


# ===================== La configuración académica =====================
# Dos valores que la facultad decide y que hasta ahora solo se podían cambiar
# tocando `datos_iniciales.json`: cuándo se puede uno inscribir a materias y
# cuánta asistencia se exige. Son decisiones de cada cuatrimestre, no
# constantes del programa.
MINIMO_ASISTENCIA_MIN = 0
MINIMO_ASISTENCIA_MAX = 100


def _config_academica(yo: dict) -> dict:
    """La configuración, siempre con la misma forma.

    `puedeEditar` va acá y no solo en la lectura: la pantalla reemplaza su
    estado con lo que devuelve cada guardado, y un campo que falta se lee
    como «no puede». Sin esto, después de guardar el período se
    deshabilitaban solos los campos de asistencia.
    """
    return {
        "periodoInscripcion": ac.periodo_materias(),
        "asistencia": dict(d.CONFIG_ASISTENCIA),
        "puedeEditar": es_supervisor(yo),
    }


@router.get("/configuracion", summary="La configuración académica de la facultad")
def ver_configuracion(yo: dict = UsuarioActual):
    """La ve y la cambia quien supervisa: es el calendario de la secretaría.

    El docente y el estudiante no entran acá, pero sí ven el resultado: si
    la inscripción está abierta, qué mínimo de asistencia se exige y los
    eventos en el Calendario.
    """
    _exigir_supervisor(yo)
    return _config_academica(yo)


@router.put("/configuracion/periodo", summary="Abrir o cerrar la inscripción a materias")
def cambiar_periodo(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Las dos fechas del período de inscripción.

    **No se valida contra hoy.** Un período que ya pasó es un dato legítimo
    —la facultad registra lo que hizo— y uno que todavía no empezó es lo
    normal al planificar el cuatrimestre que viene. Lo único que no puede
    pasar es que termine antes de empezar.
    """
    _exigir_que_administre_lo_academico(yo)

    desde = _fecha_de(cuerpo.get("desde"), "la fecha de apertura")
    hasta = _fecha_de(cuerpo.get("hasta"), "la fecha de cierre")
    if hasta < desde:
        raise HTTPException(400, "La inscripción no puede cerrar antes de abrir")

    antes = dict(d.periodo_inscripcion_materias)
    d.periodo_inscripcion_materias["desde"] = d.iso(desde)
    d.periodo_inscripcion_materias["hasta"] = d.iso(hasta)

    _anotar(
        yo,
        "período de inscripción",
        f"del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}",
        antes=antes,
        despues=dict(d.periodo_inscripcion_materias),
    )
    return _config_academica(yo)


@router.put("/configuracion/asistencia", summary="El mínimo de asistencia exigido")
def cambiar_asistencia(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """El porcentaje que la facultad exige para regularizar.

    Cambiarlo **no recalcula nada hacia atrás**: la condición de cada alumno
    se calcula al mirarla, así que subir el mínimo a mitad de cuatrimestre
    deja a gente por debajo de un día para el otro. Es una decisión de la
    facultad y el campus la obedece, pero conviene saberlo.
    """
    _exigir_que_administre_lo_academico(yo)

    minimo = cuerpo.get("minimoPorDefecto")
    if not isinstance(minimo, int) or not MINIMO_ASISTENCIA_MIN <= minimo <= MINIMO_ASISTENCIA_MAX:
        raise HTTPException(400, "El mínimo de asistencia va de 0 a 100")

    descuenta = cuerpo.get("justificadaDescuenta")
    if not isinstance(descuenta, bool):
        raise HTTPException(400, "Hay que decir si la falta justificada descuenta")

    antes = dict(d.CONFIG_ASISTENCIA)
    d.CONFIG_ASISTENCIA["minimoPorDefecto"] = minimo
    d.CONFIG_ASISTENCIA["justificadaDescuenta"] = descuenta

    _anotar(
        yo,
        "configuración de asistencia",
        f"mínimo {minimo} %"
        + (", la justificada descuenta" if descuenta else ", la justificada no descuenta"),
        antes=antes,
        despues=dict(d.CONFIG_ASISTENCIA),
    )
    return _config_academica(yo)


# ===================== Los eventos de la facultad =====================
# Lo que pasa en el campus y no es una clase, una entrega ni un examen: una
# jornada, un acto, una suspensión de actividades. Estaban en el calendario
# pero no había forma de cargarlos, así que la colección iba a quedar vacía
# para siempre y uno de los cuatro tipos del calendario no se podía usar.
TIPOS_EVENTO = ("evento", "examen")
MAX_LUGAR = 120


def _hora_de(valor, que: str) -> str | None:
    """Una hora "HH:MM", o nada. Las dos son válidas: un acto puede durar
    todo el día y no tener horario."""
    texto = str(valor or "").strip()
    if not texto:
        return None
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", texto):
        raise HTTPException(400, f"{que.capitalize()} tiene que ser una hora como 09:00")
    return texto


def _leer_evento(cuerpo: dict) -> dict:
    tipo = str(cuerpo.get("tipo") or "evento").strip()
    if tipo not in TIPOS_EVENTO:
        raise HTTPException(400, "Ese tipo de evento no existe")

    fecha = _fecha_de(cuerpo.get("fecha"), "la fecha del evento")
    desde = _hora_de(cuerpo.get("desde"), "la hora de inicio")
    hasta = _hora_de(cuerpo.get("hasta"), "la hora de fin")
    if desde and hasta and hasta < desde:
        raise HTTPException(400, "El evento no puede terminar antes de empezar")

    # Un evento puede ser de un módulo —un parcial— o de toda la facultad.
    curso_id = cuerpo.get("cursoId")
    if curso_id is not None:
        curso = d.buscar_curso(curso_id)
        if not curso:
            raise HTTPException(400, "Ese módulo no existe")
        curso_id = curso["id"]

    return {
        "tipo": tipo,
        "titulo": _texto(cuerpo.get("titulo"), "el título del evento", MAX_NOMBRE),
        "fecha": d.iso(fecha),
        "desde": desde,
        "hasta": hasta,
        "lugar": _texto(cuerpo.get("lugar"), "el lugar", MAX_LUGAR, obligatorio=False),
        "cursoId": curso_id,
    }


def _evento_publico(evento: dict) -> dict:
    curso = d.buscar_curso(evento.get("cursoId")) if evento.get("cursoId") else None
    return {**evento, "curso": curso["nombre"] if curso else None}


@router.get("/eventos", summary="Los eventos del calendario académico")
def listar_eventos(yo: dict = UsuarioActual):
    """Los ve quien supervisa. El resto del campus los ve en el Calendario,
    que es donde sirven."""
    _exigir_supervisor(yo)
    eventos = sorted(d.eventos, key=lambda e: e["fecha"], reverse=True)
    return {
        "eventos": [_evento_publico(e) for e in eventos],
        "tipos": list(TIPOS_EVENTO),
        "puedeEditar": es_supervisor(yo),
    }


@router.post("/eventos", status_code=201, summary="Agregar un evento")
def crear_evento(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_que_administre_lo_academico(yo)
    evento = {"id": d.nuevo_id_evento(), **_leer_evento(cuerpo)}
    d.eventos.append(evento)

    _anotar(
        yo,
        "evento agregado",
        f"{evento['titulo']} · {evento['fecha'][:10]}",
        elemento_id=evento["id"],
        despues={k: evento[k] for k in ("titulo", "fecha", "tipo")},
    )
    return _evento_publico(evento)


@router.put("/eventos/{id_evento}", summary="Modificar un evento")
def editar_evento(id_evento: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_que_administre_lo_academico(yo)
    evento = d.buscar_en(d.eventos, id_evento)
    if not evento:
        raise HTTPException(404, "Ese evento no existe")

    antes = {k: evento.get(k) for k in ("titulo", "fecha", "tipo", "lugar")}
    evento.update(_leer_evento({**evento, **cuerpo}))

    _anotar(
        yo,
        "evento modificado",
        f"{evento['titulo']} · {evento['fecha'][:10]}",
        elemento_id=evento["id"],
        antes=antes,
        despues={k: evento.get(k) for k in ("titulo", "fecha", "tipo", "lugar")},
    )
    return _evento_publico(evento)


@router.delete("/eventos/{id_evento}", summary="Quitar un evento")
def borrar_evento(id_evento: int, yo: dict = UsuarioActual):
    """Se borra de verdad: un evento no deja historial del que colgarse, al
    revés que una materia o una comisión."""
    _exigir_que_administre_lo_academico(yo)
    evento = d.buscar_en(d.eventos, id_evento)
    if not evento:
        raise HTTPException(404, "Ese evento no existe")

    d.eventos.remove(evento)
    _anotar(
        yo,
        "evento quitado",
        f"{evento['titulo']} · {evento['fecha'][:10]}",
        elemento_id=id_evento,
        antes={k: evento.get(k) for k in ("titulo", "fecha", "tipo")},
    )
    return {"eliminado": id_evento}


@router.get("/materias", summary="Todas las materias del plan de estudios")
def listar_materias(
    yo: dict = UsuarioActual,
    q: str | None = None,
    carreraId: int | None = None,
    planId: int | None = None,
    anio: int | None = None,
    estado: str | None = None,
    orden: str | None = None,
):
    """El listado del panel.

    Lo lee cualquiera que haya iniciado sesión: un estudiante necesita ver el
    plan y sus correlatividades para saber qué puede cursar. Crear y editar,
    en cambio, es solo del administrador.
    """
    buscado = _sin_tildes(q)
    salida = []
    for m in d.materias_plan:
        if carreraId and m.get("carreraId") != carreraId:
            continue
        if planId and m.get("planId") != planId:
            continue
        if anio and m.get("anio") != anio:
            continue
        if estado == "activas" and not m.get("activa", True):
            continue
        if estado == "inactivas" and m.get("activa", True):
            continue
        if buscado and buscado not in _sin_tildes(
            f"{m['nombre']} {m.get('codigo') or ''}"
        ):
            continue
        salida.append(_materia_completa(m))

    claves = {
        "nombre": lambda m: m["nombre"].lower(),
        "codigo": lambda m: (m["codigo"] or "").lower(),
        "carrera": lambda m: ((m["carrera"] or ""), m["anio"], m["nombre"].lower()),
    }
    salida.sort(key=claves.get(orden, lambda m: (m["anio"], m["cuatrimestre"], m["nombre"].lower())))

    return {
        "materias": salida,
        "modalidades": d.MODALIDADES_MATERIA,
        "condiciones": d.CONDICIONES_CORRELATIVA,
        "modos": d.MODOS_CORRELATIVA,
        "puedeAdministrar": es_administrador(yo),
    }


@router.post("/materias", status_code=201, summary="Crear una materia")
def crear_materia(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    datos = _leer_materia(cuerpo)

    materia = {"id": d.nuevo_id_materia(), **datos, "cursoId": None}
    d.materias_plan.append(materia)

    _anotar(
        yo,
        "materia creada",
        f"{materia['codigo']} · {materia['nombre']}",
        elemento_id=materia["id"],
        despues={"nombre": materia["nombre"], "anio": materia["anio"]},
        carrera_id=materia["carreraId"],
        materia_id=materia["id"],
    )
    return _materia_completa(materia)


@router.patch("/materias/{id_materia}", summary="Editar una materia")
def editar_materia(id_materia: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    _exigir_administrador(yo)
    materia = d.buscar_materia(id_materia)
    if not materia:
        raise HTTPException(404, "Esa materia no existe")

    antes = {
        "nombre": materia["nombre"],
        "codigo": materia.get("codigo"),
        "anio": materia.get("anio"),
        "activa": materia.get("activa", True),
        "correlativas": materia.get("correlativas"),
    }
    datos = _leer_materia({**materia, **cuerpo}, materia_id=id_materia)
    materia.update(datos)

    _anotar(
        yo,
        "materia editada",
        f"{materia['codigo']} · {materia['nombre']}",
        elemento_id=materia["id"],
        antes=antes,
        despues={
            "nombre": materia["nombre"],
            "codigo": materia.get("codigo"),
            "anio": materia.get("anio"),
            "activa": materia.get("activa", True),
            "correlativas": materia.get("correlativas"),
        },
        carrera_id=materia.get("carreraId"),
        materia_id=materia["id"],
    )
    return _materia_completa(materia)


@router.delete("/materias/{id_materia}", summary="Dar de baja o eliminar una materia")
def borrar_materia(id_materia: int, yo: dict = UsuarioActual):
    """Si la materia tiene actividad académica **no se elimina**: se da de baja.

    Borrarla dejaría historiales apuntando a una materia que no existe, actas
    sin materia y correlatividades rotas. Una materia dada de baja deja de
    ofrecerse pero conserva todo lo que pasó.
    """
    _exigir_administrador(yo)
    materia = d.buscar_materia(id_materia)
    if not materia:
        raise HTTPException(404, "Esa materia no existe")

    actividad = _actividad_de_materia(materia)
    tiene_historia = any(
        actividad[k] for k in ("inscriptos", "historial", "mesas", "dictados")
    ) or actividad["esCorrelativaDe"] or actividad["tieneModulo"]

    if tiene_historia:
        materia["activa"] = False
        _anotar(
            yo,
            "materia dada de baja",
            f"{materia['codigo']} · {materia['nombre']}",
            elemento_id=materia["id"],
            antes={"activa": True},
            despues={"activa": False},
            materia_id=materia["id"],
        )
        return {"materia": _materia_completa(materia), "eliminada": False}

    d.materias_plan.remove(materia)
    _anotar(
        yo,
        "materia eliminada",
        f"{materia['codigo']} · {materia['nombre']}",
        elemento_id=materia["id"],
        antes={"nombre": materia["nombre"]},
    )
    return {"eliminada": True, "id": id_materia}
