"""Sube a Firestore la estructura académica de `datos_iniciales.json`.

**Es opcional y se corre a mano.** El servidor no lo hace solo, a propósito:
las carreras, sedes, planes, comisiones y materias que trae ese archivo son
un juego de ejemplo para desarrollar, y subirlas solas las convertiría en el
plan de estudios de la facultad sin que nadie lo decidiera. Después nadie
sabría cuáles son de verdad.

Sirve para dos cosas:

- **Seguir probando** con el campus que ya venías usando, ahora persistido.
- **Arrancar de un plan ya armado** si esas carreras y materias son las que
  la facultad va a usar de verdad.

Si la facultad va a cargar su propio plan desde Administración, no hace falta
correrlo: dejá las colecciones vacías.

Uso (desde backend/, con el servidor apagado):
    python -m app.importar_estructura           # muestra qué haría
    python -m app.importar_estructura --subir   # lo sube
"""

from __future__ import annotations

import sys

from .servicios import certificados

certificados.configurar()

from . import datos as d  # noqa: E402
from .servicios import firestore as fs  # noqa: E402
from .servicios import persistencia as p  # noqa: E402


def resumen() -> list[tuple[str, int]]:
    return [
        (atributo, len(getattr(d, atributo)))
        for atributo in p.INSTITUCIONALES
    ]


def main() -> None:
    subir = "--subir" in sys.argv

    print("Estructura académica en datos_iniciales.json:\n")
    for atributo, cuantos in resumen():
        print(f"  {atributo:24} {cuantos}")

    if not subir:
        print(
            "\nNo se subió nada. Para hacerlo:"
            "\n    python -m app.importar_estructura --subir"
        )
        return

    fs.inicializar_firestore()
    cliente = fs.obtener_firestore()

    # Si ya hay estructura cargada no se pisa: sería duplicar el plan o,
    # peor, reemplazar el de la facultad por el de ejemplo.
    for coleccion in ("carreras", "sedes", "planesEstudio", "comisiones", "materiasPlan", "dictados"):
        if list(cliente.collection(coleccion).limit(1).stream()):
            print(
                f"\nFirestore ya tiene «{coleccion}» cargada. No se sube nada:"
                "\nborrala desde Administración si querés reemplazarla."
            )
            return

    escritos = 0
    for coleccion, (atributo, clave) in p.REGISTROS.items():
        if atributo not in p.INSTITUCIONALES:
            continue
        for item in getattr(d, atributo):
            cliente.collection(coleccion).document(clave(item)).set(item)
            escritos += 1

    # Los contadores tienen que quedar por encima de lo que se acaba de subir,
    # o la próxima alta pisaría una materia existente.
    p._ajustar_contadores()
    cliente.collection(p.CONFIGURACION_COL).document(p.CONTADORES).set(dict(d._proximos))

    print(f"\nSubidos {escritos} documentos. Reiniciá el servidor para que los tome.")


if __name__ == "__main__":
    main()
