"""Auditoría: quién hizo qué, cuándo y qué cambió.

Un solo registro para todo el campus. La tentación es que cada apartado se
arme el suyo —y de hecho había tres: `historialUsuarios`, `historialAsistencia`
y `moderacionBiblioteca`—, pero entonces "¿quién tocó esto?" hay que
preguntárselo a cada módulo por separado y con una forma distinta cada vez.

Acá hay **una función para anotar** (`registrar`) y **una para consultar**
(`buscar`). Un módulo nuevo se suma llamando a `registrar`, sin tocar nada de
esto.

Qué queda de un apartado y qué viene acá
----------------------------------------
No todo historial es auditoría. `moderacionBiblioteca` y `historialAsistencia`
son **datos del apartado**: el estudiante ve el motivo de su rechazo, el
tribunal ve la corrección de una falta. Esos se quedan donde están y además
emiten su evento de auditoría. `historialUsuarios`, en cambio, era auditoría y
nada más: sus dos pantallas ahora leen de acá.

Lo que no se guarda
-------------------
Contraseñas, tokens y claves: `_limpiar` los saca aunque el que llama se
distraiga, porque un registro que no se puede borrar es el peor lugar para un
secreto.

Integridad
----------
La lista es **solo de agregar**. No hay función para editar ni para borrar un
evento, ni acá ni en las rutas: la única forma de alterar el historial sería
tocar el proceso, no la aplicación.
"""

from __future__ import annotations

import contextvars
import re
import unicodedata
from typing import Any

from .. import datos as d

# La petición que se está atendiendo, puesta por el middleware de main.py.
#
# Está acá para que `registrar` pueda anotar la dirección IP sin que cada
# ruta del campus tenga que recibir el `Request` y pasarlo. Un sistema
# centralizado de auditoría no puede costarle una firma a cada función.
peticion_actual: contextvars.ContextVar = contextvars.ContextVar(
    "peticion_actual", default=None
)

# ===================== El vocabulario =====================
# Las acciones y los módulos son listas cerradas a propósito: si cada módulo
# inventa su palabra, el filtro "¿qué se borró ayer?" deja de funcionar.

ACCIONES = {
    "ingreso": "Inicio de sesión",
    "ingreso_fallido": "Intento de inicio fallido",
    "salida": "Cierre de sesión",
    "creacion": "Creación",
    "edicion": "Modificación",
    "baja": "Eliminación",
    "estado": "Cambio de estado",
    "asignacion": "Asignación",
    "reasignacion": "Reasignación",
    "roles": "Cambio de roles o permisos",
    "aprobacion": "Aprobación",
    "rechazo": "Rechazo",
    "descarga": "Descarga de documento",
    "publicacion": "Publicación",
}

MODULOS = {
    "usuarios": "Usuarios y permisos",
    "academico": "Gestión académica",
    "asistencias": "Asistencias",
    "calificaciones": "Calificaciones",
    "finales": "Finales e inscripciones",
    "biblioteca": "Biblioteca",
    "modulos": "Módulos y contenido",
    "sesion": "Acceso al campus",
}

RESULTADOS = {"exito": "Exitosa", "fallo": "Fallida"}

# Campos que no se guardan jamás, por más que lleguen en el detalle
SECRETOS = re.compile(
    r"contrase|password|passwd|token|secret|clave|api[_-]?key|authorization", re.I
)

# Dos eventos idénticos muy seguidos son el mismo evento contado dos veces
# (un doble clic, un reintento del navegador). Se descarta el segundo.
VENTANA_REPETIDO = 2.0


def _limpiar(valor: Any, profundidad: int = 0) -> Any:
    """Saca del detalle cualquier cosa que parezca un secreto.

    Va acá y no en quien llama: el registro no se puede borrar, así que no
    puede depender de que cada módulo se acuerde.
    """
    if profundidad > 4:
        return "…"
    if isinstance(valor, dict):
        return {
            k: ("(oculto)" if SECRETOS.search(str(k)) else _limpiar(v, profundidad + 1))
            for k, v in valor.items()
        }
    if isinstance(valor, (list, tuple)):
        return [_limpiar(v, profundidad + 1) for v in valor[:50]]
    if isinstance(valor, str):
        return valor[:2000]
    return valor


def _sin_tildes(texto: Any) -> str:
    sin = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in sin if unicodedata.category(c) != "Mn").lower()


def ip_de(peticion=None) -> str | None:
    """La dirección de quien pide, si el servidor la tiene.

    Detrás de un proxy la real viene en `X-Forwarded-For`; se toma la primera,
    que es la del cliente. Si no se pasa ninguna, se usa la que el middleware
    dejó en el contexto; sin eso —una acción del propio servidor— queda en
    `None`.
    """
    if peticion is None:
        peticion = peticion_actual.get()
    if peticion is None:
        return None
    reenviada = peticion.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()[:45]
    cliente = getattr(peticion, "client", None)
    return getattr(cliente, "host", None)


def registrar(
    quien: dict | int | None,
    accion: str,
    modulo: str,
    *,
    elemento: str | None = None,
    elemento_id: Any = None,
    elemento_tipo: str | None = None,
    persona_id: int | None = None,
    antes: Any = None,
    despues: Any = None,
    detalle: str | None = None,
    resultado: str = "exito",
    peticion=None,
    carrera_id: int | None = None,
    sede_id: int | None = None,
    comision_id: int | None = None,
    materia_id: int | None = None,
) -> dict | None:
    """Anota un evento. Es lo único que un módulo necesita saber de todo esto.

    `quien` puede ser la persona entera o su id. El **rol queda congelado**: se
    guarda el que tenía al hacerlo, no el que tenga cuando alguien lea el
    registro, porque si no un cambio de rol reescribiría el pasado.

    `antes` y `despues` son lo que pide el pliego: al modificar algo hay que
    poder ver qué valor tenía y cuál quedó.
    """
    if accion not in ACCIONES or modulo not in MODULOS:
        # Un módulo nuevo tiene que sumarse al vocabulario, no inventar el
        # suyo. Igual se anota: perder el evento sería peor.
        accion = accion if accion in ACCIONES else "edicion"
        modulo = modulo if modulo in MODULOS else "usuarios"

    persona = quien if isinstance(quien, dict) else d.buscar_persona(quien)

    evento = {
        "id": d.nuevo_id_auditoria(),
        "cuando": d.iso(d.ahora()),
        "quienId": persona["id"] if persona else None,
        "quien": persona["nombre"] if persona else "Alguien sin identificar",
        "rol": d.rol_principal(persona) if persona else None,
        "roles": d.roles_de(persona) if persona else [],
        "accion": accion,
        "modulo": modulo,
        "elemento": _limpiar(elemento),
        "elementoId": elemento_id,
        "elementoTipo": elemento_tipo,
        "personaId": persona_id,
        "antes": _limpiar(antes),
        "despues": _limpiar(despues),
        "detalle": _limpiar(detalle),
        "resultado": resultado if resultado in RESULTADOS else "exito",
        "ip": ip_de(peticion),
        # El alcance: con esto el supervisor filtra por su ámbito y el docente
        # ve lo de sus materias sin que haya que adivinarlo después.
        "carreraId": carrera_id,
        "sedeId": sede_id,
        "comisionId": comision_id,
        "materiaId": materia_id,
    }

    if _repetido(evento):
        return None

    d.auditoria.append(evento)
    return evento


def _repetido(evento: dict) -> bool:
    """Un doble clic no son dos cambios.

    Se miran los últimos eventos y se descarta el que sea igual en todo lo que
    importa y haya pasado hace menos de dos segundos.
    """
    ahora = d.desde_iso(evento["cuando"])
    claves = (
        "quienId", "accion", "modulo", "elementoId", "elementoTipo",
        "personaId", "resultado",
    )
    for previo in reversed(d.auditoria[-40:]):
        if (ahora - d.desde_iso(previo["cuando"])).total_seconds() > VENTANA_REPETIDO:
            break
        if all(previo.get(k) == evento.get(k) for k in claves):
            if previo.get("antes") == evento.get("antes") and previo.get(
                "despues"
            ) == evento.get("despues"):
                return True
    return False


# ===================== Consulta =====================
def _texto_de(evento: dict) -> str:
    """Todo lo que tiene sentido buscar por palabra suelta."""
    return _sin_tildes(
        " ".join(
            str(x)
            for x in (
                evento.get("quien"),
                evento.get("elemento"),
                evento.get("detalle"),
                evento.get("antes"),
                evento.get("despues"),
                ACCIONES.get(evento["accion"]),
                MODULOS.get(evento["modulo"]),
            )
            if x is not None
        )
    )


def buscar(filtros: dict, permitidos: set[str] | None = None) -> list[dict]:
    """Los eventos que coinciden, del más nuevo al más viejo.

    `permitidos` recorta por módulo según el rol de quien consulta; `None`
    quiere decir todos.
    """
    q = _sin_tildes(filtros.get("q"))
    desde = filtros.get("desde")
    hasta = filtros.get("hasta")

    def entero(clave):
        try:
            return int(filtros[clave]) if filtros.get(clave) else None
        except (TypeError, ValueError):
            return None

    usuario_id = entero("usuarioId")
    carrera_id = entero("carreraId")
    sede_id = entero("sedeId")
    comision_id = entero("comisionId")
    materia_id = entero("materiaId")
    persona_id = entero("personaId")

    salida = []
    for e in d.auditoria:
        if permitidos is not None and e["modulo"] not in permitidos:
            continue
        if usuario_id and e.get("quienId") != usuario_id:
            continue
        if persona_id and e.get("personaId") != persona_id:
            continue
        if filtros.get("rol") and filtros["rol"] not in (e.get("roles") or []):
            continue
        if filtros.get("accion") and e["accion"] != filtros["accion"]:
            continue
        if filtros.get("modulo") and e["modulo"] != filtros["modulo"]:
            continue
        if filtros.get("resultado") and e["resultado"] != filtros["resultado"]:
            continue
        if carrera_id and e.get("carreraId") != carrera_id:
            continue
        if sede_id and e.get("sedeId") != sede_id:
            continue
        if comision_id and e.get("comisionId") != comision_id:
            continue
        if materia_id and e.get("materiaId") != materia_id:
            continue
        # Las fechas se comparan como texto ISO: "2026-11-14" ordena igual que
        # la fecha, y así "hasta" incluye todo el día sin tener que sumarle uno.
        if desde and e["cuando"][:10] < desde:
            continue
        if hasta and e["cuando"][:10] > hasta:
            continue
        if q and q not in _texto_de(e):
            continue
        salida.append(e)

    salida.sort(key=lambda e: e["cuando"], reverse=True)
    return salida


def resumir(eventos: list[dict]) -> dict:
    """Los números de arriba de la pantalla, sobre lo que se está mirando."""
    hoy = d.iso(d.ahora())[:10]
    administrativas = {"roles", "estado", "baja", "asignacion", "reasignacion"}
    return {
        "total": len(eventos),
        "hoy": sum(1 for e in eventos if e["cuando"][:10] == hoy),
        "modificaciones": sum(1 for e in eventos if e["accion"] == "edicion"),
        "administrativas": sum(1 for e in eventos if e["accion"] in administrativas),
        "fallidas": sum(1 for e in eventos if e["resultado"] == "fallo"),
    }


def con_nombres(evento: dict) -> dict:
    """El evento como se muestra: las claves resueltas a texto legible."""
    carrera = d.buscar_en(d.carreras_institucion, evento.get("carreraId"))
    sede = d.buscar_en(d.sedes, evento.get("sedeId"))
    comision = d.buscar_en(d.comisiones, evento.get("comisionId"))
    materia = d.buscar_en(d.materias_plan, evento.get("materiaId"))
    afectada = d.buscar_persona(evento.get("personaId"))

    return {
        **evento,
        "nombreAccion": ACCIONES.get(evento["accion"], evento["accion"]),
        "nombreModulo": MODULOS.get(evento["modulo"], evento["modulo"]),
        "nombreResultado": RESULTADOS.get(evento["resultado"], evento["resultado"]),
        "afectada": afectada["nombre"] if afectada else None,
        "carrera": carrera["nombre"] if carrera else None,
        "sede": sede["nombre"] if sede else None,
        "comision": comision["nombre"] if comision else None,
        "materia": materia["nombre"] if materia else None,
    }
