"""Pruebas de concurrencia: dos peticiones a la vez sobre la misma memoria.

El servidor atiende varias peticiones al mismo tiempo, cada una en su hilo, y
todas leen y escriben las listas de `datos.py`. Lo que se prueba acá son las
carreras que salieron del análisis de la migración: cosas que con una sola
persona usando el campus no pasan nunca, y con un aula entera sí.

**Ninguna toca Firestore.** El guardado se prueba contra un Firestore falso
que imita lo que importa del real: congela el documento en el momento en que
se lo entrega (como `lote.set()`), tarda un rato al azar en confirmarlo (la
red) y aplica las escrituras en el orden en que terminan, no en el que
empezaron. Mientras dura la prueba, pedir el cliente real da error: si algo
intentara escribir en la base de la facultad, la prueba falla en vez de
escribir.

Para que los hilos se alternen seguido se baja `sys.setswitchinterval`. Un
resultado limpio dice que la carrera **no se reprodujo** en tantas vueltas; un
resultado sucio dice que **puede pasar**, no con qué frecuencia pasaría con
tráfico real.

Uso (desde backend/):
    python -m pruebas.concurrencia             # una pasada
    python -m pruebas.concurrencia --veces 5   # repetida, para ver que no es suerte
"""

from __future__ import annotations

import argparse
import contextlib
import json
import random
import sys
import threading
import time

from app import datos as d
from app.servicios import firestore as fs
from app.servicios import persistencia

from . import escenario

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


def en_paralelo(cantidad: int, funcion) -> tuple[list, list[str]]:
    """Corre `funcion` en `cantidad` hilos que arrancan todos juntos."""
    barrera = threading.Barrier(cantidad)
    resultados: list = []
    errores: list[str] = []

    def correr(numero: int) -> None:
        barrera.wait()
        try:
            resultados.append(funcion(numero))
        except Exception as error:  # noqa: BLE001 - se cuenta como falla
            errores.append(repr(error))

    hilos = [threading.Thread(target=correr, args=(i,)) for i in range(cantidad)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    return resultados, errores


@contextlib.contextmanager
def hilos_que_se_alternan():
    anterior = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        yield
    finally:
        sys.setswitchinterval(anterior)


# ===================== El Firestore falso =====================
def _texto(valor) -> str:
    return json.dumps(valor, sort_keys=True, default=str, ensure_ascii=False)


class FirestoreFalso:
    """Lo que importa del real para estas carreras, y nada más."""

    def __init__(self, inicial: dict[tuple[str, str], str]):
        self.documentos = dict(inicial)
        self.borrados: set[tuple[str, str]] = set()
        self.vueltas = 0
        self._candado = threading.Lock()

    def escribir(self, cambios, bajas) -> None:
        # Se congela al entregarlo, como `lote.set()`: lo que llegue a la base
        # es lo que había en este instante, no lo que haya al confirmar.
        congelados = [(c, k, _texto(v)) for c, k, v in cambios]
        bajas = list(bajas)
        # La red: tarda, y dos escrituras pueden terminar en cualquier orden
        time.sleep(random.uniform(0, 0.004))
        with self._candado:
            self.vueltas += 1
            for coleccion, clave, texto in congelados:
                self.documentos[(coleccion, clave)] = texto
            for clave in bajas:
                self.documentos.pop(tuple(clave), None)
                self.borrados.add(tuple(clave))


def _lo_que_deberia_haber() -> dict[tuple[str, str], str]:
    """La memoria, escrita como la escribiría el guardado."""
    salida = {
        clave: _texto(persistencia._para_firestore(valor))
        for clave, valor in persistencia._documentos().items()
    }
    for coleccion in persistencia.SOLO_AGREGAR:
        atributo, clave = persistencia.REGISTROS[coleccion]
        for item in getattr(d, atributo):
            salida[(coleccion, clave(item))] = _texto(persistencia._para_firestore(item))
    return salida


def _prohibido(*_args, **_kwargs):
    raise RuntimeError("prueba: el Firestore real no se toca")


@contextlib.contextmanager
def con_firestore_falso():
    """Prende el guardado contra el falso y deja todo como estaba al salir."""
    inicial = _lo_que_deberia_haber()
    falso = FirestoreFalso(inicial)
    originales = (
        persistencia._activo,
        persistencia._huellas,
        dict(persistencia._ya_escritos),
        persistencia._escribir,
        fs.obtener_firestore,
    )
    persistencia._activo = True
    persistencia._huellas = {
        clave: persistencia._huella(valor) for clave, valor in persistencia._documentos().items()
    }
    persistencia._ya_escritos.clear()
    for coleccion in persistencia.SOLO_AGREGAR:
        atributo, clave = persistencia.REGISTROS[coleccion]
        persistencia._ya_escritos[coleccion] = {clave(x) for x in getattr(d, atributo)}
    persistencia._escribir = falso.escribir
    fs.obtener_firestore = _prohibido
    try:
        yield falso
    finally:
        (
            persistencia._activo,
            persistencia._huellas,
            ya_escritos,
            persistencia._escribir,
            fs.obtener_firestore,
        ) = originales
        persistencia._ya_escritos.clear()
        persistencia._ya_escritos.update(ya_escritos)


# ===================== Punto 1: el guardado =====================
VUELTAS_E3 = 400


def e3_la_fotografia(veces: int) -> None:
    """E3 tal cual: recorrer una lista mientras otra petición la cambia."""
    grupo("Guardado: la fotografía de la memoria (E3)")

    escenario.cargar()
    reales = set(persistencia._documentos())
    extra = {"id": 999001, "titulo": "x", "fecha": d.iso(d.ahora()), "tipo": "evento"}
    parar = threading.Event()

    def mover_lista() -> None:
        while not parar.is_set():
            d.eventos.insert(0, extra)
            d.eventos.remove(extra)

    def mover_diccionario() -> None:
        while not parar.is_set():
            d.contenidos[99999] = []
            d.contenidos.pop(99999, None)

    faltaron = explotaron = 0
    with hilos_que_se_alternan():
        hilos = [threading.Thread(target=mover_lista), threading.Thread(target=mover_diccionario)]
        for hilo in hilos:
            hilo.start()
        try:
            for _ in range(VUELTAS_E3 * veces):
                try:
                    vistas = set(persistencia._documentos())
                except RuntimeError:
                    explotaron += 1
                    continue
                if reales - vistas:
                    faltaron += 1
        finally:
            parar.set()
            for hilo in hilos:
                hilo.join()

    total = VUELTAS_E3 * veces
    comprobar(
        f"ninguna fotografía pierde un registro que existe ({total} vueltas)",
        faltaron == 0,
        f"{faltaron} lo habrían borrado de Firestore",
    )
    comprobar(
        f"ninguna fotografía explota porque un diccionario cambió ({total} vueltas)",
        explotaron == 0,
        f"{explotaron} habrían terminado en 500",
    )


def _una_peticion(numero: int, vuelta: int, estables: list[dict]) -> None:
    """Lo que hace una petición cualquiera: tocar la memoria y guardar."""
    propio = {"id": 900000 + numero * 1000 + vuelta, "titulo": f"e{numero}-{vuelta}",
              "fecha": "2026-01-01T00:00:00Z", "tipo": "evento"}
    d.eventos.append(propio)                                  # alta
    persona = estables[(numero + vuelta) % len(estables)]
    persona["bio"] = f"{numero}-{vuelta}"                     # cambio en el lugar
    persona.pop("extraConcurrencia", None) if vuelta % 2 else persona.update(
        {"extraConcurrencia": vuelta}                         # el diccionario cambia de tamaño
    )
    d.contenidos[880000 + numero] = [{"id": vuelta}]          # el diccionario de módulos crece
    if vuelta % 3 == 0:
        d.contenidos.pop(880000 + numero, None)
    if vuelta % 2:
        d.eventos.remove(propio)                              # baja
    if vuelta % 4 == 0:
        d.eventos.insert(0, propio)                           # corre a todos los demás
        d.eventos.remove(propio)
    persistencia.guardar_cambios()


def guardados_simultaneos(veces: int) -> None:
    grupo("Guardado: muchas peticiones guardando a la vez")

    hilos, vueltas = 8, 25
    for repeticion in range(veces):
        escenario.cargar()
        estables = d.personas[:6]
        claves_estables = set(persistencia._documentos())
        errores: list[str] = []

        def peticiones(numero: int) -> None:
            for vuelta in range(vueltas):
                try:
                    _una_peticion(numero, vuelta, estables)
                except Exception as error:  # noqa: BLE001 - un 500 de esa petición
                    errores.append(repr(error))

        with con_firestore_falso() as falso, hilos_que_se_alternan():
            en_paralelo(hilos, peticiones)
            # Una petición más, tranquila, después de todas: la que en la
            # realidad llega un rato después y no tiene a nadie al lado.
            persistencia.guardar_cambios()
            esperado = _lo_que_deberia_haber()
            distintos = {k for k in esperado.keys() | falso.documentos.keys()
                         if esperado.get(k) != falso.documentos.get(k)}
            borrados_buenos = falso.borrados & claves_estables

        sufijo = f" (pasada {repeticion + 1})" if veces > 1 else ""
        comprobar(
            f"ningún guardado termina en error{sufijo}",
            not errores,
            f"{len(errores)} de {hilos * vueltas}: {errores[:1]}",
        )
        comprobar(
            f"la base queda igual a la memoria{sufijo}",
            not distintos,
            f"{len(distintos)} documentos distintos, p. ej. {sorted(distintos)[:3]}",
        )
        comprobar(
            f"no se borra nunca un registro que siguió existiendo{sufijo}",
            not borrados_buenos,
            sorted(borrados_buenos)[:3],
        )


def guardados_que_se_cruzan() -> None:
    """Dos guardados con fotografías de momentos distintos, a la vez en la red.

    Alguien desmarca un módulo favorito y lo vuelve a marcar enseguida. El
    primer guardado sale con la baja y tarda; el segundo ve el favorito otra
    vez, igual a como estaba guardado, así que no lo escribe. Si el primero
    termina antes, la base se queda sin el favorito y las huellas —las del
    segundo— dicen que está: no se vuelve a escribir nunca, y al reiniciar el
    servidor el favorito desapareció.
    """
    grupo("Guardado: una baja y un alta que se cruzan en la red")

    escenario.cargar()
    favorito = {"personaId": 1, "cursoId": 1}
    d.favoritos_modulo.append(favorito)
    clave = ("favoritosModulo", "1_1")

    with con_firestore_falso() as falso:
        compuertas = [threading.Event(), threading.Event()]
        entraron = [threading.Event(), threading.Event()]
        llamadas = 0
        sano = falso.escribir

        def lento(cambios, bajas):
            nonlocal llamadas
            turno = min(llamadas, 1)
            llamadas += 1
            entraron[turno].set()
            compuertas[turno].wait(5)
            sano(cambios, bajas)

        persistencia._escribir = lento

        def desmarcar():
            d.favoritos_modulo.remove(favorito)
            persistencia.guardar_cambios()

        def volver_a_marcar():
            d.favoritos_modulo.append(favorito)
            d.personas[0]["bio"] = "otro cambio, para que este guardado escriba algo"
            persistencia.guardar_cambios()

        primero = threading.Thread(target=desmarcar)
        primero.start()
        entraron[0].wait(5)                 # el primero ya está en la red
        segundo = threading.Thread(target=volver_a_marcar)
        segundo.start()
        entraron[1].wait(0.5)               # el segundo, si nadie lo frena, también
        compuertas[0].set()                 # termina primero el más viejo
        primero.join(5)
        compuertas[1].set()
        segundo.join(5)
        persistencia._escribir = sano

        persistencia.guardar_cambios()      # la petición siguiente, tranquila
        comprobar("el favorito sigue en la memoria", favorito in d.favoritos_modulo)
        comprobar("y en la base", clave in falso.documentos)
        comprobar("la base queda igual a la memoria", falso.documentos == _lo_que_deberia_haber())


def la_red_sin_candado() -> None:
    """Mientras una vuelta está en la red, el campus no se frena."""
    grupo("Guardado: el candado no se toma durante la red")

    escenario.cargar()
    with con_firestore_falso() as falso:
        compuerta, adentro = threading.Event(), threading.Event()
        sano = falso.escribir

        def lento(cambios, bajas):
            adentro.set()
            compuerta.wait(5)
            sano(cambios, bajas)

        persistencia._escribir = lento
        d.personas[0]["bio"] = "primera"
        primera = threading.Thread(target=persistencia.guardar_cambios)
        primera.start()
        adentro.wait(5)

        libre = persistencia._turno.acquire(blocking=False)
        if libre:
            persistencia._turno.release()
        comprobar("con una vuelta en la red, el candado está libre", libre)

        inicio = time.perf_counter()
        d.eventos.append({"id": 990010, "titulo": "x", "fecha": "2026-01-01", "tipo": "evento"})
        comprobar("y la memoria se sigue usando sin esperar",
                  time.perf_counter() - inicio < 0.05)

        # Diez peticiones terminan mientras tanto: esperan, y una sola vuelta
        # las cubre a todas.
        vueltas_antes = falso.vueltas
        esperando = [threading.Thread(target=persistencia.guardar_cambios) for _ in range(10)]
        for hilo in esperando:
            hilo.start()
        time.sleep(0.2)
        comprobar("las que terminan mientras tanto no salen a la red",
                  falso.vueltas == vueltas_antes)
        compuerta.set()
        primera.join(5)
        for hilo in esperando:
            hilo.join(5)
        persistencia._escribir = sano
        comprobar("una sola vuelta más las cubre a todas",
                  falso.vueltas - vueltas_antes <= 2, falso.vueltas - vueltas_antes)
        comprobar("nadie quedó esperando", not any(h.is_alive() for h in esperando))
        comprobar("y lo de todas quedó guardado", falso.documentos == _lo_que_deberia_haber())


def guardado_sin_carrera() -> None:
    """Lo de siempre, sin nadie al lado: que el arreglo no cambie nada."""
    grupo("Guardado: una petición sola, como siempre")

    escenario.cargar()
    with con_firestore_falso() as falso:
        comprobar("sin cambios no escribe", persistencia.guardar_cambios() == 0 and falso.vueltas == 0)

        d.eventos.append({"id": 990001, "titulo": "Acto", "fecha": "2026-05-25", "tipo": "evento"})
        d.personas[0]["bio"] = "otra"
        escritos = persistencia.guardar_cambios()
        comprobar("un alta y un cambio son dos documentos", escritos == 2, escritos)
        comprobar("el alta llegó", ("eventos", "990001") in falso.documentos)

        d.eventos.pop()
        escritos = persistencia.guardar_cambios()
        comprobar("una baja es un documento", escritos == 1, escritos)
        comprobar("la baja llegó", ("eventos", "990001") not in falso.documentos)

        d.auditoria.append({"id": 990002, "accion": "edicion", "modulo": "usuarios"})
        comprobar("lo de solo agregar se escribe una vez", persistencia.guardar_cambios() == 1)
        comprobar("y no se repite", persistencia.guardar_cambios() == 0)
        comprobar("la base queda igual a la memoria", falso.documentos == _lo_que_deberia_haber())

    # Si Firestore falla, no se da por guardado y se reintenta
    escenario.cargar()
    with con_firestore_falso() as falso:
        sano = persistencia._escribir

        def caido(*_a):
            raise RuntimeError("sin red")

        persistencia._escribir = caido
        d.personas[0]["bio"] = "reintento"
        comprobar("una falla devuelve cero", persistencia.guardar_cambios() == 0)
        persistencia._escribir = sano
        comprobar("la petición siguiente lo reintenta", persistencia.guardar_cambios() == 1)
        comprobar("y queda guardado", falso.documentos == _lo_que_deberia_haber())

    comprobar("al terminar, el guardado queda apagado", not persistencia.activo())
    comprobar("y el cliente de Firestore es el real otra vez", fs.obtener_firestore is not _prohibido)


# ===================== Correr =====================
def correr() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--veces", type=int, default=1)
    veces = parser.parse_args().veces

    import logging

    logging.disable(logging.ERROR)

    guardado_sin_carrera()
    e3_la_fotografia(veces)
    guardados_que_se_cruzan()
    la_red_sin_candado()
    guardados_simultaneos(veces)

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
