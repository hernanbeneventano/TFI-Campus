"""Subir y guardar archivos, con la validación en un solo lugar.

Lo usan la Biblioteca y el contenido de un módulo. Antes la validación vivía
entera dentro de la Biblioteca; al hacer falta también para los archivos de
una materia, copiarla habría dejado dos reglas que se irían separando con el
tiempo, y la de seguridad es justamente la que no puede divergir.

Qué se comprueba, y por qué cada cosa
-------------------------------------
- **Los bytes, no la extensión.** Cualquiera renombra un `.exe` a `.pdf`. Se
  mira la firma del archivo y tiene que ser la del formato que dice ser.
- **El tipo que declara el navegador tiene que coincidir** con la extensión.
- **Nada que el navegador pueda ejecutar**: ni `.html`, ni `.svg`, ni `.js`.
  Un SVG es un documento con scripts adentro, no una imagen inofensiva.
- **Un DOCX tiene que ser un DOCX**: que sea un ZIP no alcanza, porque
  cualquier `.zip` renombrado lo sería. Se exige que traiga adentro el
  documento de Word.
- **El nombre se limpia**: `../../etc/passwd` queda en `passwd.pdf`.
- **Un tamaño máximo**, configurable por quien despliega.

Dónde viven los bytes
---------------------
En memoria, en `datos.py`, aparte de la ficha: el elemento guarda nombre,
tamaño y tipo, y los bytes se piden por su propia ruta con el control de
acceso puesto. Se pierden al reiniciar, como el resto. Cuando esté Firebase
Storage, esto pasa a ser una referencia al bucket y lo demás no cambia.
"""

from __future__ import annotations

import base64
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException


@dataclass
class Archivo:
    """Un archivo para bajar: los bytes, su tipo y las cabeceras que lleva.

    Es lo que devuelven los servicios en vez de una respuesta de un
    framework: cada uno arma con esto la suya (FastAPI con `Response`, Django
    con `adaptadores.descargar`), y salen iguales.
    """

    contenido: bytes
    tipo: str
    cabeceras: dict[str, str]


def _es_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-"


def _es_epub(b: bytes) -> bool:
    # Un EPUB es un ZIP: tiene que empezar con PK y declarar su mimetype
    return b[:2] == b"PK" and b"application/epub+zip" in b[:200]


def _es_docx(b: bytes) -> bool:
    """Un DOCX es un ZIP con `word/document.xml` adentro.

    No alcanza con que sea un ZIP: un `.zip` cualquiera renombrado a `.docx`
    pasaría, y después el visor no tendría qué mostrar. El nombre de esa
    entrada aparece en el listado del ZIP, así que se lo busca en los bytes
    sin descomprimir nada —descomprimir lo que todavía no se validó es
    justamente lo que no conviene hacer—.
    """
    return b[:2] == b"PK" and b"word/document.xml" in b


def _es_png(b: bytes) -> bool:
    return b[:8] == b"\x89PNG\r\n\x1a\n"


def _es_jpg(b: bytes) -> bool:
    return b[:3] == b"\xff\xd8\xff"


# Solo formatos de lectura y de imagen. Nada de ejecutables ni de cosas que el
# navegador pueda correr.
FORMATOS: dict[str, dict] = {
    "pdf": {"mime": "application/pdf", "firma": _es_pdf},
    "epub": {"mime": "application/epub+zip", "firma": _es_epub},
    # Word. Se acepta porque es lo que entrega media facultad, y el campus lo
    # muestra sin descargarlo: lo dibuja la pantalla, no un programa del
    # servidor ni un visor de terceros.
    "docx": {
        "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "firma": _es_docx,
    },
    "png": {"mime": "image/png", "firma": _es_png},
    "jpg": {"mime": "image/jpeg", "firma": _es_jpg},
    "jpeg": {"mime": "image/jpeg", "firma": _es_jpg},
}

# Los que puede alojar la Biblioteca: ahí son libros, no imágenes
FORMATOS_BIBLIOTECA = {"pdf", "epub"}


# Lo que puede pesar una imagen en el campus: diez megas. Una foto sacada con
# el celular entra holgada y nadie necesita subir un afiche a un chat.
#
# El tope es **uno solo** para todas —el avatar, el adjunto de un mensaje, la
# portada de una novedad—: es el mismo archivo con distinto destino, y tres
# topes distintos se descubren fallando, nunca leyendo.
IMAGENES_MAX_MB = int(os.environ.get("IMAGENES_MAX_MB") or 10)


def maximo_mb(variable: str = "ARCHIVOS_MAX_MB", por_defecto: int = 15) -> int:
    return int(os.environ.get(variable) or por_defecto)


def nombre_seguro(nombre: Any, extension: str) -> str:
    """El nombre que mande el navegador no se usa tal cual: podría traer una
    ruta ("../../algo") o caracteres que rompan la cabecera de la descarga."""
    base = str(nombre if nombre is not None else "archivo")
    base = re.split(r"[\\/]", base)[-1]
    base = re.sub(r"\.[^.]*$", "", base)
    base = unicodedata.normalize("NFD", base)
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    base = re.sub(r"[^a-zA-Z0-9 _-]", "", base).strip()[:80]
    return f"{base or 'archivo'}.{extension}"


def leer_subida(cuerpo: dict, *, permitidos: set[str] | None = None, max_mb: int | None = None):
    """Valida lo que llegó y devuelve `(bytes, ficha)`.

    `ficha` es lo que se guarda al lado del elemento: nombre, tamaño y tipo.
    Los bytes se guardan aparte.

    Lanza el error HTTP que corresponda; quien llama no tiene que validar nada
    más.
    """
    aceptados = permitidos if permitidos is not None else set(FORMATOS)
    tope = max_mb if max_mb is not None else maximo_mb()

    extension = str(cuerpo.get("extension") or "").lower().lstrip(".")
    formato = FORMATOS.get(extension)
    if not formato or extension not in aceptados:
        lista = " y ".join(sorted(e.upper() for e in aceptados))
        raise HTTPException(415, f"Solo se aceptan archivos {lista}")

    # El tipo que declara el navegador tiene que coincidir con la extensión…
    declarado = str(cuerpo.get("tipo") or "")
    if declarado and declarado != formato["mime"]:
        raise HTTPException(415, "El tipo del archivo no coincide con su extensión")

    try:
        contenido = base64.b64decode(str(cuerpo.get("contenido") or ""), validate=False)
    except Exception:
        raise HTTPException(400, "No se pudo leer el archivo")

    if len(contenido) == 0:
        raise HTTPException(400, "El archivo está vacío")
    if len(contenido) > tope * 1024 * 1024:
        raise HTTPException(413, f"El archivo supera los {tope} MB")

    # …y el contenido real tiene que ser lo que dice ser
    if not formato["firma"](contenido):
        raise HTTPException(415, f"El archivo no es un {extension.upper()} válido")

    ficha = {
        "nombre": nombre_seguro(cuerpo.get("nombre"), extension),
        "tamano": len(contenido),
        "tipo": formato["mime"],
    }
    return contenido, ficha


def peso_legible(bytes_: int) -> str:
    """"320 KB", para mostrar al lado del archivo."""
    if bytes_ < 1024:
        return f"{bytes_} B"
    if bytes_ < 1024 * 1024:
        return f"{round(bytes_ / 1024)} KB"
    return f"{bytes_ / (1024 * 1024):.1f} MB"
