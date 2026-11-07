"""Búsqueda de libros en catálogos públicos: Google Books y Open Library.

Va del lado del servidor a propósito. Así la clave de Google (si se usa) no
viaja al navegador, se puede cachear entre usuarios y, si una fuente se cae,
la pantalla sigue funcionando con la otra y con la biblioteca propia.

Documentación:
  https://developers.google.com/books/docs/v1/using
  https://openlibrary.org/dev/docs/api/search
"""

from __future__ import annotations

import asyncio
import os
import re
import ssl
import time
import unicodedata
from typing import Any

import httpx

GOOGLE = "https://www.googleapis.com/books/v1/volumes"
OPENLIBRARY = "https://openlibrary.org/search.json"

# Las dos interfaces son públicas pero piden moderación. La espera está medida
# contra Open Library, que ronda los 4 s: si una tarda más, se responde con lo
# que haya llegado de la otra en vez de dejar esperando.
ESPERA = 9.0
POR_FUENTE = 20

AGENTE = "CampusTFI/0.1 (proyecto academico FaCENA-UNNE)"

# httpx verifica los certificados contra el paquete de Mozilla que trae
# `certifi`. Eso falla en cualquier equipo donde algo inspeccione el tráfico
# HTTPS y lo vuelva a firmar: un antivirus con escaneo web, o el proxy de una
# institución. La raíz de esos intermediarios está en el almacén del sistema
# operativo, no en el de Mozilla.
#
# Con el contexto estándar de Python la verificación sigue activa, pero usa
# las autoridades en las que confía el sistema. Es lo mismo que hace el
# navegador, y lo que hacía la versión en Node.
CONTEXTO_TLS = ssl.create_default_context()

# Caché en memoria. Las mismas búsquedas se repiten muchísimo (alguien escribe,
# borra una letra y vuelve a escribir) y las interfaces tienen límites.
CACHE_SEGUNDOS = 10 * 60
CACHE_MAXIMO = 200
_cache: dict[str, tuple[float, dict]] = {}


def _de_cache(clave: str) -> dict | None:
    guardado = _cache.get(clave)
    if not guardado:
        return None
    cuando, datos = guardado
    if time.time() - cuando > CACHE_SEGUNDOS:
        del _cache[clave]
        return None
    return datos


def _a_cache(clave: str, datos: dict) -> None:
    # El más viejo primero: los diccionarios conservan el orden de inserción
    if len(_cache) >= CACHE_MAXIMO:
        del _cache[next(iter(_cache))]
    _cache[clave] = (time.time(), datos)


# ===================== Armado de las consultas =====================
def _consulta_google(texto: str, campo: str) -> str:
    limpio = texto.strip()
    if campo == "titulo":
        return f"intitle:{limpio}"
    if campo == "autor":
        return f"inauthor:{limpio}"
    if campo == "isbn":
        return f"isbn:{re.sub(r'[^0-9Xx]', '', limpio)}"
    if campo == "tema":
        return f"subject:{limpio}"
    return limpio


def _parametros_google(texto: str, campo: str, idioma: str | None) -> dict:
    # Google Books no exige clave para buscar, pero con una el límite es más
    # alto. Si está, se usa; si no, se busca igual.
    parametros = {
        "q": _consulta_google(texto, campo),
        "maxResults": str(POR_FUENTE),
        "printType": "books",
    }
    if idioma:
        parametros["langRestrict"] = idioma
    clave = os.environ.get("GOOGLE_BOOKS_API_KEY")
    if clave:
        parametros["key"] = clave
    return parametros


def _parametros_openlibrary(texto: str, campo: str) -> dict:
    limpio = texto.strip()
    parametros: dict[str, str] = {}
    if campo == "titulo":
        parametros["title"] = limpio
    elif campo == "autor":
        parametros["author"] = limpio
    elif campo == "isbn":
        parametros["isbn"] = re.sub(r"[^0-9Xx]", "", limpio)
    elif campo == "tema":
        parametros["subject"] = limpio
    else:
        parametros["q"] = limpio

    parametros["limit"] = str(POR_FUENTE)
    # Pedir solo los campos que se usan: la respuesta completa es enorme
    parametros["fields"] = (
        "key,title,author_name,first_publish_year,isbn,cover_i,language,"
        "subject,publisher,ebook_access,ia"
    )
    return parametros


# ===================== Normalización =====================
def _a_https(url: str | None) -> str | None:
    """Google devuelve las portadas en http; el campus va en https y el
    navegador bloquearía la imagen por contenido mixto."""
    if not isinstance(url, str):
        return None
    return re.sub(r"^http://", "https://", url)


def _desde_google(volumen: dict) -> dict:
    v = volumen.get("volumeInfo") or {}
    acceso = volumen.get("accessInfo") or {}
    isbn = next(
        (i for i in v.get("industryIdentifiers", []) if str(i.get("type", "")).startswith("ISBN")),
        None,
    )
    imagenes = v.get("imageLinks") or {}

    # Solo lo que la interfaz dice que se puede leer de verdad. Nada de
    # inventar enlaces de descarga: si no es de dominio público, va el enlace
    # a la ficha.
    lee_completo = (
        v.get("viewability") == "ALL_PAGES"
        or acceso.get("accessViewStatus") == "FULL_PUBLIC_DOMAIN"
    )
    pdf = acceso.get("pdf") or {}
    pdf_publico = pdf.get("isAvailable") and pdf.get("downloadLink") and acceso.get("publicDomain")

    publicado = v.get("publishedDate")

    return {
        "id": f"google:{volumen.get('id')}",
        "fuente": "google",
        "nombreFuente": "Google Books",
        "externo": True,
        "titulo": v.get("title") or "Sin título",
        "subtitulo": v.get("subtitle"),
        "autor": ", ".join(v.get("authors", [])) or None,
        "descripcion": v.get("description"),
        "editorial": v.get("publisher"),
        "anioPublicacion": str(publicado)[:4] if publicado else None,
        "isbn": isbn.get("identifier") if isbn else None,
        "idioma": v.get("language"),
        "categorias": v.get("categories", []),
        "portada": _a_https(imagenes.get("thumbnail") or imagenes.get("smallThumbnail")),
        # Qué se puede hacer realmente con este libro
        "enlaceLectura": v.get("previewLink") if lee_completo else None,
        "enlaceVistaPrevia": v.get("previewLink") if acceso.get("viewability") == "PARTIAL" else None,
        "enlaceDescarga": pdf.get("downloadLink") if pdf_publico else None,
        "enlaceFicha": v.get("infoLink") or v.get("canonicalVolumeLink"),
        "dominioPublico": bool(acceso.get("publicDomain")),
    }


def _desde_openlibrary(doc: dict) -> dict:
    isbns = doc.get("isbn") or []
    acceso = doc.get("ebook_access")
    # "borrowable" y "public" son los únicos accesos que dan algo real
    prestable = acceso == "borrowable"
    libre = acceso == "public"
    ia = (doc.get("ia") or [None])[0]
    anio = doc.get("first_publish_year")

    return {
        "id": f"openlibrary:{doc.get('key')}",
        "fuente": "openlibrary",
        "nombreFuente": "Open Library",
        "externo": True,
        "titulo": doc.get("title") or "Sin título",
        "subtitulo": None,
        "autor": ", ".join(doc.get("author_name", [])) or None,
        "descripcion": None,
        "editorial": (doc.get("publisher") or [None])[0],
        "anioPublicacion": str(anio) if anio else None,
        "isbn": isbns[0] if isbns else None,
        "idioma": (doc.get("language") or [None])[0],
        "categorias": (doc.get("subject") or [])[:6],
        "portada": (
            f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-M.jpg"
            if doc.get("cover_i")
            else None
        ),
        "enlaceLectura": f"https://archive.org/details/{ia}" if libre and ia else None,
        "enlacePrestamo": f"https://archive.org/details/{ia}" if prestable and ia else None,
        "enlaceVistaPrevia": None,
        "enlaceDescarga": None,
        "enlaceFicha": f"https://openlibrary.org{doc.get('key')}",
        "dominioPublico": bool(libre),
    }


# ===================== Unificación =====================
def _sin_tildes(texto: str | None) -> str:
    sin = unicodedata.normalize("NFD", texto or "")
    sin = "".join(c for c in sin if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", sin.lower()).strip()


def _huella(libro: dict) -> str:
    """Para detectar el mismo libro en las dos fuentes: el ISBN si lo hay y,
    si no, título y autor sin tildes, signos ni mayúsculas."""
    if libro.get("isbn"):
        return "isbn:" + re.sub(r"[^0-9Xx]", "", libro["isbn"]).upper()
    autor = " ".join(_sin_tildes(libro.get("autor")).split(" ")[:2])
    return f"t:{_sin_tildes(libro.get('titulo'))}|a:{autor}"


def _unir(preferido: dict, otro: dict) -> dict:
    """Cuando un libro está en las dos fuentes se queda el de Google, que trae
    descripción y portada más seguido, pero se completan los huecos con el de
    Open Library y se anotan las dos fuentes."""
    unido = dict(preferido)
    for campo in ("descripcion", "editorial", "anioPublicacion", "isbn", "idioma", "portada"):
        if unido.get(campo) is None:
            unido[campo] = otro.get(campo)
    for campo in ("enlaceLectura", "enlacePrestamo"):
        if unido.get(campo) is None:
            unido[campo] = otro.get(campo)
    unido["tambienEn"] = otro["nombreFuente"]
    unido["enlaceOtraFuente"] = otro.get("enlaceFicha")
    return unido


def _combinar(de_google: list[dict], de_openlibrary: list[dict]) -> list[dict]:
    por_huella: dict[str, dict] = {}

    for libro in de_google:
        por_huella[_huella(libro)] = libro

    for libro in de_openlibrary:
        clave = _huella(libro)
        ya_esta = por_huella.get(clave)
        por_huella[clave] = _unir(ya_esta, libro) if ya_esta else libro

    return list(por_huella.values())


# ===================== Consulta =====================
async def _traer(cliente: httpx.AsyncClient, url: str, parametros: dict) -> Any:
    respuesta = await cliente.get(url, params=parametros)
    respuesta.raise_for_status()
    return respuesta.json()


async def buscar_libros_externos(texto: str, campo: str = "todo", idioma: str | None = None) -> dict:
    """Busca en los dos catálogos a la vez y devuelve los resultados unificados.

    Si una fuente falla o tarda, se informa en `fuentes` y se devuelve lo de la
    otra: la pantalla avisa, pero no se queda vacía.
    """
    limpio = (texto or "").strip()
    if len(limpio) < 2:
        return {"libros": [], "fuentes": [], "desdeCache": False}

    clave = f"{limpio.lower()}|{campo}|{idioma}"
    guardado = _de_cache(clave)
    if guardado:
        return {**guardado, "desdeCache": True}

    async with httpx.AsyncClient(
        timeout=ESPERA,
        headers={"User-Agent": AGENTE},
        follow_redirects=True,
        verify=CONTEXTO_TLS,
    ) as cliente:
        # Las dos en paralelo: una lenta no debe arrastrar a la otra
        google, openlibrary = await asyncio.gather(
            _traer(cliente, GOOGLE, _parametros_google(limpio, campo, idioma)),
            _traer(cliente, OPENLIBRARY, _parametros_openlibrary(limpio, campo)),
            return_exceptions=True,
        )

    fuentes: list[dict] = []

    libros_google: list[dict] = []
    if isinstance(google, Exception):
        fuentes.append(
            {"fuente": "google", "nombre": "Google Books", "estado": "error", "error": str(google)}
        )
    else:
        libros_google = [_desde_google(v) for v in (google.get("items") or [])]
        fuentes.append(
            {
                "fuente": "google",
                "nombre": "Google Books",
                "estado": "ok",
                "cuantos": len(libros_google),
            }
        )

    libros_open: list[dict] = []
    if isinstance(openlibrary, Exception):
        fuentes.append(
            {
                "fuente": "openlibrary",
                "nombre": "Open Library",
                "estado": "error",
                "error": str(openlibrary),
            }
        )
    else:
        libros_open = [_desde_openlibrary(d) for d in (openlibrary.get("docs") or [])]
        fuentes.append(
            {
                "fuente": "openlibrary",
                "nombre": "Open Library",
                "estado": "ok",
                "cuantos": len(libros_open),
            }
        )

    datos = {"libros": _combinar(libros_google, libros_open), "fuentes": fuentes}

    # Un resultado vacío porque las dos fallaron no se cachea: conviene
    # reintentar en el próximo pedido.
    if any(f["estado"] == "ok" for f in fuentes):
        _a_cache(clave, datos)

    return {**datos, "desdeCache": False}


async def obtener_libro_externo(identificador: str) -> dict | None:
    """Un libro externo por su id ("google:xxx" u "openlibrary:/works/OL1W")."""
    fuente, _, resto = str(identificador).partition(":")

    async with httpx.AsyncClient(
        timeout=ESPERA,
        headers={"User-Agent": AGENTE},
        follow_redirects=True,
        verify=CONTEXTO_TLS,
    ) as cliente:
        if fuente == "google":
            volumen = await _traer(cliente, f"{GOOGLE}/{resto}", {})
            return _desde_google(volumen)

        if fuente == "openlibrary":
            # La ficha de una obra no trae los autores resueltos; la búsqueda
            # por clave sí.
            datos = await _traer(cliente, OPENLIBRARY, {"q": f"key:{resto}", "limit": "1"})
            docs = datos.get("docs") or []
            if not docs:
                return None

            libro = _desde_openlibrary(docs[0])
            # La descripción vive en otro recurso
            try:
                obra = await _traer(cliente, f"https://openlibrary.org{resto}.json", {})
                descripcion = obra.get("description")
                libro["descripcion"] = (
                    descripcion if isinstance(descripcion, str) else (descripcion or {}).get("value")
                )
            except Exception:
                # Sin descripción se muestra igual: no es motivo para fallar
                pass
            return libro

    return None
