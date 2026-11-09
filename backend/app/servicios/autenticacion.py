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

# Mientras el campus se desarrolla conviene poder usarlo sin iniciar sesión.
# Si no llega token, se responde como el usuario de prueba.
#
# En producción esto tiene que estar apagado: sin él, cualquiera que llegue sin
# token entra como esa persona. Por eso la variable se llama como se llama y no
# algo como "modo_desarrollo": que quede claro qué se está permitiendo.
def _permite_usuario_de_prueba() -> bool:
    return (os.environ.get("PERMITIR_USUARIO_SIN_TOKEN") or "si").lower() in ("si", "1", "true")


def _persona_por_correo(correo: str | None) -> dict | None:
    if not correo:
        return None
    buscado = correo.strip().lower()
    return next((p for p in d.personas if (p.get("correo") or "").lower() == buscado), None)


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
                return persona
        raise HTTPException(401, "Hay que iniciar sesión")

    try:
        datos_token = auth.verify_id_token(token)
    except auth.ExpiredIdTokenError:
        raise HTTPException(401, "La sesión venció. Volvé a iniciar sesión.")
    except auth.RevokedIdTokenError:
        raise HTTPException(401, "La sesión fue cerrada. Volvé a iniciar sesión.")
    except (auth.InvalidIdTokenError, auth.UserDisabledError):
        raise HTTPException(401, "La sesión no es válida. Volvé a iniciar sesión.")
    except Exception:
        # Un fallo al verificar no puede interpretarse como "pase"
        raise HTTPException(503, "No se pudo verificar la sesión. Probá de nuevo.")

    persona = _persona_por_correo(datos_token.get("email"))
    if persona is None:
        # La cuenta existe en Firebase pero nadie con ese correo está en el
        # campus. Es un caso real: alguien de la facultad con cuenta de Google
        # que todavía no fue dado de alta.
        raise HTTPException(
            403,
            "Tu cuenta no está dada de alta en el campus. Pedí el alta en la secretaría.",
        )

    return persona


def identificar_id(peticion: Request) -> int:
    """El identificador de quien consulta, para las rutas que solo necesitan eso."""
    return identificar(peticion)["id"]


# Atajos para leer en las rutas
UsuarioActual = Depends(identificar)
IdUsuarioActual = Depends(identificar_id)
