"""La aplicación que el banco compara.

**No se levanta un servidor.** Se carga la aplicación en el mismo proceso y se
la maneja con su cliente en proceso (`pruebas/cliente.py`). Tres motivos:

1. **No hay puertos que choquen** ni que haya que esperar a que abran, ni un
   servidor que quede colgado si el banco se corta por la mitad.
2. **La identidad funciona.** `actuar_como()` sirve sin inventar un token de
   verdad por cada persona del escenario, ni agregarle al campus una cabecera
   que permita suplantar a cualquiera, que es exactamente el agujero que no
   queremos.
3. **Se puede comparar lo que guardó**, no solo lo que contestó: el banco
   repone la memoria de `datos.py` entre caso y caso y mira en qué quedó.

Contra qué se compara
---------------------
Durante la migración se comparaban dos aplicaciones vivas: FastAPI, que era
la referencia, contra Django. FastAPI ya no está: lo que contestaba y lo que
guardaba quedó **grabado** (`grabaciones/fastapi.json.gz`) y Django se compara
contra esa grabación.

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


def rutas_del_campus() -> list[tuple[str, str]]:
    """(método, camino) de cada ruta de la interfaz, como se anotaron."""
    from app.main import todas_las_rutas

    return sorted({(r.metodo, r.camino) for r in todas_las_rutas() if r.camino.startswith("/api")})


def django() -> Aplicacion:
    """El campus tal como corre de verdad: Django con todas sus capas."""
    from ..cliente import crear_cliente

    return Aplicacion("Django", crear_cliente(), rutas_del_campus())


DISPONIBLES: dict[str, Callable[[], Aplicacion]] = {
    "django": django,
}
