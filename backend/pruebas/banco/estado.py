"""La memoria del campus: sacarle una foto y volver a dejarla como estaba.

Por qué no alcanza `escenario.cargar()`
---------------------------------------
Parece un reinicio y no lo es. Repone las 36 colecciones que están en
`datos_de_prueba.json` y deja afuera las otras cuatro —`carreras_institucion`,
`favoritos_modulo`, `archivos_subidos`, `cierres_cursada`— más los contadores
`_proximos`.

Se ve enseguida: el mismo `POST /api/institucion/carreras` da 201 la primera
vez y 409 la segunda, porque la carrera de la primera sigue ahí. Y
`/api/cursos/1/favorito` alterna entre marcado y desmarcado.

Para el banco eso es fatal: si las dos aplicaciones no arrancan del mismo
estado, **toda** diferencia que encuentre es ruido y el banco deja de servir
para lo único que existe. Así que acá se copia el campus entero y se lo
repone entero.

Cómo se repone
--------------
Reemplazando **el contenido**, nunca la variable: los módulos hicieron
`from .. import datos as d` y se quedaron con la referencia, así que
asignarle otra lista a `d.personas` no los alcanzaría. Es el mismo cuidado
que ya tienen `persistencia.cargar()` y `escenario.cargar()`.

De dónde sale la lista de qué copiar
------------------------------------
De `persistencia.REGISTROS`, que es donde el campus ya declara todo lo que
hay que guardar. Si alguien agrega una colección y la anota ahí para que se
persista —que es obligatorio, lo cuida `pruebas/persistencia.py`— el banco la
copia sin que nadie se acuerde de tocar este archivo.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from app import datos as d
from app.servicios import persistencia


def _colecciones() -> list[str]:
    """Los atributos de `datos.py` que forman el estado del campus."""
    nombres = {atributo for atributo, _clave in persistencia.REGISTROS.values()}
    nombres |= set(persistencia.POR_CURSO.values())
    nombres |= set(persistencia.CONFIGURACION)
    return sorted(nombres)


def tomar() -> dict[str, Any]:
    """Una copia profunda del campus entero."""
    foto: dict[str, Any] = {}
    for nombre in _colecciones():
        valor = getattr(d, nombre, None)
        if valor is not None:
            foto[nombre] = copy.deepcopy(valor)

    # Los contadores también: si no, la segunda corrida le pone otros
    # identificadores a lo que cree, y el banco marcaría una diferencia que
    # no existe.
    foto["_proximos"] = dict(d._proximos)

    # Y los bytes que el campus tenga guardados en memoria, que es donde caen
    # los archivos cuando R2 no está configurado —el caso de las pruebas—.
    archivos = getattr(d, "_archivos", None)
    if isinstance(archivos, dict):
        foto["_archivos"] = dict(archivos)

    return foto


def reponer(foto: dict[str, Any]) -> None:
    """Deja el campus exactamente como estaba cuando se sacó la foto."""
    for nombre, guardado in foto.items():
        if nombre == "_proximos":
            d._proximos.clear()
            d._proximos.update(guardado)
            continue
        if nombre == "_archivos":
            actual = getattr(d, "_archivos", None)
            if isinstance(actual, dict):
                actual.clear()
                actual.update(guardado)
            continue

        actual = getattr(d, nombre, None)
        copia = copy.deepcopy(guardado)
        if isinstance(actual, list):
            actual[:] = copia
        elif isinstance(actual, dict):
            actual.clear()
            actual.update(copia)
        else:
            setattr(d, nombre, copia)


def huella() -> str:
    """Una firma del estado, para comparar **lo que cada servidor escribió**.

    Dos servidores pueden contestar lo mismo y guardar cosas distintas; eso
    es un error igual de grave y no se ve mirando la respuesta. La huella
    deja compararlo sin tener que recorrer cuarenta colecciones a mano.
    """
    crudo = json.dumps(tomar(), sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:16]


def comparable(foto: dict[str, Any]) -> dict[str, Any]:
    """La foto lista para comparar: sin lo que cambia solo.

    Va por la misma vara que las respuestas. Sin esto, cualquier cosa que
    escriba marca diferencia, porque la fecha se sella con el reloj y el
    registro de auditoría anota una entrada propia en cada petición.
    """
    from . import normalizar

    return normalizar.aplicar(foto, camino="campus")
