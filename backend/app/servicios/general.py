"""Lo que pide la pantalla en todos lados: quién soy y las campanitas.

Vive acá y no en `main.py` para que FastAPI y Django contesten **con la misma
función** mientras dure la migración: cada framework solo la llama.
"""

from __future__ import annotations

from .. import datos as d


def yo_mismo(persona: dict) -> dict:
    """El usuario que inició sesión, como lo muestra el menú.

    Sale del token de Firebase que manda el navegador.

    Si no llega token y está permitido el usuario de prueba, devuelve ese.
    """
    nombre = persona.get("nombre", "")
    primero, _, resto = nombre.partition(" ")
    return d.con_presencia(
        {
            **persona,
            # El menú lateral muestra el nombre partido
            "nombre": primero,
            "apellido": resto,
            # La foto la pone `con_presencia`, que la firma a partir de la
            # clave del archivo. Ponerla también acá la firmaba sobre el
            # diccionario ya modificado —es decir, sobre la dirección— y la
            # firma no validaba.
        }
    )


def contadores(persona: dict) -> dict:
    """Cuántas cosas nuevas hay en cada apartado, **para quien pregunta**.

    Contaba siempre sobre `d.usuario_actual`, el usuario de prueba: todos
    veían los mismos números y no eran los suyos. Es de lo poco que se mira
    en cada pantalla, así que equivocarse ahí se nota en todo el campus.
    """
    return d.resumen_de_novedades(persona["id"])

