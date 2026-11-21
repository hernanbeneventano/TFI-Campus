"""Los dos frenos del campus: cuánto puede pesar una petición y cuántas van.

Por qué hacen falta
-------------------
El campus no tenía ninguno. Cualquiera con la dirección podía mandar
peticiones todo lo rápido que quisiera y cuerpos tan grandes como quisiera, y
las dos cosas tumban el servidor sin necesidad de encontrarle ningún error:
alcanza con insistir.

Pesa más de lo habitual porque **los archivos viajan en base64 adentro del
JSON**: una entrega de 20 MB son unos 27 MB de cuerpo, y el servidor los tiene
enteros en memoria para poder validarlos. Unas pocas subidas a la vez son
cientos de megas.

El tope de tamaño
-----------------
Se mira la cabecera `Content-Length` **antes** de leer el cuerpo: rechazarlo
después de recibirlo no evita nada, que es justamente lo que había que
evitar. Un cliente que no la mande se corta igual mientras lee.

El freno, y por qué no va por IP
--------------------------------
Una ventana que corre, en memoria. En memoria alcanza porque el campus es **un
solo proceso** (ver `main.py`); si algún día fueran varios, esto tendría que
vivir afuera, como la persistencia.

Lo que cuenta **no es la dirección sino la sesión**. En una facultad todas las
máquinas salen a internet por la misma IP, así que contar por dirección es
contar a toda la facultad junta: con treinta personas usando el campus desde
el laboratorio, el freno se dispara por usarlo bien. Se cuenta entonces por el
token que manda el navegador, que es una sesión. Para el que llega sin token
—que es quien puede estar abusando— se vuelve a la dirección.

El token no se verifica acá: solo se lo usa como etiqueta, y verificarlo
cuesta justamente lo que este freno quiere evitar. Se guarda su huella, no el
token: un valor que no hace falta guardar entero no se guarda entero.

Es un freno contra el abuso, no un control de acceso: quien usa el campus
normalmente no lo toca ni de lejos. Las consultas tienen su propio límite, más
alto, porque una pantalla hace varias al abrirse.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import deque

# Un cuerpo más grande que esto no se lee. Tiene que entrar la subida más
# pesada que el campus acepta —una entrega de 20 MB— más lo que agrega el
# base64 (un tercio) y el resto del JSON.
MAXIMO_MB = int(os.environ.get("PETICION_MAX_MB") or 30)
MAXIMO_BYTES = MAXIMO_MB * 1024 * 1024

VENTANA_SEGUNDOS = 60
# Por minuto y por dirección. Las de escritura son pocas de verdad: nadie
# guarda ciento veinte veces por minuto a mano.
MAXIMO_ESCRITURAS = int(os.environ.get("PETICIONES_ESCRITURA_POR_MINUTO") or 120)
# Las de lectura son muchas: abrir una pantalla puede ser diez.
MAXIMO_LECTURAS = int(os.environ.get("PETICIONES_LECTURA_POR_MINUTO") or 600)

METODOS_QUE_ESCRIBEN = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_visitas: dict[tuple[str, bool], deque[float]] = {}


def _limpiar_viejas(cola: deque[float], ahora: float) -> None:
    while cola and ahora - cola[0] > VENTANA_SEGUNDOS:
        cola.popleft()


def direccion_de(peticion) -> str:
    """De dónde viene. Detrás de un proxy, la primera de `X-Forwarded-For`."""
    reenviada = peticion.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return peticion.client.host if peticion.client else "desconocida"


def quien_es(peticion) -> str:
    """A quién se le cuenta esta petición: la sesión, o la dirección.

    Ver arriba: por dirección sola, una facultad entera cuenta como una sola
    persona.
    """
    cabecera = peticion.headers.get("authorization") or ""
    if cabecera.lower().startswith("bearer ") and len(cabecera) > 7:
        return "sesion:" + hashlib.sha256(cabecera[7:].strip().encode()).hexdigest()[:16]
    return "ip:" + direccion_de(peticion)


def demasiado_grande(peticion) -> bool:
    largo = peticion.headers.get("content-length")
    try:
        return largo is not None and int(largo) > MAXIMO_BYTES
    except ValueError:
        return False


def excede(peticion) -> bool:
    """Si esta dirección ya pasó su cupo del minuto. Anota la visita."""
    escribe = peticion.method.upper() in METODOS_QUE_ESCRIBEN
    tope = MAXIMO_ESCRITURAS if escribe else MAXIMO_LECTURAS

    clave = (quien_es(peticion), escribe)
    ahora = time.monotonic()
    cola = _visitas.setdefault(clave, deque())
    _limpiar_viejas(cola, ahora)

    if len(cola) >= tope:
        return True

    cola.append(ahora)
    return False


def olvidar_todo() -> None:
    """Para las pruebas: deja el contador en cero."""
    _visitas.clear()
