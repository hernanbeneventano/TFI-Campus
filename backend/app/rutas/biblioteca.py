"""Biblioteca: catálogo propio, consulta de catálogos externos, aportes,
moderación y archivos."""

from __future__ import annotations

import base64
import os
import re
import time
import unicodedata
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Body, HTTPException, Request, Response

from .. import datos as d
from ..servicios.libros_externos import buscar_libros_externos, obtener_libro_externo

router = APIRouter(prefix="/api/biblioteca", tags=["Biblioteca"])

# Mientras no haya login, el que consulta y aporta es siempre el usuario de
# prueba, igual que en el resto de las rutas.
YO = d.usuario_actual["id"]


# ===================== Permisos =====================
def _puede_moderar(persona_id: int) -> bool:
    """La facultad todavía no tiene un rol de administrador: en `personas`
    solo hay Estudiante y Docente. Hasta que exista, **modera el docente**,
    que es quien responde por el material de su cátedra. El día que se agregue
    el rol, alcanza con cambiar esta función.
    """
    persona = d.buscar_persona(persona_id)
    return bool(persona and persona["rol"] == "Docente")


def _puede_aportar(persona_id: int) -> bool:
    """Subir material lo puede hacer cualquiera: los aportes de estudiantes no
    se publican solos, quedan esperando moderación."""
    return d.buscar_persona(persona_id) is not None


def _puede_ver(material: dict, persona_id: int) -> bool:
    """Un material pendiente o rechazado lo ven quien lo subió y los docentes;
    nadie más. Así un aporte sin revisar no aparece en el catálogo."""
    if material["estado"] == "aprobado":
        return True
    return material["subidoPor"] == persona_id or _puede_moderar(persona_id)


def _puede_editar(material: dict, persona_id: int) -> bool:
    return material["subidoPor"] == persona_id or _puede_moderar(persona_id)


# ===================== Límite de pedidos =====================
# Freno simple contra el abuso de la búsqueda externa y de la subida. En
# memoria y por persona, que es lo que se puede hacer sin login ni Redis.
_golpes: dict[str, list[float]] = {}


def _dentro_del_limite(clave: str, cuantos: int, ventana: float) -> bool:
    ahora = time.time()
    previos = [t for t in _golpes.get(clave, []) if ahora - t < ventana]
    if len(previos) >= cuantos:
        _golpes[clave] = previos
        return False
    previos.append(ahora)
    _golpes[clave] = previos
    return True


# ===================== Presentación =====================
def _nombre_categoria(id_categoria: str) -> str:
    return next(
        (c["nombre"] for c in d.categorias if c["id"] == id_categoria), "Otros materiales"
    )


def _con_datos(material: dict, persona_id: int = YO) -> dict:
    quien = d.buscar_persona(material["subidoPor"])
    es_favorito = any(
        f["personaId"] == persona_id and str(f["materialId"]) == str(material["id"])
        for f in d.favoritos_biblioteca
    )
    archivo = material.get("archivo")

    return {
        **material,
        # El archivo se describe, pero sus bytes nunca viajan en el listado:
        # se piden aparte, con el control de acceso puesto.
        "archivo": (
            {"nombre": archivo["nombre"], "tamano": archivo["tamano"], "tipo": archivo["tipo"]}
            if archivo
            else None
        ),
        "tieneArchivo": bool(archivo),
        "externo": False,
        "fuente": "campus",
        "nombreFuente": material.get("editorial") or "Biblioteca del campus",
        "nombreCategoria": _nombre_categoria(material["categoria"]),
        "subidoPorNombre": quien["nombre"] if quien else "Alguien del campus",
        "favorito": es_favorito,
        "puedeEditar": _puede_editar(material, persona_id),
        "puedeModerar": _puede_moderar(persona_id),
    }


# ===================== Búsqueda en la biblioteca propia =====================
def _sin_tildes(texto: Any) -> str:
    sin = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in sin if unicodedata.category(c) != "Mn").lower()


def _coincide(material: dict, texto: str, campo: str) -> bool:
    if not texto:
        return True
    buscado = _sin_tildes(texto)

    donde = {
        "titulo": [material.get("titulo")],
        "autor": [material.get("autor")],
        "isbn": [material.get("isbn")],
        "tema": [
            material.get("materia"),
            _nombre_categoria(material["categoria"]),
            material.get("descripcion"),
        ],
    }.get(
        campo,
        [
            material.get("titulo"),
            material.get("autor"),
            material.get("isbn"),
            material.get("descripcion"),
            material.get("materia"),
            material.get("carrera"),
            material.get("editorial"),
            _nombre_categoria(material["categoria"]),
        ],
    )

    return any(buscado in _sin_tildes(valor) for valor in donde)


def _ordenar(lista: list[dict], orden: str) -> list[dict]:
    if orden == "titulo":
        return sorted(lista, key=lambda m: m["titulo"].lower())
    if orden == "autor":
        return sorted(lista, key=lambda m: (m.get("autor") or "").lower())
    # Por defecto, lo más nuevo arriba
    return sorted(lista, key=lambda m: d.desde_iso(m["creado"]), reverse=True)


def _filtrar_propios(p: dict, persona_id: int) -> list[dict]:
    estado = p.get("estado") or ""
    texto = (p.get("q") or "").strip()
    campo = p.get("campo") or "todo"

    resultado = []
    for m in d.materiales:
        if not _puede_ver(m, persona_id):
            continue
        # Sin filtro de estado, el catálogo muestra solo lo aprobado: los
        # propios pendientes se consultan desde "Mis aportes".
        if (m["estado"] != estado) if estado else (m["estado"] != "aprobado"):
            continue
        if p.get("categoria") and m["categoria"] != p["categoria"]:
            continue
        if p.get("tipo") and m["tipo"] != p["tipo"]:
            continue
        if p.get("carrera") and m["carrera"] != p["carrera"]:
            continue
        if p.get("materia") and m["materia"] != p["materia"]:
            continue
        if p.get("idioma") and m["idioma"] != p["idioma"]:
            continue
        if not _coincide(m, texto, campo):
            continue
        resultado.append(m)

    return _ordenar(resultado, p.get("orden") or "fecha")


def _paginar(lista: list[dict], p: dict) -> dict:
    try:
        pagina = max(1, int(p.get("pagina") or 1))
    except ValueError:
        pagina = 1
    try:
        por_pagina = min(48, max(1, int(p.get("porPagina") or 12)))
    except ValueError:
        por_pagina = 12

    desde = (pagina - 1) * por_pagina
    paginas = max(1, -(-len(lista) // por_pagina))
    return {
        "pagina": pagina,
        "porPagina": por_pagina,
        "total": len(lista),
        "paginas": paginas,
        "recortada": lista[desde : desde + por_pagina],
    }


# ===================== Rutas con nombre fijo =====================
# Van antes que /{id}; si no, "favoritos" se tomaría como el id de un material
# (mismo cuidado que en mensajes).


@router.get("/opciones", summary="Datos para armar los filtros de la pantalla")
def opciones_biblioteca():
    visibles = [m for m in d.materiales if m["estado"] == "aprobado"]

    materias = sorted(
        {c["nombre"] for c in d.cursos} | {m["materia"] for m in d.materiales if m.get("materia")},
        key=str.lower,
    )

    return {
        "categorias": [
            {**c, "cuantos": sum(1 for m in visibles if m["categoria"] == c["id"])}
            for c in d.categorias
        ],
        "carreras": d.carreras,
        # Las materias salen de los cursos del campus más las que ya tengan
        # los materiales, para que el filtro no se quede corto.
        "materias": materias,
        "tipos": d.TIPOS_MATERIAL,
        "idiomas": sorted({m["idioma"] for m in visibles if m.get("idioma")}),
        "total": len(visibles),
        "puedeAportar": _puede_aportar(YO),
        "puedeModerar": _puede_moderar(YO),
        "pendientes": (
            sum(1 for m in d.materiales if m["estado"] == "pendiente")
            if _puede_moderar(YO)
            else 0
        ),
    }


@router.get("/mis-aportes", summary="Los aportes propios, con estado e historial")
def mis_aportes():
    mios = [m for m in d.materiales if m["subidoPor"] == YO]
    return {
        "materiales": [
            {
                **_con_datos(m),
                "historial": [
                    {
                        **h,
                        "moderador": (
                            p["nombre"] if (p := d.buscar_persona(h["moderadorId"])) else None
                        ),
                    }
                    for h in d.moderacion_biblioteca
                    if h["materialId"] == m["id"]
                ],
            }
            for m in _ordenar(mios, "fecha")
        ]
    }


@router.get("/pendientes", summary="La cola de moderación")
def pendientes():
    """Solo para quien modera."""
    if not _puede_moderar(YO):
        raise HTTPException(403, "Solo los docentes pueden revisar los aportes")
    cola = [m for m in d.materiales if m["estado"] == "pendiente"]
    return {"materiales": [_con_datos(m) for m in _ordenar(cola, "fecha")]}


@router.get("/favoritos", summary="Materiales guardados")
def obtener_favoritos():
    mios = [f for f in d.favoritos_biblioteca if f["personaId"] == YO]

    # Los favoritos pueden ser propios o externos: los propios se resuelven
    # acá y de los externos se devuelve el identificador, que la pantalla usa
    # para volver a pedirlos si hace falta.
    propios = []
    for f in mios:
        m = next((m for m in d.materiales if str(m["id"]) == str(f["materialId"])), None)
        if m and _puede_ver(m, YO):
            propios.append(_con_datos(m))

    externos = [
        {"id": f["materialId"], "creado": f["creado"]}
        for f in mios
        if ":" in str(f["materialId"])
    ]

    return {"materiales": propios, "externos": externos}


# ===================== Catálogo =====================
@router.get("", summary="Buscar en el catálogo propio y en los externos")
async def listar_materiales(request: Request):
    p = dict(request.query_params)
    fuente = p.get("fuente") or "todo"
    texto = (p.get("q") or "").strip()

    propios = [] if fuente == "externos" else _filtrar_propios(p, YO)
    paginacion = _paginar(propios, p)
    recortada = paginacion.pop("recortada")

    respuesta: dict[str, Any] = {
        "materiales": [_con_datos(m) for m in recortada],
        **paginacion,
        "externos": [],
        "fuentes": [],
    }

    # Los catálogos externos solo se consultan si hay algo que buscar: no
    # tiene sentido pedirles "todo", y además cuentan contra el límite.
    if fuente != "campus" and len(texto) >= 2:
        if not _dentro_del_limite(f"buscar:{YO}", 30, 60):
            respuesta["fuentes"] = [{"estado": "limite", "nombre": "Catálogos externos"}]
            return respuesta

        try:
            resultado = await buscar_libros_externos(
                texto, p.get("campo") or "todo", p.get("idioma") or None
            )
            # Marcar los que ya están en favoritos, igual que los propios
            respuesta["externos"] = [
                {
                    **l,
                    "favorito": any(
                        f["personaId"] == YO and str(f["materialId"]) == str(l["id"])
                        for f in d.favoritos_biblioteca
                    ),
                }
                for l in resultado["libros"]
            ]
            respuesta["fuentes"] = resultado["fuentes"]
        except Exception as e:
            # Que se caigan las dos interfaces no puede dejar sin biblioteca
            # al campus
            respuesta["fuentes"] = [
                {"estado": "error", "nombre": "Catálogos externos", "error": str(e)}
            ]

    return respuesta


@router.post("", status_code=201, summary="Aportar material")
def crear_material(cuerpo: dict[str, Any] = Body(default={})):
    if not _puede_aportar(YO):
        raise HTTPException(403, "No tenés permiso para aportar material")
    if not _dentro_del_limite(f"aportar:{YO}", 10, 60 * 60):
        raise HTTPException(429, "Demasiados aportes seguidos. Probá de nuevo en un rato.")

    campos = _leer_campos(cuerpo)
    problema = _validar(campos, cuerpo, exigir_autorizacion=True)
    if problema:
        raise HTTPException(400, problema)

    # Quien modera publica directo; el resto espera revisión
    estado = "aprobado" if _puede_moderar(YO) else "pendiente"
    quien = d.buscar_persona(YO)
    ahora = d.iso(d.ahora())

    material = {
        "id": d.nuevo_id_material(),
        **campos,
        "isbn": campos["isbn"] or None,
        "editorial": campos["editorial"] or None,
        "enlace": campos["enlace"] or None,
        "portada": campos["portada"] or None,
        "licencia": campos["licencia"] or None,
        "anio": campos["anio"] or None,
        "descripcion": campos["descripcion"] or None,
        "autor": campos["autor"] or (quien["nombre"] if quien else None),
        "archivo": None,
        "subidoPor": YO,
        "estado": estado,
        "moderadoPor": YO if estado == "aprobado" else None,
        "motivo": None,
        "creado": ahora,
        "actualizado": ahora,
    }
    d.materiales.append(material)

    if estado == "aprobado":
        d.moderacion_biblioteca.append(
            {
                "id": d.nuevo_id_moderacion(),
                "materialId": material["id"],
                "moderadorId": YO,
                "accion": "aprobado",
                "motivo": "Publicado por quien modera",
                "fecha": ahora,
            }
        )

    return _con_datos(material)


# ===================== Validación de la ficha =====================
def _leer_campos(cuerpo: dict) -> dict:
    texto = lambda v: str(v if v is not None else "").strip()  # noqa: E731
    return {
        "titulo": texto(cuerpo.get("titulo")),
        "autor": texto(cuerpo.get("autor")),
        "descripcion": texto(cuerpo.get("descripcion")),
        "tipo": texto(cuerpo.get("tipo")) or "otro",
        "carrera": texto(cuerpo.get("carrera")),
        "materia": texto(cuerpo.get("materia")),
        "anio": texto(cuerpo.get("anio")),
        "idioma": texto(cuerpo.get("idioma")) or "es",
        "isbn": texto(cuerpo.get("isbn")),
        "categoria": texto(cuerpo.get("categoria")) or "otros",
        "editorial": texto(cuerpo.get("editorial")),
        "enlace": texto(cuerpo.get("enlace")),
        "licencia": texto(cuerpo.get("licencia")),
        "portada": texto(cuerpo.get("portada")),
    }


def _validar(campos: dict, cuerpo: dict, *, exigir_autorizacion: bool) -> str | None:
    if not campos["titulo"]:
        return "El material necesita un título"
    if len(campos["titulo"]) > 200:
        return "El título es demasiado largo"
    if campos["tipo"] not in d.TIPOS_MATERIAL:
        return "Ese tipo de material no existe"
    if not any(c["id"] == campos["categoria"] for c in d.categorias):
        return "Esa categoría no existe"
    if campos["isbn"] and not re.fullmatch(r"[0-9Xx-]{10,17}", campos["isbn"]):
        return "Ese ISBN no parece válido"

    # Solo http(s): un enlace "javascript:" en la ficha sería un agujero
    for nombre, valor in (("enlace", campos["enlace"]), ("portada", campos["portada"])):
        if not valor:
            continue
        partes = urlparse(valor)
        if partes.scheme not in ("http", "https"):
            return f"El {nombre} tiene que ser una dirección http o https"
        if not partes.netloc:
            return f"El {nombre} no es una dirección válida"

    # Compartir material ajeno sin permiso es el riesgo principal de todo esto
    if exigir_autorizacion and cuerpo.get("autorizado") is not True:
        return "Hay que confirmar que tenés autorización para compartir el material"
    return None


# ===================== El archivo =====================
# Tamaño máximo, configurable. Lo que llega es base64, que ocupa un tercio más
# que el archivo original: el límite se compara contra los bytes reales.
MAX_MB = int(os.environ.get("BIBLIOTECA_MAX_MB") or 15)
MAX_BYTES = MAX_MB * 1024 * 1024


def _es_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-"


def _es_epub(b: bytes) -> bool:
    # Un EPUB es un ZIP: tiene que empezar con PK y declarar su mimetype
    return b[:2] == b"PK" and b"application/epub+zip" in b[:200]


# Solo formatos de lectura. Nada de ejecutables ni de cosas que el navegador
# pueda correr: ni .exe, ni .js, ni .html, ni .svg.
FORMATOS = {
    "pdf": {"mime": "application/pdf", "firma": _es_pdf},
    "epub": {"mime": "application/epub+zip", "firma": _es_epub},
}


def _nombre_seguro(nombre: Any, extension: str) -> str:
    """El nombre que mande el navegador no se usa tal cual: podría traer una
    ruta ("../../algo") o caracteres que rompan la cabecera de la descarga."""
    base = str(nombre if nombre is not None else "material")
    base = re.split(r"[\\/]", base)[-1]
    base = re.sub(r"\.[^.]*$", "", base)
    base = unicodedata.normalize("NFD", base)
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    base = re.sub(r"[^a-zA-Z0-9 _-]", "", base).strip()[:80]
    return f"{base or 'material'}.{extension}"


def _buscar_material(id_material: str) -> dict:
    try:
        buscado = int(id_material)
    except (TypeError, ValueError):
        raise HTTPException(404, "Material no encontrado")
    material = next((m for m in d.materiales if m["id"] == buscado), None)
    if not material:
        raise HTTPException(404, "Material no encontrado")
    return material


@router.post("/{id_material:path}/archivo", status_code=201, summary="Subir el archivo")
def subir_archivo(id_material: str, cuerpo: dict[str, Any] = Body(default={})):
    material = _buscar_material(id_material)
    if not _puede_editar(material, YO):
        raise HTTPException(403, "Solo quien lo subió puede cambiar el archivo")
    if not _dentro_del_limite(f"subir:{YO}", 20, 60 * 60):
        raise HTTPException(429, "Demasiadas subidas seguidas. Probá de nuevo en un rato.")

    extension = str(cuerpo.get("extension") or "").lower().lstrip(".")
    formato = FORMATOS.get(extension)
    if not formato:
        aceptados = " y ".join(e.upper() for e in FORMATOS)
        raise HTTPException(415, f"Solo se aceptan archivos {aceptados}")

    # El tipo que declara el navegador tiene que coincidir con la extensión…
    declarado = str(cuerpo.get("tipo") or "")
    if declarado and declarado != formato["mime"]:
        raise HTTPException(415, "El tipo del archivo no coincide con su extensión")

    try:
        bytes_archivo = base64.b64decode(str(cuerpo.get("contenido") or ""), validate=False)
    except Exception:
        raise HTTPException(400, "No se pudo leer el archivo")

    if len(bytes_archivo) == 0:
        raise HTTPException(400, "El archivo está vacío")
    if len(bytes_archivo) > MAX_BYTES:
        raise HTTPException(413, f"El archivo supera los {MAX_MB} MB")
    # …y el contenido real tiene que ser lo que dice ser. La extensión sola no
    # prueba nada: cualquiera renombra un .exe a .pdf.
    if not formato["firma"](bytes_archivo):
        raise HTTPException(415, f"El archivo no es un {extension.upper()} válido")

    d.guardar_archivo(material["id"], bytes_archivo)
    material["archivo"] = {
        "nombre": _nombre_seguro(cuerpo.get("nombre"), extension),
        "tamano": len(bytes_archivo),
        "tipo": formato["mime"],
    }
    # Si el archivo está alojado acá, el enlace externo sobra
    material["enlace"] = None
    material["actualizado"] = d.iso(d.ahora())

    return _con_datos(material)


@router.get("/{id_material:path}/archivo", summary="Descargar el archivo")
def descargar_archivo(id_material: str):
    """Pasa por el control de acceso: un pendiente no se baja aunque alguien
    adivine el id."""
    material = _buscar_material(id_material)
    if not _puede_ver(material, YO):
        raise HTTPException(403, "Ese material todavía no está disponible")

    contenido = d.leer_archivo(material["id"])
    if not contenido or not material.get("archivo"):
        raise HTTPException(404, "Este material no tiene un archivo alojado en el campus")

    return Response(
        content=contenido,
        media_type=material["archivo"]["tipo"],
        headers={
            # Siempre como descarga y sin dejar que el navegador adivine el
            # tipo: un archivo de otra persona no se abre dentro del campus.
            "Content-Disposition": f'attachment; filename="{material["archivo"]["nombre"]}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ===================== Moderación =====================
def _moderar(id_material: str, accion: str, motivo: str) -> dict:
    if not _puede_moderar(YO):
        raise HTTPException(403, "Solo los docentes pueden moderar la biblioteca")

    material = _buscar_material(id_material)

    # Rechazar sin decir por qué no le sirve a nadie: quien aportó no sabe qué
    # corregir.
    if accion == "rechazado" and not motivo:
        raise HTTPException(400, "Hay que indicar el motivo del rechazo")

    ahora = d.iso(d.ahora())
    material["estado"] = accion
    material["moderadoPor"] = YO
    material["motivo"] = motivo or None
    material["actualizado"] = ahora

    d.moderacion_biblioteca.append(
        {
            "id": d.nuevo_id_moderacion(),
            "materialId": material["id"],
            "moderadorId": YO,
            "accion": accion,
            "motivo": motivo or None,
            "fecha": ahora,
        }
    )

    return _con_datos(material)


@router.post("/{id_material:path}/aprobar", summary="Aprobar un aporte")
def aprobar_material(id_material: str):
    return _moderar(id_material, "aprobado", "")


@router.post("/{id_material:path}/rechazar", summary="Rechazar un aporte")
def rechazar_material(id_material: str, cuerpo: dict[str, Any] = Body(default={})):
    return _moderar(id_material, "rechazado", str(cuerpo.get("motivo") or "").strip())


# ===================== Favoritos =====================
@router.post("/{id_material:path}/favorito", status_code=201, summary="Guardar en favoritos")
def agregar_favorito(id_material: str):
    """Vale tanto para un material propio como para un libro externo: el id
    externo ("google:xxx") es estable y se guarda tal cual."""
    es_externo = ":" in id_material

    if not es_externo:
        material = _buscar_material(id_material)
        if not _puede_ver(material, YO):
            raise HTTPException(403, "Ese material todavía no está disponible")

    clave: Any = id_material if es_externo else int(id_material)
    ya_esta = any(
        f["personaId"] == YO and str(f["materialId"]) == str(clave)
        for f in d.favoritos_biblioteca
    )
    if not ya_esta:
        d.favoritos_biblioteca.append(
            {"personaId": YO, "materialId": clave, "creado": d.iso(d.ahora())}
        )

    return {"id": clave, "favorito": True}


@router.delete("/{id_material:path}/favorito", summary="Quitar de favoritos")
def quitar_favorito(id_material: str):
    for i, f in enumerate(d.favoritos_biblioteca):
        if f["personaId"] == YO and str(f["materialId"]) == str(id_material):
            d.favoritos_biblioteca.pop(i)
            break
    return {"id": id_material, "favorito": False}


# ===================== Ficha, edición y baja =====================
# Van al final: su patrón admite barras y se comería a las rutas de arriba.
@router.get("/{id_material:path}", summary="Ficha de un material")
async def obtener_material(id_material: str):
    # Un id con dos puntos es de un catálogo externo ("google:xxx")
    if ":" in id_material:
        try:
            libro = await obtener_libro_externo(id_material)
        except Exception:
            libro = None
        if not libro:
            raise HTTPException(404, "No se encontró ese libro")
        return {
            **libro,
            "favorito": any(
                f["personaId"] == YO and str(f["materialId"]) == str(id_material)
                for f in d.favoritos_biblioteca
            ),
            "relacionados": [],
        }

    material = _buscar_material(id_material)
    if not _puede_ver(material, YO):
        raise HTTPException(403, "Ese material todavía no está disponible")

    # Material relacionado: de la misma materia o categoría, sin repetirse
    relacionados = [
        _con_datos(m)
        for m in d.materiales
        if m["id"] != material["id"]
        and m["estado"] == "aprobado"
        and (m["materia"] == material["materia"] or m["categoria"] == material["categoria"])
    ][:4]

    return {
        **_con_datos(material),
        "relacionados": relacionados,
        "historial": [
            {**h, "moderador": (p["nombre"] if (p := d.buscar_persona(h["moderadorId"])) else None)}
            for h in d.moderacion_biblioteca
            if h["materialId"] == material["id"]
        ],
    }


@router.patch("/{id_material:path}", summary="Editar un material")
def editar_material(id_material: str, cuerpo: dict[str, Any] = Body(default={})):
    material = _buscar_material(id_material)
    if not _puede_editar(material, YO):
        raise HTTPException(403, "Solo quien lo subió o un docente puede editarlo")

    campos = _leer_campos({**material, **cuerpo})
    problema = _validar(campos, cuerpo, exigir_autorizacion=False)
    if problema:
        raise HTTPException(400, problema)

    material.update(
        {
            **campos,
            "isbn": campos["isbn"] or None,
            "editorial": campos["editorial"] or None,
            "enlace": None if material.get("archivo") else (campos["enlace"] or None),
            "portada": campos["portada"] or None,
            "licencia": campos["licencia"] or None,
            "anio": campos["anio"] or None,
            "descripcion": campos["descripcion"] or None,
            "actualizado": d.iso(d.ahora()),
        }
    )

    # Si lo edita quien lo subió y no modera, vuelve a la cola: el texto que se
    # aprobó ya no es el que está.
    if not _puede_moderar(YO) and material["estado"] == "aprobado":
        material["estado"] = "pendiente"
        material["moderadoPor"] = None

    return _con_datos(material)


@router.delete("/{id_material:path}", summary="Retirar un material")
def borrar_material(id_material: str):
    material = _buscar_material(id_material)
    if not _puede_editar(material, YO):
        raise HTTPException(403, "Solo quien lo subió o un docente puede retirarlo")

    d.materiales.remove(material)
    d.borrar_archivo(material["id"])
    # Los favoritos que apuntaban ahí quedarían colgados
    d.favoritos_biblioteca[:] = [
        f for f in d.favoritos_biblioteca if str(f["materialId"]) != str(material["id"])
    ]

    return {"retirado": material["id"]}
