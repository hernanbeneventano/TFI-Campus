"""El perfil propio y la administración de cuentas.

Dos cosas que parecen la misma y no lo son:

- **Mi perfil**: cualquiera edita sus datos de contacto. Nadie se cambia el
  rol ni el estado de su propia cuenta, por razones obvias: si alguien
  pudiera asignarse "Administrador", los permisos no servirían de nada.
- **Las cuentas**: el administrador da de alta personas, asigna roles y
  suspende cuentas.

Los campos sensibles —roles, estado, legajo— están separados de los que uno
edita de sí mismo. No es una cuestión de esconder botones: son dos rutas
distintas con dos permisos distintos.

**Contraseña y sesiones** no están acá: las maneja Firebase Authentication.
El campus nunca ve una contraseña. Lo que sí hace esta ruta es mantener los
dos lados de acuerdo —el padrón de `personas` y el acceso en Firebase— a
través de `servicios/cuentas.py`: al dar de alta crea el acceso, al cambiar
los roles los copia al token y al suspender una cuenta la deshabilita.

Si Firebase no responde, la operación del campus **no falla**: la cuenta
queda `pendiente` y la respuesta trae el motivo en `acceso`, para que la
secretaría sepa que esa persona todavía no puede entrar.
"""

from __future__ import annotations

import re
import secrets

from fastapi import APIRouter, Body, HTTPException

from .. import datos as d
from ..servicios import auditoria, cuentas
from ..servicios.autenticacion import UsuarioActual
from .institucion import es_administrador

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])

CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Un DNI argentino: 7 u 8 dígitos, sin puntos
DNI = re.compile(r"^\d{7,8}$")
TELEFONO = re.compile(r"^[\d\s()+-]{6,25}$")


def _texto(valor, campo: str, maximo: int, obligatorio: bool = False) -> str | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            raise HTTPException(400, f"Falta {campo}")
        return None
    if not isinstance(valor, str):
        raise HTTPException(400, f"{campo} tiene que ser texto")
    limpio = valor.strip()
    if len(limpio) > maximo:
        raise HTTPException(400, f"{campo} no puede pasar de {maximo} caracteres")
    return limpio


# De lo que se anota a la acción del vocabulario de auditoría. La frase que
# escribe cada ruta ("carrera creada", "plan dado de baja") ya dice qué pasó:
# alcanza con mirar su última palabra.
_ACCION_POR_PALABRA = {
    "creada": "creacion", "creado": "creacion", "creadas": "creacion",
    "editada": "edicion", "editado": "edicion", "configurado": "edicion",
    "baja": "baja", "eliminada": "baja", "eliminado": "baja",
    "estado": "estado", "roles": "roles", "cuenta": "estado",
    "asignado": "asignacion", "asignada": "asignacion",
    "reasignado": "reasignacion", "cambiada": "reasignacion",
}


def _accion_de(que: str) -> str:
    for palabra in reversed(que.lower().split()):
        if palabra in _ACCION_POR_PALABRA:
            return _ACCION_POR_PALABRA[palabra]
    return "edicion"


def _anotar(
    yo: dict, que: str, detalle: str, persona_id: int, *, antes=None, despues=None
) -> None:
    """Todo lo que pasa con una cuenta va al registro central de auditoría.

    Vale también cuando lo hace un administrador: el pliego pide que nadie
    quede afuera, y de hecho es de quien más importa saberlo.
    """
    auditoria.registrar(
        yo,
        _accion_de(que),
        "usuarios",
        elemento=detalle,
        elemento_id=persona_id,
        elemento_tipo="persona",
        persona_id=persona_id,
        antes=antes,
        despues=despues,
        detalle=que,
    )


def _informe(*resultados: cuentas.Resultado) -> dict:
    """Lo que hay que contarle a la secretaría sobre el acceso en Firebase.

    Se queda con la primera falla, que es la que hay que resolver; si no hubo
    ninguna, con lo que salió bien. El enlace sirve para que la persona elija
    su contraseña la primera vez.
    """
    fallada = next((r for r in resultados if not r.hecho), None)
    elegida = fallada or (resultados[0] if resultados else cuentas.Resultado(True))
    return {
        "hecho": elegida.hecho,
        "motivo": elegida.motivo,
        "enlace": elegida.enlace,
        # Se muestra una sola vez, al dar el alta: no queda guardada
        "contrasena": elegida.contrasena,
    }


# Firebase pide seis caracteres como mínimo
MINIMO_CONTRASENA = 6


def _contrasena_provisoria(cuerpo: dict) -> str:
    """La que elija quien da el alta, o una al azar si no puso ninguna.

    Al azar es mejor que una fija: una contraseña inicial igual para todos
    sería, en la práctica, no tener contraseña. Se muestra una vez en la
    pantalla del alta y no se guarda; después la cambia cada uno.
    """
    elegida = cuerpo.get("contrasena")
    if elegida in (None, ""):
        return secrets.token_urlsafe(6)

    if not isinstance(elegida, str):
        raise HTTPException(400, "La contraseña tiene que ser texto")
    if len(elegida) < MINIMO_CONTRASENA:
        raise HTTPException(
            400, f"La contraseña tiene que tener al menos {MINIMO_CONTRASENA} caracteres"
        )
    if len(elegida) > 72:
        raise HTTPException(400, "La contraseña es demasiado larga")
    return elegida


def _perfil(persona: dict, completo: bool = False) -> dict:
    """La ficha de una persona, con sus asociaciones académicas."""
    salida = {
        **d.con_presencia(persona),
        # `con_presencia` usa `estado` para conectado/ausente/desconectado y
        # pisaría el de la cuenta. Son dos cosas distintas: una es si está
        # mirando la pantalla ahora, la otra si la cuenta sirve para entrar.
        "estadoCuenta": persona.get("estado", "activa"),
        "asociaciones": [
            d.asociacion_completa(a) for a in d.asociaciones_de(persona["id"])
        ],
    }
    if not completo:
        # El DNI y el teléfono son de cada uno: no viajan en los listados
        salida.pop("dni", None)
        salida.pop("telefono", None)
        salida.pop("fechaNacimiento", None)
    return salida


# ===================== Mi perfil =====================
@router.get("/yo", summary="Mi perfil completo")
def mi_perfil(yo: dict = UsuarioActual):
    """Todo lo mío, con mis carreras y comisiones."""
    return {
        "perfil": _perfil(yo, completo=True),
        "estadosCuenta": d.ESTADOS_CUENTA,
        "puedeAdministrar": es_administrador(yo),
        # Lo que todavía no se puede hacer y la pantalla tiene que decir
        "pendientes": {
            "contrasena": "Se cambia desde Firebase Authentication, que todavía no está habilitado.",
            "sesiones": "Las sesiones activas llegan con el inicio de sesión real.",
            "foto": "La subida de imágenes llega con Firebase Storage.",
        },
    }


@router.put("/yo", summary="Editar mis datos")
def editar_mi_perfil(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Los datos propios de contacto, y nada más.

    Roles, estado de la cuenta y legajo no se tocan desde acá: si uno pudiera
    cambiarse el rol, los permisos del campus no significarían nada. Para eso
    está la administración de cuentas.
    """
    prohibidos = {"roles", "rol", "estado", "id"} & set(cuerpo)
    if prohibidos:
        raise HTTPException(
            403,
            "Los roles y el estado de la cuenta los cambia un administrador, no vos.",
        )

    if "nombre" in cuerpo:
        yo["nombre"] = _texto(cuerpo["nombre"], "el nombre", 120, obligatorio=True)

    if "correo" in cuerpo and (cuerpo["correo"] or "").strip().lower() != (
        yo.get("correo") or ""
    ).lower():
        # El correo es la identidad de la cuenta: es con lo que el servidor
        # reconoce a la persona detrás del token de Firebase. Si se lo
        # cambiara acá, su cuenta de Firebase seguiría con el viejo y el
        # campus dejaría de reconocerla: se quedaría afuera ella misma.
        raise HTTPException(
            403,
            "El correo no se cambia desde acá: es con el que entrás. "
            "Pedíselo a la secretaría.",
        )

    if "dni" in cuerpo:
        dni = _texto(cuerpo["dni"], "el DNI", 10)
        if dni and not DNI.match(dni):
            raise HTTPException(400, "El DNI son 7 u 8 números, sin puntos")
        yo["dni"] = dni

    if "telefono" in cuerpo:
        telefono = _texto(cuerpo["telefono"], "el teléfono", 25)
        if telefono and not TELEFONO.match(telefono):
            raise HTTPException(400, "Ese teléfono no tiene un formato válido")
        yo["telefono"] = telefono

    if "fechaNacimiento" in cuerpo:
        fecha = cuerpo["fechaNacimiento"]
        if fecha:
            try:
                nacimiento = d.desde_iso(fecha)
            except (ValueError, TypeError, AttributeError):
                raise HTTPException(400, "Esa fecha de nacimiento no es válida")
            if nacimiento > d.ahora():
                raise HTTPException(400, "La fecha de nacimiento no puede ser futura")
        yo["fechaNacimiento"] = fecha or None

    _anotar(yo, "perfil editado", "datos personales", yo["id"])
    return mi_perfil(yo)


# ===================== Administración de cuentas =====================
@router.get("", summary="Las cuentas del campus")
def listar(yo: dict = UsuarioActual, q: str | None = None, rol: str | None = None):
    """El padrón, para el administrador.

    El supervisor también la necesita para saber a quién inscribir, así que
    la lee; pero no puede cambiar nada de acá.
    """
    from .institucion import es_supervisor

    if not es_supervisor(yo):
        raise HTTPException(403, "No tenés acceso al padrón de usuarios")

    gente = d.personas
    if rol:
        gente = [p for p in gente if d.tiene_rol(p, rol)]
    if q:
        texto = q.strip().lower()
        gente = [
            p
            for p in gente
            if texto in p["nombre"].lower() or texto in (p.get("correo") or "").lower()
        ]

    return {
        "usuarios": sorted(
            (_perfil(p) for p in gente), key=lambda p: p["nombre"]
        ),
        "roles": d.ROLES,
        "estadosCuenta": d.ESTADOS_CUENTA,
        "puedeAdministrar": es_administrador(yo),
    }


@router.get("/historial", summary="Los cambios sobre las cuentas")
def historial(yo: dict = UsuarioActual):
    """Vista del registro central, recortada a las cuentas.

    El apartado completo de auditoría, con todos sus filtros, está en
    `/api/auditoria`: esto es el atajo desde la pantalla de Cuentas.
    """
    if not es_administrador(yo):
        raise HTTPException(403, "Solo el administrador ve el historial de cuentas")

    return {
        "historial": [
            {
                **auditoria.con_nombres(e),
                "que": e.get("elementoTipo") or e["accion"],
                "detalle": e.get("elemento"),
                "quienNombre": e["quien"],
                "sobreNombre": auditoria.con_nombres(e)["afectada"],
            }
            for e in auditoria.buscar({"modulo": "usuarios"})[:200]
        ]
    }


@router.patch("/{id_persona}", summary="Cambiar roles o estado de una cuenta")
def administrar(id_persona: int, cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Roles y estado de la cuenta: solo el administrador.

    Dos resguardos que importan: nadie se edita a sí mismo —para no quitarse
    el rol y quedar afuera, ni dárselo— y el campus no se queda sin ningún
    administrador.
    """
    if not es_administrador(yo):
        raise HTTPException(403, "Solo el administrador puede cambiar roles y cuentas")

    persona = d.buscar_persona(id_persona)
    if not persona:
        raise HTTPException(404, "Esa persona no existe")
    if persona["id"] == yo["id"]:
        raise HTTPException(
            403,
            "No podés cambiarte los roles a vos mismo. Pedíselo a otro administrador.",
        )

    # Lo que haya que hacer en Firebase según lo que se cambie acá
    hechos: list[cuentas.Resultado] = []

    if "roles" in cuerpo:
        roles = cuerpo["roles"]
        if not isinstance(roles, list) or not roles:
            raise HTTPException(400, "Hay que dejar al menos un rol")
        desconocidos = [r for r in roles if r not in d.ROLES]
        if desconocidos:
            raise HTTPException(400, f"El rol «{desconocidos[0]}» no existe")

        # Que no quede el campus sin administrador
        if d.tiene_rol(persona, "Administrador") and "Administrador" not in roles:
            otros = [
                p
                for p in d.personas
                if p["id"] != persona["id"] and d.tiene_rol(p, "Administrador")
            ]
            if not otros:
                raise HTTPException(
                    409,
                    "Es la única cuenta de administrador: asigná otra antes de quitarle el rol.",
                )

        antes = d.roles_de(persona)
        persona["roles"] = list(dict.fromkeys(roles))
        # Los roles también viajan en el token, para las reglas de Firestore.
        # Los permisos de la API no dependen de esto: los decide el servidor
        # leyendo `personas`.
        hechos.append(cuentas.sincronizar_roles(persona.get("correo", ""), persona["roles"]))
        _anotar(
            yo,
            "roles cambiados",
            persona["nombre"],
            persona["id"],
            antes={"roles": antes},
            despues={"roles": persona["roles"]},
        )

    if "estado" in cuerpo:
        if cuerpo["estado"] not in d.ESTADOS_CUENTA:
            raise HTTPException(400, "Ese estado de cuenta no existe")
        antes_estado = persona.get("estado", "activa")
        persona["estado"] = cuerpo["estado"]
        # Suspender en el campus tiene que cortar el acceso de verdad: si no,
        # la persona no entra a la API pero sigue pudiendo iniciar sesión.
        hechos.append(cuentas.cambiar_estado(persona.get("correo", ""), persona["estado"]))
        _anotar(
            yo,
            "estado de cuenta cambiada",
            persona["nombre"],
            persona["id"],
            antes={"estado": antes_estado},
            despues={"estado": persona["estado"]},
        )

    return {"usuario": _perfil(persona, completo=True), "acceso": _informe(*hechos)}


@router.post("", status_code=201, summary="Dar de alta una cuenta")
def crear(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Alta de una persona en el campus, con su acceso.

    Es el único camino para que exista una cuenta: **nadie se registra solo**.
    La secretaría carga los datos, y con eso la persona ya puede entrar la
    próxima vez que lo intente.

    Se la agrega al padrón, se le crea la cuenta en Firebase Authentication y
    se le deja una **contraseña provisoria**: la que haya puesto quien da el
    alta, o una al azar. Viaja en la respuesta para mostrarla una vez —es lo
    que hay que pasarle a la persona— y no se guarda en ninguna parte: el
    campus no puede volver a mostrarla, solo cambiarla. Después cada uno pone
    la suya desde «¿Olvidaste tu contraseña?».

    Si el acceso no se pudo crear, la cuenta queda **pendiente**: figura en el
    padrón pero no entra, y el servidor se lo dice con todas las letras
    cuando lo intente.
    """
    if not es_administrador(yo):
        raise HTTPException(403, "Solo el administrador puede dar de alta cuentas")

    nombre = _texto(cuerpo.get("nombre"), "el nombre", 120, obligatorio=True)
    correo = _texto(cuerpo.get("correo"), "el correo", 150, obligatorio=True)
    if not CORREO.match(correo):
        raise HTTPException(400, "Ese correo no tiene un formato válido")
    if any(p.get("correo", "").lower() == correo.lower() for p in d.personas):
        raise HTTPException(409, "Ya hay una cuenta con ese correo")

    roles = cuerpo.get("roles") or ["Estudiante"]
    if not isinstance(roles, list) or any(r not in d.ROLES for r in roles):
        raise HTTPException(400, "Los roles no son válidos")

    persona = {
        "id": max((p["id"] for p in d.personas), default=0) + 1,
        "nombre": nombre,
        "correo": correo,
        "roles": list(dict.fromkeys(roles)),
        "accesoHaceMin": 100000,
        "dni": None,
        "telefono": None,
        "fechaNacimiento": None,
        "foto": None,
        "estado": "pendiente",
        "creada": d.iso(d.ahora()),
    }
    d.personas.append(persona)

    acceso = cuentas.crear(correo, nombre, _contrasena_provisoria(cuerpo))
    if acceso.hecho:
        # Ya puede entrar, con la contraseña provisoria
        persona["estado"] = "activa"
        cuentas.sincronizar_roles(correo, persona["roles"])

    _anotar(
        yo,
        "cuenta creada",
        f"{nombre} ({', '.join(persona['roles'])})",
        persona["id"],
        despues={"roles": persona["roles"], "acceso": "creado" if acceso.hecho else "pendiente"},
    )
    return {"usuario": _perfil(persona, completo=True), "acceso": _informe(acceso)}
