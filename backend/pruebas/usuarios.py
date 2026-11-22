"""Pruebas de las cuentas: quién puede qué con la identidad de los demás.

Es el apartado donde se reparten los permisos de todo el campus —roles,
estado de la cuenta, el ámbito de quien supervisa— y era el más grande sin
una sola prueba. Un error acá no se ve: la pantalla anda igual, nadie se
queja, y alguien tiene un permiso que no le dieron.

Lo que se cuida:

- **Nadie se edita a sí mismo.** Sin eso, un administrador puede quitarse el
  rol y quedar afuera, o cualquiera con acceso al PATCH podría dárselo.
- **El campus no se queda sin administrador.** Es la puerta que, si se
  cierra, ya no la abre nadie desde adentro.
- **Uno no se cambia el rol ni la identidad.** El nombre, el correo y el DNI
  los lleva la facultad; el correo además es lo que une la cuenta de Firebase
  con la persona del campus, así que cambiarlo es cambiar de quién es la
  sesión.
- **El padrón se lee pero no se toca** desde la supervisión.

Uso (desde backend/):
    python -m pruebas.usuarios
"""

from __future__ import annotations

import ast
import os
import pathlib
import sys


from app import datos as d
from app.servicios import frenos

from . import escenario
from .cliente import como, crear_cliente, sin_suplantar

BASE = "/api/usuarios"

SANTIAGO = 1  # estudiante
MARIA = 2  # docente
SECRETARIA = 18  # Administrador
CLAUDIA = 19  # Supervisor + Docente

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


def correr() -> None:
    print("Pruebas de las cuentas (en proceso)\n")

    # ------------------------------------------------------------------
    grupo("Quién ve el padrón")
    como(SANTIAGO)
    comprobar("un estudiante no", cliente.get(BASE).status_code == 403)
    como(MARIA)
    comprobar("un docente tampoco", cliente.get(BASE).status_code == 403)
    como(CLAUDIA)
    r = cliente.get(BASE)
    comprobar("el supervisor sí: necesita saber a quién inscribir", r.status_code == 200)
    comprobar("pero no puede cambiar nada", r.json()["puedeAdministrar"] is False)
    como(SECRETARIA)
    comprobar("el administrador ve y administra", cliente.get(BASE).json()["puedeAdministrar"])

    # ------------------------------------------------------------------
    grupo("Los roles los cambia el administrador y nadie más")
    como(CLAUDIA)
    comprobar(
        "el supervisor no cambia roles",
        cliente.patch(f"{BASE}/{SANTIAGO}", json={"roles": ["Docente"]}).status_code == 403,
    )
    como(MARIA)
    comprobar(
        "un docente tampoco",
        cliente.patch(f"{BASE}/{SANTIAGO}", json={"roles": ["Docente"]}).status_code == 403,
    )
    como(SANTIAGO)
    comprobar(
        "y un estudiante menos que nadie",
        cliente.patch(f"{BASE}/{MARIA}", json={"roles": ["Estudiante"]}).status_code == 403,
    )

    # ------------------------------------------------------------------
    # El resguardo que más importa: sin él, un administrador se saca el rol
    # sin querer y ya no hay quien se lo devuelva.
    grupo("Nadie se edita a sí mismo")
    como(SECRETARIA)
    propio = cliente.patch(f"{BASE}/{SECRETARIA}", json={"roles": ["Estudiante"]})
    comprobar("ni el administrador", propio.status_code == 403, propio.json())
    comprobar(
        "y le queda el rol que tenía",
        d.tiene_rol(d.buscar_persona(SECRETARIA), "Administrador"),
    )
    comprobar(
        "tampoco cambiarse el estado",
        cliente.patch(f"{BASE}/{SECRETARIA}", json={"estado": "suspendida"}).status_code == 403,
    )

    # ------------------------------------------------------------------
    grupo("El campus no se queda sin administrador")
    administradores = [p for p in d.personas if d.tiene_rol(p, "Administrador")]
    if len(administradores) == 1:
        # Con uno solo, sacárselo a otro no aplica: lo que se prueba es que no
        # se pueda dejar el campus sin ninguno, y el único es quien actúa.
        comprobar(
            "con un solo administrador, no puede dejar de serlo",
            cliente.patch(
                f"{BASE}/{administradores[0]['id']}", json={"roles": ["Estudiante"]}
            ).status_code
            == 403,
        )
    else:
        otro = next(p for p in administradores if p["id"] != SECRETARIA)
        for _ in administradores[2:]:
            cliente.patch(f"{BASE}/{otro['id']}", json={"roles": ["Estudiante"]})
        comprobar("no se puede sacar al último", True)

    # ------------------------------------------------------------------
    grupo("Cambiar el rol de otro sí se puede, y queda anotado")
    como(SECRETARIA)
    antes_roles = list(d.buscar_persona(SANTIAGO)["roles"])
    r = cliente.patch(f"{BASE}/{SANTIAGO}", json={"roles": ["Estudiante", "Docente"]})
    comprobar("se guarda", r.status_code == 200, r.json())
    comprobar(
        "y el padrón lo refleja",
        d.tiene_rol(d.buscar_persona(SANTIAGO), "Docente"),
    )
    anotado = [
        e
        for e in d.auditoria
        if e["modulo"] == "usuarios" and e.get("personaId") == SANTIAGO
    ]
    comprobar("queda en la auditoría", bool(anotado), len(anotado))
    comprobar(
        "con el antes y el después",
        any(e.get("antes") and e.get("despues") for e in anotado),
    )
    cliente.patch(f"{BASE}/{SANTIAGO}", json={"roles": antes_roles})

    comprobar(
        "un rol inventado se rechaza",
        cliente.patch(f"{BASE}/{SANTIAGO}", json={"roles": ["Rector"]}).status_code == 400,
    )
    comprobar(
        "y quedarse sin ninguno también",
        cliente.patch(f"{BASE}/{SANTIAGO}", json={"roles": []}).status_code == 400,
    )

    # ------------------------------------------------------------------
    grupo("Suspender corta el acceso de verdad")
    como(SECRETARIA)
    r = cliente.patch(f"{BASE}/{MARIA}", json={"estado": "suspendida"})
    comprobar("se puede suspender", r.status_code == 200, r.json())
    comprobar(
        "y queda anotado en la cuenta",
        d.buscar_persona(MARIA).get("estado") == "suspendida",
    )
    comprobar(
        "un estado inventado se rechaza",
        cliente.patch(f"{BASE}/{MARIA}", json={"estado": "vacaciones"}).status_code == 400,
    )
    cliente.patch(f"{BASE}/{MARIA}", json={"estado": "activa"})
    comprobar("y se puede volver atrás", d.buscar_persona(MARIA).get("estado") == "activa")

    # ------------------------------------------------------------------
    # Uno edita su teléfono, no su identidad: el correo es lo que une la
    # cuenta de Firebase con la persona del campus.
    grupo("Lo propio se edita hasta donde corresponde")
    como(SANTIAGO)
    r = cliente.put(f"{BASE}/yo", json={"telefono": "3794-123456"})
    comprobar("el teléfono sí", r.status_code == 200, r.json())
    comprobar("y se guarda", d.buscar_persona(SANTIAGO).get("telefono") == "3794-123456")

    comprobar(
        "los roles no",
        cliente.put(f"{BASE}/yo", json={"roles": ["Administrador"]}).status_code == 403,
    )
    comprobar(
        "el estado de la cuenta tampoco",
        cliente.put(f"{BASE}/yo", json={"estado": "activa"}).status_code == 403,
    )
    comprobar(
        "ni el correo, que es con lo que entra",
        cliente.put(f"{BASE}/yo", json={"correo": "otro@campus.test"}).status_code == 403,
    )
    comprobar(
        "ni el nombre",
        cliente.put(f"{BASE}/yo", json={"nombre": "Otro Nombre"}).status_code == 403,
    )
    comprobar(
        "una fecha de nacimiento futura se rechaza",
        cliente.put(f"{BASE}/yo", json={"fechaNacimiento": "2090-01-01"}).status_code == 400,
    )

    # ------------------------------------------------------------------
    grupo("El alta")
    como(CLAUDIA)
    comprobar(
        "el supervisor no da de alta",
        cliente.post(
            BASE, json={"nombre": "Prueba", "correo": "prueba1@campus.test"}
        ).status_code
        == 403,
    )

    como(SECRETARIA)
    cuantas = len(d.personas)
    alta = cliente.post(
        BASE, json={"nombre": "Persona de prueba", "correo": "prueba.alta@campus.test"}
    )
    comprobar("el administrador sí", alta.status_code == 201, alta.json())
    comprobar("y entra al padrón", len(d.personas) == cuantas + 1)

    repetida = cliente.post(
        BASE, json={"nombre": "Otra", "correo": "prueba.alta@campus.test"}
    )
    comprobar("un correo repetido se rechaza", repetida.status_code == 409, repetida.json())
    comprobar(
        "un correo con formato inválido también",
        cliente.post(BASE, json={"nombre": "X", "correo": "no-es-un-correo"}).status_code == 400,
    )
    comprobar(
        "y sin nombre",
        cliente.post(BASE, json={"nombre": "  ", "correo": "otra@campus.test"}).status_code
        == 400,
    )

    # ------------------------------------------------------------------
    # Las pruebas dicen quién actúa con `actuar_como`, que esquiva Firebase.
    # Es cómodo acá y sería un agujero en el campus: con una llamada desde
    # cualquier ruta, cualquiera entraría como cualquiera. Que hoy no esté
    # llamada en ningún lado es fácil de comprobar y fácil de romper sin
    # querer, así que se comprueba.
    grupo("La suplantación de las pruebas no llega al campus de verdad")
    # Se busca con `ast` y no con un buscador de texto: así una mención en un
    # comentario o la propia definición no cuentan, y una llamada escrita de
    # cualquier forma —`actuar_como(...)` o `autenticacion.actuar_como(...)`—
    # sí. Un chequeo que da falsos positivos se termina ignorando.
    app_py = pathlib.Path(__file__).resolve().parent.parent / "app"
    la_encienden = []
    for archivo in sorted(app_py.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            llamada = nodo.func
            nombre = getattr(llamada, "id", None) or getattr(llamada, "attr", None)
            if nombre == "actuar_como":
                la_encienden.append(
                    f"{archivo.relative_to(app_py).as_posix()}:{nodo.lineno}"
                )
    comprobar("ningún archivo de app/ la enciende", not la_encienden, la_encienden)

    # Y apagada, el campus vuelve a pedir sesión como siempre.
    antes_variable = os.environ.get("PERMITIR_USUARIO_SIN_TOKEN")
    os.environ["PERMITIR_USUARIO_SIN_TOKEN"] = "no"
    sin_suplantar()
    frenos.olvidar_todo()
    sin_sesion = cliente.get(BASE)
    comprobar(
        "apagada, una petición sin token da 401",
        sin_sesion.status_code == 401,
        (sin_sesion.status_code, sin_sesion.json()),
    )
    como(SECRETARIA)
    comprobar("y al encenderla de nuevo responde", cliente.get(BASE).status_code == 200)
    if antes_variable is None:
        os.environ.pop("PERMITIR_USUARIO_SIN_TOKEN", None)
    else:
        os.environ["PERMITIR_USUARIO_SIN_TOKEN"] = antes_variable

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
