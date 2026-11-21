"""La dirección con la que se muestra la cara de alguien.

Vive aparte porque la necesitan los dos extremos: `datos.con_presencia`, que
es por donde pasa **toda** persona que el campus muestra, y la ruta que sirve
la imagen. No importa `datos`, justamente para que `datos` pueda importarla
sin dar una vuelta circular.

Por qué la dirección va firmada
-------------------------------
Una etiqueta `<img>` no manda la cabecera `Authorization`. Con la sesión como
único control, cada avatar del campus daba 401 y se veía la silueta.

Las salidas eran tres: que el navegador baje cada cara con `fetch` y la
convierta en un objeto en memoria —en una lista de treinta participantes son
treinta descargas que no se pueden cachear—; abrir la ruta a cualquiera; o
que **la dirección sea la credencial**, que es lo que hacen los enlaces
firmados de Cloudflare R2 y lo que se hace acá.

La firma sale de la clave del archivo y de un secreto del servidor, así que
no se puede fabricar a partir del número de persona. Solo viaja en respuestas
que ya pasaron por el control de sesión, y **cambia sola cuando alguien
cambia su foto**: la dirección vieja deja de servir.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

# Sale de la configuración si está, y si no se genera uno al arrancar. En ese
# caso las direcciones cambian con cada reinicio, lo que solo cuesta un pedido
# más por cara la primera vez; definir `FIRMA_FOTOS` las hace estables y
# aprovecha mejor la caché del navegador.
_SECRETO = (os.environ.get("FIRMA_FOTOS") or secrets.token_hex(32)).encode()


def firma(objeto: str) -> str:
    """Doce caracteres alcanzan: hay que adivinarlos **y** acertar la foto."""
    return hmac.new(_SECRETO, objeto.encode(), hashlib.sha256).hexdigest()[:12]


def direccion_de_archivo(objeto: str) -> str:
    """La dirección con la que la pantalla muestra o baja ese archivo.

    Misma idea que la foto de perfil: la dirección lleva la firma, así que
    sirve dentro de un `<img>` o de un `<iframe>` sin tener que agregarle la
    cabecera de sesión, y no se puede fabricar para un archivo ajeno.

    La firma va **en el camino y no en la consulta**. Con `?o=…&f=…` los
    bloqueadores de publicidad cancelaban el pedido —`ERR_BLOCKED_BY_CLIENT`,
    porque una dirección con parámetros y un archivo adentro se parece a un
    rastreador—, y el apunte no se veía sin que nada dijera por qué.
    """
    from urllib.parse import quote

    return f"/api/archivos/{firma(objeto)}/{quote(objeto)}"


def direccion(persona: dict) -> str | None:
    """La dirección con la que la pantalla muestra esa cara, o `None`."""
    objeto = persona.get("foto")
    if not objeto:
        return None
    return f"/api/usuarios/{persona['id']}/foto?f={firma(objeto)}"
