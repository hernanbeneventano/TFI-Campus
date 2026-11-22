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


def django() -> Aplicacion:
    """La que todavía no existe."""
    raise NotImplementedError(
        "El backend en Django todavía no existe. El banco está listo para "
        "recibirlo: cuando esté, esta función tiene que devolver un cliente "
        "con la misma forma que el de FastAPI —.get/.post/.put/.patch/.delete "
        "y .request(metodo, camino, json=...)— y la lista de sus rutas."
    )


DISPONIBLES: dict[str, Callable[[], Aplicacion]] = {
    "fastapi": fastapi,
    "django": django,
}
