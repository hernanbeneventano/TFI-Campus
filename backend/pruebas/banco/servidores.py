"""Las dos aplicaciones que el banco compara.

**No se levantan dos servidores.** Se cargan las dos aplicaciones en el mismo
proceso y se las maneja con su cliente en proceso. Tres motivos:

1. **No hay puertos que choquen** ni que haya que esperar a que abran, ni un
   servidor que quede colgado si el banco se corta por la mitad.
2. **La identidad funciona.** Las dos llaman a `servicios/autenticacion.py`,
   así que `actuar_como()` —lo del paso 1— sirve para las dos. Por HTTP
   habría que inventar un token de verdad por cada persona del escenario, o
   agregarle al campus una cabecera que permita suplantar a cualquiera, que
   es exactamente el agujero que no queremos.
3. **Se puede comparar lo que cada una guardó**, no solo lo que contestó. Las
   dos trabajan sobre la misma memoria de `datos.py`, así que el banco puede
   reponerla entre una y otra y mirar en qué quedó. Dos aplicaciones que
   contestan igual y escriben distinto es un error que no se ve desde afuera.

Lo que esto no prueba
---------------------
Que el servidor de verdad las sirva igual: el encolado, los tiempos de
espera, la configuración del proceso. Eso es despliegue, y va aparte.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Aplicacion:
    nombre: str
    cliente: Any
    rutas: list[tuple[str, str]]


def fastapi() -> Aplicacion:
    """La de hoy, que es la referencia: lo que ella conteste es lo correcto."""
    from fastapi.testclient import TestClient

    from app.main import app

    rutas = sorted(
        {
            (metodo, r.path)
            for r in app.routes
            if hasattr(r, "methods")
            for metodo in r.methods - {"HEAD", "OPTIONS"}
            if r.path.startswith("/api")
        }
    )
    return Aplicacion("FastAPI", TestClient(app), rutas)


def despachador() -> Aplicacion:
    """El servidor tal como corre de verdad: el despachador del frente.

    Es la comparación que importa mientras dure la migración. Contra FastAPI
    tiene que dar **cero diferencias** en todo momento: lo que esté migrado lo
    contesta Django y lo que no, FastAPI, y el que pide no tiene que poder
    notarlo. En la fase 0 no hay nada migrado, así que prueba que el
    despachador es un pasamanos de verdad.

    El cliente se arma **sin `with`**, a propósito: con `with` se dispararía el
    `lifespan`, que conecta Firestore y R2 de verdad. El banco trabaja solo
    sobre la memoria.
    """
    from fastapi.testclient import TestClient

    import despachador as modulo

    base = fastapi()
    return Aplicacion("despachador", TestClient(modulo.aplicacion), base.rutas)


def django() -> Aplicacion:
    """Django solo, con la pila de FastAPI alrededor.

    Contesta únicamente lo que esté en `campus_django/urls.py`; lo demás es
    un 404. En la fase 0 no hay nada, así que contra FastAPI da diferencias
    en todo: es la forma de ver cuánto falta, módulo por módulo, con
    `--solo`. La comparación que tiene que dar cero es la del despachador.
    """
    from fastapi.testclient import TestClient

    import despachador as modulo

    base = fastapi()
    return Aplicacion("Django", TestClient(modulo.django()), base.rutas)


DISPONIBLES: dict[str, Callable[[], Aplicacion]] = {
    "fastapi": fastapi,
    "despachador": despachador,
    "django": django,
}
