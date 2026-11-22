"""El juego de datos con el que corren las pruebas.

Las pruebas **no usan los datos que trae la aplicación**, y eso es a
propósito. El campus arranca vacío: sin estudiantes inscriptos, sin módulos,
sin mesas de examen. Es lo correcto para una instalación nueva, pero deja a
las pruebas sin nada sobre lo que comprobar nada.

Antes las suites se apoyaban en los datos de ejemplo que venían en
`datos_iniciales.json`. Al vaciarlos, las cuatro se cayeron de golpe: no
porque el campus estuviera roto, sino porque habían perdido su escenario. Un
juego de pruebas que depende de lo que la aplicación muestre se rompe cada
vez que cambian los datos de muestra, que es justamente lo que pasó.

Ahora el escenario vive acá, en `datos_de_prueba.json`, y es de las pruebas.
Tiene un campus poblado: diecinueve personas, seis módulos con contenido, diez
mesas de examen en todos sus estados, asistencias, notas e inscripciones.

`cargar()` lo mete en memoria **en el proceso de la prueba**, reemplazando lo
que haya. No toca ningún archivo: el campus de verdad sigue vacío.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from app import datos as d

ARCHIVO = Path(__file__).resolve().parent / "datos_de_prueba.json"


def cargar() -> None:
    """Deja el escenario de prueba en memoria.

    Se reemplaza **el contenido** de cada lista y diccionario, no la variable:
    los módulos del campus hicieron `from .. import datos as d` y guardaron la
    referencia, así que cambiar `d.personas = [...]` no los alcanzaría.
    """
    crudo = json.loads(io.open(ARCHIVO, encoding="utf-8").read())
    # Las fechas del archivo son relativas ({"__fecha": "aDias", "n": -400}),
    # igual que en los datos de la aplicación: `_resolver` las convierte a la
    # fecha de hoy, así el escenario sigue teniendo sentido con el correr de
    # los meses.
    escenario = d._resolver(crudo)

    for clave, valor in escenario.items():
        nombre = _nombre_python(clave)
        actual = getattr(d, nombre, None)

        if isinstance(actual, list) and isinstance(valor, list):
            actual[:] = valor
        elif isinstance(actual, dict) and isinstance(valor, dict):
            actual.clear()
            # Las claves numéricas vuelven a ser números: en JSON son texto,
            # y `contenidos`, `anuncios` y `participantes` se buscan por el
            # id del módulo, que es un entero. Sin esto el escenario cargaba
            # las carpetas con la clave "1" y `contenidos.get(1)` no
            # encontraba nada: los módulos quedaban sin contenido y ninguna
            # prueba lo notaba, porque ninguna lo miraba.
            actual.update({_como_clave(k): v for k, v in valor.items()})

    # Los contadores de identificadores arrancan en 100 y no hace falta
    # tocarlos: los del escenario son más bajos, así que una alta nueva nunca
    # pisa algo que ya está.


def _como_clave(clave):
    """"12" vuelve a ser 12; "minimoPorDefecto" se queda como está."""
    if isinstance(clave, str) and clave.lstrip("-").isdigit():
        return int(clave)
    return clave


def _nombre_python(clave: str) -> str:
    """De "asociacionesAcademicas" a "asociaciones_academicas".

    Las constantes van en mayúsculas en los dos lados y no se tocan.
    """
    if clave.isupper():
        return clave
    salida = []
    for letra in clave:
        if letra.isupper():
            salida.append("_")
            salida.append(letra.lower())
        else:
            salida.append(letra)
    return "".join(salida)
