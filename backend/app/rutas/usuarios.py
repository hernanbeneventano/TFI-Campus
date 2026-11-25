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

**Contraseña y sesiones** no están acá. Las maneja Firebase Authentication,
que todavía no está habilitado: ver `servicios/autenticacion.py`.
"""

from __future__ import annotations

import hmac
import re

from ..web import APIRouter, Body, HTTPException, Response

from .. import datos as d
from ..servicios import almacenamiento as alm
from ..servicios import archivos
from ..servicios import ambito, auditoria, cuentas, fotos, legajos
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
        # Hasta dónde llega si supervisa. Sin ámbito ve todo el campus, que es
        # como venía: ver `servicios/ambito.py`.
        "ambito": ambito.resumen(persona),
    }
    if not completo:
        # El DNI y el teléfono son de cada uno: no viajan en los listados
        salida.pop("dni", None)
        salida.pop("telefono", None)
        salida.pop("fechaNacimiento", None)
    return salida


def _fijar_ambito(yo: dict, persona: dict, crudo) -> None:
    """Hasta dónde llega quien supervisa: qué carreras y qué sedes.

    Vacío quiere decir **todo el campus**, que es lo que hacían todos los
    supervisores hasta que esto existió. Recortar es una decisión de la
    facultad, así que se guarda tal cual se pide y no se inventa un mínimo.

    Al administrador no se le pone ámbito: es el rol que define qué es la
    facultad, y recortarlo la dejaría sin nadie que la viera entera.
    """
    if d.tiene_rol(persona, "Administrador"):
        raise HTTPException(400, "El administrador alcanza todo el campus: no lleva ámbito")

    if not isinstance(crudo, dict):
        raise HTTPException(400, "El ámbito tiene que traer carreras y sedes")

    def ids_de(clave: str, coleccion: list[dict]) -> list[int]:
        valores = crudo.get(clave) or []
        if not isinstance(valores, list):
            raise HTTPException(400, f"«{clave}» tiene que ser una lista")
        salida = []
        for v in valores:
            try:
                numero = int(v)
            except (TypeError, ValueError):
                raise HTTPException(400, f"«{clave}» tiene que traer identificadores")
            if not d.buscar_en(coleccion, numero):
                raise HTTPException(400, f"En «{clave}» hay algo que no existe")
            salida.append(numero)
        return sorted(dict.fromkeys(salida))

    carreras = ids_de("carreras", d.carreras_institucion)
    sedes = ids_de("sedes", d.sedes)

    antes = persona.get("ambito") or {}
    if carreras or sedes:
        persona["ambito"] = {"carreras": carreras, "sedes": sedes}
    else:
        persona.pop("ambito", None)

    _anotar(
        yo,
        "ámbito cambiado",
        persona["nombre"],
        persona["id"],
        antes={"ambito": antes or "todo el campus"},
        despues={"ambito": persona.get("ambito") or "todo el campus"},
    )


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
            "foto": None,
        },
    }


# Lo que identifica a una persona ante la facultad. No se edita desde el
# perfil propio: un legajo vale porque alguien respondió por esos datos, y si
# cada uno pudiera cambiarse el nombre o el DNI dejaría de valer. El correo,
# además, es con lo que se entra: cambiarlo de un lado y no del otro dejaría a
# la persona afuera.
#
# Los cambia la administración desde Administración → Cuentas.
IDENTIDAD = {"nombre", "correo", "dni"}


@router.put("/yo", summary="Editar mis datos de contacto")
def editar_mi_perfil(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """El teléfono y la fecha de nacimiento, y nada más.

    Roles y estado de la cuenta tampoco: si uno pudiera cambiarse el rol, los
    permisos del campus no significarían nada.
    """
    prohibidos = {"roles", "rol", "estado", "id"} & set(cuerpo)
    if prohibidos:
        raise HTTPException(
            403,
            "Los roles y el estado de la cuenta los cambia un administrador, no vos.",
        )

    # Se comparan contra lo que ya está: que el formulario mande el mismo
    # valor sin cambios no es un intento de editar nada.
    tocados = {c for c in IDENTIDAD if c in cuerpo and (cuerpo[c] or None) != (yo.get(c) or None)}
    if tocados:
        raise HTTPException(
            403,
            "El nombre, el correo y el DNI los cambia la administración. "
            "Si hay un error, pedíselo a la secretaría.",
        )

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

    _anotar(yo, "perfil editado", "datos de contacto", yo["id"])
    return mi_perfil(yo)


# ===================== El acceso =====================
# La contraseña **no se cambia acá**: eso lo hace el navegador contra Firebase,
# que pide la actual antes de aceptar la nueva. El servidor nunca la ve, que
# es la ventaja de apoyarse en Firebase y no en un sistema propio.
#
# Lo que sí hace el servidor es lo que necesita la clave de administrador:
# contar cómo está el acceso, cortar las sesiones y, para la administración,
# restablecer la contraseña de alguien que la perdió.


@router.get("/yo/acceso", summary="Cómo está mi acceso al campus")
def mi_acceso(yo: dict = UsuarioActual):
    """El estado de la cuenta en Firebase.

    **No hay lista de sesiones activas**: Firebase Authentication no la
    expone, no se puede saber desde qué equipos entró alguien. Lo que sí se
    sabe es cuándo entró por última vez y desde cuándo valen sus tokens, que
    es lo que cambia al cerrar las sesiones.
    """
    if not cuentas.hay_firebase():
        return {"tieneAcceso": False, "sinFirebase": True}
    try:
        return cuentas.estado_de_acceso(yo.get("correo") or "")
    except Exception as e:
        raise HTTPException(502, f"No se pudo consultar el acceso: {e}")


@router.post("/yo/cerrar-sesiones", summary="Cerrar la sesión en todos los equipos")
def cerrar_mis_sesiones(yo: dict = UsuarioActual):
    """Invalida los tokens: caen todas las sesiones, también la de acá.

    Sirve cuando alguien se dejó la sesión abierta en una máquina del
    laboratorio. Como caen todas, hay que volver a entrar.
    """
    if not cuentas.hay_firebase():
        raise HTTPException(503, "El inicio de sesión todavía no está configurado")
    try:
        cuentas.cerrar_sesiones(yo.get("correo") or "")
    except ValueError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise HTTPException(502, f"No se pudieron cerrar las sesiones: {e}")

    _anotar(yo, "sesiones cerradas", yo["nombre"], yo["id"])
    return {"cerradas": True}


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
        # Para poder recortarle el ámbito a quien supervisa sin salir de acá
        "carreras": [
            {"id": c["id"], "nombre": c["nombre"]}
            for c in d.carreras_institucion
            if c.get("activa", True)
        ],
        "sedes": [
            {"id": s["id"], "nombre": s["nombre"]} for s in d.sedes if s.get("activa", True)
        ],
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

    # La identidad: lo que la persona no puede cambiarse sola
    if "nombre" in cuerpo:
        antes_nombre = persona.get("nombre")
        persona["nombre"] = _texto(cuerpo["nombre"], "el nombre", 120, obligatorio=True)
        _anotar(yo, "nombre corregido", persona["nombre"], persona["id"],
                antes={"nombre": antes_nombre}, despues={"nombre": persona["nombre"]})

    if "dni" in cuerpo:
        dni = _texto(cuerpo["dni"], "el DNI", 10)
        if dni and not DNI.match(dni):
            raise HTTPException(400, "El DNI son 7 u 8 números, sin puntos")
        antes_dni = persona.get("dni")
        persona["dni"] = dni
        _anotar(yo, "DNI corregido", persona["nombre"], persona["id"],
                antes={"dni": antes_dni}, despues={"dni": dni})

    if "correo" in cuerpo:
        correo = _texto(cuerpo["correo"], "el correo", 150, obligatorio=True)
        if not CORREO.match(correo):
            raise HTTPException(400, "Ese correo no tiene un formato válido")
        if any(
            p.get("correo", "").lower() == correo.lower() and p["id"] != persona["id"]
            for p in d.personas
        ):
            raise HTTPException(409, "Ya hay una cuenta con ese correo")

        antes_correo = persona.get("correo")
        if correo.lower() != (antes_correo or "").lower():
            # El correo es con lo que se entra: hay que moverlo también en
            # Firebase, o la persona queda con acceso a un correo que el
            # campus ya no reconoce.
            if cuentas.hay_firebase() and antes_correo:
                try:
                    cuentas.cambiar_correo(antes_correo, correo)
                except Exception as e:
                    raise HTTPException(
                        502, f"No se pudo cambiar el correo de acceso: {e}"
                    )
            persona["correo"] = correo
            _anotar(yo, "correo corregido", persona["nombre"], persona["id"],
                    antes={"correo": antes_correo}, despues={"correo": correo})

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
        # Que el estado del campus y el de Firebase no se separen: si solo
        # cambiara acá, quien ya tuviera la sesión abierta seguiría entrando.
        if cuentas.hay_firebase() and persona.get("correo"):
            try:
                cuentas.habilitar(persona["correo"], persona["estado"] == "activa")
            except Exception:
                pass
        _anotar(
            yo,
            "estado de cuenta cambiada",
            persona["nombre"],
            persona["id"],
            antes={"estado": antes_estado},
            despues={"estado": persona["estado"]},
        )

    if "ambito" in cuerpo:
        _fijar_ambito(yo, persona, cuerpo["ambito"])

    return {"usuario": _perfil(persona, completo=True)}


@router.post("", status_code=201, summary="Dar de alta una cuenta")
def crear(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Alta de una persona en el campus.

    La cuenta queda **pendiente**: existe en el padrón, pero el acceso real
    llega cuando se le cree el usuario en Firebase Authentication.
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

    # Comprobar el correo, numerar y anotar van juntos: dos altas a la vez
    # sacaban el mismo id y el mismo legajo, y el mismo correo mandado dos
    # veces pasaba dos veces por «no hay otra cuenta» (ver `legajos.padron`).
    #
    # La persona entra al padrón **antes** de pedirle el acceso a Firebase,
    # y no después: así el candado se suelta antes de la red. Mientras
    # Firebase contesta figura como «pendiente», que es justamente lo que es.
    with legajos.padron:
        if any(p.get("correo", "").lower() == correo.lower() for p in d.personas):
            raise HTTPException(409, "Ya hay una cuenta con ese correo")
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
        # Docentes, supervisores y administración llevan legajo del campus: en un
        # acta o en el registro de auditoría el nombre no identifica a nadie.
        legajos.asegurar_institucional(persona)
        d.personas.append(persona)

    # El acceso de verdad, ya sin candado: es la red. Sin esto la cuenta
    # existe en el padrón pero la persona no puede entrar, que es lo que
    # pasaba antes.
    provisoria = None
    if cuentas.hay_firebase():
        try:
            provisoria = cuentas.contrasena_provisoria()
            cuentas.crear_acceso(correo, nombre, provisoria)
            persona["estado"] = "activa"
        except Exception as e:
            # La persona queda en el padrón igual, pero pendiente: alguien
            # tiene que crearle el acceso a mano.
            provisoria = None
            persona["notaAcceso"] = f"No se pudo crear el acceso: {e}"

    _anotar(yo, "cuenta creada", f"{nombre} ({', '.join(persona['roles'])})", persona["id"])

    return {
        "usuario": _perfil(persona, completo=True),
        # Se muestra **una sola vez** y no se guarda en ningún lado, ni en la
        # auditoría: es para pasársela a la persona y que la cambie.
        "contrasenaProvisoria": provisoria,
    }


@router.post("/{id_persona}/contrasena", summary="Restablecer la contraseña de alguien")
def restablecer_contrasena(id_persona: int, yo: dict = UsuarioActual):
    """Le pone una contraseña provisoria a quien perdió la suya.

    Se devuelve **una sola vez** y no se guarda en ningún lado, ni en la
    auditoría: queda anotado que se restableció y quién lo hizo, no cuál es.
    """
    if not es_administrador(yo):
        raise HTTPException(403, "Solo el administrador puede restablecer contraseñas")
    if not cuentas.hay_firebase():
        raise HTTPException(503, "El inicio de sesión todavía no está configurado")

    persona = d.buscar_persona(id_persona)
    if not persona:
        raise HTTPException(404, "Esa persona no existe")

    provisoria = cuentas.contrasena_provisoria()
    try:
        if cuentas.buscar(persona.get("correo") or ""):
            cuentas.poner_contrasena(persona["correo"], provisoria)
        else:
            # Nunca tuvo acceso: se lo creamos ahora
            cuentas.crear_acceso(persona["correo"], persona["nombre"], provisoria)
            persona["estado"] = "activa"
    except Exception as e:
        raise HTTPException(502, f"No se pudo restablecer la contraseña: {e}")

    _anotar(yo, "contraseña restablecida", persona["nombre"], persona["id"])
    return {"contrasenaProvisoria": provisoria}


# ===================== La foto de perfil =====================

# Las imágenes van a Cloudflare R2 como todo lo demás (ver
# `servicios/almacenamiento.py`); acá queda solo la referencia.
FOTO_MAX_MB = archivos.IMAGENES_MAX_MB  # el mismo tope que el resto de las imágenes


@router.post("/yo/foto", summary="Cambiar mi foto de perfil")
def subir_mi_foto(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    """Valida la imagen mirando los bytes y la deja en el almacenamiento.

    Solo PNG y JPG: un SVG es un documento con scripts adentro, no una imagen
    inofensiva, y la foto de perfil se muestra en todo el campus.
    """
    contenido, ficha = archivos.leer_subida(
        cuerpo, permitidos={"png", "jpg", "jpeg"}, max_mb=FOTO_MAX_MB
    )

    objeto = alm.clave(alm.PERFILES, yo["id"], nombre=ficha["nombre"])

    # La anterior se va: nadie va a volver a mirar la foto vieja de alguien,
    # y dejarla es pagar lugar por un archivo que no referencia nada.
    anterior = yo.get("foto")
    if anterior and anterior != objeto:
        alm.olvidar(anterior)

    # Primero el archivo, después la ficha: si no se pudo guardar, el perfil
    # queda como estaba en vez de apuntar a una foto que no existe.
    try:
        alm.subir(objeto, contenido, ficha["tipo"])
    except Exception as error:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo guardar la imagen: {error}")

    alm.registrar(
        objeto,
        nombre=ficha["nombre"],
        tipo=ficha["tipo"],
        tamano=ficha["tamano"],
        persona_id=yo["id"],
        modulo=alm.PERFILES,
        registro_id=yo["id"],
    )
    yo["foto"] = objeto

    _anotar(yo, "foto de perfil actualizada", yo["nombre"], yo["id"])
    return mi_perfil(yo)


@router.delete("/yo/foto", summary="Quitar mi foto de perfil")
def quitar_mi_foto(yo: dict = UsuarioActual):
    objeto = yo.get("foto")
    if not objeto:
        raise HTTPException(409, "No tenés una foto cargada")
    alm.olvidar(objeto)
    yo["foto"] = None
    _anotar(yo, "foto de perfil quitada", yo["nombre"], yo["id"])
    return mi_perfil(yo)


@router.get("/{id_persona}/foto", summary="La foto de alguien del campus")
def ver_foto(id_persona: int, f: str = ""):
    """La sirve el servidor, con la dirección firmada.

    **No se puede exigir el token acá**, y esa es la razón de toda la firma:
    una etiqueta `<img>` no manda la cabecera `Authorization`. Con la sesión
    como único control, cada avatar del campus daba 401 y se veía la silueta.

    Las salidas eran tres: que el navegador baje cada cara con `fetch` y la
    convierta en un objeto en memoria —en una lista de treinta participantes
    son treinta descargas que no se pueden cachear—; abrir la ruta a
    cualquiera; o que **la dirección sea la credencial**, que es lo que hacen
    los enlaces firmados de R2 y lo que se hace acá.

    La firma sale de la clave del objeto y de un secreto del servidor, así que
    no se puede fabricar ni adivinar a partir del número de persona. Solo
    viaja en las respuestas que ya pasaron por el control de sesión, y cambia
    sola cuando alguien cambia su foto: la dirección vieja deja de servir.
    """
    persona = d.buscar_persona(id_persona)
    if not persona or not persona.get("foto"):
        raise HTTPException(404, "Esa persona no tiene foto")
    if not hmac.compare_digest(f or "", fotos.firma(persona["foto"])):
        raise HTTPException(404, "Esa persona no tiene foto")

    contenido = alm.leer(persona["foto"])
    if contenido is None:
        raise HTTPException(404, "La foto no está disponible")

    ficha = alm.ficha_de(persona["foto"]) or {}
    return Response(
        content=contenido,
        media_type=ficha.get("tipo") or "image/png",
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
            # Que el navegador la reutilice: el avatar se pide muchas veces
            # por pantalla. Privada, porque es de alguien.
            "Cache-Control": "private, max-age=300",
        },
    )
