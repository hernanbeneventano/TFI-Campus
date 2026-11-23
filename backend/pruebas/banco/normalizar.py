"""Lo que cambia solo, y que por eso no se compara.

Hay valores que son distintos en cada respuesta aunque el campus se comporte
igual: una fecha que se arma con el reloj, un identificador que sale de un
contador, el número de arranque del servidor. Compararlos marcaría
diferencias en todos lados y el banco se volvería ruido que nadie mira.

**Se reemplazan, no se borran.** Un campo que se saca de las dos respuestas
deja de poder detectarse cuando falta en una sola, y «el campo desapareció»
es justamente uno de los errores que el banco tiene que encontrar. Así que
donde había una fecha queda `<fecha>`: si en la otra respuesta no está el
campo, la diferencia sigue saltando.

Qué se normaliza y por qué
--------------------------
La lista no se inventó: salió de pedirle doce veces los mismos recursos al
mismo servidor y mirar qué cambiaba solo. El único campo inestable entre dos
llamadas idénticas resultó ser `ultimoAcceso`. A eso se le suman los que
cambian entre dos servidores distintos aunque no cambien dentro de uno:

- `instancia`, que se sortea en cada arranque para que el navegador sepa que
  el servidor se reinició;
- las fechas de lo que se crea durante la petición;
- las direcciones firmadas con un tramo al azar adentro (los adjuntos de un
  mensaje llevan `secrets.token_hex(4)` en la clave del objeto).

Los identificadores **no** se normalizan por defecto. Salen de contadores que
el banco repone antes de cada caso, así que tienen que coincidir: si no
coinciden, es que una de las dos aplicaciones creó algo de más y eso hay que
verlo, no taparlo.
"""

from __future__ import annotations

import re
from typing import Any

# Campos cuyo valor cambia solo. Se comparan por presencia, no por contenido.
POR_NOMBRE: frozenset[str] = frozenset({
    # Se calcula con el reloj en cada pedido (ver `datos.con_presencia`)
    "ultimoAcceso",
    # Se sortea en cada arranque del servidor
    "instancia",
    # Momentos que se sellan al escribir
    "fecha", "cuando", "creada", "registradaEl", "editado", "subidoEl", "desde",
    # Presencia: depende de hace cuánto fue el último acceso
    "estadoPresencia",
})

# Caminos concretos, cuando el nombre solo sería demasiado ancho. Se escriben
# como aparecen en el informe: `cuerpo.usuario.foto`.
POR_CAMINO: frozenset[str] = frozenset()

# Pedazos de texto que cambian solos aunque el campo no esté en la lista.
TEXTO_VARIABLE: tuple[tuple[str, re.Pattern], ...] = (
    # La firma de una dirección de archivo y el tramo al azar de su clave
    ("<firma>", re.compile(r"/api/archivos/[0-9a-f]{8,}/")),
    ("<azar>", re.compile(r"/[0-9a-f]{8}/(?=[^/]+$)")),
    # Fechas ISO sueltas dentro de un texto
    ("<fecha>", re.compile(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z?")),
)

MARCA = "<variable>"


def _texto(valor: str) -> str:
    for marca, patron in TEXTO_VARIABLE:
        valor = patron.sub(marca, valor)
    return valor


def aplicar(valor: Any, camino: str = "cuerpo", extra: frozenset[str] = frozenset()) -> Any:
    """Devuelve el valor con lo variable reemplazado por una marca."""
    if isinstance(valor, dict):
        # Las claves también: lo guardado se indexa por la clave del objeto, y
        # la de un adjunto de Mensajes lleva un tramo al azar. FastAPI contra
        # sí mismo ya daba distinto. El contenido se sigue comparando.
        return {
            (_texto(k) if isinstance(k, str) else k): (
                MARCA
                if (k in POR_NOMBRE or k in extra or f"{camino}.{k}" in POR_CAMINO)
                else aplicar(v, f"{camino}.{k}", extra)
            )
            for k, v in valor.items()
        }
    if isinstance(valor, list):
        return [aplicar(v, f"{camino}[{i}]", extra) for i, v in enumerate(valor)]
    if isinstance(valor, str):
        return _texto(valor)
    return valor


# ===================== Las cabeceras =====================
# No se comparan todas: `date`, `server` y el largo cambian siempre y no
# dicen nada. Estas sí, porque cada una es una decisión del campus y que se
# pierda al migrar es un error que no se ve mirando el cuerpo.
CABECERAS: tuple[str, ...] = (
    "content-type",
    "content-disposition",
    "x-content-type-options",
    "content-security-policy",
    "cache-control",
    "retry-after",
    # A dónde lleva un 307: FastAPI saca la barra final con una dirección
    # absoluta, y Django por omisión haría otra cosa.
    "location",
    # El cuerpo se compara interpretado, así que dos JSON que se leen igual
    # pasan aunque uno tenga espacios o los acentos escapados. El largo los
    # delata: es la única forma de ver una diferencia de bytes desde acá.
    "content-length",
    # Qué métodos acepta, en un 405. Starlette la arma con la primera ruta que
    # coincide en camino, y cada ruta de FastAPI tiene un solo método: juntar
    # dos en una misma vista de Django la cambiaba sin que se viera.
    "allow",
)


def cabeceras_de(respuesta) -> dict[str, str]:
    crudas = {k.lower(): v for k, v in respuesta.headers.items()}
    salida = {k: _texto(crudas[k]) for k in CABECERAS if k in crudas}
    # El largo de un .xlsx cambia solo: va comprimido y adentro lleva la hora
    # de cada evento, así que un segundo distinto comprime con un byte más o
    # menos. Se midió: FastAPI contra sí mismo daba 2197 y 2201 en dos
    # corridas. El contenido sí se compara entero, XML por XML (ver
    # `__main__._cuerpo_de`), así que el largo no agrega nada y solo mete ruido.
    if "spreadsheetml" in crudas.get("content-type", "") and "content-length" in salida:
        salida["content-length"] = MARCA
    return salida
