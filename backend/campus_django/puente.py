"""El puente: las rutas anotadas en `app/rutas/`, atendidas por Django.

Las rutas del campus se declaran con `app/web.py` —`@router.get(...)`, con
`Body`, `Query` y `Depends` en la firma—, la misma forma que tenían con
FastAPI. Este archivo lee esas anotaciones y arma la vista de Django de cada
una, que resuelve los parámetros y **llama a la misma función**. La lógica
está una sola vez, en `app/rutas/`.

Las reglas son las que aplicaba FastAPI, y están verificadas contra lo que él
contestaba (el banco, contra su grabación):

- **el camino**: la expresión que armaba Starlette (`{x}` es un tramo, `{x:path}`
  cualquier cosa, también vacía), no los conversores de Django;
- **una ruta de Django por cada ruta anotada**, en el mismo orden y con su
  único método; entre las que comparten camino elige `como_starlette`;
- **de dónde sale cada parámetro**: `Depends` es la sesión; `Body`, el cuerpo;
  `Query`, la consulta; uno que aparece en el camino, del camino; uno sin
  marca que no está en el camino, de la consulta; un diccionario sin marca,
  el cuerpo; `request`, la petición entera;
- **el orden de los errores**: el JSON roto antes que la sesión (si la ruta
  recibe cuerpo), la sesión antes que los parámetros;
- **los tipos y los valores por omisión** de la firma, convertidos por pydantic;
- **la respuesta**: el código de la ruta y el JSON de `app/web.a_json`, o la
  respuesta tal cual si la ruta la arma (`Response`).

Lo que no sabe hacer, falla al armar las rutas y no al contestar.
"""

from __future__ import annotations

import asyncio
import copy
import inspect
import json
import re
import typing

from asgiref.sync import async_to_sync
from django.urls import re_path

from app.servicios import auditoria
from app.web import Response, Ruta, _Consulta, _Cuerpo, _Dependencia

from .adaptadores import (
    OBLIGATORIO,
    _invalido,
    _va_como_json,
    consulta,
    convertir,
    cuerpo,
    de_web,
    responder,
    rutas,
)

# Los conversores de camino de Starlette
_PARAMETRO = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")
_CONVERSORES = {"str": "[^/]+", "path": ".*", "int": "[0-9]+"}


def expresion_de(camino: str) -> str:
    """La expresión de un camino, como `starlette.routing.compile_path`."""
    salida, desde = "^", 0
    for encontrado in _PARAMETRO.finditer(camino):
        nombre, tipo = encontrado.groups()
        salida += re.escape(camino[desde : encontrado.start()])
        salida += f"(?P<{nombre}>{_CONVERSORES[(tipo or ':str')[1:]]})"
        desde = encontrado.end()
    return salida + re.escape(camino[desde:]) + "$"


def _parametros_de_camino(camino: str) -> set[str]:
    return {m.group(1) for m in _PARAMETRO.finditer(camino)}


def _es_diccionario(tipo: typing.Any) -> bool:
    return tipo is dict or typing.get_origin(tipo) is dict


def _por_omision(defecto: typing.Any) -> typing.Any:
    return OBLIGATORIO if defecto is ... else copy.deepcopy(defecto)


def _vista(ruta: Ruta):
    """La vista de Django de una ruta anotada."""
    funcion = ruta.funcion
    firma = inspect.signature(funcion)
    tipos = typing.get_type_hints(funcion)
    del_camino = _parametros_de_camino(ruta.camino)

    dependencias, de_camino, de_consulta = [], [], []
    del_cuerpo = None
    peticion_entera = None
    for nombre, parametro in firma.parameters.items():
        anotado = parametro.default
        tipo = tipos.get(nombre, typing.Any)
        if isinstance(anotado, _Dependencia):
            dependencias.append((nombre, anotado.funcion))
        elif isinstance(anotado, _Cuerpo):
            del_cuerpo = (nombre, tipo, _por_omision(anotado.default))
        elif nombre in del_camino:
            de_camino.append((nombre, tipo))
        elif isinstance(anotado, _Consulta):
            de_consulta.append((nombre, tipo, _por_omision(anotado.default)))
        elif parametro.annotation in ("Request", "Request | None") or nombre == "request":
            peticion_entera = nombre
        elif _es_diccionario(tipo):
            defecto = OBLIGATORIO if anotado is inspect.Parameter.empty else copy.deepcopy(anotado)
            del_cuerpo = (nombre, tipo, defecto)
        else:
            defecto = OBLIGATORIO if anotado is inspect.Parameter.empty else anotado
            de_consulta.append((nombre, tipo, defecto))
    for dependencia in dependencias:
        if dependencia[1].__name__ not in ("identificar", "identificar_id"):
            raise TypeError(f"{ruta.camino}: el puente no conoce la dependencia {dependencia[1].__name__}")

    asincronica = asyncio.iscoroutinefunction(funcion)
    estado = ruta.estado or 200

    def vista(request, **del_pedido):
        # 1. El cuerpo antes que todo: un JSON roto es 400 ya
        if del_cuerpo is not None:
            crudo = request.body
            if crudo and _va_como_json(request):
                try:
                    json.loads(crudo)
                except ValueError:
                    raise _invalido() from None

        valores = {}
        # 2. La sesión, antes que los parámetros (401 antes que 400)
        for nombre, resolver in dependencias:
            valores[nombre] = resolver(request)

        # 3. Camino, consulta y cuerpo, con los tipos de la firma
        for nombre, tipo in de_camino:
            valores[nombre] = convertir(del_pedido[nombre], tipo)
        for nombre, tipo, defecto in de_consulta:
            valores[nombre] = consulta(request, nombre, tipo, copy.deepcopy(defecto))
        if del_cuerpo is not None:
            nombre, tipo, defecto = del_cuerpo
            valores[nombre] = cuerpo(request, tipo, defecto)
        if peticion_entera:
            # La que armaron las capas del servidor con la misma petición
            valores[peticion_entera] = auditoria.peticion_actual.get()

        # 4. La función de la ruta
        resultado = async_to_sync(funcion)(**valores) if asincronica else funcion(**valores)
        if isinstance(resultado, Response):
            return de_web(resultado)
        return responder(resultado, estado)

    vista.con_sesion = bool(dependencias)
    vista.__name__ = funcion.__name__
    vista.__doc__ = funcion.__doc__
    return vista


def rutas_de(*modulos: str, caminos: set[str] | None = None) -> list:
    """Las rutas de Django de esos módulos (`app/rutas/<modulo>.py`, o «main»).

    Con `caminos`, solo las de esos caminos (como se anotaron).
    """
    from app.main import MODULOS

    salida = []
    for modulo in modulos:
        encontradas = MODULOS[modulo].rutas
        if caminos is not None:
            encontradas = [r for r in encontradas if r.camino in caminos]
        if not encontradas:
            raise LookupError(f"No hay rutas en {modulo}")
        for ruta in encontradas:
            # La misma expresión que armaba Starlette, sin la barra inicial
            # (Django compara el camino sin ella)
            patron = expresion_de(ruta.camino).replace("^/", "^", 1)
            salida.append(re_path(patron, rutas(**{ruta.metodo.lower(): _vista(ruta)})))
    return salida
