"""Crea en Firebase el acceso de cada persona del campus.

Es el puente entre el padrón del campus (`personas` en
`app/datos_iniciales.json`) y Firebase Authentication, que es quien guarda las
contraseñas. Sin una cuenta de Firebase, una persona figura en el campus pero
no puede entrar.

Hace dos cosas, y las dos son repetibles sin consecuencias:

1. Crea la cuenta de quien no la tenga. **Sin contraseña**: la elige cada uno
   desde «¿Olvidaste tu contraseña?» en la pantalla de inicio de sesión, así
   no pasa nunca por el campus ni queda una contraseña compartida. Para las
   cuentas nuevas se imprime un enlace de un solo uso, por si el correo
   todavía no puede recibir mails.
2. Copia los roles del campus al token (lo que Firebase llama *custom
   claims*). Los permisos de la API no dependen de esto —los decide el
   servidor leyendo `personas`—, pero es lo que van a leer las reglas de
   seguridad de Firestore el día que una pantalla consulte la base sin pasar
   por el backend.

El modo `--prueba` es aparte: prepara **una cuenta por rol** con una
contraseña conocida, para poder mostrar el campus desde los cuatro lados sin
depender del correo. Son las cuatro personas que ya están en el padrón con esos
roles, así que entran a un campus con datos de verdad: Santiago tiene módulos y
entregas, María tiene sus mesas y sus actas, Claudia supervisa y la Secretaría
administra.

**Nunca borra ni deshabilita nada.** Dar de baja una cuenta se hace desde el
campus, que es donde queda registrado quién lo hizo.

Uso, desde `backend/` y con el entorno activado:

    python -m herramientas.crear_cuentas              # crea lo que falte
    python -m herramientas.crear_cuentas --ver        # no toca nada, informa
    python -m herramientas.crear_cuentas --prueba     # las cuatro de la demo

Trabaja sobre el proyecto de Firebase de `firebase-key.json`, que es el de
verdad: conviene correrlo mirando lo que imprime.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from firebase_admin import auth

from app.servicios import certificados, cuentas
from app.servicios.firestore import inicializar_firestore

# Lo mismo que hace `app/main.py` al arrancar, y por el mismo motivo: las
# bibliotecas de Google leen la configuración de certificados una sola vez, al
# construir su contexto, así que esto va antes de crear cualquier cliente. Sin
# esto, en un equipo con antivirus o proxy que inspeccione HTTPS, todas las
# llamadas fallan con CERTIFICATE_VERIFY_FAILED.
certificados.configurar()

RUTA_DATOS = Path(__file__).resolve().parents[1] / "app" / "datos_iniciales.json"

# ===================== Las cuatro cuentas de la demo =====================
# Una por rol, de las personas que ya están en el padrón. Son los cuatro roles
# del campus y no hay más: Estudiante, Docente, Supervisor y Administrador.
CUENTAS_DE_PRUEBA = [
    ("Estudiante", "santiago.sosa@campustfi.edu.ar"),
    ("Docente", "maria.gomez@campustfi.edu.ar"),
    ("Supervisor", "claudia.ferreyra@campustfi.edu.ar"),
    ("Administrador", "secretaria.academica@campustfi.edu.ar"),
]

# Para mostrar el campus hace falta poder entrar, y los correos del padrón son
# de un dominio propio: si la facultad todavía no tiene el envío configurado,
# el mail para elegir la contraseña no llega a ninguna parte. Entonces estas
# cuatro llevan una contraseña fija y conocida.
#
# Es lo contrario de lo que hace el campus en serio, donde la contraseña la
# elige cada uno y nunca pasa por el servidor (ver `servicios/cuentas.py`).
# Por eso vive acá, en una herramienta que se corre a mano, y no en
# `servicios/`: el campus no fija contraseñas.
#
# **Antes de publicar, estas cuatro cuentas se borran o se les cambia la
# contraseña.** Están para la demo del trabajo, no para quedarse.
CONTRASENA_DE_PRUEBA = "campus.2026"


def personas_con_correo() -> list[dict]:
    datos = json.loads(RUTA_DATOS.read_text(encoding="utf-8"))
    return [p for p in datos["personas"] if p.get("correo")]


def preparar_demo() -> int:
    """Deja listas las cuatro cuentas de la demo, una por rol."""
    inicializar_firestore()

    padron = {p["correo"]: p for p in personas_con_correo()}
    print("Cuatro cuentas de prueba, una por rol.")
    print(f"Contraseña para las cuatro: {CONTRASENA_DE_PRUEBA}")
    print()

    fallidas = 0
    for rol, correo in CUENTAS_DE_PRUEBA:
        persona = padron.get(correo)
        if persona is None:
            fallidas += 1
            print(f"  FALTA EN EL PADRÓN  {rol:<14} {correo}")
            continue

        resultado = cuentas.crear(correo, persona["nombre"])
        if not resultado.hecho:
            fallidas += 1
            print(f"  FALLÓ               {rol:<14} {correo}  {resultado.motivo}")
            continue

        try:
            # Se fija siempre, aunque la cuenta ya existiera: la gracia de
            # estas cuatro es que la contraseña sea conocida. El alta del
            # campus, en cambio, no pisa la de una cuenta que ya estaba.
            auth.update_user(resultado.uid, password=CONTRASENA_DE_PRUEBA)
        except Exception as falla:
            fallidas += 1
            print(f"  SIN CONTRASEÑA      {rol:<14} {correo}  {falla}")
            continue

        roles_ok = cuentas.sincronizar_roles(correo, persona.get("roles") or [])
        aviso = "" if roles_ok.hecho else f"  (roles: {roles_ok.motivo})"
        print(f"  lista               {rol:<14} {correo:<42} {persona['roles']}{aviso}")

    print()
    print("Entrar en /login con cualquiera de esos correos y esa contraseña.")
    print("Cada uno ve el campus que le corresponde: el estudiante no ve la")
    print("administración, el docente no ve el padrón, la secretaría no califica.")
    return 1 if fallidas else 0


def correr(solo_ver: bool) -> int:
    inicializar_firestore()  # deja lista la app de Firebase con la clave de servicio

    personas = personas_con_correo()
    print(f"{len(personas)} personas con correo en el padrón del campus\n")

    creadas, existentes, fallidas = 0, 0, 0
    enlaces: list[tuple[str, str]] = []

    for persona in personas:
        correo = persona["correo"]
        roles = persona.get("roles") or []
        etiqueta = f"{persona['nombre']:<22} {correo:<42}"

        if solo_ver:
            # `crear` no se llama: solo se mira si el acceso ya existe. Si la
            # consulta falla hay que decirlo: dar por hecho que no existe
            # sería contar mal y, peor, invitar a crear una cuenta repetida.
            try:
                existe = cuentas.tiene_acceso(correo)
            except Exception as falla:
                fallidas += 1
                print(f"  NO SE PUDO    {etiqueta} {falla}")
                continue
            print(f"  {'tiene acceso' if existe else 'SIN ACCESO  '}  {etiqueta} {roles}")
            existentes += 1 if existe else 0
            creadas += 0 if existe else 1
            continue

        try:
            ya_estaba = cuentas.tiene_acceso(correo)
        except Exception:
            # `crear` vuelve a intentarlo y, si falla, informa el motivo
            ya_estaba = False
        resultado = cuentas.crear(correo, persona["nombre"])

        if not resultado.hecho:
            fallidas += 1
            print(f"  FALLÓ         {etiqueta} {resultado.motivo}")
            continue

        roles_ok = cuentas.sincronizar_roles(correo, roles)
        detalle = "" if roles_ok.hecho else f"  (roles: {roles_ok.motivo})"

        if ya_estaba:
            existentes += 1
            print(f"  ya existía    {etiqueta} {roles}{detalle}")
        else:
            creadas += 1
            print(f"  creada        {etiqueta} {roles}{detalle}")
            if resultado.enlace:
                enlaces.append((correo, resultado.enlace))

    print()
    if solo_ver:
        print(
            f"Resumen: {existentes} con acceso, {creadas} sin acceso todavía, "
            f"{fallidas} que no se pudieron consultar."
        )
        print("Para crear las que falten, correr el comando sin --ver.")
        return 1 if fallidas else 0

    print(f"Resumen: {creadas} creadas, {existentes} ya existían, {fallidas} con error.")

    if enlaces:
        print("\nEnlaces para elegir la contraseña (de un solo uso, vencen):")
        for correo, enlace in enlaces:
            print(f"\n  {correo}\n  {enlace}")
        print(
            "\nSi el correo del campus ya recibe mails, no hace falta repartirlos: "
            "cada uno puede usar «¿Olvidaste tu contraseña?» en el login."
        )

    return 1 if fallidas else 0


if __name__ == "__main__":
    try:
        if "--prueba" in sys.argv:
            sys.exit(preparar_demo())
        sys.exit(correr(solo_ver="--ver" in sys.argv))
    except FileNotFoundError as falta:
        # Sin la clave de servicio no hay nada que hacer, y el motivo lo dice
        # `servicios/firestore`: dónde se la espera y cómo configurar otra ruta.
        print(f"\n{falta}\n")
        sys.exit(2)
