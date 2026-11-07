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
carreras: list[str] = _iniciales["carreras"]
favoritos_biblioteca: list[dict] = _iniciales["favoritosBiblioteca"]
moderacion_biblioteca: list[dict] = _iniciales["moderacionBiblioteca"]
TIPOS_MATERIAL: list[str] = _iniciales["TIPOS_MATERIAL"]
ESTADOS_MATERIAL: list[str] = _iniciales["ESTADOS_MATERIAL"]


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
    return {**resto, "ultimoAcceso": ultimo_acceso, "estado": estado_por_acceso(ultimo_acceso)}


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
    "mensaje": 100,
    "conversacion": 100,
    "publicacion": 100,
    "tema": 100,
    "mensajeForo": 200,
    "material": 100,
    "moderacion": 100,
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
