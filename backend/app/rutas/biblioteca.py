"""Biblioteca: el material de cada materia, los aportes y su revisión.

La biblioteca **no es un repositorio común a toda la institución**: es el
material de cada materia, y cada uno ve el de las materias que le tocan.

    materia ──< material >── quien lo subió
       │
       └── quién la cursa, quién la dicta  →  quién lo ve

De ahí salen las tres reglas que gobiernan todo el módulo:

- **Cada material pertenece a una materia del plan** (`materiaId`), siempre.
  Un material sin materia no tendría a quién mostrarse.
- **Lo que ve cada uno sale de su relación con esa materia**: el estudiante ve
  las que cursa, el docente las que dicta, y quien supervisa ve todo.
- **Modera el docente de esa materia**, no cualquier docente: el material de
  Base de Datos II lo aprueba quien da Base de Datos II. Supervisión y
  administración también, porque responden por todas.

El docente publica directo; el aporte de un estudiante espera revisión. Es la
diferencia entre material de cátedra y material aportado, y es lo que hace que
lo publicado esté revisado.

Los catálogos externos (Google Books, Open Library) siguen estando, pero son
otra cosa: ayudan a **encontrar** un libro y a completar su ficha, no viven en
la biblioteca ni dependen de una materia. Por eso solo aparecen cuando se los
busca a propósito.
"""

from __future__ import annotations

import base64
import os
import re
import time
import unicodedata
from typing import Any
from urllib.parse import urlparse

from app.errores import ErrorDeAPI
from campus_django.respuestas import descargar
from django.http import HttpRequest as Request

from .. import datos as d
from ..servicios import almacenamiento as alm
from ..servicios import ambito, auditoria
from ..servicios.libros_externos import buscar_libros_externos, obtener_libro_externo



# ===================== El alcance de cada uno =====================
# Todo lo que sigue se apoya en estas dos preguntas: qué materias puede ver
# esta persona y cuáles puede moderar. Están juntas a propósito: el día que la
# facultad delimite el ámbito del supervisor, se cambian acá y nada más.


def _supervisa(persona: dict) -> bool:
    """Quien responde por toda la institución, no por una cátedra."""
    return d.tiene_rol(persona, "Administrador", "Supervisor")


def _materias_visibles(persona: dict) -> list[dict]:
    """Las materias cuya biblioteca puede abrir esta persona.

    Estudiante: las que cursa. Docente: las que dicta. Las dos cosas si es las
    dos cosas, que pasa.

    Quien supervisa, **las de su ámbito**: todas si no se le puso ninguno —que
    es como venía—, y solo las de sus carreras si la facultad se lo recortó.
    Ver `servicios/ambito.py`.
    """
    if _supervisa(persona):
        return ambito.materias(persona)

    ids: set[int] = set()

    if d.tiene_rol(persona, "Docente"):
        ids |= {m["id"] for m in d.materias_que_dicta(persona["id"])}

    # Inscripto: la inscripción vigente o la cursada en marcha. Una materia ya
    # aprobada deja de estar "inscripta", así que su biblioteca se cierra: es
    # lo que pide que el material sea de la cursada y no del campus entero.
    ids |= {
        i["materiaId"] for i in d.inscripciones_materias if i["personaId"] == persona["id"]
    }
    ids |= {
        h["materiaId"]
        for h in d.historial_academico
        if h["personaId"] == persona["id"] and h.get("condicion") == "En curso"
    }

    return [m for m in d.materias_plan if m["id"] in ids]


def _ids_visibles(persona: dict) -> set[int]:
    return {m["id"] for m in _materias_visibles(persona)}


def _materias_que_modera(persona: dict) -> set[int] | None:
    """Las materias cuyos aportes puede aprobar. `None` quiere decir todas."""
    if _supervisa(persona):
        # Sin ámbito, todas; con ámbito, las de sus carreras. Moderar es
        # decidir qué se publica: tiene que llegar exactamente igual de lejos
        # que lo que se puede ver, o alguien aprueba material de una cátedra
        # que ni siquiera puede abrir.
        if not ambito.recortado(persona):
            return None
        return {m["id"] for m in ambito.materias(persona)}
    if d.tiene_rol(persona, "Docente"):
        return {m["id"] for m in d.materias_que_dicta(persona["id"])}
    return set()


def _modera(persona: dict, materia_id: Any) -> bool:
    """Si puede aprobar —y por lo tanto publicar directo— en esa materia."""
    cuales = _materias_que_modera(persona)
    return cuales is None or materia_id in cuales


def _modera_algo(persona: dict) -> bool:
    cuales = _materias_que_modera(persona)
    return cuales is None or bool(cuales)


# ===================== Permisos sobre un material =====================
def _puede_ver(material: dict, persona: dict) -> bool:
    """Dos candados, y hay que pasar los dos.

    El primero es la materia: el material de una materia que no cursás ni
    dictás no existe para vos. El segundo es el estado: un aporte sin revisar
    lo ven quien lo subió y quien tiene que revisarlo, nadie más.
    """
    if material["materiaId"] not in _ids_visibles(persona):
        return False
    if material["estado"] == "aprobado":
        return True
    return material["subidoPor"] == persona["id"] or _modera(persona, material["materiaId"])


def _puede_editar(material: dict, persona: dict) -> bool:
    return material["subidoPor"] == persona["id"] or _modera(persona, material["materiaId"])


def _exigir_ver(material: dict, persona: dict) -> None:
    """Un material fuera de alcance se niega como inexistente: decir "no tenés
    permiso" ya cuenta que existe y de qué materia es."""
    if not _puede_ver(material, persona):
        raise ErrorDeAPI(404, "Material no encontrado")


# ===================== Límite de pedidos =====================
# Freno simple contra el abuso de la búsqueda externa y de la subida. En
# memoria y por persona, que es lo que se puede hacer sin Redis.
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


def _materia_de(material: dict) -> dict | None:
    return d.buscar_en(d.materias_plan, material.get("materiaId"))


def _con_datos(material: dict, persona: dict) -> dict:
    quien = d.buscar_persona(material["subidoPor"])
    autorizo = d.buscar_persona(material.get("moderadoPor"))
    materia = _materia_de(material)
    archivo = material.get("archivo")

    es_favorito = any(
        f["personaId"] == persona["id"] and str(f["materialId"]) == str(material["id"])
        for f in d.favoritos_biblioteca
    )

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
        "materia": materia["nombre"] if materia else "Materia dada de baja",
        "codigoMateria": materia["codigo"] if materia else None,
        "cursoId": materia.get("cursoId") if materia else None,
        "subidoPorNombre": quien["nombre"] if quien else "Alguien del campus",
        "subidoPorRol": d.rol_principal(quien) if quien else None,
        # Quién lo autorizó: el pliego pide que quede registrado y a la vista,
        # no solo en el historial.
        "autorizadoPorNombre": autorizo["nombre"] if autorizo else None,
        "favorito": es_favorito,
        "puedeEditar": _puede_editar(material, persona),
        "puedeModerar": _modera(persona, material["materiaId"]),
    }


# ===================== Búsqueda dentro de la biblioteca =====================
def _sin_tildes(texto: Any) -> str:
    sin = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in sin if unicodedata.category(c) != "Mn").lower()


def _coincide(material: dict, texto: str, campo: str) -> bool:
    if not texto:
        return True
    buscado = _sin_tildes(texto)
    materia = _materia_de(material)
    nombre_materia = materia["nombre"] if materia else ""

    donde = {
        "titulo": [material.get("titulo")],
        "autor": [material.get("autor")],
        "isbn": [material.get("isbn")],
        "tema": [
            nombre_materia,
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
            nombre_materia,
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


def _filtrar(p: dict, persona: dict) -> list[dict]:
    estado = p.get("estado") or ""
    texto = (p.get("q") or "").strip()
    campo = p.get("campo") or "todo"
    visibles = _ids_visibles(persona)

    # Se pueden pedir una, varias o ninguna: sin ninguna, van todas las que
    # esta persona pueda ver.
    pedidas: set[int] = set()
    for trozo in (p.get("materiaIds") or p.get("materiaId") or "").split(","):
        try:
            pedidas.add(int(trozo))
        except (TypeError, ValueError):
            continue

    resultado = []
    for m in d.materiales:
        if m["materiaId"] not in visibles:
            continue
        if pedidas and m["materiaId"] not in pedidas:
            continue
        if not _puede_ver(m, persona):
            continue
        # Sin filtro de estado, la biblioteca muestra solo lo aprobado: los
        # propios pendientes se consultan desde "Mis aportes".
        if (m["estado"] != estado) if estado else (m["estado"] != "aprobado"):
            continue
        if p.get("categoria") and m["categoria"] != p["categoria"]:
            continue
        if p.get("tipo") and m["tipo"] != p["tipo"]:
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


def opciones_biblioteca(yo: dict ):
    materias = _materias_visibles(yo)
    ids = {m["id"] for m in materias}
    modera = _materias_que_modera(yo)

    visibles = [
        m for m in d.materiales if m["materiaId"] in ids and m["estado"] == "aprobado"
    ]
    pendientes = [
        m
        for m in d.materiales
        if m["estado"] == "pendiente" and (modera is None or m["materiaId"] in modera)
    ]

    return {
        # Cada materia con cuánto material tiene y en qué carácter entra la
        # persona: la pantalla arma la biblioteca de cada una con esto.
        "materias": [
            {
                "id": m["id"],
                "nombre": m["nombre"],
                "codigo": m["codigo"],
                "anio": m.get("anio"),
                "cursoId": m.get("cursoId"),
                "cuantos": sum(1 for x in visibles if x["materiaId"] == m["id"]),
                "pendientes": sum(1 for x in pendientes if x["materiaId"] == m["id"]),
                "dicto": d.dicta_materia(yo["id"], m["id"]),
                "modero": _modera(yo, m["id"]),
            }
            for m in sorted(materias, key=lambda m: (m.get("anio") or 0, m["nombre"].lower()))
        ],
        "categorias": [
            {**c, "cuantos": sum(1 for m in visibles if m["categoria"] == c["id"])}
            for c in d.categorias
        ],
        "tipos": d.TIPOS_MATERIAL,
        "idiomas": sorted({m["idioma"] for m in visibles if m.get("idioma")}),
        "total": len(visibles),
        # Aportar puede cualquiera que tenga al menos una materia; lo que
        # cambia es si se publica solo o espera revisión.
        # Quien supervisa ve el plan entero; la pantalla usa esto para no
        # llenarse de materias vacías que no son suyas.
        "superviso": _supervisa(yo),
        "puedeAportar": bool(materias),
        "publicaDirecto": _modera_algo(yo),
        "puedeModerar": _modera_algo(yo),
        "pendientes": len(pendientes) if _modera_algo(yo) else 0,
    }


def mis_aportes(yo: dict ):
    # Los propios se ven siempre, incluso si la cursada terminó: el estudiante
    # tiene que poder leer por qué le rechazaron algo.
    mios = [m for m in d.materiales if m["subidoPor"] == yo["id"]]
    return {
        "materiales": [
            {
                **_con_datos(m, yo),
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


def pendientes(yo: dict ):
    """La cola de revisión, recortada a las materias que modera quien pregunta.

    Un docente no revisa el material de una cátedra que no es la suya.
    """
    modera = _materias_que_modera(yo)
    if modera is not None and not modera:
        raise ErrorDeAPI(
            403, "Solo el docente de la materia o un supervisor revisan los aportes"
        )

    cola = [
        m
        for m in d.materiales
        if m["estado"] == "pendiente" and (modera is None or m["materiaId"] in modera)
    ]
    return {"materiales": [_con_datos(m, yo) for m in _ordenar(cola, "fecha")]}


def obtener_favoritos(yo: dict ):
    mios = [f for f in d.favoritos_biblioteca if f["personaId"] == yo["id"]]

    # Los favoritos pueden ser propios o externos: los propios se resuelven
    # acá —y si la materia ya no está a tu alcance, desaparecen— y de los
    # externos se devuelve el identificador.
    propios = []
    for f in mios:
        m = next((m for m in d.materiales if str(m["id"]) == str(f["materialId"])), None)
        if m and _puede_ver(m, yo):
            propios.append(_con_datos(m, yo))

    externos = [
        {"id": f["materialId"], "creado": f["creado"]}
        for f in mios
        if ":" in str(f["materialId"])
    ]

    return {"materiales": propios, "externos": externos}


# ===================== La biblioteca =====================
async def listar_materiales(request: Request, yo: dict ):
    p = request.GET.dict()
    fuente = p.get("fuente") or "campus"
    texto = (p.get("q") or "").strip()

    propios = [] if fuente == "externos" else _filtrar(p, yo)
    paginacion = _paginar(propios, p)
    recortada = paginacion.pop("recortada")

    respuesta: dict[str, Any] = {
        "materiales": [_con_datos(m, yo) for m in recortada],
        **paginacion,
        "externos": [],
        "fuentes": [],
    }

    # Los catálogos externos son una ayuda para encontrar un libro, no parte
    # de la biblioteca: solo se consultan si se los pide a propósito.
    if fuente == "externos" and len(texto) >= 2:
        if not _dentro_del_limite(f"buscar:{yo['id']}", 30, 60):
            respuesta["fuentes"] = [{"estado": "limite", "nombre": "Catálogos externos"}]
            return respuesta

        try:
            resultado = await buscar_libros_externos(
                texto, p.get("campo") or "todo", p.get("idioma") or None
            )
            respuesta["externos"] = [
                {
                    **l,
                    "favorito": any(
                        f["personaId"] == yo["id"] and str(f["materialId"]) == str(l["id"])
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


def crear_material(cuerpo: dict[str, Any] = {}, yo: dict = None ):
    if not _dentro_del_limite(f"aportar:{yo['id']}", 10, 60 * 60):
        raise ErrorDeAPI(429, "Demasiados aportes seguidos. Probá de nuevo en un rato.")

    campos = _leer_campos(cuerpo)
    problema = _validar(campos, cuerpo, yo, exigir_autorizacion=True)
    if problema:
        raise ErrorDeAPI(400, problema)

    repetido = _repetido(campos, None)
    if repetido:
        raise ErrorDeAPI(
            409,
            f'"{repetido["titulo"]}" ya está en la biblioteca de esta materia.',
        )

    # El docente de la materia publica directo; el aporte de un estudiante
    # queda esperando revisión. Esa es toda la diferencia.
    publica_directo = _modera(yo, campos["materiaId"])
    estado = "aprobado" if publica_directo else "pendiente"
    quien = d.buscar_persona(yo["id"])
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
        "subidoPor": yo["id"],
        "estado": estado,
        "moderadoPor": yo["id"] if publica_directo else None,
        "motivo": None,
        "creado": ahora,
        "actualizado": ahora,
    }
    d.materiales.append(material)

    if publica_directo:
        d.moderacion_biblioteca.append(
            {
                "id": d.nuevo_id_moderacion(),
                "materialId": material["id"],
                "moderadorId": yo["id"],
                "accion": "aprobado",
                "motivo": "Publicado por el docente de la materia",
                "fecha": ahora,
            }
        )

    auditoria.registrar(
        yo,
        "creacion",
        "biblioteca",
        elemento=material["titulo"],
        elemento_id=material["id"],
        elemento_tipo="material",
        materia_id=material["materiaId"],
        despues={"estado": estado, "tipo": material["tipo"]},
        detalle=(
            "Publicó material en la materia"
            if publica_directo
            else "Envió un aporte, pendiente de revisión"
        ),
    )
    return _con_datos(material, yo)


# ===================== Validación de la ficha =====================
def _leer_campos(cuerpo: dict) -> dict:
    texto = lambda v: str(v if v is not None else "").strip()  # noqa: E731

    try:
        materia_id = int(cuerpo.get("materiaId"))
    except (TypeError, ValueError):
        materia_id = None

    return {
        "titulo": texto(cuerpo.get("titulo")),
        "autor": texto(cuerpo.get("autor")),
        "descripcion": texto(cuerpo.get("descripcion")),
        "tipo": texto(cuerpo.get("tipo")) or "otro",
        "materiaId": materia_id,
        "anio": texto(cuerpo.get("anio")),
        "idioma": texto(cuerpo.get("idioma")) or "es",
        "isbn": texto(cuerpo.get("isbn")),
        "categoria": texto(cuerpo.get("categoria")) or "otros",
        "editorial": texto(cuerpo.get("editorial")),
        "enlace": texto(cuerpo.get("enlace")),
        "licencia": texto(cuerpo.get("licencia")),
        "portada": texto(cuerpo.get("portada")),
    }


def _repetido(campos: dict, excepto: int | None) -> dict | None:
    """El mismo libro dos veces en la misma materia.

    Se compara por ISBN cuando lo hay —que es el identificador de verdad— y si
    no por título y autor sin tildes ni mayúsculas. Entre materias distintas no
    es repetición: cada cátedra arma su biblioteca.
    """
    isbn = re.sub(r"[^0-9Xx]", "", campos["isbn"] or "").lower()
    titulo = _sin_tildes(campos["titulo"])
    autor = _sin_tildes(campos["autor"])

    for m in d.materiales:
        if m["id"] == excepto or m["materiaId"] != campos["materiaId"]:
            continue
        if m["estado"] == "rechazado":
            continue
        suyo = re.sub(r"[^0-9Xx]", "", m.get("isbn") or "").lower()
        if isbn and suyo and isbn == suyo:
            return m
        if _sin_tildes(m["titulo"]) == titulo and _sin_tildes(m.get("autor")) == autor:
            return m
    return None


def _validar(campos: dict, cuerpo: dict, persona: dict, *, exigir_autorizacion: bool) -> str | None:
    if not campos["titulo"]:
        return "El material necesita un título"
    if len(campos["titulo"]) > 200:
        return "El título es demasiado largo"

    # La materia es obligatoria y tiene que ser una de las suyas: sin materia
    # no hay a quién mostrarle el material.
    if campos["materiaId"] is None:
        return "Elegí la materia a la que pertenece el material"
    if not d.buscar_en(d.materias_plan, campos["materiaId"]):
        return "Esa materia no existe"
    if campos["materiaId"] not in _ids_visibles(persona):
        return "Solo podés subir material a las materias que cursás o dictás"

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
        raise ErrorDeAPI(404, "Material no encontrado")
    material = next((m for m in d.materiales if m["id"] == buscado), None)
    if not material:
        raise ErrorDeAPI(404, "Material no encontrado")
    return material


def subir_archivo(
    id_material: str, cuerpo: dict[str, Any] = {}, yo: dict = None
):
    material = _buscar_material(id_material)
    _exigir_ver(material, yo)
    if not _puede_editar(material, yo):
        raise ErrorDeAPI(403, "Solo quien lo subió puede cambiar el archivo")
    if not _dentro_del_limite(f"subir:{yo['id']}", 20, 60 * 60):
        raise ErrorDeAPI(429, "Demasiadas subidas seguidas. Probá de nuevo en un rato.")

    extension = str(cuerpo.get("extension") or "").lower().lstrip(".")
    formato = FORMATOS.get(extension)
    if not formato:
        aceptados = " y ".join(e.upper() for e in FORMATOS)
        raise ErrorDeAPI(415, f"Solo se aceptan archivos {aceptados}")

    # El tipo que declara el navegador tiene que coincidir con la extensión…
    declarado = str(cuerpo.get("tipo") or "")
    if declarado and declarado != formato["mime"]:
        raise ErrorDeAPI(415, "El tipo del archivo no coincide con su extensión")

    try:
        bytes_archivo = base64.b64decode(str(cuerpo.get("contenido") or ""), validate=False)
    except Exception:
        raise ErrorDeAPI(400, "No se pudo leer el archivo")

    if len(bytes_archivo) == 0:
        raise ErrorDeAPI(400, "El archivo está vacío")
    if len(bytes_archivo) > MAX_BYTES:
        raise ErrorDeAPI(413, f"El archivo supera los {MAX_MB} MB")
    # …y el contenido real tiene que ser lo que dice ser. La extensión sola no
    # prueba nada: cualquiera renombra un .exe a .pdf.
    if not formato["firma"](bytes_archivo):
        raise ErrorDeAPI(415, f"El archivo no es un {extension.upper()} válido")

    nombre = _nombre_seguro(cuerpo.get("nombre"), extension)
    objeto = alm.clave(alm.BIBLIOTECA, material["materiaId"], material["id"], nombre=nombre)

    # Si ya tenía uno, el anterior se va: dos archivos para una ficha que
    # solo apunta a uno dejan basura pagando lugar en el bucket.
    anterior = (material.get("archivo") or {}).get("objectKey")
    if anterior and anterior != objeto:
        alm.olvidar(anterior)

    # Se escribe primero y recién después se toca la ficha: si R2 falla, la
    # ruta corta acá con error y el material queda como estaba. Nunca al
    # revés, que es decirle al estudiante que subió algo que no está.
    try:
        alm.subir(objeto, bytes_archivo, formato["mime"])
    except Exception as error:  # noqa: BLE001
        raise ErrorDeAPI(502, f"No se pudo guardar el archivo: {error}")

    alm.registrar(
        objeto,
        nombre=nombre,
        tipo=formato["mime"],
        tamano=len(bytes_archivo),
        persona_id=yo["id"],
        modulo=alm.BIBLIOTECA,
        registro_id=material["id"],
    )

    material["archivo"] = {
        "nombre": nombre,
        "tamano": len(bytes_archivo),
        "tipo": formato["mime"],
        "objectKey": objeto,
    }
    # Si el archivo está alojado acá, el enlace externo sobra
    material["enlace"] = None
    material["actualizado"] = d.iso(d.ahora())

    return _con_datos(material, yo)


def descargar_archivo(id_material: str, yo: dict ):
    """Pasa por el mismo control que la ficha: el archivo de una materia ajena
    no se baja aunque alguien adivine el id."""
    material = _buscar_material(id_material)
    _exigir_ver(material, yo)

    guardado = material.get("archivo") or {}
    # `objectKey` es el camino nuevo; el id suelto es cómo se guardaba antes
    # de R2, y se sigue leyendo para no perder lo que ya estaba subido.
    contenido = alm.leer(guardado["objectKey"]) if guardado.get("objectKey") else None
    if contenido is None:
        contenido = d.leer_archivo(material["id"])
    if not contenido or not material.get("archivo"):
        raise ErrorDeAPI(404, "Este material no tiene un archivo alojado en el campus")

    auditoria.registrar(
        yo,
        "descarga",
        "biblioteca",
        elemento=material["titulo"],
        elemento_id=material["id"],
        elemento_tipo="material",
        materia_id=material["materiaId"],
        detalle=f"Descargó {material['archivo']['nombre']}",
    )

    return descargar(
        contenido,
        material["archivo"]["tipo"],
        {
            # Siempre como descarga y sin dejar que el navegador adivine el
            # tipo: un archivo de otra persona no se abre dentro del campus.
            "Content-Disposition": f'attachment; filename="{material["archivo"]["nombre"]}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ===================== Revisión de los aportes =====================
def _revisar(id_material: str, accion: str, motivo: str, yo: dict) -> dict:
    material = _buscar_material(id_material)

    # Quien modera la materia, no cualquier docente. Si no la modera, el
    # material se niega como inexistente, igual que en el resto.
    if not _modera(yo, material["materiaId"]):
        if material["materiaId"] not in _ids_visibles(yo):
            raise ErrorDeAPI(404, "Material no encontrado")
        raise ErrorDeAPI(
            403, "Solo el docente de la materia o un supervisor revisan los aportes"
        )

    # Rechazar sin decir por qué no le sirve a nadie: quien aportó no sabe qué
    # corregir.
    if accion == "rechazado" and not motivo:
        raise ErrorDeAPI(400, "Hay que indicar el motivo del rechazo")

    ahora = d.iso(d.ahora())
    estado_antes = material["estado"]
    material["estado"] = accion
    material["moderadoPor"] = yo["id"]
    material["motivo"] = motivo or None
    material["actualizado"] = ahora

    d.moderacion_biblioteca.append(
        {
            "id": d.nuevo_id_moderacion(),
            "materialId": material["id"],
            "moderadorId": yo["id"],
            "accion": accion,
            "motivo": motivo or None,
            "fecha": ahora,
        }
    )

    # Que le llegue: no hay mails, así que el aviso es un mensaje, como en
    # Finales. Es lo que hace que el estudiante se entere del motivo.
    materia = _materia_de(material)
    donde = materia["nombre"] if materia else "la biblioteca"
    if accion == "aprobado":
        texto = f'Tu aporte "{material["titulo"]}" ya está publicado en la biblioteca de {donde}.'
    else:
        texto = f'Tu aporte "{material["titulo"]}" para {donde} no se publicó. Motivo: {motivo}'
    if material["subidoPor"] != yo["id"]:
        d.avisar_por_mensaje(yo["id"], material["subidoPor"], texto)

    auditoria.registrar(
        yo,
        "aprobacion" if accion == "aprobado" else "rechazo",
        "biblioteca",
        elemento=material["titulo"],
        elemento_id=material["id"],
        elemento_tipo="material",
        persona_id=material["subidoPor"],
        materia_id=material["materiaId"],
        antes={"estado": estado_antes},
        despues={"estado": accion, "motivo": motivo or None},
        detalle=f"Revisó un aporte de {donde}",
    )
    return _con_datos(material, yo)


def aprobar_material(id_material: str, yo: dict ):
    return _revisar(id_material, "aprobado", "", yo)


def rechazar_material(
    id_material: str, cuerpo: dict[str, Any] = {}, yo: dict = None
):
    return _revisar(id_material, "rechazado", str(cuerpo.get("motivo") or "").strip(), yo)


# ===================== Favoritos =====================
def agregar_favorito(id_material: str, yo: dict ):
    """Vale tanto para un material de una materia como para un libro externo:
    el id externo ("google:xxx") es estable y se guarda tal cual."""
    es_externo = ":" in id_material

    if not es_externo:
        material = _buscar_material(id_material)
        _exigir_ver(material, yo)

    clave: Any = id_material if es_externo else int(id_material)
    ya_esta = any(
        f["personaId"] == yo["id"] and str(f["materialId"]) == str(clave)
        for f in d.favoritos_biblioteca
    )
    if not ya_esta:
        d.favoritos_biblioteca.append(
            {"personaId": yo["id"], "materialId": clave, "creado": d.iso(d.ahora())}
        )

    return {"id": clave, "favorito": True}


def quitar_favorito(id_material: str, yo: dict ):
    for i, f in enumerate(d.favoritos_biblioteca):
        if f["personaId"] == yo["id"] and str(f["materialId"]) == str(id_material):
            d.favoritos_biblioteca.pop(i)
            break
    return {"id": id_material, "favorito": False}


# ===================== Ficha, edición y baja =====================
# Van al final: su patrón admite barras y se comería a las rutas de arriba.
async def obtener_material(id_material: str, yo: dict ):
    # Un id con dos puntos es de un catálogo externo ("google:xxx")
    if ":" in id_material:
        try:
            libro = await obtener_libro_externo(id_material)
        except Exception:
            libro = None
        if not libro:
            raise ErrorDeAPI(404, "No se encontró ese libro")
        return {
            **libro,
            "favorito": any(
                f["personaId"] == yo["id"] and str(f["materialId"]) == str(id_material)
                for f in d.favoritos_biblioteca
            ),
            "relacionados": [],
        }

    material = _buscar_material(id_material)
    _exigir_ver(material, yo)

    # Material relacionado: de la misma materia, que es donde tiene sentido
    relacionados = [
        _con_datos(m, yo)
        for m in d.materiales
        if m["id"] != material["id"]
        and m["estado"] == "aprobado"
        and m["materiaId"] == material["materiaId"]
    ][:4]

    return {
        **_con_datos(material, yo),
        "relacionados": relacionados,
        "historial": [
            {**h, "moderador": (p["nombre"] if (p := d.buscar_persona(h["moderadorId"])) else None)}
            for h in d.moderacion_biblioteca
            if h["materialId"] == material["id"]
        ],
    }


def editar_material(
    id_material: str, cuerpo: dict[str, Any] = {}, yo: dict = None
):
    material = _buscar_material(id_material)
    _exigir_ver(material, yo)
    if not _puede_editar(material, yo):
        raise ErrorDeAPI(403, "Solo quien lo subió o el docente de la materia puede editarlo")

    # Lo que había antes, para que el registro diga qué cambió
    antes_de_editar = {
        k: material.get(k)
        for k in ("titulo", "autor", "tipo", "materiaId", "categoria", "enlace", "estado")
    }

    campos = _leer_campos({**material, **cuerpo})
    problema = _validar(campos, cuerpo, yo, exigir_autorizacion=False)
    if problema:
        raise ErrorDeAPI(400, problema)

    repetido = _repetido(campos, material["id"])
    if repetido:
        raise ErrorDeAPI(
            409, f'"{repetido["titulo"]}" ya está en la biblioteca de esta materia.'
        )

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

    # Si lo edita quien lo subió y no modera esa materia, vuelve a la cola: el
    # texto que se aprobó ya no es el que está.
    if not _modera(yo, material["materiaId"]) and material["estado"] == "aprobado":
        material["estado"] = "pendiente"
        material["moderadoPor"] = None

    auditoria.registrar(
        yo,
        "edicion",
        "biblioteca",
        elemento=material["titulo"],
        elemento_id=material["id"],
        elemento_tipo="material",
        materia_id=material["materiaId"],
        antes=antes_de_editar,
        despues={k: material.get(k) for k in antes_de_editar},
        detalle="Modificó la ficha del material",
    )
    return _con_datos(material, yo)


def borrar_material(id_material: str, yo: dict ):
    material = _buscar_material(id_material)
    _exigir_ver(material, yo)
    if not _puede_editar(material, yo):
        raise ErrorDeAPI(403, "Solo quien lo subió o el docente de la materia puede retirarlo")

    auditoria.registrar(
        yo,
        "baja",
        "biblioteca",
        elemento=material["titulo"],
        elemento_id=material["id"],
        elemento_tipo="material",
        persona_id=material["subidoPor"],
        materia_id=material["materiaId"],
        antes={"estado": material["estado"], "autor": material.get("autor")},
        detalle="Retiró el material de la biblioteca",
    )

    d.materiales.remove(material)
    guardado = material.get("archivo") or {}
    if guardado.get("objectKey"):
        alm.olvidar(guardado["objectKey"])
    d.borrar_archivo(material["id"])
    # Los favoritos que apuntaban ahí quedarían colgados
    d.favoritos_biblioteca[:] = [
        f for f in d.favoritos_biblioteca if str(f["materialId"]) != str(material["id"])
    ]

    return {"retirado": material["id"]}
