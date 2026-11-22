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
    python -m pruebas.concurrencia --intensivo # ráfagas de 200 hilos en vez de 50

Las ráfagas van de a 50 hilos por defecto. Con 200 la carrera aparece igual,
pero la máquina se arrastra mientras corre: quedan para cuando se las pide.
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
from app.servicios import modulos, persistencia

from . import escenario

pasadas = 0
fallas: list[str] = []

# Cuántos pedidos salen juntos en cada ráfaga. `--intensivo` lo sube a 200.
HILOS = 50


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


# ===================== Punto 2: la creación de módulos =====================
DOCENTE = 9          # dicta 113 y 118, que en el escenario no tienen módulo
ADMINISTRADORA = 18  # al abrir Módulos crea todos los que tengan cátedra
ESTUDIANTE = 1


def _problemas_de_modulos(materias: list[int]) -> list[str]:
    """Lo que tendría que ser cierto después de cualquier cantidad de altas."""
    problemas = []
    ids = [c["id"] for c in d.cursos]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        problemas.append(f"ids de módulo repetidos: {repetidos}")
    for materia_id in materias:
        materia = d.buscar_materia(materia_id)
        suyos = [c for c in d.cursos if c["codigo"] == materia["codigo"]]
        if len(suyos) != 1:
            problemas.append(f"{materia['codigo']}: {len(suyos)} módulos")
        if not d.buscar_curso(materia.get("cursoId")):
            problemas.append(f"{materia['codigo']}: apunta a un módulo que no existe")
    return problemas


def _con_catedra_sin_modulo() -> list[int]:
    return [
        m["id"] for m in d.materias_plan
        if not d.buscar_curso(m.get("cursoId")) and d.docentes_de_materia(m["id"])
    ]


def e2_el_docente_abre_modulos(veces: int) -> None:
    """E2 tal cual: el menú y la grilla piden la lista a la vez."""
    grupo("Módulos: el menú y la grilla del docente a la vez (E2)")

    intentos = 200 * veces
    malos: list[str] = []
    with hilos_que_se_alternan():
        for _ in range(intentos):
            escenario.cargar()
            en_paralelo(2, lambda _n: modulos.modulos_que_dicta(DOCENTE))
            malos += _problemas_de_modulos([113, 118])
    comprobar(
        f"cada materia queda con un solo módulo y sin ids repetidos ({intentos} intentos)",
        not malos,
        f"{len(malos)} problemas, p. ej. {malos[:2]}",
    )


def e2_todos_los_caminos(veces: int) -> None:
    """Los cinco llamadores de `modulo_para`, cruzados entre sí."""
    grupo("Módulos: todos los caminos que crean, a la vez")

    intentos = 100 * veces
    malos: list[str] = []
    with hilos_que_se_alternan():
        for _ in range(intentos):
            escenario.cargar()
            d.inscripciones_materias.append(
                {"id": 990100, "personaId": ESTUDIANTE, "materiaId": 113, "fecha": "2026-03-01"}
            )
            materia = d.buscar_materia(113)
            caminos = [
                lambda: modulos.modulos_que_dicta(DOCENTE),             # el docente
                lambda: modulos.modulos_con_catedra(),                  # la secretaría
                lambda: modulos.modulos_en_los_que_cursa(ESTUDIANTE),   # el alumno
                lambda: modulos.modulo_para(materia, por_inscripcion=True),  # inscribirse
                lambda: modulos.modulo_para(materia),                   # la comisión
            ]
            en_paralelo(len(caminos), lambda n: caminos[n]())
            malos += _problemas_de_modulos(
                [113, 114, 115, 116, 117, 118, 119]
            )
    comprobar(
        f"ningún camino duplica un módulo ni un id ({intentos} intentos)",
        not malos,
        f"{len(malos)} problemas, p. ej. {malos[:2]}",
    )

    # Una ráfaga sobre el mismo campus, repartidos entre los caminos
    for repeticion in range(veces):
        escenario.cargar()
        antes = len(d.cursos)
        faltaban = len(_con_catedra_sin_modulo())
        materia = d.buscar_materia(113)
        caminos = [
            lambda: modulos.modulos_que_dicta(DOCENTE),
            lambda: modulos.modulos_con_catedra(),
            lambda: modulos.modulo_para(materia, por_inscripcion=True),
            lambda: modulos.modulos_que_dicta(7),
        ]
        with hilos_que_se_alternan():
            _, errores = en_paralelo(HILOS, lambda n: caminos[n % len(caminos)]())
        malos = errores + _problemas_de_modulos([113, 114, 115, 116, 117, 118, 119])
        sufijo = f" (pasada {repeticion + 1})" if veces > 1 else ""
        comprobar(f"{HILOS} pedidos juntos: un módulo por materia{sufijo}", not malos, malos[:2])
        comprobar(f"y se crearon exactamente los que faltaban{sufijo}",
                  len(d.cursos) - antes == faltaban, (len(d.cursos) - antes, faltaban))


def e2_por_http(veces: int) -> None:
    """Lo mismo, de punta a punta: dos `GET /api/cursos` a la vez."""
    grupo("Módulos: dos GET /api/cursos a la vez, por HTTP")

    from .cliente import como, crear_cliente

    intentos = 40 * veces
    malos: list[str] = []
    distintas = 0
    for persona, materias in ((DOCENTE, [113, 118]), (ADMINISTRADORA, [113, 114, 115, 116, 117, 118, 119])):
        como(persona)
        cliente = crear_cliente()
        with hilos_que_se_alternan():
            for _ in range(intentos):
                escenario.cargar()
                respuestas, errores = en_paralelo(2, lambda _n: cliente.get("/api/cursos"))
                malos += errores
                malos += [f"estado {r.status_code}" for r in respuestas if r.status_code != 200]
                malos += _problemas_de_modulos(materias)
                if len(respuestas) == 2:
                    a, b = ({c["id"] for c in r.json()} for r in respuestas)
                    distintas += a != b
    como(None)
    comprobar(
        f"docente y secretaría: un solo módulo por materia ({2 * intentos} pares de pedidos)",
        not malos,
        f"{len(malos)} problemas, p. ej. {malos[:2]}",
    )
    comprobar("el menú y la grilla reciben la misma lista", distintas == 0, f"{distintas} veces no")


def e2_sin_carrera() -> None:
    """Lo de siempre, de a uno: que el arreglo no cambie qué se crea."""
    grupo("Módulos: de a uno, como siempre")

    escenario.cargar()
    antes = len(d.cursos)
    tope = max(c["id"] for c in d.cursos)
    faltaban = _con_catedra_sin_modulo()
    modulos.modulos_con_catedra()
    nuevos = d.cursos[antes:]
    comprobar("crea uno por cada materia con cátedra", len(nuevos) == len(faltaban),
              (len(nuevos), len(faltaban)))
    comprobar("con los ids de siempre: el más alto + 1, en orden",
              [c["id"] for c in nuevos] == list(range(tope + 1, tope + 1 + len(nuevos))))
    comprobar("una segunda vez no crea nada", (modulos.modulos_con_catedra(), len(d.cursos))[1]
              == antes + len(nuevos))
    materia = d.buscar_materia(113)
    comprobar("el que ya existe se devuelve tal cual",
              modulos.modulo_para(materia) is d.buscar_curso(materia["cursoId"]))


# ===================== Punto 3: identificadores y legajos =====================
SECRETARIA = 18
DOCENTE_DEL_TABLERO = 2  # Programación II (módulo 1) tiene el tablero 1-10


@contextlib.contextmanager
def sin_freno():
    """Las ráfagas salen todas de la misma sesión: sin esto, el freno de 120
    escrituras por minuto contestaría 429 antes de llegar a la carrera."""
    from app.servicios import frenos

    anterior = frenos.MAXIMO_ESCRITURAS
    frenos.MAXIMO_ESCRITURAS = 10**9
    frenos.olvidar_todo()
    try:
        yield
    finally:
        frenos.MAXIMO_ESCRITURAS = anterior
        frenos.olvidar_todo()


@contextlib.contextmanager
def firebase_lento():
    """Firebase de mentira, que tarda como el de verdad en dar un acceso.

    Es la espera que hay en el medio de un alta de cuenta: el real tarda
    unos 250 ms. Se reemplazan las tres funciones que usa el alta; ninguna
    llega a Firebase.
    """
    from app.servicios import cuentas

    originales = (cuentas.hay_firebase, cuentas.crear_acceso, cuentas.contrasena_provisoria)
    cuentas.hay_firebase = lambda: True
    cuentas.crear_acceso = lambda *_a: time.sleep(random.uniform(0.005, 0.03)) or "uid-falso"
    cuentas.contrasena_provisoria = lambda: "provisoria"
    try:
        yield
    finally:
        cuentas.hay_firebase, cuentas.crear_acceso, cuentas.contrasena_provisoria = originales


def _repetidos(valores: list) -> list:
    return sorted({v for v in valores if valores.count(v) > 1})


def _rafaga(persona: int, cantidad: int, pedir) -> tuple[list, list[str]]:
    """`cantidad` pedidos a la vez, todos con el mismo cliente: el cliente en
    proceso arma su propio canal por pedido, así que no hace falta uno por hilo."""
    from .cliente import como, crear_cliente

    como(persona)
    cliente = crear_cliente()
    try:
        with sin_freno(), hilos_que_se_alternan():
            return en_paralelo(cantidad, lambda n: pedir(cliente, n))
    finally:
        como(None)


def e1_los_contadores(veces: int) -> None:
    grupo("Identificadores: los contadores de datos.py (E1)")

    escenario.cargar()
    with hilos_que_se_alternan():
        resultados, errores = en_paralelo(8, lambda _n: [d.nuevo_id_mensaje() for _ in range(3000 * veces)])
    todos = [i for lista in resultados for i in lista]
    comprobar(f"{len(todos)} ids pedidos a la vez, ninguno repetido",
              not errores and len(todos) == len(set(todos)),
              f"{len(todos) - len(set(todos))} repetidos")
    comprobar("y no se saltea ninguno", sorted(todos) == list(range(min(todos), min(todos) + len(todos))))


def e4_legajos_de_carrera(veces: int) -> None:
    grupo("Legajos: inscripciones a la misma carrera a la vez (E4)")

    for repeticion in range(veces):
        escenario.cargar()
        nuevos = [
            {"id": 5000 + i, "nombre": f"Ingresante {i}", "correo": f"i{i}@campus.test",
             "roles": ["Estudiante"], "accesoHaceMin": 100000, "estado": "activa"}
            for i in range(HILOS)
        ]
        d.personas.extend(nuevos)

        def inscribir(cliente, n):
            return cliente.post("/api/institucion/asignaciones", json={
                "personaId": 5000 + n, "carreraId": 1, "sedeId": 1, "planId": 1,
            })

        respuestas, errores = _rafaga(SECRETARIA, HILOS, inscribir)
        legajos_dados = [r.json()["asociacion"]["legajo"] for r in respuestas if r.status_code == 201]
        ids = [a["id"] for a in d.asociaciones_academicas]
        sufijo = f" (pasada {repeticion + 1})" if veces > 1 else ""
        comprobar(f"{HILOS} inscripciones juntas: las {HILOS} entran{sufijo}",
                  not errores and len(legajos_dados) == HILOS,
                  (len(legajos_dados), errores[:1], {r.status_code for r in respuestas}))
        comprobar(f"ningún legajo repetido{sufijo}", not _repetidos(legajos_dados),
                  _repetidos(legajos_dados)[:3])
        comprobar(f"ningún id de inscripción repetido{sufijo}", not _repetidos(ids))

    # La misma persona dos veces a la vez: tiene que entrar una sola
    malos = 0
    for _ in range(50 * veces):
        escenario.cargar()
        d.personas.append({"id": 5000, "nombre": "Ingresante", "correo": "i@campus.test",
                           "roles": ["Estudiante"], "accesoHaceMin": 100000, "estado": "activa"})
        respuestas, _ = _rafaga(SECRETARIA, 2, lambda c, _n: c.post(
            "/api/institucion/asignaciones",
            json={"personaId": 5000, "carreraId": 1, "sedeId": 1, "planId": 1}))
        codigos = sorted(r.status_code for r in respuestas)
        suyas = [a for a in d.asociaciones_academicas if a["personaId"] == 5000]
        malos += codigos != [201, 409] or len(suyas) != 1
    comprobar(f"la misma persona dos veces a la vez: una entra y la otra recibe 409 "
              f"({50 * veces} intentos)", malos == 0, f"{malos} veces no")


def e4_altas_de_cuentas(veces: int) -> None:
    grupo("Cuentas: altas a la vez, con la espera de Firebase en el medio")

    for repeticion in range(veces):
        escenario.cargar()
        antes = len(d.personas)

        def dar_de_alta(cliente, n):
            return cliente.post("/api/usuarios", json={
                "nombre": f"Docente {n}", "correo": f"docente{n}@campus.test", "roles": ["Docente"],
            })

        with firebase_lento():
            respuestas, errores = _rafaga(SECRETARIA, HILOS, dar_de_alta)
        creadas = [r.json()["usuario"] for r in respuestas if r.status_code == 201]
        ids = [p["id"] for p in d.personas]
        legajos_personal = [p["legajo"] for p in d.personas if str(p.get("legajo", "")).startswith("FAC-")]
        sufijo = f" (pasada {repeticion + 1})" if veces > 1 else ""
        comprobar(f"{HILOS} altas juntas: las {HILOS} entran{sufijo}",
                  not errores and len(creadas) == HILOS and len(d.personas) - antes == HILOS,
                  (len(creadas), len(d.personas) - antes, errores[:1]))
        comprobar(f"ningún id de persona repetido{sufijo}", not _repetidos(ids), _repetidos(ids)[:3])
        comprobar(f"ningún legajo del personal repetido{sufijo}", not _repetidos(legajos_personal),
                  _repetidos(legajos_personal)[:3])
        comprobar(f"todas quedan activas, como con Firebase de verdad{sufijo}",
                  all(p["estado"] == "activa" for p in d.personas[antes:]))

    # El mismo correo dos veces a la vez: una cuenta sola
    malos = 0
    for _ in range(50 * veces):
        escenario.cargar()
        with firebase_lento():
            respuestas, _ = _rafaga(SECRETARIA, 2, lambda c, _n: c.post(
                "/api/usuarios",
                json={"nombre": "Repetida", "correo": "repetida@campus.test", "roles": ["Docente"]}))
        codigos = sorted(r.status_code for r in respuestas)
        mismas = [p for p in d.personas if p.get("correo") == "repetida@campus.test"]
        malos += codigos != [201, 409] or len(mismas) != 1
    comprobar(f"el mismo correo dos veces a la vez: una cuenta y un 409 ({50 * veces} intentos)",
              malos == 0, f"{malos} veces no")


def e4_publicaciones_del_tablero(veces: int) -> None:
    grupo("Tablero: publicaciones a la vez en el mismo tablero")

    for repeticion in range(veces):
        escenario.cargar()

        def publicar(cliente, n):
            return cliente.post("/api/cursos/1/tableros/1-10/publicaciones",
                                json={"columna": "Preguntas", "texto": f"consulta {n}"})

        respuestas, errores = _rafaga(DOCENTE_DEL_TABLERO, HILOS, publicar)
        dadas = [r.json()["id"] for r in respuestas if r.status_code in (200, 201)]
        tablero = next(i for c in d.contenidos[1] for i in c["items"] if i["id"] == "1-10")
        guardadas = [p["id"] for col in tablero["columnas"] for p in col.get("publicaciones") or []]
        sufijo = f" (pasada {repeticion + 1})" if veces > 1 else ""
        comprobar(f"{HILOS} publicaciones juntas: las {HILOS} entran{sufijo}",
                  not errores and len(dadas) == HILOS, (len(dadas), errores[:1]))
        comprobar(f"ningún id de publicación repetido{sufijo}", not _repetidos(guardadas),
                  _repetidos(guardadas)[:3])


def e4_sin_carrera() -> None:
    """De a uno, los números son los de siempre."""
    grupo("Identificadores y legajos: de a uno, como siempre")

    from .cliente import como, crear_cliente

    escenario.cargar()
    cliente = crear_cliente()
    como(SECRETARIA)
    d.personas.append({"id": 5000, "nombre": "Ingresante", "correo": "i@campus.test",
                       "roles": ["Estudiante"], "accesoHaceMin": 100000, "estado": "activa"})
    anio = d.ahora().year
    previa = cliente.get("/api/institucion/legajo-siguiente", params={"carreraId": 1}).json()["legajo"]
    r = cliente.post("/api/institucion/asignaciones",
                     json={"personaId": 5000, "carreraId": 1, "sedeId": 1, "planId": 1})
    comprobar("el legajo es el de la vista previa", r.json()["asociacion"]["legajo"] == previa,
              (previa, r.json()["asociacion"]["legajo"]))
    comprobar("con el formato de siempre", previa.startswith(f"LSI-{anio}-"))

    tope = max(p["id"] for p in d.personas)
    r = cliente.post("/api/usuarios", json={"nombre": "Nueva", "correo": "nueva@campus.test",
                                            "roles": ["Docente"]})
    usuario = r.json()["usuario"]
    comprobar("la persona nueva lleva el id más alto + 1", usuario["id"] == tope + 1,
              (usuario["id"], tope + 1))
    comprobar("sin Firebase queda pendiente, como siempre",
              d.buscar_persona(usuario["id"])["estado"] == "pendiente")
    comprobar("y con legajo del personal", str(d.buscar_persona(usuario["id"]).get("legajo")).startswith("FAC-"))
    r = cliente.post("/api/usuarios", json={"nombre": "Otra", "correo": "nueva@campus.test"})
    comprobar("un correo repetido sigue dando 409", r.status_code == 409, r.status_code)

    como(DOCENTE_DEL_TABLERO)
    r1 = cliente.post("/api/cursos/1/tableros/1-10/publicaciones", json={"columna": "Preguntas", "texto": "a"})
    r2 = cliente.post("/api/cursos/1/tableros/1-10/publicaciones", json={"columna": "Comentarios", "texto": "b"})
    comprobar("las publicaciones siguen numerándose de a una", r2.json()["id"] == r1.json()["id"] + 1,
              (r1.json().get("id"), r2.json().get("id")))
    como(None)


# ===================== Correr =====================
def correr() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--veces", type=int, default=1)
    parser.add_argument("--intensivo", action="store_true",
                        help="ráfagas de 200 hilos en vez de 50 (carga bastante la máquina)")
    argumentos = parser.parse_args()
    veces = argumentos.veces
    global HILOS
    if argumentos.intensivo:
        HILOS = 200
    print(f"Ráfagas de {HILOS} hilos, {veces} pasada(s).")

    import logging

    logging.disable(logging.ERROR)

    guardado_sin_carrera()
    e3_la_fotografia(veces)
    guardados_que_se_cruzan()
    la_red_sin_candado()
    guardados_simultaneos(veces)

    e2_sin_carrera()
    e2_el_docente_abre_modulos(veces)
    e2_todos_los_caminos(veces)
    e2_por_http(veces)

    e4_sin_carrera()
    e1_los_contadores(veces)
    e4_legajos_de_carrera(veces)
    e4_altas_de_cuentas(veces)
    e4_publicaciones_del_tablero(veces)

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
