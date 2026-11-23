"""Pruebas de los adaptadores: que Django conteste byte por byte como FastAPI.

En la fase 0 no se migra ninguna ruta, así que el banco de comparación todavía
no tiene nada de Django para comparar. Pero los adaptadores ya están escritos,
y un adaptador que nadie probó es una promesa. Esta suite los prueba antes de
que los use una ruta de verdad.

Cómo
----
Se registran **las mismas sondas** en las dos aplicaciones, solo en el
proceso de esta prueba —nunca en el código del campus—: una ruta de FastAPI
escrita como siempre, y su gemela en Django escrita con los adaptadores. Las
dos llaman a la misma función del medio. Después se les hace la misma
petición y se compara **el cuerpo exacto, en bytes**, el código y las
cabeceras que importan. No el JSON interpretado: dos JSON que se leen igual
pueden tener distinto largo, y una respuesta grabada deja de coincidir.

Cada sonda reproduce una de las diferencias que medimos entre FastAPI y
Django: el id no numérico, el método que no va, la barra final, el JSON roto,
el cuerpo que falta, el parámetro repetido, el 500, el CORS, el freno.

Uso (desde backend/):
    python -m pruebas.adaptadores
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any

from django.urls import clear_url_caches, path
from fastapi import Body, HTTPException
from starlette.testclient import TestClient

import despachador
from app.servicios import auditoria, frenos, persistencia
from app.servicios.autenticacion import UsuarioActual
from campus_django import urls as urls_django
from campus_django.adaptadores import (
    como_starlette,
    con_cuerpo,
    con_sesion,
    consulta,
    cuerpo,
    entero,
    responder,
    rutas,
)

from . import escenario
from .cliente import como, sin_suplantar

SANTIAGO = 1
FRONTEND = "http://localhost:5173"

pasadas = 0
fallas: list[str] = []


def comprobar(nombre: str, condicion: bool, detalle=None) -> None:
    global pasadas
    if condicion:
        pasadas += 1
        print(f"  ok     {nombre}")
    else:
        fallas.append(nombre)
        extra = f"  -> {detalle}" if detalle is not None else ""
        print(f"  FALLA  {nombre}{extra}")


def grupo(titulo: str) -> None:
    print(f"\n== {titulo} ==")


# ===================== El medio de cada sonda =====================
# Lo mismo para las dos aplicaciones: lo único que cambia es cómo se
# conectan a su framework.
def nucleo_datos(yo: dict) -> dict:
    # Tipos que el JSON tiene que convertir: una fecha, un conjunto, un
    # decimal, un None, acentos. Si el adaptador los escribiera distinto que
    # FastAPI, se nota acá.
    return {
        "yo": yo["id"],
        "lista": [1, 2, 3],
        "acento": "ñandú, árbol y güemes",
        "nada": None,
        "fecha": datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        "conjunto": {3},
        "decimal": 1.5,
    }


def nucleo_explota() -> None:
    raise RuntimeError("sonda que explota a propósito")


# ===================== Las sondas en FastAPI =====================
fastapi = despachador.fastapi
SONDA = "/api/__sonda"


def fa_datos(yo: dict = UsuarioActual):
    return nucleo_datos(yo)


def fa_lista(yo: dict = UsuarioActual):
    return [1, "dos", None]


def fa_creado(yo: dict = UsuarioActual):
    return {"creado": True}


def fa_prohibido(yo: dict = UsuarioActual):
    raise HTTPException(403, "Prohibido en la sonda")


def fa_explota(yo: dict = UsuarioActual):
    nucleo_explota()


def fa_item(id_item: int, yo: dict = UsuarioActual):
    return {"id": id_item}


def fa_consulta(pagina: int = 1, q: str | None = None, activo: bool = False,
                yo: dict = UsuarioActual):
    return {"pagina": pagina, "q": q, "activo": activo}


def fa_obligatoria(cantidad: int, yo: dict = UsuarioActual):
    return {"cantidad": cantidad}


def fa_cuerpo(datos: dict = Body(...), yo: dict = UsuarioActual):
    return {"recibido": datos}


def fa_cuerpo_opcional(datos: dict = Body(default={}), yo: dict = UsuarioActual):
    return {"recibido": datos}


def fa_cuerpo_que_cambia(datos: dict = Body(default={}), yo: dict = UsuarioActual):
    # Una ruta que modifica lo que recibió: con el valor por omisión, cada
    # pedido tiene que recibir uno nuevo y no el que dejó el anterior.
    datos["veces"] = datos.get("veces", 0) + 1
    return {"recibido": datos}


def fa_ip(yo: dict = UsuarioActual):
    return {"ip": auditoria.ip_de()}


# Dos rutas con el mismo camino y métodos distintos, como `GET /contactos` y
# `POST /{id}` en Mensajes: `POST /mezcla/fijo` lo atiende la segunda.
def fa_mezcla_fijo(yo: dict = UsuarioActual):
    return {"fijo": True}


def fa_mezcla_por_id(id_x: int, yo: dict = UsuarioActual):
    return {"id": id_x}


for camino, funcion, metodos, extra in [
    ("/datos", fa_datos, ["GET"], {}),
    ("/lista", fa_lista, ["GET"], {}),
    ("/creado", fa_creado, ["POST"], {"status_code": 201}),
    ("/prohibido", fa_prohibido, ["GET"], {}),
    ("/explota", fa_explota, ["GET"], {}),
    ("/item/{id_item}", fa_item, ["GET"], {}),
    ("/consulta", fa_consulta, ["GET"], {}),
    ("/obligatoria", fa_obligatoria, ["GET"], {}),
    ("/cuerpo", fa_cuerpo, ["POST"], {}),
    ("/cuerpo-opcional", fa_cuerpo_opcional, ["POST"], {}),
    ("/cuerpo-que-cambia", fa_cuerpo_que_cambia, ["POST"], {}),
    ("/ip", fa_ip, ["GET"], {}),
    ("/mezcla/fijo", fa_mezcla_fijo, ["GET"], {}),
    ("/mezcla/{id_x}", fa_mezcla_por_id, ["POST"], {}),
]:
    fastapi.add_api_route(SONDA + camino, funcion, methods=metodos, **extra)


# ===================== Las mismas sondas en Django =====================
@con_sesion
def dj_datos(request, yo):
    return responder(nucleo_datos(yo))


@con_sesion
def dj_lista(request, yo):
    return responder([1, "dos", None])


@con_sesion
def dj_creado(request, yo):
    return responder({"creado": True}, estado=201)


@con_sesion
def dj_prohibido(request, yo):
    raise HTTPException(403, "Prohibido en la sonda")


@con_sesion
def dj_explota(request, yo):
    nucleo_explota()


@con_sesion
def dj_item(request, yo, id_item):
    return responder({"id": entero(id_item)})


@con_sesion
def dj_consulta(request, yo):
    return responder({
        "pagina": consulta(request, "pagina", int, 1),
        "q": consulta(request, "q", str | None, None),
        "activo": consulta(request, "activo", bool, False),
    })


@con_sesion
def dj_obligatoria(request, yo):
    return responder({"cantidad": consulta(request, "cantidad", int)})


@con_cuerpo
@con_sesion
def dj_cuerpo(request, yo):
    return responder({"recibido": cuerpo(request, dict)})


@con_cuerpo
@con_sesion
def dj_cuerpo_opcional(request, yo):
    return responder({"recibido": cuerpo(request, dict, defecto={})})


@con_cuerpo
@con_sesion
def dj_cuerpo_que_cambia(request, yo):
    datos = cuerpo(request, dict, defecto={})
    datos["veces"] = datos.get("veces", 0) + 1
    return responder({"recibido": datos})


@con_sesion
def dj_ip(request, yo):
    return responder({"ip": auditoria.ip_de()})


@con_sesion
def dj_mezcla_fijo(request, yo):
    return responder({"fijo": True})


@con_sesion
def dj_mezcla_por_id(request, yo, id_x):
    return responder({"id": entero(id_x)})


S = SONDA.lstrip("/")
urls_django.urlpatterns += [
    path(f"{S}/datos", rutas(get=dj_datos)),
    path(f"{S}/lista", rutas(get=dj_lista)),
    path(f"{S}/creado", rutas(post=dj_creado)),
    path(f"{S}/prohibido", rutas(get=dj_prohibido)),
    path(f"{S}/explota", rutas(get=dj_explota)),
    path(f"{S}/item/<str:id_item>", rutas(get=dj_item)),
    path(f"{S}/consulta", rutas(get=dj_consulta)),
    path(f"{S}/obligatoria", rutas(get=dj_obligatoria)),
    path(f"{S}/cuerpo", rutas(post=dj_cuerpo)),
    path(f"{S}/cuerpo-opcional", rutas(post=dj_cuerpo_opcional)),
    path(f"{S}/cuerpo-que-cambia", rutas(post=dj_cuerpo_que_cambia)),
    path(f"{S}/ip", rutas(get=dj_ip)),
    *como_starlette([
        path(f"{S}/mezcla/fijo", rutas(get=dj_mezcla_fijo)),
        path(f"{S}/mezcla/<str:id_x>", rutas(post=dj_mezcla_por_id)),
    ]),
]
clear_url_caches()

# Sin `with`: así no se dispara el arranque, que conectaría Firestore de
# verdad. Y sin relanzar los errores del servidor, para poder comparar el 500.
fa = TestClient(fastapi, raise_server_exceptions=False)
dj = TestClient(despachador.django(), raise_server_exceptions=False)

CABECERAS = (
    "content-type", "content-length", "location", "allow", "retry-after",
    "vary", "access-control-allow-origin", "access-control-allow-methods",
    "access-control-allow-headers", "access-control-max-age",
    "access-control-allow-credentials", "x-content-type-options",
)


def _cabeceras(r) -> dict:
    return {k: r.headers[k] for k in CABECERAS if k in r.headers}


def igual(nombre: str, metodo: str, camino: str, **extra) -> tuple:
    """La misma petición a las dos; comprueba código, bytes y cabeceras."""
    frenos.olvidar_todo()
    a = fa.request(metodo, camino, follow_redirects=False, **extra)
    frenos.olvidar_todo()
    b = dj.request(metodo, camino, follow_redirects=False, **extra)

    diferencias = []
    if a.status_code != b.status_code:
        diferencias.append(f"estado {a.status_code} vs {b.status_code}")
    if a.content != b.content:
        diferencias.append(f"cuerpo {a.content[:70]!r} vs {b.content[:70]!r}")
    ca, cb = _cabeceras(a), _cabeceras(b)
    if ca != cb:
        distintas = {k: (ca.get(k), cb.get(k)) for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)}
        diferencias.append(f"cabeceras {distintas}")
    comprobar(f"{nombre}  [{a.status_code}]", not diferencias, "; ".join(diferencias))
    return a, b


def vistas_sin_sesion(patrones, publicas: set[str]) -> list[str]:
    """Las rutas de Django cuya vista no pasa por `con_sesion`.

    Olvidarse de la sesión es dejar una ruta abierta, y ya pasó con cinco
    rutas de FastAPI. Esta función es la que lo vigila cuando se migren.
    """
    abiertas = []
    for patron in patrones:
        camino = str(patron.pattern)
        if camino in publicas:
            continue
        vista = patron.callback
        vistas = getattr(vista, "por_metodo", {"*": vista}).values()
        if not all(getattr(v, "con_sesion", False) for v in vistas):
            abiertas.append(camino)
    return abiertas


def correr() -> None:
    print("Pruebas de los adaptadores de Django (en proceso)\n")
    escenario.cargar()
    como(SANTIAGO)

    # ------------------------------------------------------------------
    grupo("El JSON sale con los mismos bytes")
    igual("fechas, conjuntos, acentos, None y decimales", "GET", f"{SONDA}/datos")
    igual("una lista en la raíz", "GET", f"{SONDA}/lista")
    igual("un 201", "POST", f"{SONDA}/creado")

    # ------------------------------------------------------------------
    grupo("Los errores, con el mismo formato")
    igual("un 403 lanzado por la vista", "GET", f"{SONDA}/prohibido")
    a, b = igual("un 500 inesperado", "GET", f"{SONDA}/explota")
    igual("un 500 no lleva CORS, como en FastAPI", "GET", f"{SONDA}/explota",
          headers={"Origin": FRONTEND})
    igual("una ruta que no existe", "GET", "/api/__sonda/no-existe")

    # ------------------------------------------------------------------
    grupo("Los métodos")
    igual("un método que la ruta no tiene", "DELETE", f"{SONDA}/datos")
    igual("HEAD sobre una ruta GET", "HEAD", f"{SONDA}/datos")
    igual("OPTIONS sin ser una consulta de CORS", "OPTIONS", f"{SONDA}/datos")

    # ------------------------------------------------------------------
    grupo("La barra final")
    igual("se saca con un 307", "GET", f"{SONDA}/datos/")
    igual("y conserva la consulta", "GET", f"{SONDA}/datos/?x=1&y=dos")
    igual("si sin barra tampoco existe, 404", "GET", "/api/__sonda/no-existe/")

    # ------------------------------------------------------------------
    grupo("Los parámetros de camino")
    for valor in ["12", "-3", "abc", "1.0", "%2012", "12abc", "0"]:
        igual(f"id «{valor}»", "GET", f"{SONDA}/item/{valor}")

    # ------------------------------------------------------------------
    grupo("Los parámetros de consulta")
    for consulta_ in ["", "?pagina=2", "?pagina=abc", "?pagina=", "?pagina=1&pagina=5",
                      "?q=hola", "?activo=true", "?activo=yes", "?activo=1",
                      "?activo=no", "?activo=talvez", "?pagina=%2B7"]:
        igual(f"«{consulta_ or '(ninguno)'}»", "GET", f"{SONDA}/consulta{consulta_}")
    igual("obligatorio que falta", "GET", f"{SONDA}/obligatoria")
    igual("obligatorio presente", "GET", f"{SONDA}/obligatoria?cantidad=4")

    # ------------------------------------------------------------------
    grupo("El cuerpo")
    igual("un diccionario", "POST", f"{SONDA}/cuerpo", json={"a": 1, "b": "ñ"})
    igual("una lista en vez de diccionario", "POST", f"{SONDA}/cuerpo", json=[1, 2])
    igual("JSON roto", "POST", f"{SONDA}/cuerpo", content=b"{no es json",
          headers={"content-type": "application/json"})
    igual("cuerpo vacío y obligatorio", "POST", f"{SONDA}/cuerpo")
    igual("JSON sin tipo de contenido", "POST", f"{SONDA}/cuerpo", content=b'{"a":1}')
    igual("JSON con tipo text/plain", "POST", f"{SONDA}/cuerpo", content=b'{"a":1}',
          headers={"content-type": "text/plain"})
    igual("tipo +json", "POST", f"{SONDA}/cuerpo", content=b'{"a":1}',
          headers={"content-type": "application/vnd.campus+json"})
    igual("opcional y vacío", "POST", f"{SONDA}/cuerpo-opcional")
    igual("opcional con datos", "POST", f"{SONDA}/cuerpo-opcional", json={"x": 1})
    # `null` es «no vino»: FastAPI usa el valor por omisión si lo hay, y si
    # el cuerpo es obligatorio, 400. Lo encontró la sonda de los cuerpos.
    igual("opcional y null", "POST", f"{SONDA}/cuerpo-opcional", content=b"null",
          headers={"content-type": "application/json"})
    igual("obligatorio y null", "POST", f"{SONDA}/cuerpo", content=b"null",
          headers={"content-type": "application/json"})
    # FastAPI entrega una copia del valor por omisión en cada pedido
    igual("el valor por omisión, la primera vez", "POST", f"{SONDA}/cuerpo-que-cambia")
    igual("y la segunda, igual que la primera", "POST", f"{SONDA}/cuerpo-que-cambia")
    # Sin sesión y con JSON roto: FastAPI lee el cuerpo antes que la sesión (400)
    como(None)
    igual("JSON roto y sin sesión: 400 antes que 401", "POST", f"{SONDA}/cuerpo",
          content=b"{roto", headers={"content-type": "application/json"})
    igual("JSON sano y sin sesión: 401", "POST", f"{SONDA}/cuerpo", json={"a": 1})
    igual("texto plano roto y sin sesión: 401", "POST", f"{SONDA}/cuerpo",
          content=b"{roto", headers={"content-type": "text/plain"})
    como(SANTIAGO)
    igual("opcional con JSON roto", "POST", f"{SONDA}/cuerpo-opcional",
          content=b"[[[", headers={"content-type": "application/json"})

    # Dos rutas con el mismo camino y distinto método. Starlette prefiere la
    # que coincide en camino **y** método; Django, la primera que coincide en
    # camino. Lo iguala `como_starlette`.
    igual("mismo camino: el GET de la ruta fija", "GET", f"{SONDA}/mezcla/fijo")
    igual("mismo camino: el POST cae en la del id (400)", "POST", f"{SONDA}/mezcla/fijo")
    igual("mismo camino: el POST con un id", "POST", f"{SONDA}/mezcla/7")
    igual("ninguna lo acepta: 405 con el Allow de la primera", "DELETE", f"{SONDA}/mezcla/fijo")
    igual("el GET con un id: 405", "GET", f"{SONDA}/mezcla/7")

    # ------------------------------------------------------------------
    grupo("La sesión")
    sin_suplantar()
    igual("sin token", "GET", f"{SONDA}/datos")
    igual("con un token inventado", "GET", f"{SONDA}/datos",
          headers={"Authorization": "Bearer inventado"})
    igual("sin token y con un id inválido: primero la sesión", "GET", f"{SONDA}/item/abc")
    como(SANTIAGO)
    igual("suplantando, entra", "GET", f"{SONDA}/datos")

    # ------------------------------------------------------------------
    grupo("CORS")
    igual("con el origen del frontend", "GET", f"{SONDA}/datos", headers={"Origin": FRONTEND})
    igual("con un origen ajeno", "GET", f"{SONDA}/datos", headers={"Origin": "https://otro.sitio"})
    igual("consulta previa (preflight)", "OPTIONS", f"{SONDA}/datos", headers={
        "Origin": FRONTEND,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    igual("un error también lleva CORS", "GET", f"{SONDA}/prohibido", headers={"Origin": FRONTEND})

    # ------------------------------------------------------------------
    grupo("El freno")
    igual("un envío de más de 30 MB", "POST", f"{SONDA}/creado",
          headers={"content-length": str(frenos.MAXIMO_BYTES + 1)})

    respuestas = {}
    for nombre, cliente in (("fa", fa), ("dj", dj)):
        frenos.olvidar_todo()
        for _ in range(frenos.MAXIMO_ESCRITURAS):
            cliente.post(f"{SONDA}/creado")
        respuestas[nombre] = cliente.post(f"{SONDA}/creado")
    a, b = respuestas["fa"], respuestas["dj"]
    comprobar("pasarse del minuto da el mismo 429",
              (a.status_code, a.content, a.headers.get("retry-after"))
              == (b.status_code, b.content, b.headers.get("retry-after")),
              ((a.status_code, a.content), (b.status_code, b.content)))
    comprobar("y es un 429 de verdad", a.status_code == 429, a.status_code)
    frenos.olvidar_todo()

    # ------------------------------------------------------------------
    grupo("La auditoría ve la IP")
    igual("sin proxy", "GET", f"{SONDA}/ip")
    igual("detrás de un proxy", "GET", f"{SONDA}/ip",
          headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"})
    comprobar("y no queda vacía", dj.get(f"{SONDA}/ip").json().get("ip") is not None)

    # ------------------------------------------------------------------
    # El guardado es lo que no puede faltar: una ruta de Django que no
    # guardara contestaría bien y perdería el dato al reiniciar.
    grupo("El guardado corre después de cada petición")
    llamadas = {"n": 0}
    activo_real, guardar_real = persistencia.activo, persistencia.guardar_cambios
    persistencia.activo = lambda: True
    persistencia.guardar_cambios = lambda: llamadas.__setitem__("n", llamadas["n"] + 1)
    try:
        fa.get(f"{SONDA}/datos")
        en_fastapi = llamadas["n"]
        llamadas["n"] = 0
        dj.get(f"{SONDA}/datos")
        en_django = llamadas["n"]
    finally:
        persistencia.activo, persistencia.guardar_cambios = activo_real, guardar_real
    comprobar("en FastAPI, una vez", en_fastapi == 1, en_fastapi)
    comprobar("en Django, una vez", en_django == 1, en_django)

    # ------------------------------------------------------------------
    grupo("Ninguna vista de Django queda sin sesión")
    # Las públicas a propósito. La de archivos va con la misma expresión que
    # arma Starlette (ver `campus_django/archivos.py`): es esa y ninguna otra.
    publicas = {
        r"^api/salud$",  # por el puente: la misma expresión que arma Starlette
        r"^api/archivos/(?P<f>[^/]+)/(?P<o>.*)$",
        r"^api/usuarios/(?P<id_persona>[^/]+)/foto$",
    }
    reales = [p for p in urls_django.urlpatterns if not str(p.pattern).startswith(S)]
    comprobar("las rutas reales del campus",
              not vistas_sin_sesion(reales, publicas), vistas_sin_sesion(reales, publicas))

    def abierta(request):
        return responder({})

    prueba = [path("api/con", rutas(get=dj_datos)), path("api/sin", rutas(get=abierta))]
    comprobar("y el vigilante encuentra una abierta",
              vistas_sin_sesion(prueba, publicas) == ["api/sin"], vistas_sin_sesion(prueba, publicas))

    # ------------------------------------------------------------------
    print("\n" + "-" * 52)
    total = pasadas + len(fallas)
    print(f"{pasadas}/{total} comprobaciones pasaron")
    if fallas:
        print("\nFallaron:")
        for f in fallas:
            print(f"  - {f}")
        sys.exit(1)
    print("Todo en orden.")


if __name__ == "__main__":
    correr()
