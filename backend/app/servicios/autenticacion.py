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

# Mientras el campus se desarrolla conviene poder usarlo sin iniciar sesión.
# Si no llega token, se responde como el usuario de prueba.
#
# **Viene apagado.** Hay que pedirlo a propósito con
# `PERMITIR_USUARIO_SIN_TOKEN=si` en el `.env`, que no viaja por el
# repositorio. Estaba al revés —abierto si la variable faltaba— y eso
# significaba que una copia recién clonada, o un despliegue nuevo, arrancaba
# con el campus entero abierto como Secretaría Académica, que es
# administradora. Un valor por defecto que hay que acordarse de apagar es un
# agujero esperando a que alguien se distraiga.
#
# La variable se llama como se llama, y no algo como "modo_desarrollo", para
# que quede claro qué se está permitiendo al encenderla.
def _permite_usuario_de_prueba() -> bool:
    return (os.environ.get("PERMITIR_USUARIO_SIN_TOKEN") or "no").lower() in ("si", "1", "true")


# ===================== Quién actúa, en las pruebas =====================
# Las pruebas necesitan hacer la misma petición como distintas personas: lo
# que comprueban es justamente quién ve qué. Eso se resolvía con
# `dependency_overrides` de FastAPI, que reemplaza la dependencia desde
# afuera. Es cómodo y **no existe fuera de FastAPI**, así que era lo único que
# ataba las catorce suites al framework.
#
# Acá la suplantación vive adentro: `identificar` la consulta antes que nada.
# Es Python a secas, así que sigue funcionando con cualquier framework que
# llame a esta función.
#
# **No agrega superficie de ataque.** Se enciende únicamente llamando a
# `actuar_como()` desde adentro del proceso: no hay ruta, cabecera ni variable
# de entorno que lo haga, y nada de `app/` la llama (hay una comprobación en
# `pruebas/usuarios.py` que lo verifica). Quien pueda ejecutar Python dentro
# del servidor ya puede editar `datos.personas` directamente, así que esto no
# le da nada que no tuviera.
#
# Se guarda **el identificador y no la persona**: las pruebas recargan su
# escenario y reemplazan el contenido de `datos.personas`, así que una
# referencia al diccionario quedaría apuntando a alguien que ya no está.
_suplantado: dict[str, int | None] = {"personaId": None}


def actuar_como(persona_id: int | None) -> None:
    """Hace que `identificar` devuelva a esa persona. **Solo para pruebas.**

    Con `None` se apaga y se vuelve a la verificación de siempre.
    """
    _suplantado["personaId"] = persona_id


def suplantando() -> int | None:
    """A quién se está suplantando, o `None` si a nadie.

    Está para poder comprobarlo desde las pruebas, que es la forma de dejar
    anotado que en el campus de verdad esto vale `None`.
    """
    return _suplantado["personaId"]


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

    De `peticion` solo se usa `.headers`, así que sirve igual cualquier
    petición que tenga esa propiedad.
    """
    # Las pruebas dicen quién actúa sin pasar por Firebase (ver arriba). En el
    # campus de verdad esto vale siempre None y la función sigue de largo.
    #
    # Si apuntara a alguien que no existe se sigue por el camino normal y la
    # petición termina en 401: es preferible que una prueba mal escrita falle
    # fuerte a que entre como quien no quiso.
    suplantada = _suplantado["personaId"]
    if suplantada is not None:
        persona = d.buscar_persona(suplantada)
        if persona:
            return persona

    token = _token_de(peticion)

    if token is None:
        if _permite_usuario_de_prueba():
            persona = d.buscar_persona(d.usuario_actual["id"])
            if persona:
                return persona
        raise HTTPException(401, "Hay que iniciar sesión")

    try:
        # `check_revoked` hace que Firebase mire también si esa cuenta fue
        # deshabilitada o si se le revocaron las sesiones. Sin esto, el token
        # que la persona ya tenía en la mano le seguía sirviendo hasta
        # vencerse —hasta una hora—, así que suspender a alguien no lo sacaba
        # del campus en el momento, que es justo para lo que se suspende.
        datos_token = auth.verify_id_token(token, check_revoked=True)
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

    # Y el estado que lleva el campus, que es el que mira la secretaría.
    # `cuentas.habilitar` deshabilita además la cuenta en Firebase, pero si
    # esa llamada falló —sin red, o la cuenta no existe allá— la suspensión
    # solo quedaría anotada acá y no serviría de nada. Comparar el estado
    # cierra ese caso sin costo.
    if persona is not None and (persona.get("estado") or "activa") != "activa":
        _anotar_fallo(
            f"La cuenta está {persona.get('estado')}", datos_token.get("email")
        )
        raise HTTPException(
            403,
            "Tu cuenta no está habilitada para entrar al campus. Consultá en la secretaría.",
        )

    if persona is None:
        # La cuenta existe en Firebase pero nadie con ese correo está en el
        # campus. Es un caso real: alguien de la facultad con cuenta de Google
        # que todavía no fue dado de alta.
        _anotar_fallo("El correo no está dado de alta en el campus", datos_token.get("email"))
        raise HTTPException(
            403,
            "Tu cuenta no está dada de alta en el campus. Pedí el alta en la secretaría.",
        )

    _anotar_ingreso(persona)
    return persona


def identificar_id(peticion: Request) -> int:
    """El identificador de quien consulta, para las rutas que solo necesitan eso."""
    return identificar(peticion)["id"]


# Atajos para leer en las rutas
UsuarioActual = Depends(identificar)
IdUsuarioActual = Depends(identificar_id)
