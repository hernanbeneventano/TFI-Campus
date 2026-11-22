"""Comparar dos respuestas por su estructura, no por su texto.

Comparar el JSON como cadena diría «son distintas» y nada más: habría que
leer las dos a ojo para encontrar qué cambió, y con respuestas de cien
campos eso no se hace. Acá se recorren las dos en paralelo y se devuelve una
lista de diferencias, cada una con el camino exacto y de qué tipo es.

Los cuatro tipos importan porque no significan lo mismo:

- **falta**  el campo está en la primera y no en la segunda. Es el error más
             común al migrar: una respuesta que se armó de nuevo y se olvidó
             un campo. La pantalla lo muestra vacío y nadie se entera.
- **sobra**  está en la segunda y no en la primera. Suele ser un campo
             interno que se escapó, y a veces es información que no tenía
             que salir.
- **tipo**   mismo campo, distinto tipo. `"7"` y `7` se ven iguales en el
             informe y rompen el frontend igual.
- **valor**  mismo tipo, distinto contenido.

El orden de las listas **sí** se compara: el campus ordena a propósito en
casi todos lados —las alertas por nivel, las mesas por fecha, los inscriptos
sin corregir primero— y perder ese orden es un error de verdad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FALTA = "falta"
SOBRA = "sobra"
TIPO = "tipo"
VALOR = "valor"

AUSENTE = object()


@dataclass
class Diferencia:
    camino: str
    clase: str
    a: Any = None
    b: Any = None

    def __str__(self) -> str:
        if self.clase == FALTA:
            return f"{self.camino}: falta en B (en A vale {_corto(self.a)})"
        if self.clase == SOBRA:
            return f"{self.camino}: sobra en B ({_corto(self.b)})"
        if self.clase == TIPO:
            return (
                f"{self.camino}: tipo {type(self.a).__name__} -> "
                f"{type(self.b).__name__}  ({_corto(self.a)} vs {_corto(self.b)})"
            )
        return f"{self.camino}: {_corto(self.a)} -> {_corto(self.b)}"


def _corto(valor: Any, tope: int = 70) -> str:
    texto = repr(valor)
    return texto if len(texto) <= tope else texto[: tope - 1] + "…"


def comparar(a: Any, b: Any, camino: str = "cuerpo") -> list[Diferencia]:
    """Todas las diferencias entre dos valores, con su camino."""
    salida: list[Diferencia] = []

    if a is AUSENTE:
        return [Diferencia(camino, SOBRA, b=b)]
    if b is AUSENTE:
        return [Diferencia(camino, FALTA, a=a)]

    # Los booleanos son enteros en Python: sin esto, True y 1 pasarían por
    # iguales y el frontend recibiría otra cosa.
    if type(a) is not type(b) and not (a is None and b is None):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))
                and not isinstance(a, bool) and not isinstance(b, bool)):
            return [Diferencia(camino, TIPO, a, b)]

    if isinstance(a, dict):
        for clave in a:
            salida += comparar(a[clave], b.get(clave, AUSENTE), f"{camino}.{clave}")
        for clave in b:
            if clave not in a:
                salida.append(Diferencia(f"{camino}.{clave}", SOBRA, b=b[clave]))
        return salida

    if isinstance(a, list):
        if len(a) != len(b):
            salida.append(
                Diferencia(f"{camino}.length", VALOR, len(a), len(b))
            )
        for i in range(min(len(a), len(b))):
            salida += comparar(a[i], b[i], f"{camino}[{i}]")
        return salida

    if a != b:
        salida.append(Diferencia(camino, VALOR, a, b))
    return salida


@dataclass
class Resultado:
    """Lo que dio comparar una petición en las dos aplicaciones."""

    nombre: str
    metodo: str
    camino: str
    estado_a: int | None = None
    estado_b: int | None = None
    diferencias: list[Diferencia] = field(default_factory=list)
    cabeceras: list[Diferencia] = field(default_factory=list)
    estado_campus: list[str] = field(default_factory=list)
    error_a: str | None = None
    error_b: str | None = None

    @property
    def coincide(self) -> bool:
        return not (
            self.diferencias
            or self.cabeceras
            or self.estado_campus
            or self.error_a
            or self.error_b
            or self.estado_a != self.estado_b
        )

    @property
    def solo_en_uno(self) -> bool:
        """Anduvo en una aplicación y se cayó en la otra."""
        return bool(self.error_a) != bool(self.error_b)
