"""El acceso de cada persona, del lado de Firebase Authentication.

El campus tiene dos mitades de cada cuenta y conviene no confundirlas:

- **La persona** vive en `personas`: su nombre, su DNI, sus roles. Es lo que
  sabe la facultad.
- **El acceso** vive en Firebase Authentication: el correo y la contraseña con
  los que entra. Es lo que sabe Google.

Las une el **correo**. Este servicio es el único lugar que toca la mitad de
Firebase, así que si mañana se cambia de proveedor hay un solo archivo que
mirar.

**La contraseña nunca pasa por acá al iniciar sesión**: eso lo hace el
navegador contra Firebase. Este servicio solo interviene cuando la facultad
crea una cuenta, la suspende o le corta las sesiones a alguien.
"""

from __future__ import annotations

import secrets
import string

from firebase_admin import auth

# Una contraseña provisoria legible pero no adivinable. Se muestra una sola
# vez a quien crea la cuenta, para que se la pase a la persona; no se guarda
# en ningún lado, ni siquiera en la auditoría.
ALFABETO = string.ascii_letters + string.digits
LARGO_PROVISORIA = 12


def hay_firebase() -> bool:
    """Si el kit de administrador está inicializado.

    Sin él el campus sigue funcionando —los datos están en memoria—, pero no
    se puede dar acceso a nadie. Conviene que la pantalla lo pueda decir en
    vez de fallar con un error de Google.
    """
    try:
        import firebase_admin

        return bool(firebase_admin._apps)
    except Exception:
        return False


def contrasena_provisoria() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(LARGO_PROVISORIA))


def buscar(correo: str):
    """La cuenta de Firebase de ese correo, o `None` si no tiene."""
    try:
        return auth.get_user_by_email(correo)
    except Exception:
        return None


def crear_acceso(correo: str, nombre: str, contrasena: str) -> str:
    """Le da acceso real a alguien y devuelve su identificador de Firebase.

    Si el correo ya tenía cuenta se reutiliza y solo se le pone la contraseña
    nueva: que la persona figure dos veces en Firebase sería peor que
    reutilizarla.
    """
    existente = buscar(correo)
    if existente:
        auth.update_user(existente.uid, password=contrasena, display_name=nombre)
        return existente.uid

    creado = auth.create_user(email=correo, password=contrasena, display_name=nombre)
    return creado.uid


def cambiar_correo(correo_viejo: str, correo_nuevo: str) -> None:
    """Mueve el acceso al correo nuevo.

    Hace falta porque el vínculo entre Firebase y el campus es el correo: si
    se cambia de un lado y no del otro, la persona entra pero el campus no la
    reconoce.
    """
    cuenta = buscar(correo_viejo)
    if cuenta:
        auth.update_user(cuenta.uid, email=correo_nuevo)


def poner_contrasena(correo: str, contrasena: str) -> None:
    cuenta = buscar(correo)
    if not cuenta:
        raise ValueError("Esa persona todavía no tiene acceso al campus")
    auth.update_user(cuenta.uid, password=contrasena)


def habilitar(correo: str, puede_entrar: bool) -> None:
    """Suspender una cuenta en el campus tiene que cortar el acceso de verdad.

    Si solo cambiara el estado en `personas`, quien ya tuviera la sesión
    abierta seguiría entrando hasta que venciera el token.
    """
    cuenta = buscar(correo)
    if not cuenta:
        return
    auth.update_user(cuenta.uid, disabled=not puede_entrar)
    if not puede_entrar:
        auth.revoke_refresh_tokens(cuenta.uid)


def cerrar_sesiones(correo: str) -> None:
    """Corta todas las sesiones abiertas de esa persona, en todos sus equipos.

    Firebase no permite listar las sesiones activas ni cerrar una sola: lo que
    se puede es invalidar los tokens, y entonces caen todas. Es lo que sirve
    cuando alguien se dejó la sesión abierta en la máquina del laboratorio.
    """
    cuenta = buscar(correo)
    if not cuenta:
        raise ValueError("Esa persona todavía no tiene acceso al campus")
    auth.revoke_refresh_tokens(cuenta.uid)


def estado_de_acceso(correo: str) -> dict:
    """Lo que se puede contar sobre el acceso de alguien.

    **No hay lista de sesiones activas**: Firebase Authentication no la
    expone. Lo que sí se sabe es cuándo entró por última vez y desde cuándo
    valen sus tokens, que es con lo que se arma la pantalla.
    """
    cuenta = buscar(correo)
    if not cuenta:
        return {"tieneAcceso": False}

    datos = cuenta.user_metadata
    return {
        "tieneAcceso": True,
        "deshabilitada": cuenta.disabled,
        "creado": datos.creation_timestamp,
        "ultimoIngreso": datos.last_sign_in_timestamp,
        # Desde cuándo valen los tokens: si se cerraron las sesiones, es el
        # momento en que se cerraron.
        "sesionesDesde": getattr(datos, "tokens_valid_after_timestamp", None),
        "proveedores": [p.provider_id for p in cuenta.provider_data],
    }
