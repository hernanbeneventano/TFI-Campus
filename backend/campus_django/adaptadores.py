"""Lo que hace falta para que una vista de Django conteste igual que FastAPI.

FastAPI hace solo muchas cosas que Django no: convierte y valida los
parámetros, lee el cuerpo como JSON, rechaza los métodos que no van, arma el
JSON de la respuesta. Cada una es un lugar donde una migración puede
contestar distinto sin que nadie lo note.

La regla de este archivo: **usar las herramientas de FastAPI, no imitarlas.**
Mientras conviven, la conversión la hace `pydantic` —el mismo motor que usa
FastAPI—, el JSON lo arman su `jsonable_encoder` y el `JSONResponse` de
Starlette, y los errores se lanzan con las mismas excepciones, que formatean
los mismos manejadores. Una imitación sale parecida; esto sale igual. El día
que FastAPI se vaya, este es el único archivo que hay que reescribir, y el
banco de comparación dice si quedó igual.

Lo que no está acá porque no hace falta
---------------------------------------
El freno, la auditoría, el guardado, el CORS y el formato de los errores:
las peticiones que van a Django pasan por la misma pila que FastAPI (ver
`despachador.py`).

Cómo se escribe una vista
-------------------------
    @con_sesion
    def ver_curso(request, yo, id_curso):
        curso = cursos.obtener(entero(id_curso), yo)   # misma lógica de app/
        return responder(curso)

    urlpatterns = [path("api/cursos/<str:id_curso>", rutas(get=ver_curso))]
"""

from __future__ import annotations

import email.message
import json
from functools import wraps
from typing import Any, Callable

from django.http import HttpResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import TypeAdapter, ValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response

from app.servicios.autenticacion import identificar

OBLIGATORIO = object()


# ===================== Las respuestas =====================
def de_starlette(respuesta: Response) -> HttpResponse:
    """Una respuesta de Starlette pasada a Django sin cambiarle nada.

    Django pone `text/html; charset=utf-8` si no se le dice otra cosa, y una
    respuesta de Starlette puede no tener `content-type` (una redirección).
    Se copian las cabeceras tal cual y se saca la que Django agregó por su
    cuenta.
    """
    salida = HttpResponse(content=respuesta.body, status=respuesta.status_code)
    del salida["Content-Type"]
    for nombre, valor in respuesta.headers.items():
        salida[nombre] = valor
    return salida


def responder(valor: Any, estado: int = 200, cabeceras: dict | None = None) -> HttpResponse:
    """El JSON exactamente como lo arma FastAPI.

    FastAPI pasa lo que devuelve la ruta por `jsonable_encoder` y lo escribe
    con `JSONResponse`: sin espacios, con los acentos tal cual y sin
    `charset` en el tipo. `JsonResponse` de Django lo escribe con espacios y
    los acentos escapados, que el navegador lee igual pero no es lo mismo: el
    largo cambia, y una respuesta grabada deja de coincidir.
    """
    return de_starlette(
        JSONResponse(content=jsonable_encoder(valor), status_code=estado, headers=cabeceras)
    )


def descargar(contenido: bytes, tipo: str, cabeceras: dict | None = None) -> HttpResponse:
    """Un archivo para bajar, con los mismos bytes y cabeceras que FastAPI.

    Se arma con la `Response` de Starlette —la que devuelve la ruta de
    FastAPI— y se pasa tal cual: así el `content-type` lleva o no su
    `charset` exactamente igual, y el largo coincide.
    """
    return de_starlette(Response(content=contenido, media_type=tipo, headers=cabeceras))


# ===================== La validación =====================
def _invalido() -> RequestValidationError:
    """La misma excepción que lanza FastAPI cuando un dato no valida.

    El manejador del campus la convierte en 400 con «Los datos enviados no son
    válidos», así que no importa qué dato falló: el mensaje es el mismo.
    """
    return RequestValidationError(errors=[])


def convertir(valor: Any, tipo: Any) -> Any:
    """Convierte con las reglas de FastAPI, que son las de `pydantic`."""
    try:
        return TypeAdapter(tipo).validate_python(valor)
    except ValidationError:
        raise _invalido() from None


def entero(valor: Any) -> int:
    """Un parámetro de camino que tiene que ser entero.

    En `urls.py` los parámetros van como `<str:...>`, no `<int:...>`: con
    `<int:>` un identificador no numérico daría 404 y hoy da 400.
    """
    return convertir(valor, int)


def consulta(request, nombre: str, tipo: Any = str, defecto: Any = OBLIGATORIO) -> Any:
    """Un parámetro de la consulta (`?pagina=2`).

    Si se repite gana el último, igual que en FastAPI. Si falta y no tiene
    valor por omisión, es un 400, igual que en FastAPI.
    """
    if nombre not in request.GET:
        if defecto is OBLIGATORIO:
            raise _invalido()
        return defecto
    return convertir(request.GET.get(nombre), tipo)


def parametros(request) -> dict[str, str]:
    """Todos los parámetros de la consulta, como `dict(request.query_params)`.

    Con uno repetido gana el último, igual que en Starlette, y uno vacío
    (`?q=`) llega como texto vacío. Para las rutas que reciben los filtros
    sueltos en vez de declararlos uno por uno.
    """
    return request.GET.dict()


def cuerpo(request, tipo: Any = dict, defecto: Any = OBLIGATORIO) -> Any:
    """El cuerpo de la petición, leído como lo lee FastAPI.

    La regla es la de `fastapi.routing`: se intenta leer como JSON si no hay
    tipo declarado o si el tipo es `application/json` (o `+json`). Con otro
    tipo de contenido el cuerpo queda en bytes, y entonces no valida como
    diccionario. Un JSON roto es un 400, y un cuerpo que falta también, salvo
    que la ruta tenga un valor por omisión (`Body(default={})`).
    """
    crudo = request.body
    if not crudo:
        if defecto is OBLIGATORIO:
            raise _invalido()
        return defecto

    valor: Any = crudo
    tipo_contenido = request.headers.get("content-type")
    leer_json = not tipo_contenido
    if tipo_contenido:
        mensaje = email.message.Message()
        mensaje["content-type"] = tipo_contenido
        if mensaje.get_content_maintype() == "application":
            subtipo = mensaje.get_content_subtype()
            leer_json = subtipo == "json" or subtipo.endswith("+json")
    if leer_json:
        try:
            valor = json.loads(crudo)
        except ValueError:
            raise _invalido() from None

    return convertir(valor, tipo)


# ===================== La sesión =====================
def con_sesion(vista: Callable) -> Callable:
    """La vista recibe a la persona que hace la consulta, como `UsuarioActual`.

    Es `identificar()` —la misma función que usa FastAPI—, así que valen el
    token de Firebase, el estado de la cuenta y la suplantación de las
    pruebas. Corre **antes** que la vista, y por lo tanto antes de convertir
    los parámetros: sin sesión y con un parámetro inválido, FastAPI contesta
    401 y no 400, y acá tiene que pasar lo mismo.

    Toda vista lleva esto salvo las públicas (la salud del servidor, los
    archivos y las fotos firmadas). Una prueba lo verifica: olvidarse es
    dejar una ruta abierta, y ya pasó.
    """

    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        yo = identificar(request)
        return vista(request, yo, *args, **kwargs)

    envuelta.con_sesion = True
    return envuelta


# ===================== Los métodos =====================
def rutas(**vistas: Callable) -> Callable:
    """Una ruta que atiende varios métodos, cada uno con su vista.

        rutas(get=listar, post=crear)

    Como en FastAPI, un método que la ruta no tiene es un 405 con
    `{"error": "Method Not Allowed"}`. Django no trae nada de esto: una vista
    suelta atiende cualquier método.

    **El GET no atiende HEAD.** Starlette sí lo agrega solo, y era fácil
    suponer que FastAPI también; no lo hace: sus `APIRoute` registran
    exactamente los métodos declarados, y `HEAD /api/salud` da 405 en el
    servidor de hoy. Lo encontró `pruebas/adaptadores.py`.
    """
    por_metodo = {metodo.upper(): vista for metodo, vista in vistas.items()}
    permitidos = ", ".join(sorted(por_metodo))

    def atender(request, *args, **kwargs):
        vista = por_metodo.get(request.method.upper())
        if vista is None:
            raise HTTPException(status_code=405, headers={"Allow": permitidos})
        return vista(request, *args, **kwargs)

    atender.por_metodo = por_metodo
    return atender
