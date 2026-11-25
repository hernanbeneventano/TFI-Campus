"""Lo que hace falta para que una vista de Django conteste como el campus.

Django no hace solo varias cosas que el campus da por sentadas: convertir y
validar los parámetros, leer el cuerpo como JSON, rechazar los métodos que no
van, armar el JSON de la respuesta. Cada una es un lugar donde se puede
contestar distinto sin que nadie lo note.

Estas reglas salieron de la migración desde FastAPI, que las hacía solas, y
se verificaron contra lo que él contestaba, sonda por sonda
(`pruebas/adaptadores.py`, contra la grabación). La conversión de los datos la
hace `pydantic`; el JSON y las respuestas, `app/web.py`.

Lo que no está acá porque no hace falta
---------------------------------------
El freno, la auditoría, el guardado, el CORS y el formato de los errores: son
capas que envuelven a Django (`campus_django/asgi.py`).

Cómo se escribe una vista
-------------------------
    @con_sesion
    def ver_curso(request, yo, id_curso):
        curso = cursos.obtener(entero(id_curso), yo)   # misma lógica de app/
        return responder(curso)

    urlpatterns = [path("api/cursos/<str:id_curso>", rutas(get=ver_curso))]

La mayoría de las vistas no se escriben: las arma `puente.py` desde las rutas
anotadas en `app/rutas/`.
"""

from __future__ import annotations

import copy
import email.message
import json
from functools import wraps
from typing import Any, Callable

from django.http import HttpResponse
from pydantic import TypeAdapter, ValidationError

from app.web import ErrorDeValidacion, HTTPException, JSONResponse, Response, a_json

from app.servicios.autenticacion import identificar

OBLIGATORIO = object()


# ===================== Las respuestas =====================
def de_web(respuesta: Response) -> HttpResponse:
    """Una respuesta de Starlette pasada a Django sin cambiarle nada.

    Django pone `text/html; charset=utf-8` si no se le dice otra cosa, y una
    respuesta de Starlette puede no tener `content-type` (una redirección).
    Se copian las cabeceras tal cual y se saca la que Django agregó por su
    cuenta.
    """
    salida = HttpResponse(content=respuesta.body, status=respuesta.status_code)
    del salida["Content-Type"]
    for nombre, valor in respuesta.cabeceras:
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
    return de_web(JSONResponse(a_json(valor), estado, cabeceras))


def descargar(contenido: bytes, tipo: str, cabeceras: dict | None = None) -> HttpResponse:
    """Un archivo para bajar, con los mismos bytes y cabeceras que FastAPI.

    Se arma con la `Response` de Starlette —la que devuelve la ruta de
    FastAPI— y se pasa tal cual: así el `content-type` lleva o no su
    `charset` exactamente igual, y el largo coincide.
    """
    return de_web(Response(contenido, headers=cabeceras, media_type=tipo))


# ===================== La validación =====================
def _invalido() -> ErrorDeValidacion:
    """La misma excepción que lanza FastAPI cuando un dato no valida.

    El manejador del campus la convierte en 400 con «Los datos enviados no son
    válidos», así que no importa qué dato falló: el mensaje es el mismo.
    """
    return ErrorDeValidacion()


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


def _va_como_json(request) -> bool:
    """Si FastAPI leería este cuerpo como JSON: sin tipo de contenido, o con
    `application/json` o un `+json`. Si no, lo deja en bytes."""
    tipo_contenido = request.headers.get("content-type")
    if not tipo_contenido:
        return True
    mensaje = email.message.Message()
    mensaje["content-type"] = tipo_contenido
    if mensaje.get_content_maintype() != "application":
        return False
    subtipo = mensaje.get_content_subtype()
    return subtipo == "json" or subtipo.endswith("+json")


def con_cuerpo(vista: Callable) -> Callable:
    """Para las vistas que reciben cuerpo: un JSON roto es 400 **antes** de
    mirar la sesión, como en FastAPI.

    FastAPI lee el cuerpo de la ruta antes de resolver sus dependencias, así
    que `POST` sin sesión y con un JSON roto da 400 y no 401. Pasaba en
    `/api/archivos/confirmar`. Solo lo hace si la ruta declara un cuerpo, por
    eso es un decorador aparte y no va en `con_sesion`. Va **por fuera**:

        @con_cuerpo
        @con_sesion
        def confirmar(request, yo): ...
    """

    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        crudo = request.body
        if crudo and _va_como_json(request):
            try:
                json.loads(crudo)
            except ValueError:
                raise _invalido() from None
        return vista(request, *args, **kwargs)

    envuelta.con_sesion = getattr(vista, "con_sesion", False)
    return envuelta


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
        # Una copia, como FastAPI (`deepcopy(field.default)`): si la vista
        # modifica lo que recibió, el pedido siguiente no lo tiene que heredar.
        return copy.deepcopy(defecto)

    valor: Any = crudo
    if _va_como_json(request):
        try:
            valor = json.loads(crudo)
        except ValueError:
            raise _invalido() from None
        # `null` es «no vino»: FastAPI usa el valor por omisión si la ruta lo
        # tiene y, si el cuerpo es obligatorio, contesta 400. Sin esto, un
        # `null` en `Body(default={})` daba 200 en FastAPI y 400 acá.
        if valor is None and defecto is not OBLIGATORIO:
            return copy.deepcopy(defecto)

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


# ===================== Elegir la ruta como Starlette =====================
def como_starlette(patrones: list) -> list:
    """Las rutas, eligiendo entre ellas como lo hace Starlette.

    Cuando un mismo camino coincide con dos rutas que aceptan métodos
    distintos, los dos frameworks eligen distinto:

    - **Starlette** busca primero una ruta que coincida en camino **y** en
      método. Solo si no hay ninguna, contesta 405 con el `Allow` de la
      primera que coincidió en camino.
    - **Django** se queda con la primera que coincide en camino, y ahí
      `rutas()` contesta 405 si el método no es de ella.

    Pasa con las rutas de nombre fijo y las que toman un identificador:
    `GET /api/mensajes/contactos` y `POST /api/mensajes/{id}`. A un
    `POST /api/mensajes/contactos` FastAPI lo manda a la segunda («contactos»
    no es un número: 400), y Django contestaba 405.

    Esto envuelve cada ruta para que, si el método no es suyo, busque entre
    **las que vienen después** una que coincida en camino y en método. Las de
    antes no hace falta mirarlas: si alguna coincidiera en camino, Django ya
    la habría elegido a ella.
    """
    from django.urls.resolvers import URLPattern

    salida = []
    for posicion, patron in enumerate(patrones):
        vista = patron.callback
        siguientes = patrones[posicion + 1 :]

        def envuelta(request, *args, _vista=vista, _siguientes=siguientes, **kwargs):
            metodo = request.method.upper()
            if metodo not in getattr(_vista, "por_metodo", {}):
                camino = request.path_info.lstrip("/")
                for otra in _siguientes:
                    if metodo not in getattr(otra.callback, "por_metodo", {}):
                        continue
                    encontrada = otra.resolve(camino)
                    if encontrada:
                        return otra.callback(request, *encontrada.args, **encontrada.kwargs)
            return _vista(request, *args, **kwargs)

        # Lo que miran las pruebas (los métodos y si lleva sesión)
        envuelta.por_metodo = getattr(vista, "por_metodo", {})
        salida.append(URLPattern(patron.pattern, envuelta, patron.default_args, patron.name))
    return salida
