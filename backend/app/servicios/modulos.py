"""El módulo de una materia: cuándo existe y quién lo ve.

Una **materia del plan** y un **módulo** no son lo mismo. La materia es lo que
dice el plan de estudios y existe siempre; el módulo es la cursada de este
cuatrimestre, con su contenido, sus anuncios y su gente.

El módulo aparece cuando hay alguien del otro lado:

- la cátedra, apenas el administrador le asigna la materia a un docente;
- o el primer estudiante que se inscribe.

Antes solo pasaba lo segundo, y entonces un docente con materias asignadas
entraba a Módulos y no veía nada: el módulo todavía no se había creado porque
nadie se había anotado. Es al revés de como se usa — el docente arma el
contenido **antes** de que llegue el primer alumno.

Este servicio existe para que las dos rutas que lo necesitan —inscripciones y
cursos— creen el módulo de la misma manera, en vez de tener cada una su copia.
"""

from __future__ import annotations

import threading

from .. import datos as d

# Los colores de la banda de cada módulo. Son tonos de la misma familia y
# todos tienen contraste suficiente con el texto blanco encima.
COLORES = ["#2E4057", "#8A1C3B", "#3F5E7A", "#6B2E4A", "#44506B", "#A4193D"]

ORDINAL = {1: "1.er", 2: "2.º"}


def periodo_de(materia: dict) -> str:
    """"2026 – 1.er cuatrimestre", con el mismo formato que los módulos."""
    anio = d.ahora().year
    return f"{anio} – {ORDINAL.get(materia.get('cuatrimestre'), '1.er')} cuatrimestre"


# ===================== De a uno =====================
# `modulo_para` es el único lugar del campus que crea módulos, y se llama
# desde cinco caminos: el docente y la secretaría al abrir Módulos, el
# alumno al abrirla o al inscribirse, y la institución al ponerlo en una
# comisión. Varios corren a la vez todo el tiempo —el menú lateral y la
# grilla piden la lista al mismo tiempo al entrar—, y «¿ya tiene módulo? → no
# → crearlo» hecho por dos peticiones juntas creaba dos módulos para la misma
# materia, muchas veces con el mismo id (`pruebas/concurrencia.py`).
#
# El candado cubre exactamente eso: volver a mirar, armar el módulo y
# anotarlo en la materia. Todo en memoria, sin red ni esperas, y sin tomar
# ningún otro candado adentro. El camino de siempre —el módulo ya existe—
# ni siquiera lo toca.
_creando = threading.Lock()


def modulo_para(materia: dict, por_inscripcion: bool = False) -> dict:
    """El módulo de esa materia. Si no existe, se crea.

    `por_inscripcion` marca los que creó un alumno al anotarse, que son los
    únicos que se dan de baja si se arrepiente: el de una cátedra se queda,
    porque el docente puede haber cargado contenido.
    """
    existente = d.buscar_curso(materia.get("cursoId"))
    if existente:
        return existente

    with _creando:
        # Se vuelve a mirar adentro: otra petición pudo haberlo creado entre
        # la primera mirada y el candado.
        existente = d.buscar_curso(materia.get("cursoId"))
        if existente:
            return existente
        return _crear(materia, por_inscripcion)


def _crear(materia: dict, por_inscripcion: bool) -> dict:
    """Arma el módulo y lo anota. Solo se llama con `_creando` tomado."""
    docentes = d.docentes_de_materia(materia["id"])
    docente = d.buscar_persona(docentes[0]) if docentes else None

    nuevo = {
        "id": max((c["id"] for c in d.cursos), default=0) + 1,
        "codigo": materia["codigo"],
        "nombre": materia["nombre"],
        "docente": docente["nombre"] if docente else "Sin asignar",
        "docenteId": docentes[0] if docentes else None,
        "periodo": periodo_de(materia),
        "color": COLORES[materia["id"] % len(COLORES)],
        "creadoPorInscripcion": por_inscripcion,
    }
    d.cursos.append(nuevo)
    materia["cursoId"] = nuevo["id"]
    return nuevo


def sincronizar_docente(materia: dict) -> dict | None:
    """Pone en el módulo el docente que dice el dictado.

    Hace falta porque son dos registros: el **dictado** dice quién da la
    materia en una comisión, y el **módulo** guarda su docente a cargo para
    la pantalla y para los permisos. Si solo se cambiaba el dictado, el módulo
    se quedaba con el docente anterior: quien dejó la materia la seguía viendo
    y quien la tomó no la veía aparecer.

    Se llama al configurar o quitar un dictado, que son los dos únicos lugares
    donde eso cambia.
    """
    modulo = d.buscar_curso(materia.get("cursoId"))
    if not modulo:
        return None

    docentes = d.docentes_de_materia(materia["id"])
    nuevo = docentes[0] if docentes else None
    persona = d.buscar_persona(nuevo)

    modulo["docenteId"] = nuevo
    modulo["docente"] = persona["nombre"] if persona else "Sin asignar"
    return modulo


def modulos_que_dicta(persona_id: int) -> list[dict]:
    """Los módulos de las materias que esa persona tiene asignadas.

    **Los crea si todavía no existen.** Esa es la parte que importa: el
    docente tiene que poder entrar a su materia y empezar a cargar contenido
    el día que se la asignan, no el día que se anota el primer alumno.

    De paso deja el docente del módulo al día con el dictado: un módulo que
    creó un alumno al inscribirse pudo haber nacido sin nadie a cargo.
    """
    salida = []
    for materia in d.materias_que_dicta(persona_id):
        modulo_para(materia)
        modulo = sincronizar_docente(materia)
        if modulo:
            salida.append(modulo)
    return salida


def modulos_en_los_que_cursa(persona_id: int) -> list[dict]:
    """Los módulos de las materias a las que el estudiante está inscripto.

    **Los crea si todavía no existen**, igual que `modulos_que_dicta` con los
    del docente, y por el mismo motivo: estar inscripto y no tener dónde
    cursar es el peor estado posible, porque todo parece andar menos lo único
    que importa.

    Hace falta porque a una inscripción se llega por más de un camino —el
    estudiante se anota, o la institución lo pone en una comisión y eso lo
    inscribe en las materias que esa comisión dicta— y alcanza con que uno
    solo se olvide de crear el módulo para que la pantalla quede vacía.
    Resolverlo acá, donde se arma la lista, lo arregla para todos los caminos
    y para los que se agreguen después.
    """
    salida = []
    for inscripcion in d.inscripciones_materias:
        if inscripcion["personaId"] != persona_id:
            continue
        materia = d.buscar_materia(inscripcion["materiaId"])
        if not materia:
            continue
        salida.append(modulo_para(materia, por_inscripcion=True))
    return salida


def modulos_con_catedra() -> list[dict]:
    """Los módulos de todas las materias que tienen docente asignado.

    **Los crea si faltan**, igual que `modulos_que_dicta` con los del docente.
    Es la misma regla de siempre —el módulo existe desde que la institución le
    asigna la materia a alguien— aplicada al campus entero.

    Hace falta para quien administra o supervisa: su pantalla de Módulos
    muestra todo el campus, pero los módulos se venían creando solo cuando el
    docente entraba a la suya. Hasta que no entraba ninguno, la secretaría
    veía "0 módulos" con el plan entero cargado y los dictados asignados, que
    es exactamente lo que no tiene que pasar: parece que no se configuró nada.
    """
    salida = []
    for materia in d.materias_plan:
        if not d.docentes_de_materia(materia["id"]):
            continue
        modulo_para(materia)
        modulo = sincronizar_docente(materia)
        if modulo:
            salida.append(modulo)
    return salida


# ===================== El horario semanal =====================
DIAS = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def cursada_de(curso_id: int) -> list[dict]:
    """Los días y horarios de clase de ese módulo.

    No aparece en ninguna otra parte de la pantalla del módulo: sin esto hay
    que ir al calendario para saber cuándo se cursa.

    Vive acá y no en una ruta porque lo necesitan las dos: la pantalla, para
    mostrarlo, y la gestión, para devolverlo actualizado al agregar o quitar
    un día.
    """
    return [
        {
            "dia": DIAS[c["dia"]],
            "diaNumero": c["dia"],
            "desde": c["desde"],
            "hasta": c["hasta"],
            "aula": c.get("aula"),
        }
        for c in sorted(
            (c for c in d.clases if c["cursoId"] == curso_id),
            key=lambda c: (c["dia"], c["desde"]),
        )
    ]
