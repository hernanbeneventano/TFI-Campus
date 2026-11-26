"""Compara el contrato actual de Django con la grabación de referencia.

    python -m pruebas.banco                    # Django contra la grabación
    python -m pruebas.banco --detalle 10       # hasta 10 diferencias por caso
    python -m pruebas.banco --solo foro        # los casos cuyo nombre contenga eso

La referencia es un fixture de pruebas: no contiene ni ejecuta código de
servidor, solo lo que el campus contestó y en qué quedó la memoria.

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
import pathlib
import logging
import re
import sys
import traceback
from datetime import datetime
from unittest.mock import patch
from typing import Any

from app import datos
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
    # Las exportaciones se comparan **enteras**: un archivo que baja con una
    # columna de menos o un renglón cambiado es justo lo que hay que ver.
    if tipo.startswith("text/csv"):
        return {"<csv>": respuesta.text.splitlines()}
    if "spreadsheetml" in tipo:
        # Un .xlsx es un ZIP: se compara lo de adentro, archivo por archivo.
        # Los bytes del ZIP no, porque llevan la hora en que se armó y dos
        # exportaciones idénticas nunca coincidirían.
        import io
        import zipfile

        try:
            with zipfile.ZipFile(io.BytesIO(respuesta.content)) as paquete:
                return {"<xlsx>": {n: paquete.read(n).decode("utf-8") for n in sorted(paquete.namelist())}}
        except (zipfile.BadZipFile, UnicodeDecodeError):
            return {"<xlsx ilegible>": len(respuesta.content)}
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


# ===================== La grabación =====================
# La grabación de referencia guarda lo que contestó y lo que quedó, caso a caso.
# De lo guardado se registra **qué cambió** respecto del campus de partida
# —no el campus entero, que serían decenas de megas por nada—.
def _cambios(base: dict, foto: dict) -> list[str]:
    return [str(c) for c in comparar(estado.comparable(base), estado.comparable(foto), "campus")]


def grabar(app: servidores.Aplicacion, lista: list, base: dict, ruta: str) -> int:
    import gzip
    import json

    salida = {"rutas": app.rutas, "casos": {}}
    for caso in lista:
        corrida = _correr(app, caso, base)
        salida["casos"][caso.nombre] = {
            "pasos": corrida[:-1],
            "cambios": _cambios(base, corrida[-1]["foto"]),
        }
    with gzip.open(ruta, "wt", encoding="utf-8") as archivo:
        json.dump(salida, archivo, ensure_ascii=False, default=str)
    pedidos = sum(len(c["pasos"]) for c in salida["casos"].values())
    print(f"Grabados {len(lista)} casos y {pedidos} pedidos de {app.nombre} en {ruta}")
    return 0


def contra_grabado(b: servidores.Aplicacion, ruta: str, solo: str | None, base: dict, detalle: int) -> int:
    import gzip
    import json

    with gzip.open(ruta, "rt", encoding="utf-8") as archivo:
        grabado = json.load(archivo)
    rutas = [tuple(r) for r in grabado["rutas"]]
    lista = catalogo.todos(rutas)
    if solo:
        lista = [c for c in lista if solo.lower() in c.nombre.lower()]
    faltan = [c.nombre for c in lista if c.nombre not in grabado["casos"]]
    if faltan:
        print(f"Casos que no están en la grabación: {faltan[:5]}")
        return 2
    print(f"Banco de comparación: grabación ({ruta}) contra {b.nombre}")
    print(f"{len(lista)} casos")
    print()

    resultados: list[Resultado] = []
    for caso in lista:
        esperado = grabado["casos"][caso.nombre]
        cruda = _correr(b, caso, base)
        foto = cruda[-1]["foto"]
        # Lo grabado pasó por JSON: se compara contra lo nuevo pasado igual
        corrida = json.loads(json.dumps(cruda[:-1], default=str))
        for paso, pa, pb in zip(caso.pasos, esperado["pasos"], corrida):
            r = Resultado(nombre=caso.nombre, metodo=paso.metodo, camino=paso.camino,
                          estado_a=pa["estado"], estado_b=pb["estado"],
                          error_a=pa["error"], error_b=pb["error"])
            if not (pa["error"] or pb["error"]):
                r.diferencias = comparar(pa["cuerpo"], pb["cuerpo"])
                r.cabeceras = comparar(pa["cabeceras"], pb["cabeceras"], "cabeceras")
            resultados.append(r)
        cambios = _cambios(base, foto)
        if cambios != esperado["cambios"] and resultados:
            faltaron = [c for c in esperado["cambios"] if c not in cambios]
            sobraron = [c for c in cambios if c not in esperado["cambios"]]
            resultados[-1].estado_campus = [f"falta: {c}" for c in faltaron] + [f"sobra: {c}" for c in sobraron]
    return informar(resultados, rutas, detalle)


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
        candidatas = [
            (metodo, camino)
            for metodo, camino, expresion in patrones
            if metodo == r.metodo and expresion.match(limpio)
        ]
        if candidatas:
            cubiertas_set.add(max(candidatas, key=lambda ruta: _especificidad(ruta[1])))
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
        print("\nHay diferencias. Cada una es o un cambio de comportamiento o algo")
        print("variable que falta normalizar en `normalizar.py`.")
        return 1
    print("\nNinguna diferencia.")
    return 0


def _especificidad(camino: str) -> tuple[int, int, int]:
    """Prefiere la ruta concreta a otra más amplia que también coincida."""
    segmentos = camino.strip("/").split("/")
    fijos = [segmento for segmento in segmentos if not segmento.startswith("{")]
    parametros_path = sum(":path}" in segmento for segmento in segmentos)
    return len(fijos), sum(map(len, fijos)), -parametros_path


GRABACION = str(pathlib.Path(__file__).with_name("grabaciones") / "contrato.json.gz")


def main() -> int:
    opciones = argparse.ArgumentParser(description="Compara Django contra la grabación de referencia del contrato")
    opciones.add_argument("--contra", default="django", choices=sorted(servidores.DISPONIBLES))
    opciones.add_argument("--detalle", type=int, default=6)
    opciones.add_argument("--solo", default=None, help="solo los casos que contengan ese texto")
    opciones.add_argument("--grabar", default=None,
                          help="graba lo que contesta y guarda la aplicación, como nueva referencia")
    opciones.add_argument("--contra-grabado", default=GRABACION, dest="grabado",
                          help="grabación de referencia para comparar respuestas y estado")
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

    # La grabación de referencia se hizo el 23/11/2026. El escenario usa fechas
    # relativas a hoy, así que el banco debe reponer ese mismo día para
    # comparar calendario, finales y nombres de exportación sin ruido.
    reloj = datetime(2026, 11, 23, 12).astimezone()
    with patch.object(datos, "ahora", return_value=reloj):
        aplicacion = servidores.DISPONIBLES[args.contra]()
        escenario.cargar()
        base = estado.tomar()

        if args.grabar:
            # Solo cuando un cambio de comportamiento es a propósito: la
            # grabación es la referencia, y regrabarla acepta lo que hoy contesta.
            return grabar(aplicacion, catalogo.todos(aplicacion.rutas), base, args.grabar)

        return contra_grabado(aplicacion, args.grabado, args.solo, base, args.detalle)


if __name__ == "__main__":
    sys.exit(main())
