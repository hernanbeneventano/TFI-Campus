"""El lado de Firebase Authentication de una cuenta del campus.

Una persona del campus vive en dos lugares y hay que mantenerlos de acuerdo:

- En `personas`: quién es, qué roles tiene, si su cuenta está activa. Eso lo
  administra la secretaría desde el campus.
- En Firebase Authentication: el correo y la contraseña con los que entra.
  Eso lo sabe Firebase, y nosotros nunca vemos la contraseña.

Este módulo es el único que habla con Firebase Auth para escribir, así que es
el único lugar donde hay que mirar cuando los dos lados se desincronizan. El
vínculo entre ambos es el **correo**, igual que al verificar el token
(`servicios/autenticacion.py`).

**Nada de acá puede hacer fallar una operación del campus.** Si Firebase no
está configurado —en desarrollo, sin `firebase-key.json`— o si la llamada
falla, se devuelve el motivo y el campus sigue andando: la cuenta queda
`pendiente`, que es justamente "existe en el padrón pero todavía no puede
entrar". Que el alta de una persona explote porque Firebase está caído sería
peor que dejarla pendiente.
"""

from __future__ import annotations

from dataclasses import dataclass

import firebase_admin
from firebase_admin import auth


@dataclass
class Resultado:
    """Cómo salió la operación contra Firebase.

    `motivo` está pensado para mostrárselo a la secretaría, no para el
    registro técnico: dice qué hacer, no qué excepción se levantó.
    """

    hecho: bool
    motivo: str | None = None
    uid: str | None = None
    # Enlace para que la persona elija su contraseña la primera vez
    enlace: str | None = None
    # La contraseña provisoria, **solo** cuando se acaba de crear la cuenta.
    # No se guarda en ninguna parte: se muestra una vez a quien da el alta y
    # no hay forma de volver a verla, solo de cambiarla.
    contrasena: str | None = None


SIN_FIREBASE = "Firebase Authentication no está configurado en este servidor."


def disponible() -> bool:
    """Si hay una app de Firebase inicializada en este proceso.

    La inicializa `servicios/firestore.inicializar_firestore()` al arrancar el
    servidor. En las pruebas, que corren sin ese arranque, esto devuelve False
    y todo el módulo se vuelve inofensivo.
    """
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        return False


def _buscar(correo: str):
    """El usuario de Firebase con ese correo, o None si no existe."""
    try:
        return auth.get_user_by_email(correo)
    except auth.UserNotFoundError:
        return None


def tiene_acceso(correo: str) -> bool:
    """Si esa persona ya tiene cuenta en Firebase y puede iniciar sesión."""
    return disponible() and _buscar(correo) is not None


def enlace_para_contrasena(correo: str) -> str | None:
    """Enlace de un solo uso para que la persona elija su contraseña.

    Firebase también puede mandar ese correo por su cuenta, pero los correos
    del campus son de un dominio propio: si la facultad todavía no tiene el
    envío configurado, el mail no llega a ninguna parte. Con el enlace en la
    respuesta, la secretaría puede pasárselo por otro medio y el alta no queda
    a medias.
    """
    try:
        return auth.generate_password_reset_link(correo)
    except Exception:
        # Falta la configuración de correo del proyecto, o la cuenta no está.
        # No es motivo para que el alta falle.
        return None


def crear(correo: str, nombre: str | None = None, contrasena: str | None = None) -> Resultado:
    """Da de alta el acceso de esa persona.

    Con `contrasena`, la cuenta queda lista para entrar: es el alta que hace
    la secretaría, que después le pasa esa clave provisoria a la persona. Sin
    ella, la cuenta se crea igual pero todavía no se puede usar, y hay que
    elegir una contraseña con el enlace que se devuelve.

    En los dos casos la contraseña **no se guarda en el campus**: se la manda
    a Firebase y no queda en ninguna parte nuestra. El campus no puede volver
    a mostrarla, solo cambiarla, que es como tiene que ser.

    Si la cuenta ya existía se la reutiliza y no se le toca la contraseña:
    pasa de verdad —alguien de la facultad con cuenta de antes, a quien recién
    ahora se le da el alta en el campus— y pisársela lo dejaría afuera.
    """
    if not disponible():
        return Resultado(False, SIN_FIREBASE)

    try:
        usuario = _buscar(correo)
        if usuario is not None:
            return Resultado(True, uid=usuario.uid)

        usuario = auth.create_user(
            email=correo,
            display_name=nombre or None,
            password=contrasena or None,
        )
        return Resultado(
            True,
            uid=usuario.uid,
            enlace=None if contrasena else enlace_para_contrasena(correo),
            contrasena=contrasena,
        )
    except auth.EmailAlreadyExistsError:
        # Carrera entre dos altas simultáneas: la cuenta ya está, alcanza
        existente = _buscar(correo)
        if existente:
            return Resultado(True, uid=existente.uid)
        return Resultado(False, "Ese correo ya tiene una cuenta de acceso.")
    except ValueError:
        return Resultado(False, "Firebase rechazó el correo o el nombre.")
    except Exception:
        return Resultado(False, "No se pudo crear el acceso. Probá de nuevo en un rato.")


def sincronizar_roles(correo: str, roles: list[str]) -> Resultado:
    """Copia los roles del campus al token de la persona.

    Los permisos los decide **siempre el servidor**, que lee los roles de
    `personas`: para que la API funcione, esto no hace falta. Se mantiene al
    día porque es lo que van a leer las reglas de seguridad de Firestore el
    día que una pantalla consulte la base sin pasar por el backend; ahí las
    reglas solo pueden mirar lo que viaja en el token.

    **El token no se actualiza en el momento**: Firebase lo renueva cuando
    está por vencer, hasta una hora después. Por eso el campus no usa estos
    roles para decidir nada ahora mismo.
    """
    if not disponible():
        return Resultado(False, SIN_FIREBASE)

    usuario = _buscar(correo)
    if usuario is None:
        return Resultado(False, "Esa persona todavía no tiene cuenta de acceso.")

    try:
        auth.set_custom_user_claims(usuario.uid, {"roles": list(roles)})
        return Resultado(True, uid=usuario.uid)
    except Exception:
        return Resultado(False, "No se pudieron actualizar los roles del acceso.")


def cambiar_estado(correo: str, estado: str) -> Resultado:
    """Habilita o deshabilita el acceso según el estado de la cuenta.

    El servidor ya rechaza a quien no está activa (ver
    `servicios/autenticacion.py`), pero eso corta recién al consultar la API.
    Deshabilitarla en Firebase es más fuerte: no puede ni iniciar sesión ni
    pedir un token nuevo, y los que ya tenga dejan de servir.
    """
    if not disponible():
        return Resultado(False, SIN_FIREBASE)

    usuario = _buscar(correo)
    if usuario is None:
        return Resultado(False, "Esa persona todavía no tiene cuenta de acceso.")

    try:
        auth.update_user(usuario.uid, disabled=estado != "activa")
        # Cortar las sesiones abiertas de una cuenta suspendida: si no, el
        # token que ya tiene en el navegador le sigue sirviendo hasta vencer.
        if estado != "activa":
            auth.revoke_refresh_tokens(usuario.uid)
        return Resultado(True, uid=usuario.uid)
    except Exception:
        return Resultado(False, "No se pudo cambiar el estado del acceso.")
