"""Los catálogos externos, que ahora atiende el servicio de Node.

Antes acá estaba la implementación entera: las dos interfaces, la caché, la
unificación por ISBN. Hoy eso vive en `backend-node/`, y este archivo es el
cliente.

Por qué se movió
----------------
Es la única parte del campus que no tiene estado propio: no toca `datos.py`,
no mira el historial académico y no decide permisos. Lo único que hace es
esperar a dos servidores ajenos al mismo tiempo y juntar lo que contestan,
que es exactamente para lo que sirve Node.

Lo que **no** se movió, y a propósito:

- **Quién puede buscar.** Lo decide el campus, que es el único que sabe quién
  pregunta. Node no ve tokens ni roles.
- **El freno por persona.** Sigue en `rutas/biblioteca.py`, porque es por
  persona y acá todas las peticiones llegan con la misma cara.
- **Los favoritos.** Un libro externo se puede guardar, y eso es un dato del
  campus: vive en Firestore, no en Node.

La frontera, para quien migre Biblioteca a Django
-------------------------------------------------
**Estas dos funciones no cambian.** `rutas/biblioteca.py` las importa igual
que antes y con la misma firma, así que Biblioteca llama a este servicio
desde sus vistas de Django sin trasladar las rutas ni los permisos del campus
a Node.

Si el servicio no está levantado
--------------------------------
La biblioteca de la materia sigue funcionando entera; lo único que se cae es
la búsqueda en catálogos externos, y se cae **avisando**, con la misma forma
que cuando se cae Google: un estado de error en `fuentes`, que la pantalla ya
sabe mostrar. Es la misma regla de siempre: que una fuente ajena no deje sin
biblioteca al campus.
"""

from __future__ import annotations

import os

import httpx

# ===================== A dónde se le pregunta =====================
# El servicio escucha en la misma máquina y no se publica. Si algún día va a
# otro host, se cambia acá y nada más.
URL = os.environ.get("CATALOGOS_URL", "http://127.0.0.1:4000").rstrip("/")

# El secreto compartido. Si el servicio tiene CLAVE_INTERNA definida, acá
# tiene que estar la misma o contesta 401.
CLAVE = os.environ.get("CATALOGOS_CLAVE") or None

# Un poco más que la espera del servicio (9 s por fuente): el que tiene que
# cortar por tiempo es él, que sabe con qué se quedó, no nosotros.
ESPERA = 12.0

NOMBRE = "Catálogos externos"


def _cabeceras() -> dict[str, str]:
    return {"X-Clave-Interna": CLAVE} if CLAVE else {}


def _no_disponible(motivo: str) -> dict:
    """La misma forma que una fuente caída, para que la pantalla no distinga
    entre «Google no contesta» y «el servicio no está levantado»: las dos son
    «ahora no se puede buscar afuera»."""
    return {
        "libros": [],
        "fuentes": [{"fuente": "catalogos", "nombre": NOMBRE, "estado": "error", "error": motivo}],
        "desdeCache": False,
    }


async def _pedir(camino: str, parametros: dict) -> httpx.Response:
    async with httpx.AsyncClient(timeout=ESPERA, headers=_cabeceras()) as cliente:
        return await cliente.get(f"{URL}{camino}", params=parametros)


async def buscar_libros_externos(texto: str, campo: str = "todo", idioma: str | None = None) -> dict:
    """Busca en los catálogos externos. Devuelve `{libros, fuentes, desdeCache}`.

    Nunca levanta excepción: si el servicio no está o falla, el error viaja en
    `fuentes` y `libros` queda vacío.
    """
    limpio = (texto or "").strip()
    # Se corta acá y no se gasta una petición: con una letra no hay búsqueda
    # que sirva. El servicio hace la misma comprobación por su cuenta.
    if len(limpio) < 2:
        return {"libros": [], "fuentes": [], "desdeCache": False}

    parametros: dict[str, str] = {"texto": limpio, "campo": campo}
    if idioma:
        parametros["idioma"] = idioma

    try:
        respuesta = await _pedir("/catalogos/buscar", parametros)
    except httpx.HTTPError:
        return _no_disponible("el servicio de catálogos no responde")

    if respuesta.status_code == 429:
        return {
            "libros": [],
            "fuentes": [{"fuente": "catalogos", "nombre": NOMBRE, "estado": "limite"}],
            "desdeCache": False,
        }
    if respuesta.status_code != 200:
        return _no_disponible(f"el servicio de catálogos respondió {respuesta.status_code}")

    try:
        return respuesta.json()
    except ValueError:
        return _no_disponible("el servicio de catálogos contestó algo que no se entiende")


async def obtener_libro_externo(identificador: str) -> dict | None:
    """Un libro externo por su id («google:xxx» u «openlibrary:/works/OL1W»).

    `None` si no existe o si no se pudo averiguar. Quien llama ya contesta 404
    en ese caso, que es lo correcto: no sabemos si existe.
    """
    try:
        respuesta = await _pedir("/catalogos/libro", {"id": str(identificador)})
    except httpx.HTTPError:
        return None

    if respuesta.status_code != 200:
        return None

    try:
        return respuesta.json().get("libro")
    except ValueError:
        return None
