"""El cliente con el que las pruebas le hablan al campus, y quién lo usa.

**Es el único archivo de `pruebas/` que sabe qué framework hay abajo.** Las
catorce suites piden el cliente acá y no lo arman por su cuenta, así que
cambiar de framework es cambiar este archivo y nada más.

Antes no era así: cada suite hacía

    app.dependency_overrides[identificar] = lambda: d.buscar_persona(...)
    app.dependency_overrides[identificar_id] = lambda: ...
    cliente = TestClient(app)

`dependency_overrides` es de FastAPI y no tiene equivalente en otros
frameworks, así que eran trece archivos atados al framework por el mecanismo
central de todas las pruebas: poder hacer la misma petición como distintas
personas. Ahora esa suplantación vive en `servicios/autenticacion.py`, en
Python a secas, y acá queda solo el cliente.

Qué necesita una suite de este archivo:

    from .cliente import como, crear_cliente

    cliente = crear_cliente()
    como(SANTIAGO)
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.servicios import autenticacion


def crear_cliente() -> TestClient:
    """Un cliente que le pega al campus sin levantar el servidor.

    En proceso a propósito: las pruebas también miran la memoria del servidor
    —`d.auditoria`, `d.personas`— para comprobar que lo que devuelve una ruta
    es lo que de verdad quedó guardado.
    """
    return TestClient(app)


def como(persona_id: int | None) -> None:
    """Las siguientes peticiones las hace esa persona.

    Es lo que reemplaza a `dependency_overrides`: `identificar` lo consulta
    antes de mirar el token, así que no hace falta Firebase ni una sesión de
    verdad para probar quién ve qué.
    """
    autenticacion.actuar_como(persona_id)


def sin_suplantar() -> None:
    """Vuelve a la verificación de siempre.

    Cada suite corre en su propio proceso, así que en la práctica no hace
    falta limpiar; está para la prueba que comprueba que la costura arranca
    apagada.
    """
    autenticacion.actuar_como(None)
