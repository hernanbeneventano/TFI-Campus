"""¿El banco encuentra una diferencia cuando la hay?

Que FastAPI contra sí mismo dé cero prueba que el banco **no inventa**
diferencias. Falta la mitad que importa de verdad: que las **encuentre**. Un
comparador que siempre dice «todo igual» da cero igual que uno que funciona,
y es exactamente el que uno querría descubrir antes de migrar y no después.

Acá se compara el campus contra una copia a la que se le mete un defecto a
propósito, uno por vez, y se comprueba que el informe lo marque. Son los
cinco errores que una migración comete de verdad:

1. un campo que se perdió al rearmar la respuesta;
2. un campo de más que se escapó;
3. el mismo campo con otro tipo —`"7"` en vez de `7`— que se ve igual en
   pantalla y rompe el frontend;
4. otro código de estado, que es un permiso o una validación que cambió;
5. una cabecera que se perdió, como el `nosniff` de una descarga.

    python -m pruebas.banco --autoprueba
"""

from __future__ import annotations

from typing import Any

from app.servicios import frenos

from .. import escenario
from . import estado, servidores
from .casos import Caso, Paso, SECRETARIA


class _Respuesta:
    """Una respuesta con el defecto puesto, con la forma que usa el banco."""

    def __init__(self, status_code: int, cuerpo: Any, headers: dict):
        self.status_code = status_code
        self._cuerpo = cuerpo
        self.headers = headers
        self.text = str(cuerpo)
        self.content = b""

    def json(self):
        return self._cuerpo


class _ClienteConDefecto:
    """Envuelve al cliente de verdad y le aplica un defecto a la respuesta."""

    def __init__(self, cliente, defecto):
        self._cliente = cliente
        self._defecto = defecto

    def request(self, metodo, camino, **extra):
        real = self._cliente.request(metodo, camino, **extra)
        try:
            cuerpo = real.json()
        except ValueError:
            return real
        estado_http, cuerpo, cabeceras = self._defecto(
            real.status_code, cuerpo, dict(real.headers)
        )
        return _Respuesta(estado_http, cuerpo, cabeceras)


def _con_defecto(defecto) -> servidores.Aplicacion:
    base = servidores.django()
    return servidores.Aplicacion(
        "FastAPI con defecto", _ClienteConDefecto(base.cliente, defecto), base.rutas
    )


# ===================== Los cinco defectos =====================
def _falta_un_campo(estado_http, cuerpo, cabeceras):
    if isinstance(cuerpo, dict) and "estado" in cuerpo:
        cuerpo = {k: v for k, v in cuerpo.items() if k != "estado"}
    return estado_http, cuerpo, cabeceras


def _sobra_un_campo(estado_http, cuerpo, cabeceras):
    if isinstance(cuerpo, dict):
        cuerpo = {**cuerpo, "colado": "no debería estar"}
    return estado_http, cuerpo, cabeceras


def _cambia_el_tipo(estado_http, cuerpo, cabeceras):
    if isinstance(cuerpo, dict) and "estado" in cuerpo:
        cuerpo = {**cuerpo, "estado": 1}
    return estado_http, cuerpo, cabeceras


def _otro_estado(estado_http, cuerpo, cabeceras):
    return (403 if estado_http == 200 else estado_http), cuerpo, cabeceras


def _falta_una_cabecera(estado_http, cuerpo, cabeceras):
    return estado_http, cuerpo, {
        k: v for k, v in cabeceras.items() if k.lower() != "content-type"
    }


DEFECTOS = [
    ("un campo que se perdió", _falta_un_campo, "falta en B"),
    ("un campo de más", _sobra_un_campo, "sobra en B"),
    ("el mismo campo con otro tipo", _cambia_el_tipo, "tipo "),
    ("otro código de estado", _otro_estado, "ESTADO"),
    ("una cabecera que se perdió", _falta_una_cabecera, "cabeceras"),
]

CASO = Caso("salud", [Paso("GET", "/api/salud", SECRETARIA)])


def correr() -> int:
    from .__main__ import comparar_caso

    print("¿El banco encuentra una diferencia cuando la hay?\n")
    escenario.cargar()
    frenos.olvidar_todo()
    base = estado.tomar()
    a = servidores.django()

    fallas = 0
    for nombre, defecto, esperado in DEFECTOS:
        b = _con_defecto(defecto)
        resultados = comparar_caso(a, b, CASO, base)
        informe = " ".join(
            [str(d) for r in resultados for d in r.diferencias + r.cabeceras]
            + [f"ESTADO {r.estado_a} {r.estado_b}" for r in resultados
               if r.estado_a != r.estado_b]
        )
        encontrado = any(not r.coincide for r in resultados) and esperado in informe
        print(f"  {'ok   ' if encontrado else 'FALLA'}  {nombre}")
        if not encontrado:
            fallas += 1
            print(f"         esperaba «{esperado}» y el informe dijo: {informe[:160] or '(nada)'}")

    # Y que sin defecto siga dando cero: un comparador que marca todo
    # tampoco sirve.
    resultados = comparar_caso(a, servidores.django(), CASO, base)
    limpio = all(r.coincide for r in resultados)
    print(f"  {'ok   ' if limpio else 'FALLA'}  sin defecto, no inventa diferencias")
    if not limpio:
        fallas += 1

    print()
    print(f"{len(DEFECTOS) + 1 - fallas} de {len(DEFECTOS) + 1} comprobaciones")
    return 1 if fallas else 0
