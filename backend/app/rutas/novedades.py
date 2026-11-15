"""Muro de novedades institucionales, con reacciones anónimas.

Quién publica y quién reacciona salen de la **sesión**: cada ruta recibe `yo`
del token de Firebase que verifica `servicios/autenticacion.py`. Antes había
una constante de módulo con el usuario de prueba, de cuando no había login;
con sesiones de verdad eso publicaba todo a nombre de la misma persona y
contaba las reacciones de ella, no las de quien estaba mirando.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios.autenticacion import IdUsuarioActual

router = APIRouter(prefix="/api/novedades", tags=["Novedades"])

# Las únicas reacciones posibles
REACCIONES = ["leido", "util", "dudas"]


def _puede_publicar(persona_id: int) -> bool:
    """Solo los docentes publican y editan; los estudiantes leen."""
    persona = d.buscar_persona(persona_id)
    return d.tiene_rol(persona, "Docente", "Supervisor", "Administrador")


def _resumir_reacciones(publicacion: dict, yo: int) -> dict:
    """Las reacciones salen contadas, nunca con la lista de quiénes
    reaccionaron: el que lee ve cuántos fueron y cuál puso él, y nada más."""
    reacciones = publicacion.get("reacciones") or {}
    cuenta = {tipo: len(reacciones.get(tipo, [])) for tipo in REACCIONES}
    mia = next((tipo for tipo in REACCIONES if yo in reacciones.get(tipo, [])), None)
    return {"cuenta": cuenta, "miReaccion": mia}


def _con_autor(publicacion: dict, yo: int) -> dict:
    autor = d.buscar_persona(publicacion["autorId"])
    sin_quienes = {k: v for k, v in publicacion.items() if k != "reacciones"}
    return {
        **sin_quienes,
        **_resumir_reacciones(publicacion, yo),
        "autor": (
            {"id": autor["id"], "nombre": autor["nombre"], "rol": d.rol_principal(autor)}
            if autor
            else None
        ),
        # Para que el frontend sepa si mostrarle el botón de editar
        "puedeEditar": _puede_publicar(yo) and publicacion["autorId"] == yo,
    }


def _anclar_solo(id_publicacion: int) -> None:
    """Solo puede haber una destacada a la vez."""
    for p in d.publicaciones:
        p["anclada"] = p["id"] == id_publicacion


@router.get("", summary="Listar las publicaciones del muro")
def listar_publicaciones(yo: int = IdUsuarioActual):
    """La anclada va siempre primera; el resto, de la más nueva a la más vieja."""
    ordenadas = sorted(
        d.publicaciones,
        key=lambda p: (bool(p.get("anclada")), d.desde_iso(p["fecha"])),
        reverse=True,
    )
    return {
        "publicaciones": [_con_autor(p, yo) for p in ordenadas],
        "puedePublicar": _puede_publicar(yo),
    }


@router.post("", status_code=201, summary="Publicar una novedad")
def crear_publicacion(cuerpo: dict[str, Any] = Body(default={}), yo: int = IdUsuarioActual):
    if not _puede_publicar(yo):
        raise HTTPException(403, "Solo los docentes pueden publicar novedades")

    titulo = str(cuerpo.get("titulo") or "").strip()
    texto = str(cuerpo.get("cuerpo") or "").strip()
    categoria = str(cuerpo.get("categoria") or "Académico").strip()
    ambito = str(cuerpo.get("ambito") or "Institucional").strip()
    # Por ahora la imagen es una dirección: todavía no hay dónde subir archivos
    imagen = str(cuerpo.get("imagen") or "").strip() or None

    if not titulo or not texto:
        raise HTTPException(400, "La novedad necesita un título y un texto")

    publicacion = {
        "id": d.nuevo_id_publicacion(),
        "autorId": yo,
        "ambito": ambito,
        "categoria": categoria,
        "titulo": titulo,
        "cuerpo": texto,
        "imagen": imagen,
        "fecha": d.iso(d.ahora()),
        "editada": None,
        "anclada": False,
        "reacciones": {"leido": [], "util": [], "dudas": []},
    }
    d.publicaciones.append(publicacion)

    if cuerpo.get("anclada"):
        _anclar_solo(publicacion["id"])

    return _con_autor(publicacion, yo)


@router.put("/{id_publicacion}", summary="Editar una novedad propia")
def editar_publicacion(
    id_publicacion: int,
    cuerpo: dict[str, Any] = Body(default={}),
    yo: int = IdUsuarioActual,
):
    publicacion = next((p for p in d.publicaciones if p["id"] == id_publicacion), None)
    if not publicacion:
        raise HTTPException(404, "Novedad no encontrada")
    if not _puede_publicar(yo) or publicacion["autorId"] != yo:
        raise HTTPException(403, "Solo quien la publicó puede editarla")

    titulo = str(cuerpo.get("titulo") or "").strip()
    texto = str(cuerpo.get("cuerpo") or "").strip()
    if not titulo or not texto:
        raise HTTPException(400, "La novedad necesita un título y un texto")

    publicacion["titulo"] = titulo
    publicacion["cuerpo"] = texto
    publicacion["imagen"] = str(cuerpo.get("imagen") or "").strip() or None
    publicacion["editada"] = d.iso(d.ahora())

    if cuerpo.get("anclada"):
        _anclar_solo(publicacion["id"])
    elif publicacion.get("anclada"):
        publicacion["anclada"] = False

    return _con_autor(publicacion, yo)


@router.post("/{id_publicacion}/reaccion", summary="Reaccionar, o quitar la reacción")
def reaccionar(
    id_publicacion: int,
    cuerpo: dict[str, Any] = Body(default={}),
    yo: int = IdUsuarioActual,
):
    """Cada persona tiene una sola: poner otra reemplaza la anterior, y tocar
    la misma de nuevo la saca."""
    publicacion = next((p for p in d.publicaciones if p["id"] == id_publicacion), None)
    if not publicacion:
        raise HTTPException(404, "Novedad no encontrada")

    tipo = cuerpo.get("tipo")
    if tipo is not None and tipo not in REACCIONES:
        raise HTTPException(400, "Esa reacción no existe")

    publicacion.setdefault("reacciones", {"leido": [], "util": [], "dudas": []})
    reacciones = publicacion["reacciones"]

    ya_estaba = next((t for t in REACCIONES if yo in reacciones.get(t, [])), None)
    for t in REACCIONES:
        reacciones[t] = [i for i in reacciones.get(t, []) if i != yo]

    # Tocar la que ya estaba puesta la saca
    if tipo and tipo != ya_estaba:
        reacciones[tipo].append(yo)

    return _con_autor(publicacion, yo)
