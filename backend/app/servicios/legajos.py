"""El legajo: el número con el que la facultad identifica a una persona.

Por qué se genera solo
----------------------
Escribirlo a mano no escala y no es seguro: dos personas con el mismo legajo
son dos legajos que dejan de identificar a nadie, y el que carga no tiene cómo
saber cuál fue el último. Es un contador, y los contadores los lleva el
sistema.

Uno por carrera, no uno para todo el campus
-------------------------------------------
**El legajo pertenece a la carrera.** El 42 de Sistemas y el 42 de Matemática
son dos personas distintas, y así funciona en la facultad: cada carrera lleva
su propia numeración. Por eso el prefijo sale del código de la carrera y el
número se cuenta **dentro de esa carrera**.

    SIS-2026-0042
    │   │    └── el número dentro de esa carrera, con cuatro dígitos
    │   └── el año de ingreso: dos personas del mismo número en años
    │       distintos siguen siendo distinguibles
    └── el código de la carrera

El año va adentro a propósito. Sin él, el contador tendría que ser eterno y
un legajo no diría cuándo entró esa persona, que es lo primero que se mira en
un expediente.

Los docentes también tienen legajo
----------------------------------
No cursan ninguna carrera, así que no entran en esa numeración, pero la
facultad igual necesita identificarlos: en un acta, en una planilla de
asistencia o en el registro de auditoría, "María Gómez" no alcanza y el correo
no es un identificador institucional. Llevan un legajo **del campus**, con su
propio prefijo, y se les asigna solo al darlos de alta.
"""

from __future__ import annotations

import os
import re

from .. import datos as d

# El prefijo de los legajos del personal. Configurable porque cada facultad
# usa el suyo, y cambiarlo no puede implicar tocar el código.
PREFIJO_PERSONAL = (os.environ.get("PREFIJO_LEGAJO_PERSONAL") or "FAC").upper()

DIGITOS = 4

# Quiénes llevan legajo del campus en vez de legajo de carrera.
ROLES_CON_LEGAJO = ("Docente", "Administrador", "Supervisor")


def _prefijo_de_carrera(carrera: dict | None) -> str:
    """El código de la carrera, o unas siglas armadas con su nombre.

    Una carrera sin código no puede quedarse sin legajos: se arma algo
    estable a partir del nombre, que es mejor que un prefijo vacío.
    """
    if not carrera:
        return "GEN"
    codigo = (carrera.get("codigo") or "").strip().upper()
    if codigo:
        return re.sub(r"[^A-Z0-9]", "", codigo)[:6] or "GEN"

    iniciales = "".join(p[0] for p in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", carrera.get("nombre") or ""))
    return (iniciales[:3] or "GEN").upper()


def _numero(legajo: str | None, prefijo: str, anio: int) -> int:
    """El número de un legajo, si pertenece a ese prefijo y a ese año."""
    if not legajo:
        return 0
    partes = str(legajo).strip().upper().split("-")
    if len(partes) != 3 or partes[0] != prefijo or partes[1] != str(anio):
        return 0
    try:
        return int(partes[2])
    except ValueError:
        return 0


def _armar(prefijo: str, anio: int, numero: int) -> str:
    return f"{prefijo}-{anio}-{numero:0{DIGITOS}d}"


def proximo_de_carrera(carrera_id, anio: int) -> str:
    """El siguiente legajo libre de esa carrera para ese año de ingreso.

    Se cuenta sobre los que ya existen y no sobre cuántos son: si alguien se
    dio de baja, su número no se reutiliza. Un legajo reutilizado apunta a dos
    expedientes distintos.
    """
    carrera = d.buscar_en(d.carreras_institucion, carrera_id)
    prefijo = _prefijo_de_carrera(carrera)

    usados = [
        _numero(a.get("legajo"), prefijo, anio)
        for a in d.asociaciones_academicas
        if a.get("carreraId") == (carrera["id"] if carrera else carrera_id)
    ]
    return _armar(prefijo, anio, max(usados, default=0) + 1)


def proximo_institucional(anio: int) -> str:
    """El siguiente legajo del personal para ese año."""
    usados = [_numero(p.get("legajo"), PREFIJO_PERSONAL, anio) for p in d.personas]
    return _armar(PREFIJO_PERSONAL, anio, max(usados, default=0) + 1)


def asegurar_institucional(persona: dict) -> str | None:
    """Le pone legajo del campus si le corresponde y no tiene.

    Devuelve el legajo, o `None` si esa persona no lleva uno: un estudiante
    tiene el de su carrera y darle además uno del campus sería un segundo
    número para la misma persona.
    """
    if persona.get("legajo"):
        return persona["legajo"]
    if not d.tiene_rol(persona, *ROLES_CON_LEGAJO):
        return None

    persona["legajo"] = proximo_institucional(d.ahora().year)
    return persona["legajo"]
