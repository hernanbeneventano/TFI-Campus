"""El juego de datos con el que corren las pruebas.

Las pruebas **no usan los datos que trae la aplicación**, y eso es a
propósito. El campus arranca vacío: sin estudiantes inscriptos, sin módulos,
sin mesas de examen. Es lo correcto para una instalación nueva, pero deja a
las pruebas sin nada sobre lo que comprobar nada.

Antes las suites se apoyaban en los datos de ejemplo que venían en
`datos_iniciales.json`. Al vaciarlos, las cuatro se cayeron de golpe: no
porque el campus estuviera roto, sino porque habían perdido su escenario. Un
juego de pruebas que depende de lo que la aplicación muestre se rompe cada
vez que cambian los datos de muestra, que es justamente lo que pasó.

Ahora el escenario vive acá, en `datos_de_prueba.json`, y es de las pruebas.
Tiene un campus poblado: diecinueve personas, seis módulos con contenido, diez
mesas de examen en todos sus estados, asistencias, notas e inscripciones.

`cargar()` lo mete en memoria **en el proceso de la prueba**, reemplazando lo
que haya. No toca ningún archivo: el campus de verdad sigue vacío.

Cargar dos veces tiene que dar lo mismo
=======================================
**Antes no pasaba.** `cargar()` adivinaba en qué atributo de `datos.py` iba
cada clave, pasando el nombre de camelCase a snake_case. Funcionaba con 58 de
las 61 claves y fallaba en silencio con las otras tres, porque `carreras`
quiere decir dos cosas:

    clave JSON          datos.py la pone en      la conversión la mandaba a
    ----------------    ---------------------    --------------------------
    carreras            carreras_institucion     carreras        ← los nombres
    carrerasNombres     carreras                 carreras_nombres ← no existe

Los objetos de carrera terminaban en la lista que debía tener nombres, los
nombres se perdían, y `carreras_institucion` no se tocaba nunca: las pruebas
corrían con las carreras de `datos_iniciales.json`, no con las del escenario.

Y había más que no se reponía: lo que `datos.py` arma en código y no lee del
JSON —`archivos_subidos`, `cierres_cursada`, los bytes de `_archivos` y los
contadores de `_proximos`—, más `favoritos_modulo`, que es posterior al
escenario. Se vio en el banco de comparación: el mismo `POST` a
`/institucion/carreras` daba 201 y después 409, porque la carrera de la
primera vez seguía ahí.

No se notaba porque cada suite corre en su propio proceso y carga una sola
vez. Con dos cargas en el mismo proceso, la segunda arrancaba sucia.

Cómo se arregló: dejar de adivinar
----------------------------------
El mapa clave → atributo **se lee de `datos.py`**, de sus propias líneas
`nombre = _iniciales["clave"]`. Lo mismo los valores de arranque de lo que se
arma en código: son literales en el fuente (`archivos_subidos = []`), y se
leen de ahí. No hay ninguna lista a mano que pueda quedar desactualizada: si
alguien agrega una colección a `datos.py`, el escenario la conoce sola.

Y el escenario **tiene que estar completo**. Si trae una clave que
`datos.py` no lee, o le falta una que sí lee, `cargar()` corta con un error
que dice cuál. Es a propósito: el bug de arriba fue exactamente una clave que
iba a parar a ningún lado sin que nada fallara.

Las fechas
----------
El escenario usa fechas relativas (`{"__fecha": "haceHoras", "n": 3}`) para
seguir teniendo sentido con el correr de los meses. `haceHoras` se resuelve
al milisegundo, así que resolverlo en cada carga haría que dos cargas
seguidas difirieran. Se resuelve **una vez por proceso** y cada carga usa una
copia: el escenario es una foto fija, con las fechas contadas desde que
arrancó la corrida.
"""

from __future__ import annotations

import ast
import copy
import io
import json
from pathlib import Path
from typing import Any

from app import datos as d
from app.servicios import autenticacion, frenos, persistencia

ARCHIVO = Path(__file__).resolve().parent / "datos_de_prueba.json"
DATOS_PY = Path(d.__file__)


# ===================== Lo que dice datos.py =====================
def _leer_datos_py() -> tuple[dict[str, str], dict[str, Any]]:
    """De `datos.py`: qué clave del JSON va a cada atributo, y con qué valor
    arranca lo que se arma en código.

    Se lee el fuente con `ast` en vez de copiar la lista acá. Así el escenario
    usa **la misma regla que la aplicación** y no puede desfasarse de ella.
    """
    arbol = ast.parse(DATOS_PY.read_text(encoding="utf-8"))
    mapa: dict[str, str] = {}
    armado_en_codigo: dict[str, Any] = {}

    for nodo in arbol.body:
        if isinstance(nodo, ast.AnnAssign):
            destino, valor = nodo.target, nodo.value
        elif isinstance(nodo, ast.Assign) and len(nodo.targets) == 1:
            destino, valor = nodo.targets[0], nodo.value
        else:
            continue
        if not isinstance(destino, ast.Name) or valor is None:
            continue

        claves = [
            sub.slice.value
            for sub in ast.walk(valor)
            if isinstance(sub, ast.Subscript)
            and isinstance(sub.value, ast.Name)
            and sub.value.id == "_iniciales"
            and isinstance(sub.slice, ast.Constant)
        ]
        if claves:
            for clave in claves:
                mapa[clave] = destino.id
        elif isinstance(valor, (ast.List, ast.Dict, ast.Set)):
            # Un contenedor escrito en el fuente: es estado que el campus va
            # llenando, y arranca con este valor.
            armado_en_codigo[destino.id] = ast.literal_eval(valor)

    return mapa, armado_en_codigo


MAPA, ARMADO_EN_CODIGO = _leer_datos_py()


# ===================== El escenario, resuelto una vez =====================
_resuelto: dict | None = None


def _escenario() -> dict:
    """Una copia del escenario con las fechas ya resueltas.

    Se resuelve la primera vez y se reutiliza: ver «Las fechas» arriba.
    """
    global _resuelto
    if _resuelto is None:
        crudo = json.loads(io.open(ARCHIVO, encoding="utf-8").read())
        _resuelto = d._resolver(crudo)
    return copy.deepcopy(_resuelto)


# ===================== Cargar =====================
def cargar() -> None:
    """Deja el campus exactamente como lo describe el escenario.

    Da lo mismo desde un proceso recién arrancado que después de cien
    peticiones: todo lo que el campus guarda en memoria vuelve a un valor
    conocido.
    """
    aplicar(_escenario())


def aplicar(escenario: dict[str, Any]) -> None:
    """Pone en memoria un escenario ya resuelto. Está aparte para poder
    probar qué pasa con uno mal armado."""
    _validar(escenario)

    # 1. Lo que viene del JSON, cada clave a su atributo de verdad
    for clave, valor in escenario.items():
        _poner(MAPA[clave], valor)

    # 2. Lo que datos.py arma en código, a su valor de arranque
    for nombre, inicial in ARMADO_EN_CODIGO.items():
        _poner(nombre, copy.deepcopy(inicial))

    # 3. Los contadores, por encima del identificador más alto. Es la misma
    #    función que usa el campus al cargar de Firestore: una alta nueva
    #    nunca pisa algo que ya está.
    persistencia._ajustar_contadores()

    # 4. Lo que el proceso recuerda entre una petición y otra y que cambia
    #    lo que contesta: el freno de peticiones por minuto, y cuándo se anotó
    #    el último ingreso de cada uno —si queda, el próximo no se anota y el
    #    registro de auditoría sale distinto—.
    #
    #    Lo que **no** se toca, a propósito: a quién está suplantando la
    #    prueba (lo decide la prueba, no el escenario), la caché de catálogos
    #    externos (no es dato del campus) y las huellas de la persistencia
    #    (solo existen con Firestore encendido, y las pruebas no lo encienden).
    frenos.olvidar_todo()
    autenticacion._ultimo_ingreso.clear()


def _validar(escenario: dict[str, Any]) -> None:
    """El escenario tiene que nombrar exactamente lo que datos.py lee."""
    desconocidas = sorted(set(escenario) - set(MAPA))
    faltantes = sorted(set(MAPA) - set(escenario))
    if not (desconocidas or faltantes):
        return

    partes = []
    if desconocidas:
        partes.append(
            f"trae claves que datos.py no lee —se perderían sin aviso—: {desconocidas}"
        )
    if faltantes:
        partes.append(
            f"le faltan claves que datos.py sí lee —quedarían con lo que hubiera—: "
            f"{faltantes}"
        )
    raise ValueError("El escenario de prueba " + "; ".join(partes))


def _poner(nombre: str, valor: Any) -> None:
    """Reemplaza **el contenido**, no la variable.

    Los módulos del campus hicieron `from .. import datos as d` y guardaron
    la referencia, así que cambiar `d.personas = [...]` no los alcanzaría.
    """
    actual = getattr(d, nombre, None)
    if isinstance(actual, list) and isinstance(valor, list):
        actual[:] = valor
    elif isinstance(actual, dict) and isinstance(valor, dict):
        actual.clear()
        # Las claves numéricas vuelven a ser números: en JSON son texto, y
        # `contenidos`, `anuncios` y `participantes` se buscan por el id del
        # módulo, que es un entero. Sin esto el escenario cargaba las
        # carpetas con la clave "1" y `contenidos.get(1)` no encontraba nada.
        actual.update({_como_clave(k): v for k, v in valor.items()})
    elif isinstance(actual, set) and isinstance(valor, (set, list)):
        actual.clear()
        actual.update(valor)
    else:
        # Un escalar, o un atributo de otro tipo. Antes no había este caso y
        # cualquier cosa que no fuera lista ni diccionario se salteaba sin
        # avisar; hoy datos.py no lee ningún escalar, pero el día que lea uno
        # tiene que cargarse igual.
        setattr(d, nombre, valor)


def _como_clave(clave):
    """"12" vuelve a ser 12; "minimoPorDefecto" se queda como está."""
    if isinstance(clave, str) and clave.lstrip("-").isdigit():
        return int(clave)
    return clave
