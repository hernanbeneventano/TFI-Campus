"""Verificación de la identidad de quien consulta.

El navegador se autentica contra Firebase y recibe un token de identidad. Ese
token viaja en la cabecera `Authorization` de cada consulta y acá se verifica
con el kit de administrador, que comprueba la firma, el vencimiento y que el
token sea de este proyecto.

**La contraseña nunca pasa por este servidor.** Es la ventaja principal de
apoyarse en Firebase y no en un sistema propio: no guardamos credenciales, así
que no podemos perderlas.

El vínculo entre una cuenta de Firebase y una persona del campus es el
**correo**. Firebase sabe quién es alguien; solo el campus sabe que esa persona
es docente de Bases de Datos. Se eligió el correo y no el identificador de
Firebase porque las cuentas las crea la facultad: si hay que recrear una, la
persona sigue siendo la misma mientras conserve su correo institucional.
"""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request
from firebase_admin import auth

from .. import datos as d
from . import auditoria

# ===================== El ingreso, en el registro =====================
# `identificar` corre en **cada** consulta, así que anotar un ingreso por
# llamada llenaría la auditoría de ruido y no diría nada. Se anota uno por
# persona cada media hora: eso es, en la práctica, "entró".
#
# Los intentos fallidos sí se anotan todos: son pocos y son justamente lo que
# hay que poder mirar.
MINUTOS_ENTRE_INGRESOS = 30
_ultimo_ingreso: dict[int, float] = {}


def _anotar_ingreso(persona: dict) -> None:
    import time

    ahora = time.time()
    previo = _ultimo_ingreso.get(persona["id"])
    if previo and (ahora - previo) < MINUTOS_ENTRE_INGRESOS * 60:
        return
    _ultimo_ingreso[persona["id"]] = ahora
    auditoria.registrar(
        persona,
        "ingreso",
        "sesion",
        elemento=persona["nombre"],
        elemento_id=persona["id"],
        elemento_tipo="persona",
        persona_id=persona["id"],
        detalle="Entró al campus",
    )


def _anotar_fallo(motivo: str, correo: str | None = None) -> None:
    """Un intento que no entró.

    **No se guarda el token**: solo por qué falló y, si se sabe, con qué
    correo se intentó. Un registro que no se puede borrar es el peor lugar
    para una credencial.
    """
    auditoria.registrar(
        None,
        "ingreso_fallido",
        "sesion",
        elemento=correo or "Sin identificar",
        elemento_tipo="sesion",
        resultado="fallo",
        detalle=motivo,
    )

# Mientras el campus se desarrolla conviene poder usarlo sin iniciar sesión: si
# no llega token, se responde como el usuario de prueba de `datos.py`.
#
# **Viene apagado.** Hay que pedirlo a propósito con
# PERMITIR_USUARIO_SIN_TOKEN=si en `backend/.env`, porque encendido cualquiera
# que llegue sin token entra como esa persona. Antes venía encendido por
# defecto, de cuando no había login; ahora que hay, lo que corresponde es que
# la única forma de entrar sea una cuenta de Firebase.
#
# Por eso la variable se llama como se llama y no algo como "modo_desarrollo":
# que quede claro qué se está permitiendo.
def _permite_usuario_de_prueba() -> bool:
    return (os.environ.get("PERMITIR_USUARIO_SIN_TOKEN") or "no").lower() in ("si", "1", "true")


def _persona_por_correo(correo: str | None) -> dict | None:
    if not correo:
        return None
    buscado = correo.strip().lower()
    return next((p for p in d.personas if (p.get("correo") or "").lower() == buscado), None)


# ===================== Cuentas que no pueden entrar =====================
# El estado de la cuenta lo administra la secretaría (`rutas/usuarios.py`), y
# tiene que cortar el acceso acá: deshabilitarla en Firebase evita que pida un
# token nuevo, pero el que ya tenga en el navegador le sirve hasta que venza.
# Esta comprobación es inmediata y no cuesta una consulta a Firebase, que es
# lo que costaría verificar la revocación en cada pedido.
_CUENTA_NO_ACTIVA = {
    "suspendida": "Tu cuenta está suspendida. Hablá con la secretaría.",
    "pendiente": "Tu cuenta todavía no fue activada. Hablá con la secretaría.",
}


def _exigir_cuenta_activa(persona: dict) -> None:
    estado = persona.get("estado", "activa")
    if estado == "activa":
        return
    _anotar_fallo(f"La cuenta está {estado}", persona.get("correo"))
    raise HTTPException(
        403,
        _CUENTA_NO_ACTIVA.get(estado, "Tu cuenta no está activa. Hablá con la secretaría."),
    )


def _token_de(peticion: Request) -> str | None:
    cabecera = peticion.headers.get("Authorization") or ""
    if not cabecera.lower().startswith("bearer "):
        return None
    token = cabecera[7:].strip()
    return token or None


def identificar(peticion: Request) -> dict:
    """Devuelve la persona del campus que hace la consulta.

    Pensada para usarse como dependencia de FastAPI:

        def mi_ruta(yo: dict = Depends(identificar)):
    """
    token = _token_de(peticion)

    if token is None:
        if _permite_usuario_de_prueba():
            persona = d.buscar_persona(d.usuario_actual["id"])
            if persona:
                _exigir_cuenta_activa(persona)
                return persona
        raise HTTPException(401, "Hay que iniciar sesión")

    try:
        datos_token = auth.verify_id_token(token)
    except auth.ExpiredIdTokenError:
        _anotar_fallo("La sesión venció")
        raise HTTPException(401, "La sesión venció. Volvé a iniciar sesión.")
    except auth.RevokedIdTokenError:
        _anotar_fallo("La sesión había sido cerrada")
        raise HTTPException(401, "La sesión fue cerrada. Volvé a iniciar sesión.")
    except (auth.InvalidIdTokenError, auth.UserDisabledError):
        _anotar_fallo("Token inválido o cuenta deshabilitada")
        raise HTTPException(401, "La sesión no es válida. Volvé a iniciar sesión.")
    except Exception:
        # Un fallo al verificar no puede interpretarse como "pase"
        _anotar_fallo("No se pudo verificar la sesión")
        raise HTTPException(503, "No se pudo verificar la sesión. Probá de nuevo.")

    persona = _persona_por_correo(datos_token.get("email"))
    if persona is None:
        # La cuenta existe en Firebase pero nadie con ese correo está en el
        # campus. Es un caso real: alguien de la facultad con cuenta de Google
        # que todavía no fue dado de alta.
        _anotar_fallo("El correo no está dado de alta en el campus", datos_token.get("email"))
        raise HTTPException(
            403,
            "Tu cuenta no está dada de alta en el campus. Pedí el alta en la secretaría.",
        )

    # El token es válido y la persona existe, pero su cuenta puede estar
    # suspendida o todavía sin activar
    _exigir_cuenta_activa(persona)

    _anotar_ingreso(persona)
    return persona


def identificar_id(persona: dict = Depends(identificar)) -> int:
    """El identificador de quien consulta, para las rutas que solo necesitan eso.

    Depende de `identificar` por el sistema de dependencias y no llamándola a
    mano: así FastAPI la resuelve una sola vez por pedido aunque la ruta pida
    las dos cosas, y un reemplazo de `identificar` —como el de las pruebas—
    vale también para esta.
    """
    return persona["id"]


# Atajos para leer en las rutas
UsuarioActual = Depends(identificar)
IdUsuarioActual = Depends(identificar_id)
