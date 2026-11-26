"""Pruebas del registro de auditoría.

Corren **en proceso**, como las de Finales y las de la Biblioteca: lo que hay
que comprobar es quién puede ver el registro y qué queda anotado cuando actúa
cada uno, y sin login el servidor en marcha sería siempre la misma persona.

Lo que más importa de todo esto no es que el registro se escriba, sino que
**no se pueda alterar**: que no haya forma de borrar un evento ni de maquillar
el propio historial. Eso se prueba al final.

Uso (desde backend/):
    python -m pruebas.auditoria
"""

from __future__ import annotations

import sys


from app import datos as d

from . import escenario
from .cliente import como, crear_cliente
from app.servicios import auditoria as a

BASE = "/api/auditoria"

SANTIAGO = 1  # estudiante
MARIA = 2  # docente: dicta Programación II
LUCIA = 4  # estudiante
SECRETARIA = 18  # Administrador
CLAUDIA = 19  # Supervisor + Docente

PROG2 = 109

pasadas = 0
fallas: list[str] = []

# El campus arranca vacío, así que las pruebas cargan el suyo. Ver
# `escenario.py`: no toca ningún archivo, solo la memoria de este proceso.
escenario.cargar()

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


def correr() -> None:
    print("Pruebas del registro de auditoría (en proceso)\n")

    # ------------------------------------------------------------------
    grupo("Se anota solo, sin que el módulo haga nada especial")
    como(SECRETARIA)
    antes = len(d.auditoria)

    r = cliente.post(
        "/api/institucion/carreras", json={"nombre": "Carrera de prueba", "codigo": "CP"}
    )
    comprobar("crear una carrera responde 201", r.status_code == 201, r.json())
    comprobar("y queda anotado", len(d.auditoria) == antes + 1, len(d.auditoria))

    ultimo = d.auditoria[-1]
    comprobar("con quién fue", ultimo["quienId"] == SECRETARIA, ultimo["quienId"])
    comprobar("con qué rol tenía", ultimo["rol"] == "Administrador", ultimo["rol"])
    comprobar("con la acción", ultimo["accion"] == "creacion", ultimo["accion"])
    comprobar("con el módulo", ultimo["modulo"] == "academico", ultimo["modulo"])
    comprobar("y con el elemento", ultimo["elemento"] == "Carrera de prueba", ultimo["elemento"])

    # ------------------------------------------------------------------
    grupo("Al modificar queda el valor anterior y el nuevo")
    r = cliente.patch(f"/api/usuarios/{LUCIA}", json={"roles": ["Estudiante", "Docente"]})
    comprobar("cambiar roles responde 200", r.status_code == 200, r.json())

    cambio = d.auditoria[-1]
    comprobar("la acción es «roles»", cambio["accion"] == "roles", cambio["accion"])
    comprobar("guarda lo que había", cambio["antes"] == {"roles": ["Estudiante"]}, cambio["antes"])
    comprobar(
        "y lo que quedó",
        cambio["despues"] == {"roles": ["Estudiante", "Docente"]},
        cambio["despues"],
    )
    comprobar("y a quién afecta", cambio["personaId"] == LUCIA, cambio["personaId"])

    # Dejar a Lucía como estaba, para no ensuciar el resto de las pruebas
    cliente.patch(f"/api/usuarios/{LUCIA}", json={"roles": ["Estudiante"]})

    # ------------------------------------------------------------------
    grupo("El administrador también queda registrado")
    mios = [e for e in d.auditoria if e["quienId"] == SECRETARIA]
    comprobar("sus acciones están en el registro", len(mios) >= 3, len(mios))
    comprobar(
        "ninguna se anotó como de otro",
        all(e["rol"] == "Administrador" for e in mios),
        {e["rol"] for e in mios},
    )

    # ------------------------------------------------------------------
    grupo("No se guardan secretos")
    a.registrar(
        SECRETARIA,
        "edicion",
        "usuarios",
        elemento="Prueba",
        despues={"contrasena": "hola1234", "token": "abc", "nombre": "Ana"},
    )
    guardado = d.auditoria[-1]["despues"]
    comprobar("la contraseña no queda", guardado["contrasena"] == "(oculto)", guardado)
    comprobar("el token tampoco", guardado["token"] == "(oculto)", guardado)
    comprobar("lo que no es secreto sí", guardado["nombre"] == "Ana", guardado)

    # ------------------------------------------------------------------
    grupo("El mismo evento dos veces no se cuenta dos veces")
    cuantos = len(d.auditoria)
    for _ in range(3):
        a.registrar(
            SECRETARIA,
            "edicion",
            "academico",
            elemento="Doble clic",
            elemento_id=9999,
            elemento_tipo="prueba",
        )
    comprobar("tres clics seguidos dejan un solo evento", len(d.auditoria) == cuantos + 1,
              len(d.auditoria) - cuantos)

    # ------------------------------------------------------------------
    grupo("Quién puede ver el registro")
    como(SANTIAGO)
    comprobar("un estudiante recibe 403", cliente.get(BASE).status_code == 403)
    comprobar("y en las opciones también", cliente.get(f"{BASE}/opciones").status_code == 403)
    comprobar(
        "y no puede exportarlo", cliente.get(f"{BASE}/exportar").status_code == 403
    )

    como(MARIA)
    comprobar("un docente no entra al registro general", cliente.get(BASE).status_code == 403)
    r = cliente.get(f"{BASE}/mis-materias")
    comprobar("pero sí a lo de sus materias", r.status_code == 200, r.status_code)
    comprobar(
        "y ahí solo hay materias suyas",
        all(m["id"] in {x["id"] for x in d.materias_que_dicta(MARIA)} for m in r.json()["materias"]),
        r.json()["materias"],
    )

    como(CLAUDIA)
    r = cliente.get(BASE)
    comprobar("el supervisor entra", r.status_code == 200, r.status_code)
    comprobar(
        "pero no ve lo de usuarios y permisos",
        all(e["modulo"] != "usuarios" for e in r.json()["eventos"]),
        {e["modulo"] for e in r.json()["eventos"]},
    )

    como(SECRETARIA)
    r = cliente.get(BASE)
    comprobar("el administrador ve todo", r.status_code == 200, r.status_code)
    comprobar(
        "incluido lo de usuarios",
        any(e["modulo"] == "usuarios" for e in r.json()["eventos"]),
    )

    # ------------------------------------------------------------------
    grupo("Los filtros")
    r = cliente.get(BASE, params={"modulo": "usuarios"})
    comprobar(
        "por módulo",
        all(e["modulo"] == "usuarios" for e in r.json()["eventos"]) and r.json()["total"] > 0,
        r.json()["total"],
    )

    r = cliente.get(BASE, params={"accion": "creacion"})
    comprobar(
        "por acción",
        all(e["accion"] == "creacion" for e in r.json()["eventos"]) and r.json()["total"] > 0,
    )

    r = cliente.get(BASE, params={"usuarioId": SECRETARIA})
    comprobar(
        "por usuario",
        all(e["quienId"] == SECRETARIA for e in r.json()["eventos"]) and r.json()["total"] > 0,
    )

    r = cliente.get(BASE, params={"q": "carrera de prueba"})
    comprobar("por palabra, sin que importen las mayúsculas", r.json()["total"] >= 1,
              r.json()["total"])

    r = cliente.get(BASE, params={"desde": "2099-01-01"})
    comprobar("por fecha desde", r.json()["total"] == 0, r.json()["total"])

    r = cliente.get(BASE, params={"modulo": "usuarios", "accion": "creacion"})
    combinado = r.json()
    comprobar(
        "y se combinan",
        all(e["modulo"] == "usuarios" and e["accion"] == "creacion" for e in combinado["eventos"]),
    )

    # ------------------------------------------------------------------
    grupo("El resumen y la paginación")
    r = cliente.get(BASE, params={"porPagina": 2})
    comprobar("una página trae lo pedido", len(r.json()["eventos"]) <= 2, len(r.json()["eventos"]))
    comprobar("y dice cuántas hay", r.json()["paginas"] >= 2, r.json()["paginas"])
    comprobar(
        "el resumen cuenta todo lo filtrado, no la página",
        r.json()["resumen"]["total"] == r.json()["total"] > 2,
        (r.json()["resumen"]["total"], r.json()["total"]),
    )

    # ------------------------------------------------------------------
    grupo("El detalle")
    evento = d.auditoria[0]
    r = cliente.get(f"{BASE}/{evento['id']}")
    comprobar("se abre un movimiento", r.status_code == 200, r.status_code)
    comprobar("con los nombres resueltos", "nombreAccion" in r.json() and "nombreModulo" in r.json())

    como(CLAUDIA)
    de_usuarios = next(e for e in d.auditoria if e["modulo"] == "usuarios")
    r = cliente.get(f"{BASE}/{de_usuarios['id']}")
    comprobar("uno fuera de alcance responde 404, no 403", r.status_code == 404, r.status_code)

    # ------------------------------------------------------------------
    grupo("Exportar")
    como(SECRETARIA)
    r = cliente.get(f"{BASE}/exportar", params={"formato": "csv"})
    comprobar("el CSV responde 200", r.status_code == 200, r.status_code)
    comprobar("empieza con el BOM, para Excel", r.text.startswith("﻿"), r.text[:5])
    comprobar("y trae los títulos", "Valor anterior;Valor nuevo" in r.text)

    r = cliente.get(f"{BASE}/exportar", params={"formato": "xlsx"})
    comprobar("el XLSX responde 200", r.status_code == 200, r.status_code)
    comprobar("y es un ZIP, como todo .xlsx", r.content[:2] == b"PK", r.content[:4])

    comprobar(
        "exportar también queda registrado",
        d.auditoria[-1]["accion"] == "descarga",
        d.auditoria[-1]["accion"],
    )

    # ------------------------------------------------------------------
    grupo("El registro no se puede alterar")
    alguno = d.auditoria[0]["id"]
    for metodo in ("delete", "put", "patch", "post"):
        # `delete` no lleva cuerpo; los otros sí
        llamar = getattr(cliente, metodo)
        r = llamar(f"{BASE}/{alguno}") if metodo == "delete" else llamar(
            f"{BASE}/{alguno}", json={}
        )
        comprobar(
            f"{metodo.upper()} sobre un evento no existe",
            r.status_code in (404, 405),
            r.status_code,
        )

    r = cliente.post(BASE, json={"accion": "creacion", "modulo": "usuarios"})
    comprobar("no se puede escribir un evento a mano", r.status_code == 405, r.status_code)

    # Nadie puede maquillar su propio historial: el único camino para anotar es
    # `registrar`, que siempre pone a quien actúa, y no hay ninguno para sacar.
    comprobar(
        "no hay forma de borrar un evento desde la aplicación",
        not any(
            hasattr(a, nombre) for nombre in ("borrar", "eliminar", "limpiar", "editar")
        ),
        [n for n in dir(a) if not n.startswith("_")],
    )

    # Limpieza: la carrera de prueba se busca por nombre, porque el alta
    # devuelve el catálogo entero y no la carrera suelta.
    creada = next(
        (c for c in d.carreras_institucion if c["nombre"] == "Carrera de prueba"), None
    )
    if creada:
        cliente.delete(f"/api/institucion/carreras/{creada['id']}")


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
