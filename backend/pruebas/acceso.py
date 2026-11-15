"""Pruebas del ingreso al campus y de los cuatro roles.

Lo que se comprueba acá es quién entra y qué puede hacer: la verificación del
token, el estado de la cuenta y el límite de cada rol. Es lo único que, si
falla, deja el campus abierto.

A diferencia del resto, estas pruebas **no reemplazan `identificar`**: es
justamente la función que hay que probar. Lo que se reemplaza es la
verificación del token contra Firebase, que es la parte que no se puede hacer
sin red ni cuentas de verdad: un token de prueba es acá el correo de alguien,
y la función sigue haciendo todo lo demás —buscar a la persona, mirar el
estado de su cuenta, anotar el ingreso— tal como en producción.

Uso (desde backend/):
    python -m pruebas.acceso
"""

from __future__ import annotations

import os
import sys

from fastapi.testclient import TestClient
from firebase_admin import auth

from app import datos as d
from app.main import app
from app.servicios import autenticacion, cuentas

cliente = TestClient(app)

# Personas de los datos de prueba, por rol
ESTUDIANTE = "santiago.sosa@campustfi.edu.ar"
DOCENTE = "maria.gomez@campustfi.edu.ar"
SUPERVISOR = "claudia.ferreyra@campustfi.edu.ar"
ADMINISTRADOR = "secretaria.academica@campustfi.edu.ar"

pasadas = 0
fallas: list[str] = []


# ===================== Andamiaje =====================
# El "token" de estas pruebas es el correo de quien consulta. Reemplazar solo
# `verify_id_token` deja intacto todo lo que viene después, que es lo que
# interesa probar.
def _verificar_falso(token: str, **_):
    if token == "vencido":
        raise auth.ExpiredIdTokenError("venció", None)
    if token == "roto":
        raise auth.InvalidIdTokenError("no es un token")
    if token == "caido":
        # Cualquier otro fallo al verificar: no puede interpretarse como pase
        raise RuntimeError("Firebase no responde")
    return {"email": token}


autenticacion.auth.verify_id_token = _verificar_falso


def como(correo: str | None):
    """Las cabeceras de quien consulta. Sin correo, nadie: no va token."""
    return {"Authorization": f"Bearer {correo}"} if correo else {}


def sin_usuario_de_prueba(permitir: bool) -> None:
    os.environ["PERMITIR_USUARIO_SIN_TOKEN"] = "si" if permitir else "no"


def persona_de(correo: str) -> dict:
    return next(p for p in d.personas if p["correo"] == correo)


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


def error_de(r) -> str:
    try:
        return r.json().get("error", "")
    except ValueError:
        return ""


# ===================== Las pruebas =====================
def correr() -> None:
    print("Pruebas de acceso y roles (en proceso)\n")

    # ------------------------------------------------------------------
    grupo("El token")
    sin_usuario_de_prueba(permitir=False)

    r = cliente.get("/api/me")
    comprobar("sin token no se entra", r.status_code == 401, r.status_code)

    r = cliente.get("/api/me", headers=como("vencido"))
    comprobar("un token vencido no entra", r.status_code == 401, error_de(r))

    r = cliente.get("/api/me", headers=como("roto"))
    comprobar("un token inválido no entra", r.status_code == 401, error_de(r))

    r = cliente.get("/api/me", headers=como("caido"))
    comprobar(
        "si no se puede verificar, no se pasa igual (503, no 200)",
        r.status_code == 503,
        r.status_code,
    )

    r = cliente.get("/api/me", headers=como("alguien.de.afuera@gmail.com"))
    comprobar(
        "una cuenta de Firebase que no está en el campus no entra",
        r.status_code == 403,
        error_de(r),
    )

    r = cliente.get("/api/me", headers=como(ESTUDIANTE))
    comprobar("con token válido entra", r.status_code == 200, error_de(r))
    comprobar(
        "y el servidor resuelve quién es por su correo",
        r.status_code == 200 and r.json()["correo"] == ESTUDIANTE,
        r.json() if r.status_code == 200 else None,
    )

    # ------------------------------------------------------------------
    grupo("El usuario de prueba, que en producción va apagado")
    sin_usuario_de_prueba(permitir=True)
    r = cliente.get("/api/me")
    comprobar("con la variable encendida se entra sin token", r.status_code == 200)
    sin_usuario_de_prueba(permitir=False)
    comprobar(
        "y apagada vuelve a pedir sesión",
        cliente.get("/api/me").status_code == 401,
    )

    # ------------------------------------------------------------------
    grupo("El estado de la cuenta")
    alumno = persona_de(ESTUDIANTE)
    original = alumno.get("estado", "activa")

    alumno["estado"] = "suspendida"
    r = cliente.get("/api/me", headers=como(ESTUDIANTE))
    comprobar("una cuenta suspendida no entra", r.status_code == 403, r.status_code)
    comprobar(
        "y se le dice por qué, sin tecnicismos",
        "suspendida" in error_de(r).lower(),
        error_de(r),
    )

    alumno["estado"] = "pendiente"
    r = cliente.get("/api/me", headers=como(ESTUDIANTE))
    comprobar("una cuenta pendiente de activar tampoco", r.status_code == 403, r.status_code)

    alumno["estado"] = original
    comprobar(
        "activa de nuevo, entra",
        cliente.get("/api/me", headers=como(ESTUDIANTE)).status_code == 200,
    )

    # ------------------------------------------------------------------
    grupo("Los cuatro roles")
    # Cada uno contra la ruta que lo define: la administración de cuentas es
    # del administrador, la auditoría general de la supervisión, la gestión de
    # finales de la cátedra.
    #
    # El padrón lo **lee** también el supervisor, porque necesita saber a quién
    # inscribir; cambiarlo sigue siendo del administrador y eso se comprueba
    # más abajo. Y la gestión de finales la ven la supervisión y la
    # administración enteras: ven todo, pero no califican.
    casos = [
        ("estudiante", ESTUDIANTE, {"usuarios": 403, "auditoria": 403, "finales": 403}),
        ("docente", DOCENTE, {"usuarios": 403, "auditoria": 403, "finales": 200}),
        ("supervisor", SUPERVISOR, {"usuarios": 200, "auditoria": 200, "finales": 200}),
        ("administrador", ADMINISTRADOR, {"usuarios": 200, "auditoria": 200, "finales": 200}),
    ]
    rutas = {
        "usuarios": "/api/usuarios",
        "auditoria": "/api/auditoria",
        "finales": "/api/finales/gestion/mesas",
    }
    for nombre, correo, esperado in casos:
        for clave, codigo in esperado.items():
            real = cliente.get(rutas[clave], headers=como(correo)).status_code
            # Sin flechas: la consola de Windows no las sabe escribir y la
            # prueba se caería al imprimir el nombre de la comprobación.
            comprobar(f"{nombre} en {rutas[clave]} da {codigo}", real == codigo, real)

    # Ver no es firmar: el acta la firma el tribunal
    mesas = cliente.get("/api/finales/gestion/mesas", headers=como(ADMINISTRADOR)).json()
    comprobar(
        "la administración ve las mesas pero no puede calificar ninguna",
        bool(mesas) and not any(m["puedeCalificar"] for m in mesas),
        [m["id"] for m in mesas if m["puedeCalificar"]] if isinstance(mesas, list) else mesas,
    )
    comprobar(
        "ni editarlas, que es del titular de la materia",
        isinstance(mesas, list) and not any(m["puedeEditar"] for m in mesas),
        [m["id"] for m in mesas if m["puedeEditar"]] if isinstance(mesas, list) else mesas,
    )

    comprobar(
        "el supervisor que además es docente conserva los dos roles",
        d.tiene_rol(persona_de(SUPERVISOR), "Supervisor")
        and d.tiene_rol(persona_de(SUPERVISOR), "Docente"),
        d.roles_de(persona_de(SUPERVISOR)),
    )

    # ------------------------------------------------------------------
    grupo("Nadie se asciende solo")
    admin = persona_de(ADMINISTRADOR)
    r = cliente.patch(
        f"/api/usuarios/{admin['id']}",
        json={"roles": ["Administrador", "Docente"]},
        headers=como(ADMINISTRADOR),
    )
    comprobar("un administrador no se edita a sí mismo", r.status_code == 403, error_de(r))

    alumno = persona_de(ESTUDIANTE)
    r = cliente.patch(
        f"/api/usuarios/{alumno['id']}",
        json={"roles": ["Administrador"]},
        headers=como(ESTUDIANTE),
    )
    comprobar("un estudiante no se da el rol de administrador", r.status_code == 403, error_de(r))
    comprobar(
        "y sus roles quedaron intactos",
        d.roles_de(persona_de(ESTUDIANTE)) == ["Estudiante"],
        d.roles_de(persona_de(ESTUDIANTE)),
    )

    r = cliente.patch(
        f"/api/usuarios/{admin['id']}",
        json={"roles": ["Docente"]},
        headers=como(SUPERVISOR),
    )
    comprobar("el supervisor tampoco cambia roles", r.status_code == 403, error_de(r))

    r = cliente.patch(
        f"/api/usuarios/{alumno['id']}",
        json={"roles": ["Inventado"]},
        headers=como(ADMINISTRADOR),
    )
    comprobar("un rol que no existe se rechaza", r.status_code == 400, error_de(r))
    comprobar(
        "son cuatro y nada más",
        d.ROLES == ["Estudiante", "Docente", "Supervisor", "Administrador"],
        d.ROLES,
    )

    # ------------------------------------------------------------------
    grupo("Suspender corta el acceso")
    r = cliente.patch(
        f"/api/usuarios/{alumno['id']}",
        json={"estado": "suspendida"},
        headers=como(ADMINISTRADOR),
    )
    comprobar("el administrador suspende la cuenta", r.status_code == 200, error_de(r))
    comprobar(
        "la respuesta cuenta qué pasó con el acceso de Firebase",
        "acceso" in (r.json() if r.status_code == 200 else {}),
        r.json() if r.status_code == 200 else None,
    )
    comprobar(
        "y la persona deja de entrar en el acto",
        cliente.get("/api/me", headers=como(ESTUDIANTE)).status_code == 403,
    )

    r = cliente.patch(
        f"/api/usuarios/{alumno['id']}",
        json={"estado": "activa"},
        headers=como(ADMINISTRADOR),
    )
    comprobar(
        "al reactivarla vuelve a entrar",
        r.status_code == 200
        and cliente.get("/api/me", headers=como(ESTUDIANTE)).status_code == 200,
        error_de(r),
    )

    # ------------------------------------------------------------------
    grupo("Sin Firebase configurado, el campus sigue andando")
    # Es el caso de estas pruebas: no hay app de Firebase inicializada.
    comprobar("se detecta que no está disponible", cuentas.disponible() is False)
    resultado = cuentas.crear("nuevo@campustfi.edu.ar", "Nuevo")
    comprobar(
        "crear un acceso avisa el motivo y no explota",
        resultado.hecho is False and bool(resultado.motivo),
        resultado,
    )
    comprobar(
        "sincronizar roles, igual",
        cuentas.sincronizar_roles(ESTUDIANTE, ["Estudiante"]).hecho is False,
    )
    comprobar("y cambiar el estado, igual", cuentas.cambiar_estado(ESTUDIANTE, "activa").hecho is False)

    r = cliente.post(
        "/api/usuarios",
        json={"nombre": "Rodrigo Paz", "correo": "rodrigo.paz@campustfi.edu.ar"},
        headers=como(ADMINISTRADOR),
    )
    # (sigue abajo: la cuenta queda pendiente porque no hay Firebase)
    comprobar("el alta de una persona funciona igual", r.status_code == 201, error_de(r))
    nueva = r.json()["usuario"] if r.status_code == 201 else {}
    comprobar(
        "pero la cuenta queda pendiente: todavía no puede entrar",
        nueva.get("estadoCuenta") == "pendiente",
        nueva.get("estadoCuenta"),
    )
    comprobar(
        "y la respuesta explica por qué",
        r.status_code == 201 and r.json()["acceso"]["hecho"] is False,
        r.json().get("acceso") if r.status_code == 201 else None,
    )
    comprobar(
        "esa persona pendiente no entra",
        cliente.get("/api/me", headers=como("rodrigo.paz@campustfi.edu.ar")).status_code == 403,
    )

    # ------------------------------------------------------------------
    grupo("Las cuentas solo las crea la administración")
    # Es la regla de la facultad: nadie se registra solo, ni un alumno ni un
    # docente. El alta es el único camino para que exista una cuenta.
    for rol, correo in (("estudiante", ESTUDIANTE), ("docente", DOCENTE), ("supervisor", SUPERVISOR)):
        r = cliente.post(
            "/api/usuarios",
            json={"nombre": "Colado", "correo": f"colado.{rol}@campustfi.edu.ar"},
            headers=como(correo),
        )
        comprobar(f"un {rol} no puede dar de alta una cuenta", r.status_code == 403, r.status_code)

    comprobar(
        "y nadie quedó agregado al padrón",
        not any("colado." in (p.get("correo") or "") for p in d.personas),
        [p["correo"] for p in d.personas if "colado." in (p.get("correo") or "")],
    )

    r = cliente.post(
        "/api/usuarios",
        json={
            "nombre": "Clave Corta",
            "correo": "clave.corta@campustfi.edu.ar",
            "contrasena": "123",
        },
        headers=como(ADMINISTRADOR),
    )
    comprobar("una contraseña de menos de 6 caracteres se rechaza", r.status_code == 400, error_de(r))

    r = cliente.post(
        "/api/usuarios",
        json={
            "nombre": "Delfina Sosa",
            "correo": "delfina.sosa@campustfi.edu.ar",
            "roles": ["Docente"],
            "contrasena": "provisoria.2026",
        },
        headers=como(ADMINISTRADOR),
    )
    comprobar("el administrador le asigna la contraseña en el alta", r.status_code == 201, error_de(r))
    comprobar(
        "la respuesta no la guarda en el padrón, solo la devuelve",
        r.status_code == 201 and "contrasena" not in r.json()["usuario"],
        list(r.json()["usuario"].keys()) if r.status_code == 201 else None,
    )
    comprobar(
        "el correo repetido se rechaza",
        cliente.post(
            "/api/usuarios",
            json={"nombre": "Otra", "correo": "delfina.sosa@campustfi.edu.ar"},
            headers=como(ADMINISTRADOR),
        ).status_code
        == 409,
    )

    resumir()


def resumir() -> None:
    total = pasadas + len(fallas)
    print("\n" + "=" * 58)
    print(f"{pasadas} de {total} comprobaciones correctas")
    if fallas:
        print("\nFallaron:")
        for f in fallas:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    correr()
