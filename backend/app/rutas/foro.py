"""Foro de consultas por asignatura."""

from __future__ import annotations

from typing import Any

from ..web import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import auditoria
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/foro", tags=["Foro"])


def _modera(persona: dict | None) -> bool:
    """Quien puede retirar lo que escribió otro.

    El foro es de los estudiantes y cada uno maneja lo suyo; sacar el mensaje
    de otra persona es moderar, y eso es de la administración.
    """
    return d.tiene_rol(persona, "Administrador", "Supervisor")


def _autor_de(id_persona: int) -> dict | None:
    """Quién escribió. Sale de `datos.resumen_de_persona`, que trae también
    la foto: antes esta ficha la armaba el foro por su cuenta y sin la cara."""
    return d.resumen_de_persona(id_persona)


def _curso_de(id_curso: Any) -> dict | None:
    curso = d.buscar_curso(id_curso)
    return (
        {
            "id": curso["id"],
            "nombre": curso["nombre"],
            "codigo": curso["codigo"],
            "color": curso["color"],
        }
        if curso
        else None
    )


def _con_votos(mensaje: dict, yo: dict) -> dict:
    """Los votos salen contados, nunca con la lista de quiénes fueron: igual
    que las reacciones de Novedades."""
    votos = mensaje.get("votos") or []
    resto = {k: v for k, v in mensaje.items() if k != "votos"}
    return {**resto, "utiles": len(votos), "loVote": yo["id"] in votos}


def _resumir(tema: dict, yo: dict) -> dict:
    """En la lista no hacen falta los mensajes, solo cuántos hay y cuándo fue
    el último.

    Lleva `puedeRetirar` para que la moderación se pueda hacer desde la lista:
    entrar a cada tema para sacarlo es una vuelta de más cuando hay varios.
    """
    mensajes = tema["mensajes"]
    ultimo = mensajes[-1] if mensajes else None
    return {
        "id": tema["id"],
        "titulo": tema["titulo"],
        "curso": _curso_de(tema["cursoId"]),
        "autor": _autor_de(tema["autorId"]),
        "fecha": tema["fecha"],
        "respuestas": max(len(mensajes) - 1, 0),
        "ultimaActividad": ultimo["fecha"] if ultimo else tema["fecha"],
        "ultimoAutor": _autor_de(ultimo["autorId"]) if ultimo else None,
        "puedeRetirar": tema["autorId"] == yo["id"] or _modera(yo),
        "retiroExigeMotivo": tema["autorId"] != yo["id"],
    }


def _detalle_de(tema: dict, yo: dict) -> dict:
    siguen = tema.get("siguen") or []
    return {
        "id": tema["id"],
        "titulo": tema["titulo"],
        "curso": _curso_de(tema["cursoId"]),
        "autor": _autor_de(tema["autorId"]),
        "fecha": tema["fecha"],
        "siguiendo": yo["id"] in siguen,
        "seguidores": len(siguen),
        "mensajes": [
            {
                **_con_votos(m, yo),
                "autor": _autor_de(m["autorId"]),
                "puedeRetirar": m["autorId"] == yo["id"] or _modera(yo),
                "retiroExigeMotivo": m["autorId"] != yo["id"],
            }
            for m in tema["mensajes"]
        ],
        "puedeRetirar": tema["autorId"] == yo["id"] or _modera(yo),
        "retiroExigeMotivo": tema["autorId"] != yo["id"],
    }


def _buscar_tema(id_tema: int) -> dict:
    tema = next((t for t in d.temas_foro if t["id"] == id_tema), None)
    if not tema:
        raise HTTPException(404, "Tema no encontrado")
    return tema


@router.get("", summary="Los temas y las asignaturas que tienen alguno")
def listar_temas(yo: dict = UsuarioActual):
    temas = sorted(
        (_resumir(t, yo) for t in d.temas_foro),
        key=lambda t: d.desde_iso(t["ultimaActividad"]),
        reverse=True,
    )

    asignaturas = []
    for curso in d.cursos:
        cuantos = sum(1 for t in temas if t["curso"] and t["curso"]["id"] == curso["id"])
        if cuantos > 0:
            asignaturas.append({**_curso_de(curso["id"]), "temas": cuantos})

    return {"temas": temas, "asignaturas": asignaturas}


@router.post("", status_code=201, summary="Abrir un tema")
def crear_tema(cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual):
    curso = _curso_de(cuerpo.get("cursoId"))
    titulo = str(cuerpo.get("titulo") or "").strip()
    texto = str(cuerpo.get("texto") or "").strip()

    if not curso:
        raise HTTPException(400, "Hay que elegir una asignatura")
    if not titulo or not texto:
        raise HTTPException(400, "El tema necesita un título y una consulta")

    ahora = d.iso(d.ahora())
    tema = {
        "id": d.nuevo_id_tema(),
        "cursoId": curso["id"],
        "titulo": titulo,
        "autorId": yo["id"],
        "fecha": ahora,
        "siguen": [yo["id"]],
        "mensajes": [
            {
                "id": d.nuevo_id_mensaje_foro(),
                "autorId": yo["id"],
                "texto": texto,
                "fecha": ahora,
                "votos": [],
            }
        ],
    }
    d.temas_foro.append(tema)

    return _resumir(tema, yo)


@router.get("/{id_tema}", summary="Abrir un tema con sus respuestas")
def obtener_tema(id_tema: int, yo: dict = UsuarioActual):
    return _detalle_de(_buscar_tema(id_tema), yo)


@router.post("/{id_tema}", status_code=201, summary="Responder un tema")
def responder(
    id_tema: int, cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual
):
    tema = _buscar_tema(id_tema)

    texto = str(cuerpo.get("texto") or "").strip()
    if not texto:
        raise HTTPException(400, "La respuesta no puede estar vacía")

    mensaje = {
        "id": d.nuevo_id_mensaje_foro(),
        "autorId": yo["id"],
        "texto": texto,
        "fecha": d.iso(d.ahora()),
        "votos": [],
    }
    tema["mensajes"].append(mensaje)

    return {**_con_votos(mensaje, yo), "autor": _autor_de(yo["id"])}


@router.post("/{id_tema}/seguir", summary="Seguir el tema, o dejar de seguirlo")
def seguir(id_tema: int, yo: dict = UsuarioActual):
    """Por ahora solo se guarda: los avisos van a llegar cuando haya
    notificaciones de verdad."""
    tema = _buscar_tema(id_tema)

    siguen = tema.setdefault("siguen", [])
    tema["siguen"] = (
        [i for i in siguen if i != yo["id"]]
        if yo["id"] in siguen
        else [*siguen, yo["id"]]
    )

    return _detalle_de(tema, yo)


@router.post("/{id_tema}/mensajes/{id_mensaje}/voto", summary="Marcar una respuesta como útil")
def votar(id_tema: int, id_mensaje: int, yo: dict = UsuarioActual):
    """O sacar el voto, si ya estaba puesto."""
    tema = next((t for t in d.temas_foro if t["id"] == id_tema), None)
    mensaje = (
        next((m for m in tema["mensajes"] if m["id"] == id_mensaje), None) if tema else None
    )
    if not mensaje:
        raise HTTPException(404, "Mensaje no encontrado")

    votos = mensaje.setdefault("votos", [])
    mensaje["votos"] = (
        [i for i in votos if i != yo["id"]]
        if yo["id"] in votos
        else [*votos, yo["id"]]
    )

    return {**_con_votos(mensaje, yo), "autor": _autor_de(mensaje["autorId"])}


# ===================== Retirar =====================
# Dos rutas y no una: borrar un tema entero y borrar una respuesta no son lo
# mismo. El tema se lleva puesta la conversación de todos; la respuesta es de
# quien la escribió.
#
# En los dos casos, **retirar lo de otro exige un motivo**: a quien escribió
# le desaparece el texto y sin motivo no tiene forma de saber por qué ni con
# quién hablarlo.


def _exigir_retiro(autor_id: int, yo: dict, cuerpo: dict) -> tuple[bool, str]:
    """Comprueba quién retira y devuelve si es suyo y con qué motivo."""
    es_mio = autor_id == yo["id"]
    if not es_mio and not _modera(yo):
        raise HTTPException(
            403, "Solo quien lo escribió, o la administración, pueden retirarlo"
        )

    motivo = str(cuerpo.get("motivo") or "").strip()
    if not es_mio and not motivo:
        raise HTTPException(400, "Hay que indicar por qué se retira")
    if len(motivo) > 500:
        raise HTTPException(400, "El motivo es demasiado largo")
    return es_mio, motivo


@router.delete("/{id_tema}", summary="Retirar un tema entero")
def retirar_tema(
    id_tema: int, cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual
):
    """Se lleva el tema y todas sus respuestas.

    Es lo más pesado que se puede hacer en el foro —desaparece la
    conversación de varias personas—, así que el motivo se le avisa a quien lo
    abrió y queda en la auditoría.
    """
    tema = _buscar_tema(id_tema)
    es_mio, motivo = _exigir_retiro(tema["autorId"], yo, cuerpo)

    d.temas_foro.remove(tema)

    auditoria.registrar(
        yo,
        "baja",
        "modulos",
        elemento=tema["titulo"],
        elemento_id=tema["id"],
        elemento_tipo="temaForo",
        persona_id=tema["autorId"],
        antes={"respuestas": len(tema.get("mensajes", [])) - 1},
        detalle=motivo or "Retiró su propio tema",
    )

    if not es_mio:
        d.avisar_por_mensaje(
            yo["id"],
            tema["autorId"],
            f'Se retiró del foro tu consulta "{tema["titulo"]}". Motivo: {motivo}',
        )

    return {"retirado": tema["id"]}


@router.delete("/{id_tema}/mensajes/{id_mensaje}", summary="Retirar una respuesta")
def retirar_respuesta(
    id_tema: int,
    id_mensaje: int,
    cuerpo: dict[str, Any] = Body(default={}),
    yo: dict = UsuarioActual,
):
    """Saca una respuesta suelta.

    La primera no se puede: esa **es** la consulta que abre el tema, y sin
    ella el resto de las respuestas quedan contestando a nada. Para eso está
    retirar el tema entero.
    """
    tema = _buscar_tema(id_tema)
    mensajes = tema.get("mensajes") or []

    mensaje = next((m for m in mensajes if m["id"] == id_mensaje), None)
    if not mensaje:
        raise HTTPException(404, "Esa respuesta no existe")
    if mensajes and mensajes[0]["id"] == id_mensaje:
        raise HTTPException(
            409,
            "Esa es la consulta que abre el tema: para sacarla hay que retirar el tema entero",
        )

    es_mio, motivo = _exigir_retiro(mensaje["autorId"], yo, cuerpo)
    mensajes.remove(mensaje)

    auditoria.registrar(
        yo,
        "baja",
        "modulos",
        elemento=f"Respuesta en «{tema['titulo']}»",
        elemento_id=mensaje["id"],
        elemento_tipo="respuestaForo",
        persona_id=mensaje["autorId"],
        antes={"texto": mensaje["texto"][:200]},
        detalle=motivo or "Retiró su propia respuesta",
    )

    if not es_mio:
        d.avisar_por_mensaje(
            yo["id"],
            mensaje["autorId"],
            f'Se retiró tu respuesta en la consulta "{tema["titulo"]}". Motivo: {motivo}',
        )

    return _detalle_de(tema, yo)
