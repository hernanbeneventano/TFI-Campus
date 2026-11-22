"""El panel de control de la institución: los números y las alertas.

Todo lo que sale de acá se **calcula de los datos de verdad**. No hay un solo
número de ejemplo: si la facultad todavía no cargó nada, el panel muestra cero
y lo dice, que es información. Un tablero con números inventados es peor que
no tener tablero.

Dos cosas distintas, y por eso dos funciones:

- `indicadores` / `distribuciones` responden **cómo viene la institución**.
- `alertas` responde **qué hay que hacer hoy**, y cada una lleva a la pantalla
  donde se resuelve. Una alerta que no se puede atender es ruido.

Alcance
-------
El administrador ve toda la institución. El supervisor, lo académico. Hoy no
hay un ámbito delimitado para el supervisor en los datos —no existe "las
carreras de las que Claudia responde"—, así que ve todo lo académico; el día
que se delimite, se cambia en `_alcance` y nada más.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from .. import datos as d
from . import asistencias as asis
from . import auditoria

# Cuántas filas devuelve una distribución larga: una lista de cincuenta
# comisiones no es un gráfico, es una tabla disfrazada.
TOPE_BARRAS = 10


# ===================== Quién pregunta =====================
def es_administrador(persona: dict) -> bool:
    return d.tiene_rol(persona, "Administrador")


def es_supervisor(persona: dict) -> bool:
    return d.tiene_rol(persona, "Supervisor", "Administrador")


def _estudiantes() -> list[dict]:
    return [p for p in d.personas if d.tiene_rol(p, "Estudiante")]


def _docentes() -> list[dict]:
    return [p for p in d.personas if d.tiene_rol(p, "Docente")]


def _asociaciones_activas() -> list[dict]:
    return [a for a in d.asociaciones_academicas if a.get("estado", "activa") == "activa"]


# ===================== Los números de arriba =====================
def indicadores() -> dict:
    """Lo que hay hoy en la institución, contado de los registros."""
    activas = _asociaciones_activas()
    pendientes_biblioteca = [m for m in d.materiales if m["estado"] == "pendiente"]
    cuentas_pendientes = [p for p in d.personas if p.get("estado") == "pendiente"]

    return {
        # Un estudiante "activo" es el que está inscripto a una carrera, no el
        # que tiene el rol: alguien dado de alta sin carrera todavía no cursa.
        "estudiantes": len({a["personaId"] for a in activas}),
        "estudiantesSinCarrera": len(
            [p for p in _estudiantes() if not any(a["personaId"] == p["id"] for a in activas)]
        ),
        "docentes": len(_docentes()),
        "carreras": len([c for c in d.carreras_institucion if c.get("activa", True)]),
        "sedes": len([s for s in d.sedes if s.get("activa", True)]),
        "comisiones": len([c for c in d.comisiones if c.get("activa", True)]),
        "materias": len(d.materias_plan),
        "sinComision": len([a for a in activas if not a.get("comisionId")]),
        "aportesPendientes": len(pendientes_biblioteca),
        "cuentasPendientes": len(cuentas_pendientes),
        "proximosExamenes": len(_proximos_examenes()),
    }


def _proximos_examenes() -> list[dict]:
    """Mesas de final y exámenes de cursada que todavía no pasaron."""
    hoy = d.iso(d.ahora())[:10]
    salida = []

    for mesa in d.mesas_examen:
        if mesa.get("estado") == "cancelada" or str(mesa["fecha"])[:10] < hoy:
            continue
        materia = d.buscar_materia(mesa["materiaId"])
        salida.append(
            {
                "tipo": "final",
                "titulo": f"Final de {materia['nombre'] if materia else 'una materia'}",
                "detalle": mesa.get("llamado"),
                "fecha": mesa["fecha"],
                "ruta": f"/finales/fechas?mesa={mesa['id']}",
            }
        )

    for evento in d.eventos:
        if evento.get("tipo") != "examen" or str(evento["fecha"])[:10] < hoy:
            continue
        curso = d.buscar_curso(evento.get("cursoId"))
        salida.append(
            {
                "tipo": "examen",
                "titulo": evento["titulo"],
                "detalle": curso["nombre"] if curso else None,
                "fecha": evento["fecha"],
                "ruta": "/calendario",
            }
        )

    return sorted(salida, key=lambda e: str(e["fecha"]))


# ===================== Las distribuciones =====================
def _contar_por(clave: str, coleccion: list[dict]) -> list[dict]:
    """Cuántos estudiantes hay en cada carrera, sede o comisión.

    Se listan **todas**, incluidas las que están en cero: una comisión vacía
    es justamente lo que hay que ver, y si se la saca desaparece el problema
    de la pantalla en vez de resolverse.
    """
    activas = _asociaciones_activas()
    cuenta: dict[Any, int] = {}
    for a in activas:
        if a.get(clave):
            cuenta[a[clave]] = cuenta.get(a[clave], 0) + 1

    filas = [
        {
            "id": x["id"],
            "nombre": x["nombre"],
            "cantidad": cuenta.get(x["id"], 0),
        }
        for x in coleccion
        if x.get("activa", True)
    ]
    return sorted(filas, key=lambda f: (-f["cantidad"], f["nombre"].lower()))


def _matricula() -> list[dict]:
    """Cuántos ingresaron cada año.

    Sale del `ingreso` de cada inscripción a carrera, que es un dato que ya
    estaba. No se inventa una serie mensual que la base no tiene.
    """
    cuenta: dict[int, int] = {}
    for a in _asociaciones_activas():
        anio = a.get("ingreso")
        if isinstance(anio, int):
            cuenta[anio] = cuenta.get(anio, 0) + 1
    return [{"anio": anio, "cantidad": cuenta[anio]} for anio in sorted(cuenta)]


def _asistencia_general() -> dict:
    """El porcentaje de asistencia de toda la institución.

    Solo cuentan las clases **dictadas**: una clase suspendida no es una falta
    de nadie. Es el mismo criterio que usa la pantalla de Asistencias, así que
    los dos números coinciden.
    """
    presentes = 0
    total = 0
    dictadas = {c["id"] for c in d.clases_asistencia if c.get("dictada", True)}

    for registro in d.asistencias:
        if registro["claseId"] not in dictadas:
            continue
        total += 1
        if registro["estado"] in ("presente", "justificada"):
            presentes += 1

    return {
        "porcentaje": round(presentes * 100 / total) if total else None,
        "registros": total,
        "minimo": asis.minimo_exigido(),
    }


def _rendimiento() -> dict:
    """Aprobados y desaprobados, de lo que está cargado.

    Dos fuentes, porque son dos cosas: la condición final de cada materia
    (`historialAcademico`) y las notas de los trabajos (`calificaciones`).
    """
    historial = [h for h in d.historial_academico if h.get("condicion") in ("Aprobada", "Libre")]
    aprobadas = sum(1 for h in historial if h["condicion"] == "Aprobada")

    notas = [c["nota"] for c in d.calificaciones if isinstance(c.get("nota"), (int, float))]
    aprobados_trabajos = sum(1 for n in notas if n >= 6)

    return {
        "materiasAprobadas": aprobadas,
        "materiasLibres": len(historial) - aprobadas,
        "trabajosCorregidos": len(notas),
        "trabajosAprobados": aprobados_trabajos,
        "promedio": round(sum(notas) / len(notas), 2) if notas else None,
        "sinCorregir": sum(1 for c in d.calificaciones if c.get("nota") is None),
    }


def distribuciones() -> dict:
    return {
        "porCarrera": _contar_por("carreraId", d.carreras_institucion),
        "porSede": _contar_por("sedeId", d.sedes),
        # Solo las que tienen gente: las vacías ya tienen su propia alerta, y
        # dieciséis barras en cero no son un gráfico.
        "porComision": [
            c for c in _contar_por("comisionId", d.comisiones) if c["cantidad"] > 0
        ][:TOPE_BARRAS],
        "matricula": _matricula(),
        "asistencia": _asistencia_general(),
        "rendimiento": _rendimiento(),
    }


# ===================== Las alertas =====================
# Cada una dice qué pasa, cuántos son y **adónde ir a resolverlo**. Una alerta
# que no lleva a ninguna parte obliga a buscar la pantalla a mano, que es
# justamente lo que el panel tendría que evitar.
#
# `nivel` es el del semáforo del campus: `alta` pide atención hoy, `media`
# esta semana, `info` es para saber.


def _materias_sin_docente() -> list[dict]:
    """Materias que se dictan en una comisión pero sin nadie a cargo."""
    salida = []
    for dictado in d.dictados:
        if dictado.get("docentes"):
            continue
        materia = d.buscar_materia(dictado["materiaId"])
        comision = d.buscar_en(d.comisiones, dictado["comisionId"])
        if not materia or not comision or not comision.get("activa", True):
            continue
        salida.append(
            {
                "id": dictado["id"],
                "texto": f"{materia['nombre']} · {comision['nombre']}",
                "ruta": "/administracion/estructura",
            }
        )
    return salida


def _comisiones_sin_estudiantes() -> list[dict]:
    activas = _asociaciones_activas()
    con_gente = {a["comisionId"] for a in activas if a.get("comisionId")}
    return [
        {
            "id": c["id"],
            "texto": c["nombre"],
            "ruta": f"/administracion/estudiantes?comisionId={c['id']}",
        }
        for c in d.comisiones
        if c.get("activa", True) and c["id"] not in con_gente
    ]


def _en_riesgo_de_asistencia() -> list[dict]:
    """Estudiantes por debajo del mínimo en alguna materia.

    Se calcula con el mismo servicio que la pantalla de Asistencias, no con
    una cuenta aparte: dos formas de calcular lo mismo terminan dando dos
    números distintos.
    """
    minimo = asis.minimo_exigido()
    salida = []

    for curso in d.cursos:
        dictadas = asis.clases_de(curso["id"], solo_dictadas=True)
        if not dictadas:
            continue
        ids = {c["id"] for c in dictadas}

        for persona in d.participantes_de_curso(curso):
            if not d.tiene_rol(persona, "Estudiante"):
                continue
            suyas = [a for a in d.asistencias if a["claseId"] in ids and a["personaId"] == persona["id"]]
            if not suyas:
                continue
            presentes = sum(1 for a in suyas if a["estado"] in ("presente", "justificada"))
            porcentaje = round(presentes * 100 / len(suyas))
            if porcentaje < minimo:
                salida.append(
                    {
                        "id": f"{curso['id']}-{persona['id']}",
                        "texto": f"{persona['nombre']} · {curso['nombre']} ({porcentaje} %)",
                        "ruta": f"/modulos/{curso['id']}",
                    }
                )

    return salida


def _sin_calificar() -> list[dict]:
    """Trabajos cuya entrega ya venció y todavía no tienen nota.

    Es lo que el pliego llama "docentes que no cargaron calificaciones", dicho
    desde el trabajo y no desde la persona: lo que hay que hacer es corregir
    ese trabajo, y ahí es adonde lleva.
    """
    ahora = d.ahora()
    salida = []

    for tarea in d.tareas:
        if d.desde_iso(tarea["fechaLimite"]) >= ahora:
            continue
        notas = [
            c for c in d.calificaciones
            if c["tareaId"] == tarea["id"] and c.get("nota") is not None
        ]
        if notas:
            continue
        curso = d.buscar_curso(tarea["cursoId"])
        salida.append(
            {
                "id": tarea["id"],
                "texto": f"{tarea['titulo']} · {curso['nombre'] if curso else '—'}",
                "ruta": f"/modulos/{tarea['cursoId']}",
            }
        )

    return salida


def alertas(persona: dict) -> list[dict]:
    """Lo que hay que atender, ordenado por urgencia.

    Las que no tienen nada que atender **no se devuelven**: un tablero lleno
    de ceros en verde enseña a no mirarlo.
    """
    activas = _asociaciones_activas()

    posibles = [
        {
            "id": "sin-comision",
            "nivel": "alta",
            "titulo": "Estudiantes sin comisión",
            "explicacion": "Están en una carrera pero todavía no tienen dónde cursar.",
            "cantidad": len([a for a in activas if not a.get("comisionId")]),
            "ruta": "/administracion/estudiantes",
            "accion": "Asignarles comisión",
        },
        {
            "id": "asistencia",
            "nivel": "alta",
            "titulo": "Estudiantes por debajo del mínimo de asistencia",
            "explicacion": f"Menos del {asis.minimo_exigido()} % en alguna materia.",
            "items": _en_riesgo_de_asistencia(),
            "ruta": "/asistencias/panel",
            "accion": "Ver asistencias",
        },
        {
            "id": "sin-docente",
            "nivel": "alta",
            "titulo": "Materias sin docente asignado",
            "explicacion": "Se dictan en una comisión pero no tienen a nadie a cargo.",
            "items": _materias_sin_docente(),
            "ruta": "/administracion/estructura",
            "accion": "Asignar docentes",
        },
        {
            "id": "cuentas",
            "nivel": "media",
            "titulo": "Cuentas pendientes de activación",
            "explicacion": "Existen en el padrón pero todavía no pueden entrar.",
            "cantidad": len([p for p in d.personas if p.get("estado") == "pendiente"]),
            "ruta": "/administracion/cuentas",
            "accion": "Ver cuentas",
        },
        {
            "id": "aportes",
            "nivel": "media",
            "titulo": "Aportes de biblioteca sin revisar",
            "explicacion": "Esperan que un docente los apruebe o los rechace.",
            "cantidad": len([m for m in d.materiales if m["estado"] == "pendiente"]),
            "ruta": "/biblioteca",
            "accion": "Revisar aportes",
        },
        {
            "id": "sin-calificar",
            "nivel": "media",
            "titulo": "Trabajos vencidos sin corregir",
            "explicacion": "Pasó la fecha de entrega y no tienen ninguna nota cargada.",
            "items": _sin_calificar(),
            "ruta": "/modulos",
            "accion": "Ver módulos",
        },
        {
            "id": "comisiones-vacias",
            "nivel": "media",
            "titulo": "Comisiones sin estudiantes",
            "explicacion": "Están abiertas pero no tiene a nadie asignado.",
            "items": _comisiones_sin_estudiantes(),
            "ruta": "/administracion/estudiantes",
            "accion": "Distribuir estudiantes",
        },
        {
            "id": "examenes",
            "nivel": "info",
            "titulo": "Exámenes y mesas próximas",
            "explicacion": "Lo que se viene en los próximos días.",
            "items": [
                {"id": i, "texto": e["titulo"], "ruta": e["ruta"]}
                for i, e in enumerate(_proximos_examenes()[:8])
            ],
            "ruta": "/calendario",
            "accion": "Ver el calendario",
        },
    ]

    orden = {"alta": 0, "media": 1, "info": 2}
    salida = []
    for alerta in posibles:
        items = alerta.pop("items", None)
        cantidad = alerta.get("cantidad", len(items) if items is not None else 0)
        if cantidad == 0:
            continue
        salida.append({**alerta, "cantidad": cantidad, "items": (items or [])[:6]})

    return sorted(salida, key=lambda a: orden[a["nivel"]])


# ===================== Las dos respuestas =====================
# Lo que contestan las dos rutas del panel, con su control de acceso. Viven
# acá y no en la ruta para que FastAPI y Django contesten **con la misma
# función** mientras dure la migración: cada framework solo la llama.

# Lo que ve de la actividad quien supervisa sin administrar: lo académico.
# `usuarios` —roles y cuentas suspendidas— es del administrador.
MODULOS_DE_SUPERVISION = {
    "academico", "asistencias", "calificaciones", "finales", "biblioteca", "modulos",
}


def exigir_acceso(yo: dict) -> None:
    if not es_supervisor(yo):
        raise HTTPException(
            403, "El panel de control es para la administración y la supervisión"
        )


def tablero(yo: dict) -> dict:
    """Los números, las distribuciones, lo próximo y la actividad reciente.

    Todo en una sola consulta: son ocho cuentas chicas sobre datos que ya
    están en memoria, y partirlo en cinco llamadas solo multiplicaría los
    estados de carga de la pantalla.
    """
    exigir_acceso(yo)

    return {
        "indicadores": indicadores(),
        "distribuciones": distribuciones(),
        "proximos": _proximos_examenes()[:6],
        # La actividad reciente sale del registro central de auditoría, no de
        # una lista aparte: es el mismo dato mirado desde el panel.
        "actividad": [
            auditoria.con_nombres(e)
            for e in auditoria.buscar({}, None if es_administrador(yo) else
                                      MODULOS_DE_SUPERVISION)[:8]
        ],
        "esAdministrador": es_administrador(yo),
    }


def resumen_de_alertas(yo: dict) -> dict:
    """Las alertas, con cuántos casos suman y cuántos son urgentes.

    Las que no tienen nada que atender no vienen: un tablero lleno de ceros
    en verde enseña a no mirarlo.
    """
    exigir_acceso(yo)
    lista = alertas(yo)

    return {
        "alertas": lista,
        "cuantas": sum(a["cantidad"] for a in lista),
        "urgentes": sum(a["cantidad"] for a in lista if a["nivel"] == "alta"),
    }
