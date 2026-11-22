"""Pruebas del legajo: el número con el que la facultad identifica a alguien.

Lo que más importa acá es **que la vista previa diga la verdad**. El
formulario de inscripción muestra el legajo que le va a tocar al estudiante
antes de guardarlo; si ese número y el que después escribe el servidor se
separan, la pantalla queda mintiendo y nadie se entera hasta que alguien
busca por legajo y no encuentra a la persona.

Lo demás que se cuida es que la numeración sea **por carrera** y que un
número **no se reutilice**: un legajo repetido apunta a dos expedientes
distintos, que es lo contrario de identificar.

Corre en proceso, como las demás (no hace falta el servidor levantado).

Uso (desde backend/):
    python -m pruebas.legajos
"""

from __future__ import annotations

import sys


from app import datos as d
from app.servicios import legajos

from . import escenario
from .cliente import como, crear_cliente

BASE = "/api/institucion"

SANTIAGO = 1  # estudiante
MARIA = 2  # docente
CLAUDIA = 19  # Supervisor

pasadas = 0
fallas: list[str] = []

escenario.cargar()

cliente = crear_cliente()
como(CLAUDIA)


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


def previo(carrera_id: int):
    return cliente.get(f"{BASE}/legajo-siguiente?carreraId={carrera_id}")


def sin_inscribir(carrera_id: int) -> dict:
    """Un estudiante que todavía no está en esa carrera.

    Si el escenario se quedó sin ninguno, se agrega uno: lo que se prueba acá
    es la numeración, y quedarse sin gente para inscribir no es un resultado
    de la prueba sino un límite del juego de datos.
    """
    libre = next(
        (
            p
            for p in d.personas
            if d.tiene_rol(p, "Estudiante")
            and not any(
                a["personaId"] == p["id"] and a["carreraId"] == carrera_id
                for a in d.asociaciones_academicas
            )
        ),
        None,
    )
    if libre:
        return libre

    nuevo = {
        "id": max(p["id"] for p in d.personas) + 1,
        "nombre": f"Estudiante de prueba {len(d.personas)}",
        "correo": f"prueba{len(d.personas)}@campus.test",
        "roles": ["Estudiante"],
        "estado": "activa",
        "accesoHaceMin": 1,
    }
    d.personas.append(nuevo)
    return nuevo


def inscribir(persona_id: int, carrera_id: int, legajo=None):
    plan = next(p for p in d.planes_estudio if p["carreraId"] == carrera_id)
    return cliente.post(
        f"{BASE}/asignaciones",
        json={
            "personaId": persona_id,
            "carreraId": carrera_id,
            "sedeId": d.sedes[0]["id"],
            "planId": plan["id"],
            "legajo": legajo,
        },
    )


def correr() -> None:
    print("Pruebas de los legajos (en proceso)\n")

    carrera = d.carreras_institucion[0]
    otra = next(
        (c for c in d.carreras_institucion[1:] if any(
            p["carreraId"] == c["id"] for p in d.planes_estudio
        )),
        None,
    )

    # ------------------------------------------------------------------
    grupo("Quién puede verlo antes de inscribir")
    como(SANTIAGO)
    comprobar("un estudiante no", previo(carrera["id"]).status_code == 403)
    como(MARIA)
    comprobar("un docente tampoco", previo(carrera["id"]).status_code == 403)

    como(CLAUDIA)
    r = previo(carrera["id"])
    comprobar("el supervisor sí", r.status_code == 200, r.status_code)
    comprobar("y viene con la carrera y el año", {"legajo", "carrera", "anio"} <= set(r.json()))
    comprobar(
        "una carrera que no existe se rechaza",
        previo(999999).status_code == 400,
        previo(999999).status_code,
    )

    # ------------------------------------------------------------------
    # Esto es lo que vale: la pantalla muestra un número antes de guardar y
    # el servidor arma el suyo al guardar. Si se separan, la pantalla miente.
    grupo("Lo que se muestra es lo que se guarda")
    anunciado = previo(carrera["id"]).json()["legajo"]
    alta = inscribir(sin_inscribir(carrera["id"])["id"], carrera["id"])
    comprobar("se inscribe", alta.status_code == 201, alta.json())
    asignado = alta.json()["asociacion"]["legajo"] if alta.status_code == 201 else None
    comprobar("el legajo es el que se había anunciado", asignado == anunciado,
              f"{asignado} != {anunciado}")

    siguiente = previo(carrera["id"]).json()["legajo"]
    comprobar("y el próximo ya es otro", siguiente != anunciado, siguiente)

    # ------------------------------------------------------------------
    grupo("La numeración es de la carrera, no del campus")
    comprobar(
        "el prefijo sale del código de la carrera",
        asignado.startswith((carrera.get("codigo") or "").upper()),
        asignado,
    )
    comprobar("y el año va adentro", str(d.ahora().year) in asignado, asignado)

    if otra:
        otro_previo = previo(otra["id"]).json()["legajo"]
        comprobar(
            "otra carrera numera por su cuenta",
            otro_previo.endswith("0001") and not otro_previo.startswith(asignado.split("-")[0]),
            otro_previo,
        )

    # ------------------------------------------------------------------
    # Dar de baja **no borra la inscripción**: la suspende. Por eso el número
    # sigue contado y nunca se vuelve a entregar; un legajo reutilizado
    # apuntaría a dos expedientes distintos.
    grupo("Un número no se reutiliza")
    segunda = inscribir(sin_inscribir(carrera["id"])["id"], carrera["id"])
    numero_segundo = segunda.json()["asociacion"]["legajo"]
    id_segunda = segunda.json()["asociacion"]["id"]

    baja = cliente.delete(f"{BASE}/asignaciones/{id_segunda}")
    comprobar("se da de baja", baja.status_code == 200, baja.json())
    comprobar(
        "la inscripción queda suspendida, no borrada",
        any(a["id"] == id_segunda for a in d.asociaciones_academicas),
    )
    comprobar(
        "y su legajo no vuelve a salir",
        previo(carrera["id"]).json()["legajo"] != numero_segundo,
        numero_segundo,
    )

    # ------------------------------------------------------------------
    grupo("El que viene de un sistema anterior se escribe a mano")
    a_mano = inscribir(sin_inscribir(carrera["id"])["id"], carrera["id"], "VIEJO-123")
    comprobar(
        "se respeta tal cual",
        a_mano.status_code == 201 and a_mano.json()["asociacion"]["legajo"] == "VIEJO-123",
        a_mano.json(),
    )

    # ------------------------------------------------------------------
    # Es lo que corre en el arranque del servidor, por eso se lo llama igual
    # que `main.py`: acá los datos se cargan después de arrancar.
    grupo("Los docentes llevan legajo del campus")
    docente = d.buscar_persona(MARIA)
    docente.pop("legajo", None)
    puesto = legajos.asegurar_institucional(docente)
    comprobar("se les pone uno", bool(puesto), puesto)
    comprobar(
        "con el prefijo del personal",
        str(puesto or "").startswith(legajos.PREFIJO_PERSONAL),
        puesto,
    )
    comprobar(
        "y dos docentes no comparten número",
        legajos.proximo_institucional(d.ahora().year) != puesto,
    )
    estudiante = d.buscar_persona(SANTIAGO)
    estudiante.pop("legajo", None)
    comprobar(
        "un estudiante no lleva además uno del campus",
        legajos.asegurar_institucional(estudiante) is None,
        estudiante.get("legajo"),
    )

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
