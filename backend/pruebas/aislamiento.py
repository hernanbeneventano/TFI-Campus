"""Pruebas del escenario: que cargarlo deje siempre el mismo campus.

Las otras suites dan por sentado que `escenario.cargar()` deja el campus en
un estado conocido. **No lo hacía.** Adivinaba en qué atributo iba cada clave
y se equivocaba con las de carreras; además no reponía lo que `datos.py` arma
en código ni los contadores. No se notaba porque cada suite corre en su
proceso y carga una sola vez: con dos cargas en el mismo proceso, la segunda
arrancaba sucia. Lo descubrió el banco de comparación, que sí carga muchas
veces, cuando el mismo `POST` daba 201 y después 409.

Esta suite cuida lo que esas suites suponen, y lo cuida **dentro de un solo
proceso**: carga, ensucia y vuelve a cargar todas las veces que haga falta.
Si mañana alguien agrega una colección a `datos.py` y el escenario no la
repone, falla acá y no en el banco tres semanas después.

Uso (desde backend/):
    python -m pruebas.aislamiento
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import types

from app import datos as d
from app.servicios import autenticacion, frenos

from . import escenario
from .cliente import como, crear_cliente

SANTIAGO = 1
SECRETARIA = 18

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


# Todo lo que el escenario es responsable de reponer. Se arma con lo mismo
# que usa `escenario.py`, así una colección nueva entra sola.
def _responsables() -> list[str]:
    return sorted(set(escenario.MAPA.values()) | set(escenario.ARMADO_EN_CODIGO))


def foto() -> dict:
    estado = {n: copy.deepcopy(getattr(d, n)) for n in _responsables()}
    estado["__frenos"] = len(frenos._visitas)
    estado["__ingresos"] = dict(autenticacion._ultimo_ingreso)
    return estado


def huella() -> str:
    crudo = json.dumps(foto(), sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:16]


def ensuciar(cliente) -> None:
    """Toca todo lo que antes quedaba sucio entre una carga y la otra."""
    como(SECRETARIA)
    cliente.post("/api/institucion/carreras", json={"nombre": "Sucia", "codigo": "SUC"})
    como(SANTIAGO)
    cliente.post("/api/cursos/1/favorito")
    d.archivos_subidos.append({"objectKey": "sucio/x.pdf", "nombre": "x.pdf"})
    d.cierres_cursada.append({"cursoId": 1, "personaId": 1})
    d.guardar_archivo("sucio/x.pdf", b"%PDF-sucio")
    d.carreras.append("Carrera que no existe")
    for contador in list(d._proximos):
        d._proximos[contador] += 50
    autenticacion._ultimo_ingreso[SANTIAGO] = 123.0


def correr() -> None:
    print("Pruebas del aislamiento del escenario (en proceso)\n")
    cliente = crear_cliente()

    # ------------------------------------------------------------------
    grupo("Lee el mapa de datos.py, no lo adivina")
    comprobar(
        "«carreras» va a carreras_institucion",
        escenario.MAPA.get("carreras") == "carreras_institucion",
        escenario.MAPA.get("carreras"),
    )
    comprobar(
        "«carrerasNombres» va a carreras",
        escenario.MAPA.get("carrerasNombres") == "carreras",
        escenario.MAPA.get("carrerasNombres"),
    )
    comprobar(
        "conoce lo que datos.py arma en código",
        {"archivos_subidos", "cierres_cursada", "_archivos", "_proximos"}
        <= set(escenario.ARMADO_EN_CODIGO),
        sorted(escenario.ARMADO_EN_CODIGO),
    )

    # Un contenedor de datos.py que no venga del JSON ni sea un literal —uno
    # armado con una llamada— no lo vería el mapa y quedaría sucio. Se busca
    # en el módulo vivo, no en el fuente, para que no se escape ninguno.
    # `_iniciales` queda afuera: es el JSON crudo del que se lee al arrancar y
    # nadie lo vuelve a consultar.
    cubiertos = set(_responsables()) | {"_iniciales"}
    sueltos = sorted(
        n
        for n, v in vars(d).items()
        if not n.startswith("__")
        and isinstance(v, (list, dict, set))
        and not isinstance(v, types.ModuleType)
        and n not in cubiertos
    )
    comprobar("ningún contenedor de datos.py queda sin reponer", not sueltos, sueltos)

    # ------------------------------------------------------------------
    grupo("Desde un campus limpio")
    escenario.cargar()
    crudo = escenario._escenario()
    distintos = [
        clave
        for clave, valor in crudo.items()
        if json.dumps(getattr(d, escenario.MAPA[clave]), sort_keys=True, default=str)
        != json.dumps(
            {escenario._como_clave(k): v for k, v in valor.items()}
            if isinstance(valor, dict) else valor,
            sort_keys=True, default=str,
        )
    ]
    comprobar("cada atributo tiene lo que dice el escenario", not distintos, distintos)
    comprobar(
        "las carreras son objetos",
        all(isinstance(c, dict) for c in d.carreras_institucion),
    )
    comprobar(
        "y la lista de nombres son nombres",
        all(isinstance(c, str) for c in d.carreras),
        [type(c).__name__ for c in d.carreras][:3],
    )
    comprobar(
        "lo armado en código arranca como en el fuente",
        d.archivos_subidos == [] and d.cierres_cursada == [] and d._archivos == {},
    )
    limpia = huella()

    # ------------------------------------------------------------------
    grupo("Dos veces seguidas dan lo mismo")
    escenario.cargar()
    comprobar("la segunda carga deja el mismo campus", huella() == limpia)

    # ------------------------------------------------------------------
    grupo("Después de ensuciarlo, vuelve a quedar igual")
    ensuciar(cliente)
    comprobar("el campus quedó distinto (si no, esto no prueba nada)", huella() != limpia)
    escenario.cargar()
    comprobar("recargar lo deja como la carga limpia", huella() == limpia)
    comprobar("la carrera creada no está", not any(c.get("codigo") == "SUC" for c in d.carreras_institucion))
    comprobar("el favorito no está", d.favoritos_modulo == [])
    comprobar("las fichas y los bytes no están", d.archivos_subidos == [] and d._archivos == {})
    comprobar("el cierre no está", d.cierres_cursada == [])
    comprobar("los nombres de carrera no tienen la de más", "Carrera que no existe" not in d.carreras)

    # ------------------------------------------------------------------
    # Lo que lo descubrió: con el escenario sucio, el mismo alta daba 409.
    grupo("El caso que lo descubrió")
    escenario.cargar()
    como(SECRETARIA)
    primera = cliente.post("/api/institucion/carreras", json={"nombre": "Una", "codigo": "UNA"})
    escenario.cargar()
    como(SECRETARIA)
    segunda = cliente.post("/api/institucion/carreras", json={"nombre": "Una", "codigo": "UNA"})
    comprobar("crear la misma carrera da 201 las dos veces", (primera.status_code, segunda.status_code) == (201, 201),
              (primera.status_code, segunda.status_code))
    # El alta devuelve el catálogo entero, no la carrera sola
    def id_de_una(respuesta):
        return next((c["id"] for c in respuesta.json()["carreras"] if c.get("codigo") == "UNA"), None)

    comprobar("y le toca el mismo identificador", id_de_una(primera) == id_de_una(segunda),
              (id_de_una(primera), id_de_una(segunda)))

    escenario.cargar()
    como(SANTIAGO)
    marca = cliente.post("/api/cursos/1/favorito").json().get("favorito")
    escenario.cargar()
    como(SANTIAGO)
    otra = cliente.post("/api/cursos/1/favorito").json().get("favorito")
    comprobar("el favorito arranca desmarcado en cada carga", marca is True and otra is True, (marca, otra))

    # ------------------------------------------------------------------
    grupo("Los contadores")
    escenario.cargar()
    esperados = copy.deepcopy(escenario.ARMADO_EN_CODIGO["_proximos"])
    from app.servicios import persistencia
    for coleccion, contador in persistencia._CONTADOR_DE.items():
        if contador not in esperados:
            continue
        ids = [x["id"] for x in getattr(d, persistencia.REGISTROS[coleccion][0])
               if isinstance(x.get("id"), int)]
        if ids:
            esperados[contador] = max(esperados[contador], max(ids) + 1)
    comprobar("quedan en el valor esperado", d._proximos == esperados,
              {k: (d._proximos.get(k), v) for k, v in esperados.items() if d._proximos.get(k) != v})
    ensuciar(cliente)
    escenario.cargar()
    comprobar("después de avanzarlos, vuelven al mismo valor", d._proximos == esperados)
    pisados = [
        contador
        for coleccion, contador in persistencia._CONTADOR_DE.items()
        if contador in d._proximos
        and any(x.get("id") == d._proximos[contador]
                for x in getattr(d, persistencia.REGISTROS[coleccion][0]))
    ]
    comprobar("ninguno apunta a un identificador que ya existe", not pisados, pisados)

    # ------------------------------------------------------------------
    grupo("Lo que el proceso recuerda entre peticiones")
    ensuciar(cliente)
    escenario.cargar()
    comprobar("el freno por minuto arranca en cero", len(frenos._visitas) == 0, len(frenos._visitas))
    comprobar("y los ingresos anotados también", autenticacion._ultimo_ingreso == {})

    # ------------------------------------------------------------------
    # El bug fue una clave que iba a parar a ningún lado sin que nada
    # fallara. Ahora eso tiene que cortar, y con un mensaje que diga cuál.
    grupo("Un escenario mal armado se rechaza")
    con_clave_de_mas = escenario._escenario()
    con_clave_de_mas["colecccionMalEscrita"] = []
    try:
        escenario.aplicar(con_clave_de_mas)
        comprobar("una clave que datos.py no lee", False, "no dio error")
    except ValueError as error:
        comprobar("una clave que datos.py no lee", "colecccionMalEscrita" in str(error), str(error))

    sin_una = escenario._escenario()
    sin_una.pop("favoritosModulo")
    try:
        escenario.aplicar(sin_una)
        comprobar("una clave que falta", False, "no dio error")
    except ValueError as error:
        comprobar("una clave que falta", "favoritosModulo" in str(error), str(error))

    # Y rechazarlo no puede dejar el campus a medio cargar
    escenario.cargar()
    antes = huella()
    try:
        escenario.aplicar(con_clave_de_mas)
    except ValueError:
        pass
    comprobar("rechazarlo no toca nada", huella() == antes)

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
