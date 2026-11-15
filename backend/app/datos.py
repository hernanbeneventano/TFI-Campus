"""Datos de prueba y funciones de acceso.

Se reemplazarán por Firestore cuando se haga la migración. Toda la capa de
datos vive acá: las rutas y los controladores no saben de dónde salen.

Los valores iniciales están en `datos_iniciales.json`. Las fechas se guardan
como desplazamientos relativos y se resuelven al arrancar, de modo que los
datos de prueba siempre tengan tareas próximas y atrasadas por más que pasen
los días.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AQUI = Path(__file__).parent


# ===================== Fechas =====================
# El frontend espera el mismo formato que producía `Date.toISOString()` de
# JavaScript: UTC, con milisegundos y una Z al final.
def iso(momento: datetime) -> str:
    utc = momento.astimezone(timezone.utc)
    return f"{utc.strftime('%Y-%m-%dT%H:%M:%S')}.{utc.microsecond // 1000:03d}Z"


def ahora() -> datetime:
    """El momento actual con la zona horaria local."""
    return datetime.now().astimezone()


def desde_iso(texto: str) -> datetime:
    """Interpreta una fecha ISO. Las que terminan en Z son UTC."""
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def a_dias(n: int) -> str:
    """Una fecha a N días de hoy, a las 16:00. Negativo es en el pasado."""
    d = ahora() + timedelta(days=n)
    return iso(d.replace(hour=16, minute=0, second=0, microsecond=0))


def hace_horas(n: float) -> str:
    return iso(ahora() - timedelta(hours=n))


def clave_dia(fecha: str | datetime) -> str:
    """Día en formato AAAA-MM-DD, en hora local.

    Es la clave con la que el frontend agrupa los elementos en las celdas del
    calendario.
    """
    d = desde_iso(fecha) if isinstance(fecha, str) else fecha
    return d.astimezone().strftime("%Y-%m-%d")


# ===================== Carga de los datos iniciales =====================
def _resolver(valor: Any) -> Any:
    """Convierte los marcadores de fecha en fechas concretas."""
    if isinstance(valor, list):
        return [_resolver(v) for v in valor]
    if isinstance(valor, dict):
        marca = valor.get("__fecha")
        if marca == "aDias":
            return a_dias(valor["n"])
        if marca == "haceHoras":
            return hace_horas(valor["n"])
        if marca == "fijo":
            return valor["iso"]
        return {k: _resolver(v) for k, v in valor.items()}
    return valor


_iniciales = _resolver(json.loads((AQUI / "datos_iniciales.json").read_text(encoding="utf-8")))


def _por_curso(bruto: dict) -> dict[int, Any]:
    """Las claves numéricas vuelven a ser números: en JSON son texto."""
    return {int(k): v for k, v in bruto.items()}


# El usuario que inició sesión (por ahora fijo, hasta que haya login)
usuario_actual: dict = _iniciales["usuarioActual"]

cursos: list[dict] = _iniciales["cursos"]
tareas: list[dict] = _iniciales["tareas"]
contenidos: dict[int, list] = _por_curso(_iniciales["contenidos"])
anuncios: dict[int, list] = _por_curso(_iniciales["anuncios"])
personas: list[dict] = _iniciales["personas"]
participantes: dict[int, list[int]] = _por_curso(_iniciales["participantes"])
conversaciones: list[dict] = _iniciales["conversaciones"]
publicaciones: list[dict] = _iniciales["publicaciones"]
clases: list[dict] = _iniciales["clases"]
eventos: list[dict] = _iniciales["eventos"]
temas_foro: list[dict] = _iniciales["temasForo"]

# ----- Biblioteca -----
materiales: list[dict] = _iniciales["materiales"]
categorias: list[dict] = _iniciales["categorias"]
# La Biblioteca etiqueta sus materiales con el nombre de la carrera, que es
# un filtro y no una relación fuerte. El catálogo institucional, en cambio,
# son entidades: ver `carreras_institucion`.
carreras: list[str] = _iniciales["carrerasNombres"]
favoritos_biblioteca: list[dict] = _iniciales["favoritosBiblioteca"]
moderacion_biblioteca: list[dict] = _iniciales["moderacionBiblioteca"]
TIPOS_MATERIAL: list[str] = _iniciales["TIPOS_MATERIAL"]
ESTADOS_MATERIAL: list[str] = _iniciales["ESTADOS_MATERIAL"]

# ----- Gestión académica: plan de estudios, inscripciones y finales -----
# El plan vive en los datos, no en el código: las correlatividades de cada
# materia son una lista de ids y se cambian sin tocar el servidor. Es lo que
# va a administrar el panel de la institución cuando exista.
materias_plan: list[dict] = _iniciales["materiasPlan"]
inscripcion_carrera: list[dict] = _iniciales["inscripcionCarrera"]
historial_academico: list[dict] = _iniciales["historialAcademico"]
periodo_inscripcion_materias: dict = _iniciales["periodoInscripcionMaterias"]
inscripciones_materias: list[dict] = _iniciales["inscripcionesMaterias"]
mesas_examen: list[dict] = _iniciales["mesasExamen"]
inscripciones_finales: list[dict] = _iniciales["inscripcionesFinales"]
resultados_finales: list[dict] = _iniciales["resultadosFinales"]
CONDICIONES_CURSADA: list[str] = _iniciales["CONDICIONES_CURSADA"]
CONDICIONES_FINAL: list[str] = _iniciales["CONDICIONES_FINAL"]
# Cómo se toma una mesa. Solo las usa la gestión docente, que es la que las
# ofrece en el formulario; el alumno las lee ya resueltas en la mesa.
MODALIDADES_FINAL: list[str] = _iniciales["MODALIDADES_FINAL"]
INSTANCIAS_FINAL: list[str] = _iniciales["INSTANCIAS_FINAL"]

# ----- Notas de la cursada -----
# Una calificación por alumno y por tarea. Es distinta del resultado de un
# final: esto es la corrección de lo que se entrega durante el cuatrimestre.
calificaciones: list[dict] = _iniciales["calificaciones"]

# Qué material marcó como visto cada alumno. Hoy el alumno lo guarda en su
# navegador (`services/progreso.js`); acá está del lado del servidor porque el
# docente necesita ver cómo viene el curso, y el navegador de un alumno no
# puede contestar eso. Cuando el progreso del alumno se guarde acá, las dos
# puntas usan esta misma lista.
progreso_alumnos: list[dict] = _iniciales["progresoAlumnos"]

# Qué entregó cada alumno. `tareas[].entregada` era un solo booleano para todo
# el curso: servía para la pantalla del alumno de prueba, pero no deja saber
# quién entregó y quién no, que es lo primero que mira el docente al corregir.
entregas: list[dict] = _iniciales["entregas"]

# Lo que respondió cada alumno en un cuestionario de opción múltiple. Va
# aparte de `entregas` porque no hay archivo: la respuesta es el dato, y la
# corrección es automática.
respuestas_cuestionario: list[dict] = _iniciales["respuestasCuestionario"]

# Cómo se toma un trabajo. La modalidad dice dónde se rinde y el formato
# cómo se corrige: un presencial no tiene nada que subir y su nota la carga
# el docente; un cuestionario se corrige solo.
MODALIDADES_TRABAJO: list[str] = _iniciales["MODALIDADES_TRABAJO"]
FORMATOS_TRABAJO: list[str] = _iniciales["FORMATOS_TRABAJO"]

# ----- Estructura institucional -----
# Carreras, sedes, planes y comisiones como entidades con identificador: lo
# demás las referencia en vez de repetir el nombre. Nada de esto está escrito
# en el código; lo administra quien tenga el rol de administrador.
carreras_institucion: list[dict] = _iniciales["carreras"]
sedes: list[dict] = _iniciales["sedes"]
planes_estudio: list[dict] = _iniciales["planesEstudio"]
comisiones: list[dict] = _iniciales["comisiones"]
# Dónde está cada persona: carrera + sede + comisión + plan. Una persona
# puede tener varias, en carreras distintas.
asociaciones_academicas: list[dict] = _iniciales["asociacionesAcademicas"]
historial_usuarios: list[dict] = _iniciales["historialUsuarios"]

# El registro de auditoría de todo el campus. Es **solo de agregar**: no hay
# ninguna función que edite o borre un evento, ni acá ni en las rutas.
# Ver servicios/auditoria.py.
auditoria: list[dict] = _iniciales["auditoria"]
ESTADOS_CUENTA: list[str] = _iniciales["ESTADOS_CUENTA"]
ESTADOS_ASOCIACION: list[str] = _iniciales["ESTADOS_ASOCIACION"]
TURNOS: list[str] = _iniciales["TURNOS"]


def buscar_en(coleccion: list[dict], id_buscado: Any) -> dict | None:
    """Busca por id en cualquiera de los catálogos."""
    try:
        buscado = int(id_buscado)
    except (TypeError, ValueError):
        return None
    return next((x for x in coleccion if x["id"] == buscado), None)


# Qué materia se dicta en qué comisión y quién la da. Es una relación de
# tres: la misma materia se dicta en varias comisiones con docentes
# distintos, y una comisión puede tener dos docentes para la misma materia.
dictados: list[dict] = _iniciales["dictados"]


def dictados_de_comision(comision_id: int) -> list[dict]:
    return [x for x in dictados if x["comisionId"] == comision_id]


def dictados_de_materia(materia_id: int) -> list[dict]:
    return [x for x in dictados if x["materiaId"] == materia_id]


def docentes_de_materia(materia_id: int) -> list[int]:
    """Todos los que dictan esa materia, en cualquier comisión."""
    vistos: list[int] = []
    for dictado in dictados_de_materia(materia_id):
        for docente in dictado.get("docentes") or []:
            if docente not in vistos:
                vistos.append(docente)
    return vistos


def dicta_materia(persona_id: int, materia_id: int) -> bool:
    return persona_id in docentes_de_materia(materia_id)


def materias_que_dicta(persona_id: int) -> list[dict]:
    """Las materias del plan en las que la persona figura como docente."""
    ids = {
        x["materiaId"] for x in dictados if persona_id in (x.get("docentes") or [])
    }
    return [m for m in materias_plan if m["id"] in ids]


def asociaciones_de(persona_id: int) -> list[dict]:
    return [a for a in asociaciones_academicas if a["personaId"] == persona_id]


# ----- Asistencias -----
# Las clases efectivamente dictadas y quién estuvo en cada una. Una clase
# suspendida queda registrada pero no cuenta: no existió para nadie.
clases_asistencia: list[dict] = _iniciales["clasesAsistencia"]
asistencias: list[dict] = _iniciales["asistencias"]
justificaciones: list[dict] = _iniciales["justificaciones"]
planificacion_asistencia: list[dict] = _iniciales["planificacionAsistencia"]
historial_asistencia: list[dict] = _iniciales["historialAsistencia"]
CONFIG_ASISTENCIA: dict = _iniciales["CONFIG_ASISTENCIA"]
ESTADOS_ASISTENCIA: list[str] = _iniciales["ESTADOS_ASISTENCIA"]
ESTADOS_JUSTIFICACION: list[str] = _iniciales["ESTADOS_JUSTIFICACION"]

# El cierre de cursada de cada alumno, cuando el docente lo fija a mano.
# Si no está, la condición sale del promedio: se aprueba con 6.
cierres_cursada: list[dict] = []
NOTA_PARA_APROBAR = 6
ESTADOS_CALIFICACION: list[str] = _iniciales["ESTADOS_CALIFICACION"]


def buscar_materia(id_materia: Any) -> dict | None:
    try:
        buscado = int(id_materia)
    except (TypeError, ValueError):
        return None
    return next((m for m in materias_plan if m["id"] == buscado), None)


def buscar_mesa(id_mesa: Any) -> dict | None:
    try:
        buscado = int(id_mesa)
    except (TypeError, ValueError):
        return None
    return next((m for m in mesas_examen if m["id"] == buscado), None)


def carrera_de(persona_id: int) -> dict | None:
    """La asociación académica activa de la persona.

    Es lo que la institución registra al ingresar —carrera, sede, comisión y
    plan—; sin esto el alumno no tiene plan de estudios y no puede
    inscribirse a nada. Si tuviera varias carreras se devuelve la primera
    activa: la pantalla de inscripción trabaja sobre una por vez.
    """
    suyas = [a for a in asociaciones_de(persona_id) if a.get("estado") == "activa"]
    return suyas[0] if suyas else None


def asociacion_completa(asociacion: dict) -> dict:
    """La asociación con los nombres resueltos, para mostrarla."""
    carrera = buscar_en(carreras_institucion, asociacion.get("carreraId"))
    sede = buscar_en(sedes, asociacion.get("sedeId"))
    comision = buscar_en(comisiones, asociacion.get("comisionId"))
    plan = buscar_en(planes_estudio, asociacion.get("planId"))
    return {
        **asociacion,
        "carrera": carrera["nombre"] if carrera else None,
        "sede": sede["nombre"] if sede else None,
        "comision": comision["nombre"] if comision else None,
        "plan": plan["nombre"] if plan else None,
    }


def condicion_en(persona_id: int, materia_id: int) -> str | None:
    """Cómo está la persona en una materia: Aprobada, Regular, En curso…"""
    registro = next(
        (
            h
            for h in historial_academico
            if h["personaId"] == persona_id and h["materiaId"] == materia_id
        ),
        None,
    )
    return registro["condicion"] if registro else None


# ===================== Presencia =====================
def estado_por_acceso(fecha_iso: str) -> str:
    """Estado a partir del último acceso. Los mismos cortes que usa el
    frontend para el usuario que está navegando."""
    minutos = (ahora() - desde_iso(fecha_iso)).total_seconds() / 60
    if minutos < 5:
        return "conectado"
    if minutos < 30:
        return "ausente"
    return "desconectado"


def con_presencia(persona: dict) -> dict:
    """Las personas guardan hace cuántos minutos entraron, no una fecha fija.

    Así la fecha se calcula en cada pedido y los estados siguen teniendo
    sentido por más que el servidor lleve horas levantado.
    """
    resto = {k: v for k, v in persona.items() if k != "accesoHaceMin"}
    ultimo_acceso = iso(ahora() - timedelta(minutes=persona["accesoHaceMin"]))
    return {
        **resto,
        # `rol` va derivado para las pantallas que muestran uno solo
        "rol": rol_principal(persona),
        "roles": roles_de(persona),
        "ultimoAcceso": ultimo_acceso,
        "estado": estado_por_acceso(ultimo_acceso),
    }


# ===================== Roles =====================
# Una persona puede tener varios: un docente que además supervisa, alguien de
# secretaría que también cursa. `roles` es la fuente de verdad; `rol` se
# deriva para las pantallas que muestran uno solo.
ROLES: list[str] = _iniciales["ROLES"]


def roles_de(persona: dict | None) -> list[str]:
    if not persona:
        return []
    return persona.get("roles") or ([persona["rol"]] if persona.get("rol") else [])


def tiene_rol(persona: dict | None, *buscados: str) -> bool:
    """Si la persona tiene alguno de esos roles.

    Es lo que reemplaza a `persona["rol"] == "Docente"` en todo el campus:
    con varios roles, comparar contra uno solo deja afuera al que además es
    otra cosa.
    """
    suyos = set(roles_de(persona))
    return any(r in suyos for r in buscados)


def rol_principal(persona: dict | None) -> str | None:
    """El primero de la lista: el que se muestra cuando hay lugar para uno."""
    suyos = roles_de(persona)
    return suyos[0] if suyos else None


def con_rol(persona: dict | None) -> dict | None:
    """La persona con `rol` agregado, para las pantallas que muestran uno.

    El frontend nunca decide permisos con esto —eso lo hace el servidor—,
    pero sí lo usa para escribir "Docente" debajo de un nombre.
    """
    if not persona:
        return None
    return {**persona, "rol": rol_principal(persona), "roles": roles_de(persona)}


def buscar_persona(id_persona: Any) -> dict | None:
    try:
        buscado = int(id_persona)
    except (TypeError, ValueError):
        return None
    return next((p for p in personas if p["id"] == buscado), None)


def buscar_curso(id_curso: Any) -> dict | None:
    try:
        buscado = int(id_curso)
    except (TypeError, ValueError):
        return None
    return next((c for c in cursos if c["id"] == buscado), None)


# ===================== Contenido de los módulos =====================
def contenido_generico(curso: dict) -> list[dict]:
    """Contenido mínimo para los módulos que todavía no tienen uno propio."""
    tareas_curso = [t for t in tareas if t["cursoId"] == curso["id"]]
    return [
        {
            "id": 1,
            "titulo": "Información del módulo",
            "descripcion": "Bienvenida y programa de la materia",
            "items": [
                {
                    "id": f"{curso['id']}-1",
                    "tipo": "pagina",
                    "titulo": "Bienvenida al módulo",
                    "cuerpo": [
                        f"¡Bienvenidos a {curso['nombre']}! Acá vas a encontrar todo el material "
                        "de la materia organizado por semana.",
                        f"Docente a cargo: {curso['docente']}.",
                    ],
                },
                {
                    "id": f"{curso['id']}-2",
                    "tipo": "archivo",
                    "titulo": "Programa de la materia",
                    "formato": "PDF",
                    "tamano": "280 KB",
                },
            ],
        },
        {
            "id": 2,
            "titulo": "Semana 1",
            "descripcion": "Material y actividades de la primera semana",
            "items": [
                {
                    "id": f"{curso['id']}-3",
                    "tipo": "archivo",
                    "titulo": "Clase 1",
                    "formato": "Video",
                    "tamano": "45 min",
                },
                *[
                    {
                        "id": f"{curso['id']}-t{t['id']}",
                        "tipo": "tarea",
                        "titulo": t["titulo"],
                        "tareaId": t["id"],
                    }
                    for t in tareas_curso
                ],
            ],
        },
    ]


def carpetas_de_curso(curso: dict) -> list[dict]:
    """Las carpetas con los datos de sus tareas ya resueltos.

    La usan tanto la pantalla del módulo como el panel de tareas pendientes.
    """
    base = contenidos.get(curso["id"]) or contenido_generico(curso)
    carpetas = []
    for carpeta in base:
        items = []
        for item in carpeta["items"]:
            if item.get("tipo") != "tarea":
                items.append(item)
                continue
            tarea = next((t for t in tareas if t["id"] == item.get("tareaId")), None)
            items.append(
                {
                    **item,
                    "fechaLimite": tarea.get("fechaLimite") if tarea else None,
                    "entregada": tarea.get("entregada", False) if tarea else False,
                    # `cerrada` pesa más que la fecha: el docente puede cortar
                    # las entregas antes o darle prórroga al curso. Sin esto,
                    # la pantalla muestra un plazo que ya no manda.
                    "cerrada": tarea.get("cerrada") if tarea else None,
                    "consigna": tarea.get("consigna") if tarea else None,
                    # Cómo se toma: la pantalla del alumno necesita saberlo
                    # para mostrar el cuestionario, el aviso del presencial o
                    # la subida de archivo.
                    "modalidad": tarea.get("modalidad", "virtual") if tarea else "virtual",
                    "formato": tarea.get("formato", "entrega") if tarea else "entrega",
                }
            )
        carpetas.append({**carpeta, "items": items})
    return carpetas


def participantes_de_curso(curso: dict) -> list[dict]:
    """Los módulos sin lista propia usan una genérica: su docente y un par de
    estudiantes."""
    ids = participantes.get(curso["id"]) or [curso["docenteId"], 1, 3]
    return [p for p in (buscar_persona(i) for i in ids) if p]


def anuncios_genericos(curso: dict) -> list[dict]:
    """Para los módulos que todavía no tienen anuncios propios."""
    return [
        {
            "id": 1,
            "titulo": f"Bienvenidos a {curso['nombre']}",
            "cuerpo": "En la carpeta de información está el programa de la materia y el cronograma.",
            "autor": curso["docente"],
            "fecha": a_dias(-12),
        }
    ]


# ===================== Novedades de un módulo =====================
DIAS_NOVEDAD = 7


def novedades_de_curso(curso: dict) -> dict:
    """Lo publicado en la última semana. Es lo que enciende la campanita en la
    tarjeta de Módulos."""
    desde = ahora() - timedelta(days=DIAS_NOVEDAD)

    de_anuncios = anuncios.get(curso["id"]) or anuncios_genericos(curso)
    anuncios_nuevos = sum(1 for a in de_anuncios if desde_iso(a["fecha"]) >= desde)

    tareas_nuevas = sum(
        1
        for t in tareas
        if t["cursoId"] == curso["id"]
        and not t["entregada"]
        and desde_iso(t["publicada"]) >= desde
    )

    return {
        "anuncios": anuncios_nuevos,
        "tareas": tareas_nuevas,
        "total": anuncios_nuevos + tareas_nuevas,
    }


def resumen_de_novedades(persona_id: int) -> dict:
    """Lo nuevo en cada apartado del menú. Enciende las campanitas."""
    desde = ahora() - timedelta(days=DIAS_NOVEDAD)

    modulos = sum(1 for c in cursos if novedades_de_curso(c)["total"] > 0)
    nuevas = sum(1 for p in publicaciones if desde_iso(p["fecha"]) >= desde)
    informacion = sum(
        1
        for p in publicaciones
        if p.get("ambito") == "Institucional" and desde_iso(p["fecha"]) >= desde
    )

    mensajes = sum(
        sum(1 for m in c["mensajes"] if m["deId"] != persona_id and not m["leido"])
        for c in conversaciones
        if persona_id in c["entre"]
    )

    return {
        "informacion": informacion,
        "modulos": modulos,
        "mensajes": mensajes,
        "novedades": nuevas,
    }


# ===================== Contactos =====================
def contactos_de(persona_id: int) -> list[dict]:
    """A quiénes le puede escribir una persona: solo la gente de los módulos en
    los que está, no todo el campus.

    Cada contacto viene con los módulos que comparten, para ubicarlo en la
    búsqueda.
    """
    por_id: dict[int, dict] = {}

    for curso in cursos:
        gente = participantes_de_curso(curso)
        if not any(p["id"] == persona_id for p in gente):
            continue

        for persona in gente:
            if persona["id"] == persona_id:
                continue
            if persona["id"] not in por_id:
                por_id[persona["id"]] = {**persona, "modulos": []}
            por_id[persona["id"]]["modulos"].append(curso["nombre"])

    return list(por_id.values())


# ===================== Identificadores =====================
# Arrancan altos para no chocar con los de los datos de prueba.
_proximos = {
    "auditoria": 1,
    "mensaje": 100,
    "conversacion": 100,
    "publicacion": 100,
    "tema": 100,
    "mensajeForo": 200,
    "material": 100,
    "moderacion": 100,
    "inscripcionMateria": 100,
    "inscripcionFinal": 100,
    "mesa": 100,
    "resultadoFinal": 100,
    "carpeta": 100,
    "anuncio": 100,
    "tarea": 100,
    "calificacion": 100,
    "entrega": 100,
    "respuesta": 100,
    "clase": 100,
    "asistencia": 1000,
    "justificacion": 100,
    "historialAsistencia": 100,
    "carrera": 100,
    "sede": 100,
    "plan": 100,
    "comision": 100,
    "asociacion": 100,
    "historialUsuario": 100,
    "dictado": 100,
}


def _nuevo_id(clave: str) -> int:
    valor = _proximos[clave]
    _proximos[clave] = valor + 1
    return valor


def nuevo_id_mensaje() -> int:
    return _nuevo_id("mensaje")


def nuevo_id_conversacion() -> int:
    return _nuevo_id("conversacion")


def nuevo_id_publicacion() -> int:
    return _nuevo_id("publicacion")


def nuevo_id_tema() -> int:
    return _nuevo_id("tema")


def nuevo_id_mensaje_foro() -> int:
    return _nuevo_id("mensajeForo")


def nuevo_id_material() -> int:
    return _nuevo_id("material")


def nuevo_id_moderacion() -> int:
    return _nuevo_id("moderacion")


def nuevo_id_inscripcion_materia() -> int:
    return _nuevo_id("inscripcionMateria")


def nuevo_id_inscripcion_final() -> int:
    return _nuevo_id("inscripcionFinal")


def nuevo_id_mesa() -> int:
    return _nuevo_id("mesa")


def nuevo_id_resultado_final() -> int:
    return _nuevo_id("resultadoFinal")


def nuevo_id_carpeta() -> int:
    return _nuevo_id("carpeta")


def nuevo_id_anuncio() -> int:
    return _nuevo_id("anuncio")


def nuevo_id_tarea() -> int:
    return _nuevo_id("tarea")


def nuevo_id_calificacion() -> int:
    return _nuevo_id("calificacion")


def nuevo_id_entrega() -> int:
    return _nuevo_id("entrega")


def nuevo_id_respuesta() -> int:
    return _nuevo_id("respuesta")


def nuevo_id_clase_asistencia() -> int:
    return _nuevo_id("clase")


def nuevo_id_asistencia() -> int:
    return _nuevo_id("asistencia")


def nuevo_id_justificacion() -> int:
    return _nuevo_id("justificacion")


def nuevo_id_historial_asistencia() -> int:
    return _nuevo_id("historialAsistencia")


def nuevo_id_carrera() -> int:
    return _nuevo_id("carrera")


def nuevo_id_sede() -> int:
    return _nuevo_id("sede")


def nuevo_id_plan() -> int:
    return _nuevo_id("plan")


def nuevo_id_comision() -> int:
    return _nuevo_id("comision")


def nuevo_id_asociacion() -> int:
    return _nuevo_id("asociacion")


def nuevo_id_historial_usuario() -> int:
    return _nuevo_id("historialUsuario")


def nuevo_id_auditoria() -> int:
    return _nuevo_id("auditoria")


def nuevo_id_dictado() -> int:
    return _nuevo_id("dictado")


# ===================== Contenido propio de un módulo =====================
def asegurar_contenido(curso: dict) -> list[dict]:
    """Las carpetas del módulo, listas para editar.

    `carpetas_de_curso` devuelve el contenido genérico cuando el módulo no
    tiene uno propio, pero ese genérico se arma al vuelo en cada pedido: si el
    docente edita eso, el cambio se pierde. Entonces, la primera vez que
    alguien va a modificar un módulo sin contenido propio, se guarda una copia
    del genérico y a partir de ahí se edita esa.
    """
    propio = contenidos.get(curso["id"])
    if propio is None:
        propio = contenido_generico(curso)
        contenidos[curso["id"]] = propio
    return propio


def buscar_tarea(id_tarea: Any) -> dict | None:
    try:
        buscado = int(id_tarea)
    except (TypeError, ValueError):
        return None
    return next((t for t in tareas if t["id"] == buscado), None)


# ===================== Avisos por mensaje =====================
def avisar_por_mensaje(de_id: int, para_id: int, texto: str) -> None:
    """Deja un mensaje en la conversación entre dos personas, y la crea si no
    existía.

    Es como se avisa hoy que una mesa se reprogramó, se canceló o ya tiene
    nota: no hay mails (quedaron para después) y Mensajes ya enciende su
    campanita con lo que no se leyó.
    """
    conversacion = next(
        (c for c in conversaciones if de_id in c["entre"] and para_id in c["entre"]), None
    )
    if conversacion is None:
        conversacion = {"id": nuevo_id_conversacion(), "entre": [de_id, para_id], "mensajes": []}
        conversaciones.append(conversacion)

    conversacion["mensajes"].append(
        {
            "id": nuevo_id_mensaje(),
            "deId": de_id,
            "texto": texto,
            "adjuntos": [],
            "fecha": iso(ahora()),
            "leido": False,
        }
    )


# ===================== Archivos de la biblioteca =====================
# Los bytes van en un diccionario aparte y no en `materiales`, porque el
# contenido del archivo no es un dato de la ficha: el material guarda el
# nombre, el tamaño y el tipo, y acá está lo que se descarga.
#
# Vive en memoria y se pierde al reiniciar, como el resto de los datos de
# prueba. Con Firebase Storage esto pasa a ser una referencia al bucket.
_archivos: dict[int, bytes] = {}


def guardar_archivo(material_id: int, contenido: bytes) -> None:
    _archivos[material_id] = contenido


def leer_archivo(material_id: int) -> bytes | None:
    return _archivos.get(material_id)


def borrar_archivo(material_id: int) -> None:
    _archivos.pop(material_id, None)
