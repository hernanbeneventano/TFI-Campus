"""Finales: la gestión de las mesas de examen del lado docente.

Es la otra mitad del apartado Finales. La del alumno —ver las mesas,
inscribirse, mirar sus resultados— está en `rutas/finales.py`; acá está lo
que hace la cátedra con esas mismas mesas. Las dos trabajan sobre los mismos
datos (`mesas_examen`, `inscripciones_finales`, `historial_academico`) y
sobre las mismas reglas académicas (`servicios/academico.py`), así que una
mesa que el docente crea acá es la que el alumno ve allá.

Va en un módulo aparte y con su propio prefijo (`/api/finales/gestion`)
porque son dos permisos distintos sobre el mismo recurso: la mitad del alumno
responde "¿puedo rendir?" y esta responde "¿qué hago con la mesa?". Mezclarlas
en una sola ruta obligaría a preguntar el rol en cada función.

Tres cosas, que son las tres pantallas del docente:

- **Inscriptos**: quiénes se anotaron en cada mesa, con sus datos académicos.
- **Fechas**: crear, modificar, reprogramar y cancelar mesas.
- **Resultados**: cargar las notas y cerrar el acta.

Permisos (todo se verifica acá; el frontend solo esconde lo que no va):

- Los estudiantes no entran a nada de esto (403).
- Un docente ve las mesas de las materias que tiene a cargo y las de los
  tribunales que integra.
- Crear, modificar y cancelar: el docente a cargo de la materia.
- Cargar notas y cerrar el acta: el docente a cargo o alguien del tribunal.
- Quien supervisa ve todo, pero no califica: el acta la firma el tribunal.
  Hoy no existe ese rol (en `personas` solo hay Estudiante y Docente); el día
  que se agregue, se cambia `_es_supervisor` y nada más.

Al cerrar el acta los resultados pasan a `resultados_finales` y la condición
de la materia queda en `historial_academico`, que es de donde leen las
correlatividades de la inscripción a materias: aprobar el final de
Programación I es lo que habilita a cursar Programación II.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .. import datos as d
from ..servicios import academico as ac
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/finales/gestion", tags=["Finales (gestión)"])

RESULTADOS = d.CONDICIONES_FINAL

# Desde qué nota se aprueba un final. Un solo lugar, por si la facultad la cambia.
NOTA_APROBACION = 6
NOTA_MAXIMA = 10

# Más de cinco en un tribunal no tiene sentido y frena errores de carga
MAX_TRIBUNAL = 5

_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


# ===================== Permisos =====================
def _es_supervisor(persona: dict) -> bool:
    """Todavía no hay rol de administrador. Cuando exista, va acá."""
    return persona.get("rol") in ("Administrador", "Supervisor")


def _exigir_gestion(yo: dict) -> None:
    if yo.get("rol") != "Docente" and not _es_supervisor(yo):
        raise HTTPException(403, "La gestión de finales es para docentes")


def _es_titular(yo: dict, mesa: dict) -> bool:
    materia = d.buscar_materia(mesa["materiaId"])
    return bool(materia and materia.get("docenteId") == yo["id"])


def _puede_ver(yo: dict, mesa: dict) -> bool:
    return _es_supervisor(yo) or _es_titular(yo, mesa) or yo["id"] in mesa["tribunal"]


def _puede_administrar(yo: dict, mesa: dict) -> bool:
    return _es_supervisor(yo) or _es_titular(yo, mesa)


def _puede_calificar(yo: dict, mesa: dict) -> bool:
    return _es_titular(yo, mesa) or yo["id"] in mesa["tribunal"]


def _materias_que_administra(yo: dict) -> list[dict]:
    """Las materias del plan que el docente tiene a cargo.

    Las mesas son de una materia del plan, no de un módulo: la cursada de este
    cuatrimestre es un módulo, pero el final lo rinde quien quedó regular en
    cualquier cursada anterior.
    """
    if _es_supervisor(yo):
        return list(d.materias_plan)
    return [m for m in d.materias_plan if m.get("docenteId") == yo["id"]]


# ===================== Fechas =====================
def _local(fecha: str, hora: str = "00:00") -> datetime:
    """'2026-12-03' y '16:00' → ese momento en la hora local del servidor."""
    return datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M").astimezone()


def _texto_fecha(iso: str) -> str:
    momento = d.desde_iso(iso).astimezone()
    return f"{_DIAS[momento.weekday()]} {momento.day} de {_MESES[momento.month - 1]}"


def _ya_se_tomo(mesa: dict) -> bool:
    return d.desde_iso(mesa["fecha"]) <= d.ahora()


def _periodo(mesa: dict) -> str:
    ahora = d.ahora()
    if ahora < d.desde_iso(mesa["inscripcionDesde"]):
        return "por-abrir"
    if ahora <= d.desde_iso(mesa["inscripcionHasta"]):
        return "abierta"
    return "cerrada"


# ===================== Lectura =====================
def _buscar_mesa(id_mesa: int, yo: dict) -> dict:
    mesa = d.buscar_mesa(id_mesa)
    # Si no la puede ver, para él no existe: un 403 confirmaría que está
    if not mesa or not _puede_ver(yo, mesa):
        raise HTTPException(404, "Mesa no encontrada")
    return mesa


def _inscripciones_de(mesa: dict) -> list[dict]:
    return [i for i in d.inscripciones_finales if i["mesaId"] == mesa["id"]]


def _activas(mesa: dict) -> list[dict]:
    return [i for i in _inscripciones_de(mesa) if i["estado"] == ac.MESA_INSCRIPTO]


def _materia_de(mesa: dict) -> dict:
    """La materia de la mesa con el color del módulo, si tiene uno abierto.

    El color sale del módulo (`cursos`) y no de la materia del plan, para que
    una mesa de Programación II se vea del mismo color que su módulo en toda
    la aplicación. Una materia sin cursada abierta no tiene color propio: usa
    el oscuro del resto de la interfaz.
    """
    materia = d.buscar_materia(mesa["materiaId"]) or {}
    curso = d.buscar_curso(materia.get("cursoId")) if materia.get("cursoId") else None
    docente = d.buscar_persona(materia.get("docenteId")) if materia.get("docenteId") else None
    return {
        "id": materia.get("id"),
        "codigo": materia.get("codigo"),
        "nombre": materia.get("nombre"),
        "color": (curso or {}).get("color"),
        "cursoId": materia.get("cursoId"),
        "docenteId": materia.get("docenteId"),
        "docente": (docente or {}).get("nombre"),
    }


def _resumir_mesa(mesa: dict, yo: dict) -> dict:
    activas = _activas(mesa)
    cupo = mesa.get("cupo")
    tomada = _ya_se_tomo(mesa)
    cancelada = mesa["estado"] == "cancelada"
    return {
        **mesa,
        "materia": _materia_de(mesa),
        "tribunal": [
            {"id": p["id"], "nombre": p["nombre"]}
            for p in (d.buscar_persona(i) for i in mesa["tribunal"])
            if p
        ],
        "inscriptos": len(activas),
        "cancelados": sum(1 for i in _inscripciones_de(mesa) if i["estado"] == ac.MESA_CANCELADO),
        "conResultado": sum(1 for i in activas if i.get("resultado")),
        "lugaresLibres": None if cupo is None else max(cupo - len(activas), 0),
        "periodo": _periodo(mesa),
        "tomada": tomada,
        # Lo que el frontend puede ofrecer. La que manda es la verificación de
        # cada ruta.
        "puedeEditar": _puede_administrar(yo, mesa)
        and not cancelada
        and not tomada
        and not mesa["actaCerrada"],
        "puedeCalificar": _puede_calificar(yo, mesa)
        and not cancelada
        and tomada
        and not mesa["actaCerrada"],
    }


def _ficha_alumno(persona_id: int, materia_id: int, mesa_id: int) -> dict:
    """Lo que el docente necesita saber de quien se presenta a rendir.

    Sale de donde ya vive: `inscripcion_carrera` tiene el legajo y la carrera,
    y `resultados_finales` los finales que rindió. Nada de esto se guarda de
    nuevo en la inscripción a la mesa.
    """
    persona = d.buscar_persona(persona_id) or {
        "id": persona_id,
        "nombre": "Sin datos",
        "accesoHaceMin": 99999,
    }
    carrera = d.carrera_de(persona_id) or {}
    suyos = [r for r in d.resultados_finales if r["personaId"] == persona_id]
    aprobados = [r for r in suyos if r["condicion"] == "Aprobado"]
    notas = [r["nota"] for r in aprobados if r.get("nota") is not None]
    return {
        **d.con_presencia(persona),
        "legajo": carrera.get("legajo"),
        "carrera": carrera.get("carrera"),
        "ingreso": carrera.get("ingreso"),
        "aprobadas": len(aprobados),
        "promedio": round(sum(notas) / len(notas), 2) if notas else None,
        # Las veces que ya se presentó a esta misma materia
        "intentos": [
            {"fecha": r["fecha"], "nota": r.get("nota"), "resultado": r["condicion"]}
            for r in sorted(suyos, key=lambda r: d.desde_iso(r["fecha"]))
            if r["materiaId"] == materia_id and r.get("mesaId") != mesa_id
        ],
    }


def _con_alumno(inscripcion: dict, mesa: dict) -> dict:
    """La fila de la planilla: la inscripción, el alumno y su condición.

    La condición (Regular, Libre, Aprobada) no se guarda en la inscripción:
    se lee del historial académico, que es el mismo lugar del que la lee la
    pantalla del alumno. Guardarla acá sería una copia que puede quedar vieja.
    """
    persona_id = inscripcion["personaId"]
    return {
        **inscripcion,
        "condicion": d.condicion_en(persona_id, mesa["materiaId"]) or "Libre",
        "alumno": _ficha_alumno(persona_id, mesa["materiaId"], mesa["id"]),
    }


def _registrar(mesa: dict, yo: dict, accion: str, detalle: str = "") -> None:
    mesa.setdefault("historial", []).append(
        {"fecha": d.iso(d.ahora()), "accion": accion, "detalle": detalle, "por": yo["nombre"]}
    )


# ===================== Rutas: consulta =====================
@router.get("/opciones", summary="Con qué puede trabajar quien pregunta")
def opciones(yo: dict = UsuarioActual):
    _exigir_gestion(yo)
    return {
        "materias": [
            {
                "id": m["id"],
                "codigo": m["codigo"],
                "nombre": m["nombre"],
                "color": (d.buscar_curso(m["cursoId"]) or {}).get("color") if m.get("cursoId") else None,
                # Integra siempre el tribunal: el formulario lo muestra fijo
                "docenteId": m.get("docenteId"),
            }
            for m in _materias_que_administra(yo)
        ],
        "docentes": [
            {"id": p["id"], "nombre": p["nombre"]} for p in d.personas if p["rol"] == "Docente"
        ],
        "modalidades": d.MODALIDADES_FINAL,
        "instancias": d.INSTANCIAS_FINAL,
        "resultados": RESULTADOS,
        "notaAprobacion": NOTA_APROBACION,
        "notaMaxima": NOTA_MAXIMA,
        "esSupervisor": _es_supervisor(yo),
        "puedeCrear": bool(_materias_que_administra(yo)),
    }


@router.get("/mesas", summary="Las mesas que el docente puede ver")
def listar_mesas(yo: dict = UsuarioActual, materiaId: int | None = Query(default=None)):
    """Las próximas primero, de la más cercana a la más lejana; después las ya
    tomadas, de la más reciente hacia atrás."""
    _exigir_gestion(yo)
    visibles = [
        m
        for m in d.mesas_examen
        if _puede_ver(yo, m) and (materiaId is None or m["materiaId"] == materiaId)
    ]
    ahora = d.ahora()
    proximas = sorted(
        (m for m in visibles if d.desde_iso(m["fecha"]) > ahora),
        key=lambda m: d.desde_iso(m["fecha"]),
    )
    tomadas = sorted(
        (m for m in visibles if d.desde_iso(m["fecha"]) <= ahora),
        key=lambda m: d.desde_iso(m["fecha"]),
        reverse=True,
    )
    return [_resumir_mesa(m, yo) for m in proximas + tomadas]


@router.get("/inscriptos", summary="Inscriptos por mesa, con sus datos académicos")
def listar_inscriptos(
    yo: dict = UsuarioActual,
    materiaId: int | None = Query(default=None),
    mesaId: int | None = Query(default=None),
    comision: str | None = Query(default=None),
):
    _exigir_gestion(yo)
    mesas = [m for m in listar_mesas(yo, materiaId) if (mesaId is None or m["id"] == mesaId)]

    grupos = []
    comisiones: set[str] = set()
    total = 0
    for mesa in mesas:
        filas = []
        for inscripcion in _inscripciones_de(mesa):
            comisiones.add(inscripcion["comision"])
            if comision and inscripcion["comision"] != comision:
                continue
            filas.append(_con_alumno(inscripcion, mesa))
        filas.sort(key=lambda f: (f["estado"] != ac.MESA_INSCRIPTO, f["alumno"]["nombre"]))
        total += sum(1 for f in filas if f["estado"] == ac.MESA_INSCRIPTO)
        grupos.append({"mesa": mesa, "inscriptos": filas})

    return {"grupos": grupos, "total": total, "comisiones": sorted(comisiones)}


@router.get("/mesas/{id_mesa}", summary="Una mesa, con sus inscriptos")
def obtener_mesa(id_mesa: int, yo: dict = UsuarioActual):
    _exigir_gestion(yo)
    mesa = _buscar_mesa(id_mesa, yo)
    filas = sorted(
        (_con_alumno(i, mesa) for i in _inscripciones_de(mesa)),
        key=lambda f: (f["estado"] != ac.MESA_INSCRIPTO, f["alumno"]["nombre"]),
    )
    return {"mesa": _resumir_mesa(mesa, yo), "inscriptos": filas}


# ===================== Rutas: fechas =====================
def _validar_datos_mesa(cuerpo: dict, yo: dict, mesa_actual: dict | None) -> dict:
    """Revisa todo lo que llega del formulario y devuelve la mesa armada.

    Sirve para crear y para modificar: en una modificación la materia no se
    cambia (es otra mesa) y no se cuenta a sí misma como duplicada.
    """
    if mesa_actual is None:
        try:
            materia_id = int(cuerpo.get("materiaId"))
        except (TypeError, ValueError):
            raise HTTPException(400, "Elegí la materia")
        materia = d.buscar_materia(materia_id)
        if not materia or materia not in _materias_que_administra(yo):
            raise HTTPException(403, "Solo podés crear mesas de las materias que tenés a cargo")
    else:
        materia = d.buscar_materia(mesa_actual["materiaId"])
        materia_id = materia["id"]

    llamado = str(cuerpo.get("llamado") or "").strip()
    fecha = str(cuerpo.get("fecha") or "").strip()
    desde = str(cuerpo.get("desde") or "").strip()
    hasta = str(cuerpo.get("hasta") or "").strip()
    modalidad = str(cuerpo.get("modalidad") or "").strip()
    instancia = str(cuerpo.get("instancia") or "").strip()
    lugar = str(cuerpo.get("lugar") or "").strip()
    abre = str(cuerpo.get("inscripcionDesde") or "").strip()
    cierra = str(cuerpo.get("inscripcionHasta") or "").strip()

    if not llamado:
        raise HTTPException(400, "Poné el nombre del llamado, por ejemplo «Turno diciembre · 1.er llamado»")
    if len(llamado) > 80:
        raise HTTPException(400, "El nombre del llamado es demasiado largo")
    if not (_FECHA.match(fecha) and _FECHA.match(abre) and _FECHA.match(cierra)):
        raise HTTPException(400, "Revisá las fechas: alguna está vacía o no es válida")
    if not (_HORA.match(desde) and _HORA.match(hasta)):
        raise HTTPException(400, "Revisá el horario: tiene que ser HH:MM")
    if desde >= hasta:
        raise HTTPException(400, "La hora de fin tiene que ser posterior a la de inicio")
    if modalidad not in d.MODALIDADES_FINAL:
        raise HTTPException(400, "Elegí una modalidad")
    if instancia not in d.INSTANCIAS_FINAL:
        raise HTTPException(400, "Elegí si el examen es escrito, oral o las dos cosas")
    if not lugar:
        raise HTTPException(
            400,
            "Poné el enlace de la sala virtual" if modalidad == "Virtual" else "Poné el aula o el lugar",
        )
    if len(lugar) > 120:
        raise HTTPException(400, "El lugar es demasiado largo")

    try:
        inicio = _local(fecha, desde)
        apertura = _local(abre)
        # El cierre incluye todo ese día
        cierre = _local(cierra) + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        raise HTTPException(400, "Revisá las fechas: alguna no existe")

    if inicio <= d.ahora():
        raise HTTPException(400, "La mesa tiene que ser en el futuro")
    if apertura > cierre:
        raise HTTPException(400, "La inscripción no puede cerrar antes de abrir")
    if cierre.date() >= inicio.date():
        raise HTTPException(400, "La inscripción tiene que cerrar antes del día del examen")

    # Cupo vacío = sin límite
    cupo_bruto = cuerpo.get("cupo")
    cupo = None
    if cupo_bruto not in (None, ""):
        try:
            cupo = int(cupo_bruto)
        except (TypeError, ValueError):
            raise HTTPException(400, "El cupo tiene que ser un número")
        if cupo < 1 or cupo > 500:
            raise HTTPException(400, "El cupo tiene que estar entre 1 y 500")
        if mesa_actual and cupo < len(_activas(mesa_actual)):
            raise HTTPException(
                400,
                f"Ya hay {len(_activas(mesa_actual))} inscriptos: el cupo no puede ser menor",
            )

    # El docente a cargo integra siempre el tribunal
    tribunal = [materia["docenteId"]] if materia.get("docenteId") else []
    for bruto in cuerpo.get("tribunal") or []:
        try:
            persona = d.buscar_persona(int(bruto))
        except (TypeError, ValueError):
            persona = None
        if not persona or persona["rol"] != "Docente":
            raise HTTPException(400, "En el tribunal solo puede haber docentes")
        if persona["id"] not in tribunal:
            tribunal.append(persona["id"])
    if len(tribunal) > MAX_TRIBUNAL:
        raise HTTPException(400, f"El tribunal no puede tener más de {MAX_TRIBUNAL} integrantes")

    repetida = next(
        (
            m
            for m in d.mesas_examen
            if m["materiaId"] == materia_id
            and m["estado"] == "programada"
            and (mesa_actual is None or m["id"] != mesa_actual["id"])
            and d.desde_iso(m["fecha"]).astimezone().date() == inicio.date()
        ),
        None,
    )
    if repetida:
        raise HTTPException(409, "Esa materia ya tiene una mesa ese día")

    return {
        "materiaId": materia_id,
        "llamado": llamado,
        "fecha": d.iso(inicio),
        "desde": desde,
        "hasta": hasta,
        "modalidad": modalidad,
        "instancia": instancia,
        "lugar": lugar,
        "tribunal": tribunal,
        "inscripcionDesde": d.iso(apertura),
        "inscripcionHasta": d.iso(cierre),
        "cupo": cupo,
    }


@router.post("/mesas", status_code=201, summary="Crear una mesa de examen")
def crear_mesa(cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual):
    _exigir_gestion(yo)
    datos = _validar_datos_mesa(cuerpo, yo, None)
    mesa = {
        "id": d.nuevo_id_mesa(),
        **datos,
        "estado": "programada",
        "motivoCancelacion": None,
        "actaCerrada": False,
        "historial": [],
    }
    _registrar(mesa, yo, "Creó la mesa")
    d.mesas_examen.append(mesa)
    return _resumir_mesa(mesa, yo)


def _como_se_toma(mesa: dict) -> str:
    return f"{_texto_fecha(mesa['fecha'])}, de {mesa['desde']} a {mesa['hasta']} h, {mesa['lugar']} ({mesa['modalidad'].lower()})"


@router.put("/mesas/{id_mesa}", summary="Modificar o reprogramar una mesa")
def editar_mesa(id_mesa: int, cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual):
    """Si cambia cuándo, dónde o cómo se toma y ya hay inscriptos, se les avisa
    por mensaje a cada uno: es una reprogramación."""
    _exigir_gestion(yo)
    mesa = _buscar_mesa(id_mesa, yo)
    if not _puede_administrar(yo, mesa):
        raise HTTPException(403, "Solo el docente a cargo de la materia puede modificar la mesa")
    if mesa["estado"] == "cancelada":
        raise HTTPException(409, "La mesa está cancelada")
    if mesa["actaCerrada"]:
        raise HTTPException(409, "El acta ya está cerrada")
    if _ya_se_tomo(mesa):
        raise HTTPException(409, "La mesa ya se tomó: no se puede modificar")

    datos = _validar_datos_mesa(cuerpo, yo, mesa)
    antes = _como_se_toma(mesa)
    clave = ("fecha", "desde", "hasta", "lugar", "modalidad")
    reprogramada = any(mesa[k] != datos[k] for k in clave)

    mesa.update(datos)

    if reprogramada:
        ahora_es = _como_se_toma(mesa)
        _registrar(mesa, yo, "Reprogramó la mesa", f"Antes: {antes}. Ahora: {ahora_es}.")
        materia = d.buscar_materia(mesa["materiaId"])
        for inscripcion in _activas(mesa):
            d.avisar_por_mensaje(
                yo["id"],
                inscripcion["personaId"],
                f"Se reprogramó la mesa de {materia['nombre']} ({mesa['llamado']}) en la que estás "
                f"inscripto. Antes: {antes}. Ahora: {ahora_es}. Tu inscripción sigue en pie.",
            )
    else:
        _registrar(mesa, yo, "Modificó la mesa")

    return _resumir_mesa(mesa, yo)


@router.post("/mesas/{id_mesa}/cancelar", summary="Cancelar una mesa y avisar a los inscriptos")
def cancelar_mesa(id_mesa: int, cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual):
    _exigir_gestion(yo)
    mesa = _buscar_mesa(id_mesa, yo)
    if not _puede_administrar(yo, mesa):
        raise HTTPException(403, "Solo el docente a cargo de la materia puede cancelar la mesa")
    if mesa["estado"] == "cancelada":
        raise HTTPException(409, "La mesa ya estaba cancelada")
    if _ya_se_tomo(mesa) or mesa["actaCerrada"]:
        raise HTTPException(409, "La mesa ya se tomó: no se puede cancelar")

    # Sin motivo, quien estaba inscripto no sabe qué hacer
    motivo = str(cuerpo.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(400, "Contá el motivo: les llega a los inscriptos")
    if len(motivo) > 500:
        raise HTTPException(400, "El motivo es demasiado largo")

    mesa["estado"] = "cancelada"
    mesa["motivoCancelacion"] = motivo
    _registrar(mesa, yo, "Canceló la mesa", motivo)

    materia = d.buscar_materia(mesa["materiaId"])
    for inscripcion in _activas(mesa):
        d.avisar_por_mensaje(
            yo["id"],
            inscripcion["personaId"],
            f"Se canceló la mesa de {materia['nombre']} del {_texto_fecha(mesa['fecha'])} "
            f"({mesa['llamado']}). Motivo: {motivo}",
        )

    return _resumir_mesa(mesa, yo)


# ===================== Rutas: resultados =====================
def _exigir_calificable(mesa: dict, yo: dict) -> None:
    if not _puede_calificar(yo, mesa):
        raise HTTPException(403, "Solo el tribunal de la mesa puede cargar las notas")
    if mesa["estado"] == "cancelada":
        raise HTTPException(409, "La mesa está cancelada")
    if mesa["actaCerrada"]:
        raise HTTPException(409, "El acta ya está cerrada: los resultados no se pueden cambiar")
    if not _ya_se_tomo(mesa):
        raise HTTPException(409, "Las notas se cargan después del examen")


def _validar_resultado(resultado: Any, nota: Any) -> tuple[str | None, int | None]:
    if resultado in (None, ""):
        return None, None
    if resultado not in RESULTADOS:
        raise HTTPException(400, "La condición tiene que ser Aprobado, Desaprobado o Ausente")
    if resultado == "Ausente":
        return resultado, None

    if nota in (None, ""):
        raise HTTPException(400, "Falta la nota de alguien que se presentó")
    try:
        exacta = float(nota)
    except (TypeError, ValueError):
        raise HTTPException(400, "La nota tiene que ser un número")
    valor = int(exacta)
    if exacta != valor or not 1 <= valor <= NOTA_MAXIMA:
        raise HTTPException(400, f"La nota tiene que ser un número entero entre 1 y {NOTA_MAXIMA}")
    if resultado == "Aprobado" and valor < NOTA_APROBACION:
        raise HTTPException(400, f"Para aprobar hace falta {NOTA_APROBACION} o más")
    if resultado == "Desaprobado" and valor >= NOTA_APROBACION:
        raise HTTPException(400, f"Con {valor} el examen está aprobado")
    return resultado, valor


@router.put("/mesas/{id_mesa}/resultados", summary="Guardar notas (el acta sigue abierta)")
def guardar_resultados(id_mesa: int, cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual):
    """Se puede guardar a medias y volver más tarde. Primero se valida todo y
    recién después se escribe: o se guarda la planilla entera o nada."""
    _exigir_gestion(yo)
    mesa = _buscar_mesa(id_mesa, yo)
    _exigir_calificable(mesa, yo)

    recibidos = cuerpo.get("resultados")
    if not isinstance(recibidos, list):
        raise HTTPException(400, "No llegaron resultados")

    activas = {i["id"]: i for i in _activas(mesa)}
    cambios = []
    for fila in recibidos:
        try:
            inscripcion = activas[int((fila or {}).get("inscripcionId"))]
        except (KeyError, TypeError, ValueError):
            raise HTTPException(400, "Alguien de la planilla no está inscripto en esta mesa")
        cambios.append((inscripcion, *_validar_resultado(fila.get("resultado"), fila.get("nota"))))

    for inscripcion, resultado, nota in cambios:
        inscripcion["resultado"] = resultado
        inscripcion["nota"] = nota

    _registrar(mesa, yo, "Cargó notas", f"{len(cambios)} en la planilla")
    return obtener_mesa(id_mesa, yo)


def _asentar_condicion(persona_id: int, materia_id: int, nota: int | None, fecha: str) -> None:
    """Deja la materia aprobada en el historial académico del alumno.

    Es el único efecto del acta que sale de Finales: `historial_academico` es
    de donde la inscripción a materias lee las correlatividades, así que
    aprobar el final acá habilita allá las materias que lo pedían.
    """
    registro = next(
        (
            h
            for h in d.historial_academico
            if h["personaId"] == persona_id and h["materiaId"] == materia_id
        ),
        None,
    )
    if registro is None:
        registro = {"personaId": persona_id, "materiaId": materia_id}
        d.historial_academico.append(registro)
    registro["condicion"] = ac.APROBADA
    registro["nota"] = nota
    registro["fecha"] = fecha


@router.post("/mesas/{id_mesa}/cerrar-acta", summary="Confirmar los resultados y cerrar el acta")
def cerrar_acta(id_mesa: int, yo: dict = UsuarioActual):
    """Después de esto los resultados no se tocan más: pasan al historial
    académico de cada alumno y se le avisa por mensaje."""
    _exigir_gestion(yo)
    mesa = _buscar_mesa(id_mesa, yo)
    _exigir_calificable(mesa, yo)

    activas = _activas(mesa)
    faltan = [i for i in activas if not i.get("resultado")]
    if faltan:
        raise HTTPException(
            400,
            f"Falta la condición de {len(faltan)} "
            f"{'inscripto' if len(faltan) == 1 else 'inscriptos'}: el acta se cierra completa",
        )

    materia = d.buscar_materia(mesa["materiaId"])
    for inscripcion in activas:
        d.resultados_finales.append(
            {
                "id": d.nuevo_id_resultado_final(),
                "personaId": inscripcion["personaId"],
                "materiaId": mesa["materiaId"],
                "mesaId": mesa["id"],
                "fecha": mesa["fecha"],
                "nota": inscripcion.get("nota"),
                "condicion": inscripcion["resultado"],
                "llamado": mesa.get("llamado"),
            }
        )
        # Solo el aprobado cambia la condición de la materia: desaprobar o
        # faltar deja al alumno regular, con el final todavía pendiente.
        if inscripcion["resultado"] == "Aprobado":
            _asentar_condicion(
                inscripcion["personaId"],
                mesa["materiaId"],
                inscripcion.get("nota"),
                mesa["fecha"],
            )

        nota = f" con {inscripcion['nota']}" if inscripcion.get("nota") is not None else ""
        d.avisar_por_mensaje(
            yo["id"],
            inscripcion["personaId"],
            f"Ya está el resultado del final de {materia['nombre']} del {_texto_fecha(mesa['fecha'])}: "
            f"{inscripcion['resultado']}{nota}. Lo vas a ver en tu historial académico.",
        )

    mesa["actaCerrada"] = True
    _registrar(mesa, yo, "Cerró el acta", f"{len(activas)} resultados confirmados")
    return obtener_mesa(id_mesa, yo)
