"""El puente: las rutas de un módulo de FastAPI, atendidas por Django.

Para los primeros módulos la lógica se pasó a mano a `app/servicios/` y se
escribió cada vista de Django. Funciona, pero son 145 rutas más y copiar código
a mano es justo donde se cuelan los errores. Todas las rutas del campus usan
las mismas pocas piezas —se relevó—:

- la sesión, con `identificar` o `identificar_id`;
- parámetros de camino y de consulta de tipos simples (texto, entero,
  booleano, opcionales o no);
- a lo sumo un cuerpo, que es un diccionario, obligatorio o con `{}`;
- en unas pocas, la petición entera (`Request`), para leer la consulta.

Con una superficie tan chica, la vista de Django se puede **armar leyendo la
definición de la ruta de FastAPI** en vez de escribirla. Este archivo lo hace:
la vista resuelve todo igual que FastAPI y después **llama a la misma función
de la ruta**. La lógica sigue estando una sola vez, en `app/rutas/`, y no se
toca: lo que el banco compara es exactamente el mismo código detrás.

Lo que respeta, porque el banco y las sondas mostraron que importa:

- **el camino**: la expresión regular que ya compiló Starlette, no los
  conversores de Django (`{x:path}` acepta vacío; `<path:x>` no);
- **una ruta de Django por cada ruta de FastAPI**, en el mismo orden y con su
  único método; entre las que comparten camino elige `como_starlette`;
- **el orden de los errores**: el JSON roto antes que la sesión (si la ruta
  declara cuerpo), la sesión antes que los parámetros;
- **los tipos y los valores por omisión** que declara la ruta, convertidos por
  pydantic igual que en FastAPI;
- **la respuesta**: el código de estado de la ruta y el JSON de
  `jsonable_encoder`, o la respuesta de Starlette tal cual si la ruta la arma.

El día que se retire FastAPI, las rutas de `app/rutas/` pierden sus
decoradores y quedan como las funciones que llama este puente.
"""

from __future__ import annotations

import asyncio
import copy

from asgiref.sync import async_to_sync
from django.urls import re_path
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse
from starlette.responses import Response as RespuestaStarlette

from app.servicios import auditoria

from .adaptadores import (
    OBLIGATORIO,
    _invalido,
    _va_como_json,
    consulta,
    convertir,
    cuerpo,
    de_starlette,
    responder,
    rutas,
)


def _rutas_de_fastapi(modulo: str) -> list[APIRoute]:
    """Las rutas de `app/rutas/<modulo>.py` (o de `app/main.py`, con «main»),
    en el orden en que las ve FastAPI."""
    from app.main import app

    nombre = "app.main" if modulo == "main" else f"app.rutas.{modulo}"
    return [r for r in app.routes if isinstance(r, APIRoute) and r.endpoint.__module__ == nombre]


def _por_omision(campo):
    if campo.field_info.is_required():
        return OBLIGATORIO
    return copy.deepcopy(campo.field_info.default)


def _vista(ruta: APIRoute):
    """La vista de Django de una ruta de FastAPI."""
    dp = ruta.dependant
    # Sin clase declarada FastAPI la guarda envuelta (`DefaultPlaceholder`)
    clase = getattr(ruta.response_class, "value", ruta.response_class)
    if not (isinstance(clase, type) and issubclass(clase, JSONResponse)):
        raise TypeError(f"{ruta.path}: el puente solo sabe responder JSON")
    # Lo que no usa ninguna ruta del campus: si aparece, mejor fallar al
    # arrancar que contestar distinto en silencio.
    if dp.header_params or dp.cookie_params or len(dp.body_params) > 1:
        raise TypeError(f"{ruta.path}: el puente no sabe leer cabeceras, cookies ni dos cuerpos")
    for sub in dp.dependencies:
        if sub.call.__name__ not in ("identificar", "identificar_id") or sub.dependencies:
            raise TypeError(f"{ruta.path}: el puente no conoce la dependencia {sub.call.__name__}")

    asincronica = asyncio.iscoroutinefunction(ruta.endpoint)
    estado = ruta.status_code or 200
    cuerpo_declarado = dp.body_params[0] if dp.body_params else None

    def vista(request, **del_camino):
        # 1. FastAPI lee el cuerpo antes que todo: un JSON roto es 400 ya
        if cuerpo_declarado is not None:
            crudo = request.body
            if crudo and _va_como_json(request):
                import json

                try:
                    json.loads(crudo)
                except ValueError:
                    raise _invalido() from None

        valores = {}
        # 2. La sesión, antes que los parámetros (401 antes que 400)
        for sub in dp.dependencies:
            valores[sub.name] = sub.call(request)

        # 3. Camino, consulta y cuerpo, con los tipos de la ruta
        for campo in dp.path_params:
            valores[campo.name] = convertir(del_camino[campo.alias], campo.field_info.annotation)
        for campo in dp.query_params:
            valores[campo.name] = consulta(
                request, campo.alias, campo.field_info.annotation, _por_omision(campo)
            )
        if cuerpo_declarado is not None:
            valores[cuerpo_declarado.name] = cuerpo(
                request, cuerpo_declarado.field_info.annotation, _por_omision(cuerpo_declarado)
            )
        if dp.request_param_name:
            # La de Starlette, armada con la misma petición por el middleware
            # compartido: las rutas la usan para leer la consulta.
            valores[dp.request_param_name] = auditoria.peticion_actual.get()

        # 4. La misma función que llama FastAPI
        resultado = (
            async_to_sync(ruta.endpoint)(**valores) if asincronica else ruta.endpoint(**valores)
        )
        if isinstance(resultado, RespuestaStarlette):
            return de_starlette(resultado)
        return responder(resultado, estado)

    vista.con_sesion = bool(dp.dependencies)
    vista.__name__ = ruta.endpoint.__name__
    vista.__doc__ = ruta.endpoint.__doc__
    return vista


def rutas_de(*modulos: str, caminos: set[str] | None = None) -> list:
    """Las rutas de Django de esos módulos de FastAPI, una por cada una.

    Con `caminos`, solo las de esos caminos (como los declara FastAPI).
    """
    salida = []
    for modulo in modulos:
        encontradas = _rutas_de_fastapi(modulo)
        if caminos is not None:
            encontradas = [r for r in encontradas if r.path in caminos]
        if not encontradas:
            raise LookupError(f"No hay rutas en app/rutas/{modulo}.py")
        for ruta in encontradas:
            metodos = {m.lower(): _vista(ruta) for m in ruta.methods - {"HEAD", "OPTIONS"}}
            # La misma expresión que compiló Starlette, sin la barra inicial
            # (Django compara el camino sin ella)
            camino = ruta.path_regex.pattern.replace("^/", "^", 1)
            salida.append(re_path(camino, rutas(**metodos)))
    return salida
