"""El banco de comparación: las mismas peticiones a dos aplicaciones.

    python -m pruebas.banco                    # FastAPI contra sí mismo
    python -m pruebas.banco --contra django    # FastAPI contra Django
    python -m pruebas.banco --detalle 10       # hasta 10 diferencias por caso
    python -m pruebas.banco --solo foro        # los casos cuyo nombre contenga eso

Para qué sirve correrlo contra sí mismo
---------------------------------------
Parece no tener sentido y es el primer uso: **si FastAPI contra FastAPI no da
cero diferencias, el banco está mal**. Significa que hay algo variable sin
normalizar, y entonces el día que haya Django el informe vendría lleno de
ruido y nadie lo miraría. Así que esa corrida es la que valida la
herramienta, y tiene que quedar en cero antes de empezar a migrar.

Cómo corre cada caso
--------------------
1. Se repone el campus a la foto inicial.
2. Se le hace al servidor A toda la secuencia del caso, guardando cada
   respuesta y la foto de cómo quedó el campus.
3. Se repone el campus **a la misma foto**.
4. Lo mismo con B.
5. Se comparan respuesta por respuesta, y al final en qué quedó el campus.

El orden importa: si no se repusiera en el medio, B recibiría un campus ya
modificado por A y cualquier diferencia sería culpa del banco.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import traceback
from typing import Any

from app.servicios import frenos

from .. import escenario
from ..cliente import como
from . import casos as catalogo
from . import estado, normalizar, servidores
from .comparar import Resultado, comparar


def _cuerpo_de(respuesta) -> Any:
    """El cuerpo, como JSON si lo es; si no, su texto normalizado."""
    tipo = respuesta.headers.get("content-type", "")
    if "application/json" in tipo:
        try:
            return respuesta.json()
        except ValueError:
            return {"<json ilegible>": respuesta.text[:200]}
    if tipo.startswith(("image/", "application/pdf", "application/octet-stream")):
        # De un binario se compara el tamaño, no los bytes: un informe con
        # dos megas de diferencia adentro no lo lee nadie.
        return {"<binario>": len(respuesta.content)}
    return {"<texto>": respuesta.text[:500]}


def _correr(app: servidores.Aplicacion, caso: catalogo.Caso, base: dict) -> list[dict]:
    """La secuencia completa en una aplicación, desde el campus repuesto."""
    estado.reponer(base)
    frenos.olvidar_todo()

    salida = []
    for paso in caso.pasos:
        como(paso.quien)
        try:
            if paso.cuerpo is None:
                r = app.cliente.request(paso.metodo, paso.camino)
            else:
                r = app.cliente.request(paso.metodo, paso.camino, json=paso.cuerpo)
            salida.append({
                "estado": r.status_code,
                "cuerpo": normalizar.aplicar(_cuerpo_de(r), extra=paso.variables),
                "cabeceras": normalizar.cabeceras_de(r),
                "error": None,
            })
        except Exception as fallo:  # noqa: BLE001 - se informa, no se corta
            salida.append({
                "estado": None,
                "cuerpo": None,
                "cabeceras": {},
                "error": f"{type(fallo).__name__}: {fallo}",
            })
    salida.append({"foto": estado.tomar()})
    return salida


def comparar_caso(
    a: servidores.Aplicacion, b: servidores.Aplicacion, caso: catalogo.Caso, base: dict
) -> list[Resultado]:
    ra = _correr(a, caso, base)
    rb = _correr(b, caso, base)

    resultados = []
    for paso, pa, pb in zip(caso.pasos, ra, rb):
        r = Resultado(
            nombre=caso.nombre,
            metodo=paso.metodo,
            camino=paso.camino,
            estado_a=pa["estado"],
            estado_b=pb["estado"],
            error_a=pa["error"],
            error_b=pb["error"],
        )
        if not (pa["error"] or pb["error"]):
            r.diferencias = comparar(pa["cuerpo"], pb["cuerpo"])
            r.cabeceras = comparar(pa["cabeceras"], pb["cabeceras"], "cabeceras")
        resultados.append(r)

    # Y en qué quedó el campus: dos aplicaciones pueden contestar lo mismo y
    # guardar distinto, y eso no se ve mirando las respuestas. Se compara con
    # la misma herramienta que los cuerpos, así el informe dice qué registro
    # y qué campo, no solo «cambió la colección».
    cambios = comparar(
        estado.comparable(ra[-1]["foto"]),
        estado.comparable(rb[-1]["foto"]),
        "campus",
    )
    if cambios:
        resultados[-1].estado_campus = [str(c) for c in cambios]

    return resultados


def _patrones(rutas: list[tuple[str, str]]) -> list[tuple[str, str, re.Pattern]]:
    """Cada ruta con la expresión que reconoce sus caminos concretos.

    Hace falta para la cobertura: los casos piden `/api/foro/1` y la tabla de
    rutas dice `/api/foro/{id_tema}`. Comparándolos como texto no calza nunca
    y la cobertura sale diez veces más baja de lo que es, que es peor que no
    medirla: invita a escribir casos que ya existían.
    """
    salida = []
    for metodo, camino in rutas:
        expresion = re.sub(r"\{[^}:]+:path\}", ".+", camino)
        expresion = re.sub(r"\{[^}]+\}", "[^/]+", expresion)
        salida.append((metodo, camino, re.compile("^" + expresion + "$")))
    return salida


def informar(resultados: list[Resultado], rutas: list[tuple[str, str]], detalle: int) -> int:
    distintos = [r for r in resultados if not r.coincide]

    for r in distintos:
        print(f"\n  {r.metodo:6} {r.camino}")
        print(f"         caso: {r.nombre}")
        if r.solo_en_uno:
            print(f"         ANDA EN UNA Y SE CAE EN LA OTRA")
            print(f"           A: {r.error_a or 'ok'}")
            print(f"           B: {r.error_b or 'ok'}")
        elif r.error_a or r.error_b:
            print(f"         se cayó en las dos: {r.error_a} / {r.error_b}")
        if r.estado_a != r.estado_b:
            print(f"         ESTADO: {r.estado_a} -> {r.estado_b}")
        for dif in r.diferencias[:detalle]:
            print(f"         · {dif}")
        if len(r.diferencias) > detalle:
            print(f"         … y {len(r.diferencias) - detalle} diferencias más")
        for dif in r.cabeceras[:detalle]:
            print(f"         · {dif}")
        if r.estado_campus:
            print(f"         GUARDARON DISTINTO: {', '.join(r.estado_campus)}")

    patrones = _patrones(rutas)
    cubiertas_set = set()
    for r in resultados:
        limpio = r.camino.split("?")[0]
        for metodo, camino, expresion in patrones:
            if metodo == r.metodo and expresion.match(limpio):
                cubiertas_set.add((metodo, camino))
                break
    cubiertas = len(cubiertas_set)
    sin_tocar = [f"{m} {c}" for m, c in rutas if (m, c) not in cubiertas_set]

    print("\n" + "-" * 62)
    print(f"  peticiones comparadas : {len(resultados)}")
    print(f"  idénticas             : {len(resultados) - len(distintos)}")
    print(f"  con diferencias       : {len(distintos)}")
    print(f"  rutas tocadas         : {cubiertas} de {len(rutas)} "
          f"({cubiertas * 100 // max(len(rutas), 1)} %)")
    print("-" * 62)

    if sin_tocar and detalle:
        print()
        print(f"  Sin ningún caso ({len(sin_tocar)}):")
        for x in sin_tocar:
            print(f"    {x}")

    if distintos:
        print("\nHay diferencias. Cada una es o un error de la migración o algo")
        print("variable que falta normalizar en `normalizar.py`.")
        return 1
    print("\nNinguna diferencia.")
    return 0


def main() -> int:
    opciones = argparse.ArgumentParser(description="Compara dos backends del campus")
    opciones.add_argument("--contra", default="fastapi", choices=sorted(servidores.DISPONIBLES))
    opciones.add_argument("--detalle", type=int, default=6)
    opciones.add_argument("--solo", default=None, help="solo los casos que contengan ese texto")
    opciones.add_argument("--autoprueba", action="store_true",
                          help="comprueba que el banco encuentre una diferencia cuando la hay")
    args = opciones.parse_args()

    # El campus avisa por el registro cuando Firestore no responde, y en el
    # banco no responde nunca —las pruebas no la tocan—. Son trazas
    # esperadas que taparían el informe.
    logging.disable(logging.ERROR)

    # La consola de Windows usa cp1252 y no sabe escribir algunos caracteres.
    # Un informe que se cae justo al mostrar una diferencia es inservible, así
    # que lo que no entre se reemplaza en vez de reventar.
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

    if args.autoprueba:
        from .autoprueba import correr
        return correr()

    a = servidores.fastapi()
    try:
        b = servidores.DISPONIBLES[args.contra]()
    except NotImplementedError as falta:
        print(f"\n{falta}\n")
        return 2

    print(f"Banco de comparación: {a.nombre} contra {b.nombre}")
    if a.nombre == b.nombre:
        print("(contra sí mismo: esto valida el banco, tiene que dar cero)")

    escenario.cargar()
    base = estado.tomar()

    lista = catalogo.todos(a.rutas)
    if args.solo:
        lista = [c for c in lista if args.solo.lower() in c.nombre.lower()]
    print(f"{len(lista)} casos\n")

    resultados: list[Resultado] = []
    for caso in lista:
        try:
            resultados += comparar_caso(a, b, caso, base)
        except Exception:  # noqa: BLE001
            print(f"\n  el caso «{caso.nombre}» rompió el banco:")
            traceback.print_exc()
            return 3

    return informar(resultados, a.rutas, args.detalle)


if __name__ == "__main__":
    sys.exit(main())
