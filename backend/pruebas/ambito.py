"""Pruebas del ámbito: hasta dónde llega quien supervisa.

`Supervisor` era un permiso sin recorte: quien lo tuviera veía y moderaba
**todo el campus** —la biblioteca de cualquier cátedra, el registro de
auditoría entero—. En una facultad con varias carreras eso no describe a
nadie, y el día que alguien lo nota ya hubo meses de acceso que nadie quiso
dar.

Lo que se cuida acá es que el recorte sea **de verdad y en los dos lados**: no
alcanza con esconder la carrera del desplegable si después el material se abre
igual poniendo su id. Y, sobre todo, que **sin ámbito nada cambie**: el campus
venía funcionando así y un campo nuevo que rompiera todos los permisos el día
que se agrega sería peor que el problema.

Uso (desde backend/):
    python -m pruebas.ambito
"""

from __future__ import annotations

import sys


from app import datos as d
from app.servicios import ambito as amb
from app.servicios import auditoria
from app.servicios import frenos

from . import escenario
from .cliente import como, crear_cliente

SANTIAGO = 1  # estudiante
MARIA = 2  # docente
SECRETARIA = 18  # Administrador
CLAUDIA = 19  # Supervisor

pasadas = 0
fallas: list[str] = []

escenario.cargar()
frenos.olvidar_todo()

cliente = crear_cliente()
como(SECRETARIA)


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


def fijar(persona_id: int, carreras: list[int], sedes: list[int] | None = None):
    como(SECRETARIA)
    return cliente.patch(
        f"/api/usuarios/{persona_id}",
        json={"ambito": {"carreras": carreras, "sedes": sedes or []}},
    )


def materias_que_ve(persona_id: int) -> set[int]:
    como(persona_id)
    return {m["id"] for m in cliente.get("/api/biblioteca/opciones").json()["materias"]}


def correr() -> None:
    print("Pruebas del ámbito de quien supervisa (en proceso)\n")

    # El escenario tiene una sola carrera con materias; para probar el recorte
    # hace falta una segunda. Se arma acá y no en el juego de datos porque es
    # de esta prueba: el plan de la facultad no se inventa.
    otra_carrera = max(c["id"] for c in d.carreras_institucion) + 1
    d.carreras_institucion.append(
        {"id": otra_carrera, "nombre": "Carrera de prueba", "codigo": "PRU", "activa": True}
    )
    plan = max(p["id"] for p in d.planes_estudio) + 1
    d.planes_estudio.append(
        {"id": plan, "carreraId": otra_carrera, "nombre": "Plan de prueba", "activo": True}
    )
    ajena = max(m["id"] for m in d.materias_plan) + 1
    d.materias_plan.append(
        {
            "id": ajena,
            "carreraId": otra_carrera,
            "planId": plan,
            "codigo": "PRU-1",
            "nombre": "Materia de otra carrera",
            "anio": 1,
            "cuatrimestre": 1,
            "activa": True,
            "correlativas": {},
        }
    )
    propia_de_una = next(m["id"] for m in d.materias_plan if m.get("carreraId") == 1)

    # ------------------------------------------------------------------
    grupo("Sin ámbito, nada cambia")
    comprobar("una persona sin ámbito alcanza todo", amb.de(d.buscar_persona(CLAUDIA)) is None)
    todas = materias_que_ve(CLAUDIA)
    comprobar("y ve las materias de las dos carreras", {propia_de_una, ajena} <= todas, len(todas))

    # ------------------------------------------------------------------
    grupo("Con ámbito, solo lo suyo")
    r = fijar(CLAUDIA, [1])
    comprobar("se guarda", r.status_code == 200, r.json())
    comprobar(
        "y queda dicho en la ficha",
        r.json()["usuario"]["ambito"]["carreras"][0]["id"] == 1,
        r.json()["usuario"]["ambito"],
    )

    suyas = materias_que_ve(CLAUDIA)
    comprobar("ve las de su carrera", propia_de_una in suyas)
    comprobar("y no las de la otra", ajena not in suyas, sorted(suyas)[-3:])

    # Lo que importa de verdad: que el recorte no sea solo del desplegable.
    # Esconder la carrera de la lista y dejar que el material se abra igual
    # poniendo su número no es un control de acceso.
    como(CLAUDIA)
    intento = cliente.post(
        "/api/biblioteca",
        json={
            "materiaId": ajena,
            "titulo": "Libro de prueba",
            "autor": "Alguien",
            "tipo": "Libro",
            "tengoAutorizacion": True,
        },
    )
    comprobar(
        "tampoco puede aportar a una materia fuera de su ámbito",
        intento.status_code >= 400,
        (intento.status_code, intento.json()),
    )
    comprobar(
        "y el material de esa materia no se lista",
        all(
            m["materiaId"] != ajena
            for m in cliente.get("/api/biblioteca").json().get("materiales", [])
        ),
    )

    # ------------------------------------------------------------------
    grupo("El registro de auditoría también")
    como(SECRETARIA)
    secretaria = d.buscar_persona(SECRETARIA)
    # Con `elemento_id` distinto a propósito: dos eventos iguales a menos de
    # dos segundos se toman por un doble clic y el segundo se descarta.
    uno = auditoria.registrar(
        secretaria,
        "edicion",
        "academico",
        elemento="De la carrera 1",
        elemento_id=1,
        carrera_id=1,
    )
    otro = auditoria.registrar(
        secretaria,
        "edicion",
        "academico",
        elemento="De la otra carrera",
        elemento_id=2,
        carrera_id=otra_carrera,
    )
    comprobar("se anotaron los dos eventos", bool(uno and otro), (uno, otro))

    como(CLAUDIA)
    vistos = {e["id"] for e in cliente.get("/api/auditoria?porPagina=200").json()["eventos"]}
    comprobar("ve el evento de su carrera", uno["id"] in vistos)
    comprobar("y no el de la otra", otro["id"] not in vistos)
    comprobar(
        "ni abriéndolo por su número",
        cliente.get(f"/api/auditoria/{otro['id']}").status_code == 404,
    )
    comprobar(
        "el suyo sí se abre",
        cliente.get(f"/api/auditoria/{uno['id']}").status_code == 200,
    )

    opciones = cliente.get("/api/auditoria/opciones").json()
    comprobar(
        "los filtros ofrecen solo su carrera",
        [c["id"] for c in opciones["carreras"]] == [1],
        opciones["carreras"],
    )
    comprobar("y la pantalla puede decir que está recortado", opciones["ambito"]["todo"] is False)

    # ------------------------------------------------------------------
    grupo("Quién puede ponerlo y qué se acepta")
    como(SECRETARIA)
    comprobar(
        "una carrera que no existe se rechaza",
        fijar(CLAUDIA, [999999]).status_code == 400,
    )
    comprobar(
        "algo que no es una lista también",
        cliente.patch(
            f"/api/usuarios/{CLAUDIA}", json={"ambito": {"carreras": "todas"}}
        ).status_code
        == 400,
    )

    como(MARIA)
    comprobar(
        "un docente no le fija el ámbito a nadie",
        cliente.patch(f"/api/usuarios/{CLAUDIA}", json={"ambito": {"carreras": [1]}}).status_code
        == 403,
    )
    como(SANTIAGO)
    comprobar(
        "un estudiante tampoco",
        cliente.patch(f"/api/usuarios/{CLAUDIA}", json={"ambito": {"carreras": [1]}}).status_code
        == 403,
    )

    # ------------------------------------------------------------------
    grupo("Vaciarlo devuelve todo el campus")
    comprobar("se puede vaciar", fijar(CLAUDIA, []).status_code == 200)
    comprobar(
        "y vuelve a alcanzar todo",
        amb.de(d.buscar_persona(CLAUDIA)) is None,
        d.buscar_persona(CLAUDIA).get("ambito"),
    )
    comprobar("se le ven las dos carreras otra vez", ajena in materias_que_ve(CLAUDIA))

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
