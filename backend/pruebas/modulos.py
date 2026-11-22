"""Pruebas de los módulos: quién ve cuál, y qué es de cada uno.

Las tres cosas que se cuidan acá salieron de una revisión y las tres venían
funcionando mal sin que nada fallara, que es la forma en que estos errores se
quedan meses:

1. **El alcance.** `GET /api/cursos/{id}` y `/{id}/modulo` comprobaban que el
   módulo existiera y nada más: cambiando el número en la dirección se leía el
   contenido, los anuncios y la lista completa de participantes de cualquier
   materia. Fuera de alcance tiene que responder **404 y no 403**, como en
   Biblioteca, Finales y Auditoría: un 403 ya confirma que ese módulo existe.

2. **El favorito es de cada persona.** Era un booleano adentro del curso, así
   que la estrella que ponía uno se la encontraban todos, y la ruta ni siquiera
   pedía sesión.

3. **Las campanitas son de quien pregunta.** `GET /api/contadores` contaba
   siempre sobre el usuario de prueba.

Y de paso los frenos, que no existían: el tope de tamaño y el de peticiones
por minuto.

Uso (desde backend/):
    python -m pruebas.modulos
"""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from app import datos as d
from app.main import app
from app.servicios import frenos
from app.servicios.autenticacion import identificar, identificar_id

from . import escenario

SANTIAGO = 1  # estudiante, cursa el módulo 1
MARIA = 2  # docente del módulo 1
HERNAN = 3  # estudiante, también del módulo 1
PABLO = 7  # docente de otro módulo
SECRETARIA = 18  # Administrador
CLAUDIA = 19  # Supervisor

pasadas = 0
fallas: list[str] = []

_quien = {"id": SANTIAGO}
escenario.cargar()

app.dependency_overrides[identificar] = lambda: d.buscar_persona(_quien["id"])
app.dependency_overrides[identificar_id] = lambda: _quien["id"]
cliente = TestClient(app)


def como(persona_id: int) -> None:
    _quien["id"] = persona_id


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


def mis_modulos() -> list[dict]:
    return cliente.get("/api/cursos").json()


def ids_de(modulos) -> set[int]:
    return {m["id"] for m in modulos}


def donde_esta(persona_id: int) -> set[int]:
    """Los módulos en los que esa persona figura, leído de los datos.

    Se calcula y no se escribe a mano porque los módulos **se crean solos**
    al pedirlos: el de una materia existe desde que se la asignan al docente,
    no desde que alguien entra a verla. Una lista fija de ids envejece a la
    primera inscripción.
    """
    return {
        c["id"]
        for c in d.cursos
        if c.get("docenteId") == persona_id
        or any(p["id"] == persona_id for p in d.participantes_de_curso(c))
    }


def correr() -> None:
    print("Pruebas de los módulos (en proceso)\n")
    frenos.olvidar_todo()

    # ------------------------------------------------------------------
    grupo("Cada uno ve los módulos que le tocan")
    como(SANTIAGO)
    mios = ids_de(mis_modulos())
    comprobar("el estudiante ve en los que cursa", mios == donde_esta(SANTIAGO), mios)
    comprobar("y son algunos, no todos", 0 < len(mios) < len(d.cursos), len(mios))

    como(MARIA)
    suyos = ids_de(mis_modulos())
    comprobar(
        "el docente ve los que dicta",
        suyos == {c["id"] for c in d.cursos if c.get("docenteId") == MARIA},
        suyos,
    )

    como(PABLO)
    otros = ids_de(mis_modulos())
    comprobar("y no los de otra cátedra", not (otros & suyos), otros & suyos)

    como(SECRETARIA)
    comprobar("el administrador ve todo el campus", len(mis_modulos()) >= 6)
    como(CLAUDIA)
    comprobar("el supervisor también", len(mis_modulos()) >= 6)

    # ------------------------------------------------------------------
    # Lo que más importa: que el que no lo cursa no pueda **leerlo**, no solo
    # que no lo vea listado. Esconderlo de la grilla no es un control de
    # acceso.
    grupo("Un módulo ajeno no se abre cambiando el número")
    como(SANTIAGO)
    propio = min(donde_esta(SANTIAGO))
    ajeno = min(c["id"] for c in d.cursos if c["id"] not in donde_esta(SANTIAGO))

    comprobar("la ficha da 404", cliente.get(f"/api/cursos/{ajeno}").status_code == 404)
    comprobar(
        "la pantalla del módulo también",
        cliente.get(f"/api/cursos/{ajeno}/modulo").status_code == 404,
    )
    comprobar(
        "404 y no 403: un 403 confirmaría que existe",
        cliente.get(f"/api/cursos/{ajeno}/modulo").status_code != 403,
    )
    comprobar(
        "el propio sí se abre",
        cliente.get(f"/api/cursos/{propio}/modulo").status_code == 200,
    )

    como(PABLO)
    de_otra_catedra = min(
        c["id"] for c in d.cursos if c["id"] not in donde_esta(PABLO)
    )
    comprobar(
        "un docente tampoco entra al módulo de otra cátedra",
        cliente.get(f"/api/cursos/{de_otra_catedra}/modulo").status_code == 404,
    )
    como(CLAUDIA)
    comprobar(
        "quien supervisa entra a cualquiera",
        cliente.get(f"/api/cursos/{ajeno}/modulo").status_code == 200,
    )

    # ------------------------------------------------------------------
    grupo("La estrella es de quien la pone")
    # Uno que compartan los dos: la gracia es que la estrella de uno no sea
    # la del otro estando en el mismo módulo.
    compartido = min(donde_esta(SANTIAGO) & donde_esta(HERNAN))
    antes = dict((c["id"], c.get("favorito")) for c in d.cursos)

    como(SANTIAGO)
    r = cliente.post(f"/api/cursos/{compartido}/favorito")
    comprobar("se marca", r.status_code == 200 and r.json()["favorito"] is True, r.json())
    comprobar(
        "y queda marcada para él",
        next(m for m in mis_modulos() if m["id"] == compartido)["favorito"] is True,
    )

    como(HERNAN)
    comprobar(
        "el otro estudiante del mismo módulo no la ve marcada",
        next(m for m in mis_modulos() if m["id"] == compartido)["favorito"] is False,
    )

    como(SANTIAGO)
    comprobar(
        "volver a tocarla la saca",
        cliente.post(f"/api/cursos/{compartido}/favorito").json()["favorito"] is False,
    )
    # Lo que no puede pasar es que la estrella vuelva a escribirse adentro del
    # módulo: ahí era de todos.
    comprobar(
        "no se escribe nada en el módulo",
        all(c.get("favorito") == antes.get(c["id"]) for c in d.cursos),
        [(c["id"], c.get("favorito")) for c in d.cursos if c.get("favorito") != antes.get(c["id"])],
    )
    comprobar(
        "un módulo ajeno no se puede marcar",
        cliente.post(f"/api/cursos/{ajeno}/favorito").status_code == 404,
    )

    # ------------------------------------------------------------------
    grupo("Las campanitas son de quien pregunta")
    como(SANTIAGO)
    suyas = cliente.get("/api/contadores")
    comprobar("responden", suyas.status_code == 200, suyas.status_code)
    comprobar(
        "con lo que corresponde a esa persona",
        suyas.json() == d.resumen_de_novedades(SANTIAGO),
        suyas.json(),
    )

    como(PABLO)
    comprobar(
        "y a otra persona le dan lo suyo",
        cliente.get("/api/contadores").json() == d.resumen_de_novedades(PABLO),
    )

    # ------------------------------------------------------------------
    # El botón «+ Publicar» estaba dibujado y no había ruta detrás: la única
    # forma de agregarle algo a un tablero era tocar la base.
    grupo("El tablero de consultas se puede escribir")
    como(SANTIAGO)
    tablero = next(
        (i for ap in d.contenidos.get(propio, []) for i in ap["items"] if i["tipo"] == "tablero"),
        None,
    )
    if tablero is None:
        comprobar("hay un tablero en el escenario", False, "no se encontró ninguno")
    else:
        columna = tablero["columnas"][0]["titulo"]
        cuantas = len(tablero["columnas"][0]["publicaciones"])
        camino = f"/api/cursos/{propio}/tableros/{tablero['id']}/publicaciones"

        r = cliente.post(camino, json={"columna": columna, "texto": "¿Esto queda guardado?"})
        comprobar("un estudiante publica", r.status_code == 201, r.json())
        comprobar("queda con su autor", r.json().get("autorId") == SANTIAGO, r.json())
        comprobar(
            "y entra en la columna",
            len(tablero["columnas"][0]["publicaciones"]) == cuantas + 1,
        )

        comprobar(
            "una consulta vacía se rechaza",
            cliente.post(camino, json={"columna": columna, "texto": "   "}).status_code == 400,
        )
        comprobar(
            "una columna que no existe da 404",
            cliente.post(camino, json={"columna": "Inventada", "texto": "hola"}).status_code
            == 404,
        )
        comprobar(
            "un tablero que no existe también",
            cliente.post(
                f"/api/cursos/{propio}/tableros/9-99/publicaciones",
                json={"columna": columna, "texto": "hola"},
            ).status_code
            == 404,
        )

        como(PABLO)
        comprobar(
            "y alguien de afuera del módulo no escribe",
            cliente.post(camino, json={"columna": columna, "texto": "hola"}).status_code == 404,
        )
        como(SANTIAGO)

    # ------------------------------------------------------------------
    grupo("Las rutas que se sacaron no volvieron")
    comprobar("PUT /api/me no existe", cliente.put("/api/me", json={}).status_code == 405)
    comprobar("GET /api/actividad tampoco", cliente.get("/api/actividad").status_code == 404)
    comprobar("ni GET /api/informacion", cliente.get("/api/informacion").status_code == 404)

    # ------------------------------------------------------------------
    grupo("Los frenos")
    como(SANTIAGO)
    frenos.olvidar_todo()
    grande = cliente.post(
        f"/api/cursos/{propio}/favorito",
        headers={"content-length": str(frenos.MAXIMO_BYTES + 1)},
    )
    comprobar("un envío enorme se corta antes de leerlo", grande.status_code == 413, grande.json())

    frenos.olvidar_todo()
    respuestas = [
        cliente.post(f"/api/cursos/{propio}/favorito").status_code
        for _ in range(frenos.MAXIMO_ESCRITURAS + 3)
    ]
    comprobar("se frena al pasarse del minuto", 429 in respuestas)
    comprobar(
        "pero recién después del cupo, no antes",
        respuestas.count(429) == 3,
        respuestas.count(429),
    )

    # Distinta sesión, distinto contador: si no, una facultad entera detrás de
    # la misma salida a internet se frenaría por usar bien el campus.
    frenos.olvidar_todo()
    for _ in range(frenos.MAXIMO_ESCRITURAS + 1):
        cliente.post(f"/api/cursos/{propio}/favorito", headers={"Authorization": "Bearer uno"})
    otra = cliente.post(
        f"/api/cursos/{propio}/favorito", headers={"Authorization": "Bearer dos"}
    )
    comprobar("el freno es por sesión y no por dirección", otra.status_code == 200, otra.status_code)
    frenos.olvidar_todo()

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
