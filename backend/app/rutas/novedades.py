"""Muro de novedades institucionales, con reacciones anónimas."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d

router = APIRouter(prefix="/api/novedades", tags=["Novedades"])

# Las únicas reacciones posibles
REACCIONES = ["leido", "util", "dudas"]

# Mientras no haya login, el que publica es siempre el usuario de prueba.
YO = d.usuario_actual["id"]


def _puede_publicar(persona_id: int) -> bool:
    """Solo los docentes publican y editan; los estudiantes leen."""
    persona = d.buscar_persona(persona_id)
    return bool(persona and persona["rol"] == "Docente")


def _resumir_reacciones(publicacion: dict) -> dict:
    """Las reacciones salen contadas, nunca con la lista de quiénes
    reaccionaron: el que lee ve cuántos fueron y cuál puso él, y nada más."""
    reacciones = publicacion.get("reacciones") or {}
    cuenta = {tipo: len(reacciones.get(tipo, [])) for tipo in REACCIONES}
    mia = next((tipo for tipo in REACCIONES if YO in reacciones.get(tipo, [])), None)
    return {"cuenta": cuenta, "miReaccion": mia}


def _con_autor(publicacion: dict) -> dict:
    autor = d.buscar_persona(publicacion["autorId"])
    sin_quienes = {k: v for k, v in publicacion.items() if k != "reacciones"}
    return {
        **sin_quienes,
        **_resumir_reacciones(publicacion),
        "autor": (
            {"id": autor["id"], "nombre": autor["nombre"], "rol": autor["rol"]} if autor else None
        ),
        # Para que el frontend sepa si mostrarle el botón de editar
        "puedeEditar": _puede_publicar(YO) and publicacion["autorId"] == YO,
    }


def _anclar_solo(id_publicacion: int) -> None:
    """Solo puede haber una destacada a la vez."""
    for p in d.publicaciones:
        p["anclada"] = p["id"] == id_publicacion


@router.get("", summary="Listar las publicaciones del muro")
def listar_publicaciones():
    """La anclada va siempre primera; el resto, de la más nueva a la más vieja."""
    ordenadas = sorted(
        d.publicaciones,
        key=lambda p: (bool(p.get("anclada")), d.desde_iso(p["fecha"])),
        reverse=True,
    )
    return {
        "publicaciones": [_con_autor(p) for p in ordenadas],
        "puedePublicar": _puede_publicar(YO),
    }


@router.post("", status_code=201, summary="Publicar una novedad")
def crear_publicacion(cuerpo: dict[str, Any] = Body(default={})):
    if not _puede_publicar(YO):
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
        "autorId": YO,
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

    return _con_autor(publicacion)


@router.put("/{id_publicacion}", summary="Editar una novedad propia")
def editar_publicacion(id_publicacion: int, cuerpo: dict[str, Any] = Body(default={})):
    publicacion = next((p for p in d.publicaciones if p["id"] == id_publicacion), None)
    if not publicacion:
        raise HTTPException(404, "Novedad no encontrada")
    if not _puede_publicar(YO) or publicacion["autorId"] != YO:
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

    return _con_autor(publicacion)


@router.post("/{id_publicacion}/reaccion", summary="Reaccionar, o quitar la reacción")
def reaccionar(id_publicacion: int, cuerpo: dict[str, Any] = Body(default={})):
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

    ya_estaba = next((t for t in REACCIONES if YO in reacciones.get(t, [])), None)
    for t in REACCIONES:
        reacciones[t] = [i for i in reacciones.get(t, []) if i != YO]

    # Tocar la que ya estaba puesta la saca
    if tipo and tipo != ya_estaba:
        reacciones[tipo].append(YO)

    return _con_autor(publicacion)
