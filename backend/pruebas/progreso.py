"""Pruebas del progreso del alumno: qué material marcó como visto.

Vivía en `localStorage`, y eso tenía dos problemas que no se ven probando en
una sola máquina: el alumno perdía su avance al cambiar de navegador o de
equipo, y el docente —que mira esto para saber cómo viene el curso— veía
siempre cero, porque el dato nunca salía de la computadora del alumno.

Lo que se comprueba acá es eso último sobre todo: que lo que marca el alumno
llegue a la pantalla del docente. Las dos puntas cuentan sobre la misma
lista, así que si alguna se desvía los números dejan de coincidir y nadie se
entera hasta que alguien los compara a mano.

Uso (desde backend/):
    python -m pruebas.progreso
"""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from app import datos as d
from app.main import app

from . import escenario
from app.servicios.autenticacion import identificar, identificar_id

SANTIAGO = 1  # estudiante
MARIA = 2  # docente

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


def un_curso_con_material() -> tuple[dict, list[dict], list[dict]]:
    """Un módulo que cursa Santiago, con su material y sus tareas."""
    for curso in d.cursos:
        if not any(p["id"] == SANTIAGO for p in d.participantes_de_curso(curso)):
            continue
        material, tareas = [], []
        for carpeta in d.carpetas_de_curso(curso):
            for item in carpeta["items"]:
                (material if d.es_marcable(item) else tareas).append(item)
        if material:
            return curso, material, tareas
    raise SystemExit("El escenario no tiene un módulo con material")


def correr() -> None:
    print("Pruebas del progreso del alumno (en proceso)\n")
    curso, material, tareas = un_curso_con_material()
    # Que no arrastre lo que traiga el escenario
    d.progreso_alumnos[:] = [p for p in d.progreso_alumnos if p["personaId"] != SANTIAGO]

    # ------------------------------------------------------------------
    grupo("Marcar y desmarcar")
    como(SANTIAGO)
    comprobar("al principio no hay nada marcado",
              cliente.get("/api/mi-progreso").json()["completados"] == [])

    primero = material[0]["id"]
    r = cliente.put(f"/api/cursos/{curso['id']}/mi-progreso/{primero}")
    comprobar("se marca", r.status_code == 200, (r.status_code, r.text[:140]))
    comprobar("y queda en la lista", primero in r.json()["completados"], r.json())

    r = cliente.put(f"/api/cursos/{curso['id']}/mi-progreso/{primero}")
    comprobar("marcarlo dos veces no lo duplica",
              r.json()["completados"].count(primero) == 1, r.json())

    r = cliente.delete(f"/api/cursos/{curso['id']}/mi-progreso/{primero}")
    comprobar("se desmarca", primero not in r.json()["completados"])
    comprobar("y desmarcar lo que no estaba no falla",
              cliente.delete(f"/api/cursos/{curso['id']}/mi-progreso/{primero}").status_code == 200)

    # ------------------------------------------------------------------
    grupo("Lo que no se puede marcar")
    r = cliente.put(f"/api/cursos/{curso['id']}/mi-progreso/no-existe-99")
    comprobar("un identificador inventado se rechaza", r.status_code == 404, r.status_code)

    if tareas:
        r = cliente.put(f"/api/cursos/{curso['id']}/mi-progreso/{tareas[0]['id']}")
        comprobar("una tarea no se marca a mano", r.status_code == 400, r.status_code)

    ajeno = next(
        (c for c in d.cursos
         if not any(p["id"] == SANTIAGO for p in d.participantes_de_curso(c))),
        None,
    )
    if ajeno:
        r = cliente.put(f"/api/cursos/{ajeno['id']}/mi-progreso/x-1")
        comprobar("ni material de un módulo que no se cursa", r.status_code == 403, r.status_code)

    # ------------------------------------------------------------------
    grupo("El docente ve lo que marcó el alumno")
    # Es lo que no funcionaba: el dato vivía en el navegador del alumno.
    for item in material:
        cliente.put(f"/api/cursos/{curso['id']}/mi-progreso/{item['id']}")

    como(MARIA)
    r = cliente.get(f"/api/cursos/{curso['id']}/seguimiento")
    comprobar("el seguimiento responde", r.status_code == 200, r.status_code)
    fila = next((a for a in r.json().get("alumnos", []) if a.get("id") == SANTIAGO), None)
    comprobar("el alumno aparece", fila is not None, r.json().get("alumnos"))
    if fila:
        comprobar(
            "y sus vistos son los que marcó",
            fila["vistos"] == len(material),
            (fila["vistos"], len(material)),
        )

    # Las dos puntas tienen que contar sobre lo mismo
    como(SANTIAGO)
    mios = cliente.get("/api/mi-progreso").json()["completados"]
    comprobar(
        "el alumno y el docente cuentan lo mismo",
        fila is None or fila["vistos"] == len([x for x in mios if x in {i["id"] for i in material}]),
        (fila and fila["vistos"], len(mios)),
    )

    # ------------------------------------------------------------------
    grupo("Es de cada alumno")
    otro = next(
        (p["id"] for p in d.participantes_de_curso(curso)
         if d.tiene_rol(p, "Estudiante") and p["id"] != SANTIAGO),
        None,
    )
    if otro:
        # El escenario le trae progreso propio a otros alumnos: lo que hay
        # que comprobar es que no le aparezca **lo de Santiago**, no que su
        # lista esté vacía.
        d.progreso_alumnos[:] = [p for p in d.progreso_alumnos if p["personaId"] != otro]
        como(otro)
        suyo = cliente.get("/api/mi-progreso").json()["completados"]
        comprobar("otro alumno no hereda lo marcado", suyo == [], suyo)

        # Y al marcar él, no se le mezcla con lo del otro
        cliente.put(f"/api/cursos/{curso['id']}/mi-progreso/{material[0]['id']}")
        como(SANTIAGO)
        comprobar(
            "y lo que marca uno no se le suma al otro",
            len(cliente.get("/api/mi-progreso").json()["completados"]) == len(material),
        )

    # ------------------------------------------------------------------
    grupo("Lo que estaba en el navegador se sube una vez")
    como(SANTIAGO)
    d.progreso_alumnos[:] = [p for p in d.progreso_alumnos if p["personaId"] != SANTIAGO]
    viejos = [i["id"] for i in material] + ["inventado-1", "no-existe-2"]

    r = cliente.post("/api/mi-progreso/importar", json={"completados": viejos})
    comprobar("la importación responde", r.status_code == 200, r.status_code)
    comprobar("sube lo que existe", r.json()["sumados"] == len(material), r.json()["sumados"])
    comprobar(
        "y descarta lo inventado sin fallar",
        "inventado-1" not in r.json()["completados"],
        r.json()["completados"],
    )

    r = cliente.post("/api/mi-progreso/importar", json={"completados": viejos})
    comprobar("importar de nuevo no duplica", r.json()["sumados"] == 0, r.json()["sumados"])

    comprobar("sin lista, no se hace nada",
              cliente.post("/api/mi-progreso/importar", json={}).status_code == 400)

    # ------------------------------------------------------------------
    grupo("La regla de qué se marca es una sola")
    # El alumno, el servidor y el docente la aplican; con una copia en cada
    # lado terminarían contando cosas distintas.
    from app.rutas import gestion_modulo

    comprobar("el docente usa la misma función que el servidor",
              gestion_modulo._marcable is d.es_marcable)


def resumir() -> None:
    total = pasadas + len(fallas)
    print(f"\n{'-' * 52}")
    print(f"{pasadas}/{total} comprobaciones pasaron")
    if fallas:
        print("\nFallaron:")
        for f in fallas:
            print(f"  - {f}")
        sys.exit(1)
    print("Todo en orden.")


if __name__ == "__main__":
    correr()
    resumir()
