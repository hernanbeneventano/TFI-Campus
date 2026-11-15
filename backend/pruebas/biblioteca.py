"""Pruebas de la Biblioteca.

Corren **dentro del proceso**, con el cliente de pruebas de FastAPI, por el
mismo motivo que las de Finales: lo que hay que comprobar es quién ve qué, y
para eso hay que poder ser el docente de una materia, el de otra, un alumno
inscripto, uno que no y el supervisor. Contra el servidor en marcha, sin
login, todos serían la misma persona.

Recorren el camino completo igual —la ruta, los permisos, la validación y la
respuesta— y modifican los datos en memoria de este proceso, no los del
servidor.

El reparto sale de los datos de prueba:

    Santiago (1)  estudiante, cursa Programación II (109) y Bases de Datos (110)
    Hernán (3)    estudiante, NO cursa ninguna de esas dos
    María (2)     dicta Programación II (109)
    Pablo (7)     dicta Bases de Datos (110)
    Secretaría (18)  administradora: ve todo

Uso (desde backend/):
    python -m pruebas.biblioteca
"""

from __future__ import annotations

import base64
import sys

from fastapi.testclient import TestClient

from app import datos as d
from app.main import app
from app.servicios.autenticacion import identificar

BASE = "/api/biblioteca"

# Personas
SANTIAGO = 1
MARIA = 2
HERNAN = 3
PABLO = 7
SECRETARIA = 18

# Materias del plan
PROG2 = 109  # la dicta María, la cursa Santiago
BASES = 110  # la dicta Pablo, la cursa Santiago
DISCRETA = 116  # la cursa Hernán, no Santiago

pasadas = 0
fallas: list[str] = []

_quien = {"id": SANTIAGO}
app.dependency_overrides[identificar] = lambda: d.buscar_persona(_quien["id"])
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


def ficha(materia_id: int, titulo: str, **extra) -> dict:
    return {
        "titulo": titulo,
        "autor": "Autor de prueba",
        "materiaId": materia_id,
        "tipo": "apunte",
        "categoria": "otros",
        "enlace": "https://example.org/material",
        "autorizado": True,
        **extra,
    }


def error_de(r) -> str:
    try:
        return r.json().get("error", "")
    except ValueError:
        return ""


PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


def en_base64(datos: bytes) -> str:
    return base64.b64encode(datos).decode()


def correr() -> None:
    print("Pruebas de la Biblioteca (en proceso)\n")

    # ------------------------------------------------------------------
    grupo("La biblioteca arranca vacía")
    como(SECRETARIA)
    r = cliente.get(f"{BASE}/opciones")
    comprobar("no hay ningún material cargado", r.json()["total"] == 0, r.json()["total"])

    # ------------------------------------------------------------------
    grupo("Cada uno ve las materias que le tocan")
    como(SANTIAGO)
    mias = {m["id"] for m in cliente.get(f"{BASE}/opciones").json()["materias"]}
    comprobar("el estudiante ve las que cursa", PROG2 in mias and BASES in mias, sorted(mias))
    comprobar("y no las que no cursa", DISCRETA not in mias, sorted(mias))

    como(MARIA)
    suyas = {m["id"] for m in cliente.get(f"{BASE}/opciones").json()["materias"]}
    comprobar("la docente ve la que dicta", PROG2 in suyas, sorted(suyas))
    comprobar("y no la de otra cátedra", BASES not in suyas, sorted(suyas))

    como(SECRETARIA)
    todas = cliente.get(f"{BASE}/opciones").json()["materias"]
    comprobar(
        "quien administra las ve todas", len(todas) == len(d.materias_plan), len(todas)
    )

    # ------------------------------------------------------------------
    grupo("La materia es obligatoria y tiene que ser una de las suyas")
    como(MARIA)
    r = cliente.post(BASE, json={"titulo": "Sin materia", "autorizado": True})
    comprobar("sin materia responde 400", r.status_code == 400, error_de(r))

    r = cliente.post(BASE, json=ficha(BASES, "En cátedra ajena"))
    comprobar("en una materia que no dicta responde 400", r.status_code == 400, error_de(r))

    r = cliente.post(BASE, json=ficha(PROG2, "Sin confirmar", autorizado=False))
    comprobar("sin confirmar la autorización responde 400", r.status_code == 400, error_de(r))

    r = cliente.post(BASE, json=ficha(PROG2, "Mal enlace", enlace="javascript:alert(1)"))
    comprobar("un enlace que no es http responde 400", r.status_code == 400, error_de(r))

    # ------------------------------------------------------------------
    grupo("El docente publica directo en su materia")
    r = cliente.post(BASE, json=ficha(PROG2, "Apunte de punteros"))
    comprobar("se crea y responde 201", r.status_code == 201, r.json())
    del_docente = r.json()
    comprobar("queda aprobado sin revisión", del_docente["estado"] == "aprobado", del_docente["estado"])
    comprobar("queda registrado quién lo autorizó", del_docente["autorizadoPorNombre"] is not None)

    r = cliente.post(BASE, json=ficha(PROG2, "Apunte de punteros"))
    comprobar("el mismo libro dos veces responde 409", r.status_code == 409, error_de(r))

    # ------------------------------------------------------------------
    grupo("Solo lo ve quien cursa esa materia")
    como(SANTIAGO)
    ids = [m["id"] for m in cliente.get(BASE).json()["materiales"]]
    comprobar("el alumno que la cursa lo ve", del_docente["id"] in ids, ids)

    como(HERNAN)
    ids = [m["id"] for m in cliente.get(BASE).json()["materiales"]]
    comprobar("el que no la cursa no lo ve en el listado", del_docente["id"] not in ids, ids)

    r = cliente.get(f"{BASE}/{del_docente['id']}")
    comprobar("y la ficha le responde 404, no 403", r.status_code == 404, r.status_code)

    como(PABLO)
    r = cliente.get(f"{BASE}/{del_docente['id']}")
    comprobar("el docente de otra cátedra tampoco lo ve", r.status_code == 404, r.status_code)

    # ------------------------------------------------------------------
    grupo("El archivo pasa por el mismo control")
    como(MARIA)
    r = cliente.post(
        f"{BASE}/{del_docente['id']}/archivo",
        json={"contenido": en_base64(b"MZ\x90esto es un ejecutable"), "extension": "pdf"},
    )
    comprobar("un .pdf que no es un PDF responde 415", r.status_code == 415, error_de(r))

    r = cliente.post(
        f"{BASE}/{del_docente['id']}/archivo",
        json={"contenido": en_base64(b""), "extension": "pdf"},
    )
    comprobar("un archivo vacío responde 400", r.status_code == 400, error_de(r))

    r = cliente.post(
        f"{BASE}/{del_docente['id']}/archivo",
        json={"contenido": en_base64(b"<html>hola</html>"), "extension": "html"},
    )
    comprobar("un documento HTML responde 415", r.status_code == 415, error_de(r))

    r = cliente.post(
        f"{BASE}/{del_docente['id']}/archivo",
        json={"contenido": en_base64(PDF), "extension": "pdf", "nombre": "../../etc/passwd.pdf"},
    )
    comprobar("un PDF válido responde 201", r.status_code == 201, error_de(r))
    comprobar(
        "el nombre se limpia", r.json()["archivo"]["nombre"] == "passwd.pdf", r.json()["archivo"]
    )

    como(SANTIAGO)
    r = cliente.get(f"{BASE}/{del_docente['id']}/archivo")
    comprobar("quien cursa lo descarga", r.status_code == 200 and r.content == PDF, r.status_code)

    como(HERNAN)
    r = cliente.get(f"{BASE}/{del_docente['id']}/archivo")
    comprobar("quien no cursa no lo descarga", r.status_code == 404, r.status_code)

    # ------------------------------------------------------------------
    grupo("El aporte de un estudiante espera revisión")
    como(SANTIAGO)
    r = cliente.post(BASE, json=ficha(PROG2, "Resumen de la unidad 3"))
    comprobar("se envía y responde 201", r.status_code == 201, r.json())
    aporte = r.json()
    comprobar("queda pendiente", aporte["estado"] == "pendiente", aporte["estado"])

    ids = [m["id"] for m in cliente.get(BASE).json()["materiales"]]
    comprobar("un pendiente no sale en la biblioteca", aporte["id"] not in ids, ids)

    mios = [m["id"] for m in cliente.get(f"{BASE}/mis-aportes").json()["materiales"]]
    comprobar("pero sí en sus aportes", aporte["id"] in mios, mios)

    r = cliente.get(f"{BASE}/pendientes")
    comprobar("un estudiante no abre la cola de revisión", r.status_code == 403, r.status_code)

    # ------------------------------------------------------------------
    grupo("Lo revisa el docente de esa materia, no cualquiera")
    como(PABLO)
    cola = [m["id"] for m in cliente.get(f"{BASE}/pendientes").json()["materiales"]]
    comprobar("el de otra cátedra no lo tiene en su cola", aporte["id"] not in cola, cola)

    r = cliente.post(f"{BASE}/{aporte['id']}/aprobar")
    comprobar("y aprobarlo le responde 404", r.status_code == 404, r.status_code)

    como(MARIA)
    cola = cliente.get(f"{BASE}/pendientes").json()["materiales"]
    comprobar("la docente de la materia sí lo tiene", any(m["id"] == aporte["id"] for m in cola))
    suyo = next(m for m in cola if m["id"] == aporte["id"])
    comprobar(
        "con todo lo que hace falta para decidir",
        all(suyo.get(c) for c in ("titulo", "autor", "materia", "subidoPorNombre", "creado"))
        and suyo["estado"] == "pendiente",
        suyo,
    )

    r = cliente.post(f"{BASE}/{aporte['id']}/rechazar", json={})
    comprobar("rechazar sin motivo responde 400", r.status_code == 400, error_de(r))

    antes = sum(len(c["mensajes"]) for c in d.conversaciones)
    r = cliente.post(f"{BASE}/{aporte['id']}/aprobar")
    comprobar("aprobar responde 200", r.status_code == 200, error_de(r))
    comprobar("queda aprobado", r.json()["estado"] == "aprobado", r.json()["estado"])
    despues = sum(len(c["mensajes"]) for c in d.conversaciones)
    comprobar("y le llega el aviso a quien aportó", despues == antes + 1, (antes, despues))

    como(SANTIAGO)
    ids = [m["id"] for m in cliente.get(BASE).json()["materiales"]]
    comprobar("ya aparece en la biblioteca de la materia", aporte["id"] in ids, ids)

    # ------------------------------------------------------------------
    grupo("El rechazo le dice al estudiante qué pasó")
    r = cliente.post(BASE, json=ficha(PROG2, "Libro sin permiso"))
    otro = r.json()

    como(MARIA)
    r = cliente.post(
        f"{BASE}/{otro['id']}/rechazar", json={"motivo": "No corresponde a la materia"}
    )
    comprobar("se rechaza con motivo", r.status_code == 200, error_de(r))

    como(SANTIAGO)
    mio = next(
        m for m in cliente.get(f"{BASE}/mis-aportes").json()["materiales"] if m["id"] == otro["id"]
    )
    comprobar("el estudiante ve el estado", mio["estado"] == "rechazado", mio["estado"])
    comprobar("y el motivo", mio["motivo"] == "No corresponde a la materia", mio["motivo"])
    comprobar("con el historial de quién lo revisó", len(mio["historial"]) >= 1, mio["historial"])

    ids = [m["id"] for m in cliente.get(BASE).json()["materiales"]]
    comprobar("un rechazado no se publica", otro["id"] not in ids, ids)

    # ------------------------------------------------------------------
    grupo("Editar lo aprobado lo manda de nuevo a la cola")
    r = cliente.patch(f"{BASE}/{aporte['id']}", json={"titulo": "Resumen corregido"})
    comprobar("el autor puede editarlo", r.status_code == 200, error_de(r))
    comprobar("y vuelve a pendiente", r.json()["estado"] == "pendiente", r.json()["estado"])

    r = cliente.patch(f"{BASE}/{del_docente['id']}", json={"titulo": "No es mío"})
    comprobar("no puede editar el de la cátedra", r.status_code == 403, r.status_code)

    r = cliente.delete(f"{BASE}/{del_docente['id']}")
    comprobar("ni retirarlo", r.status_code == 403, r.status_code)

    # ------------------------------------------------------------------
    grupo("Favoritos")
    r = cliente.post(f"{BASE}/{aporte['id']}/favorito")
    comprobar("se guarda el propio", r.status_code == 201, r.json())

    guardados = [m["id"] for m in cliente.get(f"{BASE}/favoritos").json()["materiales"]]
    comprobar("aparece en guardados", aporte["id"] in guardados, guardados)

    como(HERNAN)
    r = cliente.post(f"{BASE}/{del_docente['id']}/favorito")
    comprobar("no se guarda el de una materia ajena", r.status_code == 404, r.status_code)

    # ------------------------------------------------------------------
    grupo("Quien supervisa ve y revisa todo")
    como(SECRETARIA)
    r = cliente.get(f"{BASE}/pendientes")
    comprobar("abre la cola de revisión", r.status_code == 200, r.status_code)
    comprobar(
        "con el aporte reeditado adentro",
        any(m["id"] == aporte["id"] for m in r.json()["materiales"]),
        [m["id"] for m in r.json()["materiales"]],
    )

    r = cliente.delete(f"{BASE}/{del_docente['id']}")
    comprobar("y puede retirar material", r.status_code == 200, error_de(r))


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
