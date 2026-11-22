"""Muro de novedades institucionales, con reacciones anónimas."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import almacenamiento as alm
from ..servicios import archivos, auditoria, fotos
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/novedades", tags=["Novedades"])

# Las únicas reacciones posibles
REACCIONES = ["leido", "util", "dudas"]

# El ámbito es un texto libre: puede ser general ("Institucional",
# "Académico") o el nombre de una materia. La regla es **al revés** de lo que
# parece: solo se recorta cuando el ámbito nombra una materia de verdad.
#
# Importa que sea así: si se recortara todo lo que no es "Institucional", una
# novedad "Académico" no la vería nadie, porque ninguna materia se llama así.
INSTITUCIONAL = "Institucional"


def _puede_publicar(persona: dict | None) -> bool:
    """Solo los docentes publican y editan; los estudiantes leen."""
    return d.tiene_rol(persona, "Docente", "Supervisor", "Administrador")


def _modera(persona: dict | None) -> bool:
    """Quien puede retirar lo que publicó otro.

    Un docente maneja lo suyo; sacar la publicación de otra persona es
    moderar el muro de la facultad, y eso es de la administración.
    """
    return d.tiene_rol(persona, "Administrador", "Supervisor")


def _alcanza(publicacion: dict, persona: dict) -> bool:
    """Si esa novedad es para esta persona.

    Lo general lo ve **todo el mundo**, inscripto o no: es justamente lo que
    tiene sentido mostrarle a alguien recién dado de alta, mientras la
    secretaría lo inscribe. Lo de una materia, solo quien la tiene.

    Quien publica ve siempre lo suyo, aunque haya dejado de dar esa materia.
    """
    ambito = (publicacion.get("ambito") or INSTITUCIONAL).strip().lower()

    # Si no nombra una materia del campus, es un ámbito general y va para
    # todos. Un ámbito que no existe no puede dejar la novedad sin lectores.
    materias = {c["nombre"].strip().lower() for c in d.cursos}
    if ambito not in materias:
        return True

    if publicacion["autorId"] == persona["id"]:
        return True

    suyas = {c["nombre"].strip().lower() for c in d.cursos if _es_suyo(c, persona)}
    return ambito in suyas


def _es_suyo(curso: dict, persona: dict) -> bool:
    if curso.get("docenteId") == persona["id"]:
        return True
    return any(p["id"] == persona["id"] for p in d.participantes_de_curso(curso))


def _resumir_reacciones(publicacion: dict, yo: dict) -> dict:
    """Las reacciones salen contadas, nunca con la lista de quiénes
    reaccionaron: el que lee ve cuántos fueron y cuál puso él, y nada más."""
    reacciones = publicacion.get("reacciones") or {}
    cuenta = {tipo: len(reacciones.get(tipo, [])) for tipo in REACCIONES}
    mia = next(
        (tipo for tipo in REACCIONES if yo["id"] in reacciones.get(tipo, [])), None
    )
    return {"cuenta": cuenta, "miReaccion": mia}


def _buscar(id_publicacion: int) -> dict:
    """La novedad, o un 404. Tres rutas la buscaban con la misma línea."""
    publicacion = next((p for p in d.publicaciones if p['id'] == id_publicacion), None)
    if not publicacion:
        raise HTTPException(404, 'Novedad no encontrada')
    return publicacion


def _con_autor(publicacion: dict, yo: dict) -> dict:
    autor = d.buscar_persona(publicacion["autorId"])
    sin_quienes = {k: v for k, v in publicacion.items() if k != "reacciones"}

    # La dirección de la imagen se arma al leer, nunca se guarda: va firmada,
    # y una firma guardada se vuelve inválida apenas cambia el secreto o la
    # forma de la ruta —y entonces la portada que ve todo el campus queda
    # rota—. Lo que se guarda es la clave del objeto, que no cambia nunca.
    # Si no hay objeto, `imagen` es la dirección que escribió el docente.
    if publicacion.get("imagenObjeto"):
        sin_quienes["imagen"] = fotos.direccion_de_archivo(publicacion["imagenObjeto"])

    return {
        **sin_quienes,
        **_resumir_reacciones(publicacion, yo),
        # Con su foto: ver `datos.resumen_de_persona`
        "autor": d.resumen_de_persona(autor["id"]) if autor else None,
        # Para que el frontend sepa si mostrarle el botón de editar
        "puedeEditar": _puede_publicar(yo) and publicacion["autorId"] == yo["id"],
        # Retirar: la propia siempre; la de otro, solo quien modera
        "puedeRetirar": publicacion["autorId"] == yo["id"] or _modera(yo),
        "retiroExigeMotivo": publicacion["autorId"] != yo["id"],
    }


def _anclar_solo(id_publicacion: int) -> None:
    """Solo puede haber una destacada a la vez."""
    for p in d.publicaciones:
        p["anclada"] = p["id"] == id_publicacion


@router.get("", summary="Listar las publicaciones del muro")
def listar_publicaciones(yo: dict = UsuarioActual):
    """La anclada va siempre primera; el resto, de la más nueva a la más vieja.

    Se devuelven solo las que le llegan a quien pregunta: lo de la facultad
    siempre, lo de una materia solo si la tiene.
    """
    suyas = [p for p in d.publicaciones if _alcanza(p, yo)]
    ordenadas = sorted(
        suyas,
        key=lambda p: (bool(p.get("anclada")), d.desde_iso(p["fecha"])),
        reverse=True,
    )
    return {
        "publicaciones": [_con_autor(p, yo) for p in ordenadas],
        "puedePublicar": _puede_publicar(yo),
    }


@router.post("", status_code=201, summary="Publicar una novedad")
def crear_publicacion(cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual):
    if not _puede_publicar(yo):
        raise HTTPException(403, "Solo los docentes pueden publicar novedades")

    titulo = str(cuerpo.get("titulo") or "").strip()
    texto = str(cuerpo.get("cuerpo") or "").strip()
    categoria = str(cuerpo.get("categoria") or "Académico").strip()
    ambito = str(cuerpo.get("ambito") or "Institucional").strip()
    # La imagen se sube aparte, con `POST /:id/imagen`: al crear la novedad
    # todavía no hay id al que colgarla. Las de prueba del repositorio son
    # rutas a archivos propios, así que se siguen aceptando.
    imagen = str(cuerpo.get("imagen") or "").strip() or None

    if not titulo or not texto:
        raise HTTPException(400, "La novedad necesita un título y un texto")

    publicacion = {
        "id": d.nuevo_id_publicacion(),
        "autorId": yo["id"],
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
    id_publicacion: int, cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual
):
    publicacion = next((p for p in d.publicaciones if p["id"] == id_publicacion), None)
    if not publicacion:
        raise HTTPException(404, "Novedad no encontrada")
    if not _puede_publicar(yo) or publicacion["autorId"] != yo["id"]:
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


# ===================== La imagen de una novedad =====================
# Era una dirección escrita a mano: el docente tenía que subir el archivo en
# otro lado y pegar la ruta. Ahora se sube como todo lo demás, a Cloudflare R2.
IMAGEN_MAX_MB = archivos.IMAGENES_MAX_MB
FORMATOS_IMAGEN = {"png", "jpg", "jpeg"}


@router.post("/{id_publicacion}/imagen", summary="Subir la imagen de una novedad")
def subir_imagen(id_publicacion: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """La sube quien escribió la novedad.

    Solo PNG y JPG, **mirando los bytes**: un SVG es un documento con scripts
    adentro y esta imagen se muestra en la portada que ve todo el campus.
    """
    publicacion = _buscar(id_publicacion)
    if publicacion["autorId"] != yo["id"]:
        raise HTTPException(403, "Solo podés cambiar la imagen de tus propias novedades")

    contenido, ficha = archivos.leer_subida(
        cuerpo, permitidos=FORMATOS_IMAGEN, max_mb=IMAGEN_MAX_MB
    )

    objeto = alm.clave(alm.NOVEDADES, id_publicacion, nombre=ficha["nombre"])

    anterior = publicacion.get("imagenObjeto")
    if anterior and anterior != objeto:
        alm.olvidar(anterior)

    try:
        alm.subir(objeto, contenido, ficha["tipo"])
    except Exception as error:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo guardar la imagen: {error}")

    alm.registrar(
        objeto,
        nombre=ficha["nombre"],
        tipo=ficha["tipo"],
        tamano=ficha["tamano"],
        persona_id=yo["id"],
        modulo=alm.NOVEDADES,
        registro_id=id_publicacion,
    )

    publicacion["imagenObjeto"] = objeto
    publicacion["imagen"] = fotos.direccion_de_archivo(objeto)
    return _con_autor(publicacion, yo)


@router.delete("/{id_publicacion}/imagen", summary="Quitar la imagen de una novedad")
def quitar_imagen(id_publicacion: int, yo: dict = UsuarioActual):
    publicacion = _buscar(id_publicacion)
    if publicacion["autorId"] != yo["id"]:
        raise HTTPException(403, "Solo podés cambiar la imagen de tus propias novedades")

    if publicacion.get("imagenObjeto"):
        alm.olvidar(publicacion["imagenObjeto"])
    publicacion["imagenObjeto"] = None
    publicacion["imagen"] = None
    return _con_autor(publicacion, yo)


@router.post("/{id_publicacion}/reaccion", summary="Reaccionar, o quitar la reacción")
def reaccionar(
    id_publicacion: int, cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual
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

    ya_estaba = next(
        (t for t in REACCIONES if yo["id"] in reacciones.get(t, [])), None
    )
    for t in REACCIONES:
        reacciones[t] = [i for i in reacciones.get(t, []) if i != yo["id"]]

    # Tocar la que ya estaba puesta la saca
    if tipo and tipo != ya_estaba:
        reacciones[tipo].append(yo["id"])

    return _con_autor(publicacion, yo)


@router.delete("/{id_publicacion}", summary="Retirar una novedad")
def retirar_publicacion(
    id_publicacion: int, cuerpo: dict[str, Any] = Body(default={}), yo: dict = UsuarioActual
):
    """La saca del muro: su autor, o quien administra o supervisa.

    **Retirar la de otro exige un motivo** (400 si no viene). Sin eso, a quien
    publicó le desaparece el texto del muro y no tiene forma de saber por qué
    ni con quién hablarlo. El motivo le llega por Mensajes y queda en la
    auditoría.
    """
    publicacion = next((p for p in d.publicaciones if p["id"] == id_publicacion), None)
    if not publicacion:
        raise HTTPException(404, "Novedad no encontrada")

    es_mia = publicacion["autorId"] == yo["id"]
    if not es_mia and not _modera(yo):
        raise HTTPException(
            403, "Solo quien la publicó, o la administración, pueden retirarla"
        )

    motivo = str(cuerpo.get("motivo") or "").strip()
    if not es_mia and not motivo:
        raise HTTPException(400, "Hay que indicar por qué se retira la novedad")
    if len(motivo) > 500:
        raise HTTPException(400, "El motivo es demasiado largo")

    d.publicaciones.remove(publicacion)

    auditoria.registrar(
        yo,
        "baja",
        "modulos",
        elemento=publicacion["titulo"],
        elemento_id=publicacion["id"],
        elemento_tipo="novedad",
        persona_id=publicacion["autorId"],
        antes={"ambito": publicacion.get("ambito"), "titulo": publicacion["titulo"]},
        detalle=motivo or "Retiró su propia novedad",
    )

    # Que se entere quien la escribió, con el motivo
    if not es_mia:
        d.avisar_por_mensaje(
            yo["id"],
            publicacion["autorId"],
            f'Se retiró del muro tu novedad "{publicacion["titulo"]}". Motivo: {motivo}',
        )

    return {"retirada": publicacion["id"]}
