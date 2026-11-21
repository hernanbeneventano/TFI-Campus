"""Hasta dónde llega quien supervisa.

El problema
-----------
`Supervisor` era un permiso sin recorte: quien lo tuviera veía y moderaba
**todo el campus**: la biblioteca de cualquier cátedra, el registro de
auditoría entero, cualquier materia. En una facultad con varias carreras eso
no describe a nadie: quien lleva Sistemas no tiene por qué leer lo de
Bioquímica, y el día que alguien lo nota ya hubo meses de acceso que nadie
quiso dar.

La forma
--------
Cada persona puede tener un `ambito`:

    "ambito": {"carreras": [1, 3], "sedes": [2]}

- **Vacío o ausente: todo el campus.** Es lo que hacía hasta ahora, así que
  nada cambia hasta que la facultad decida recortar. Un campo nuevo que
  rompiera todos los permisos el día que se agrega sería peor que el problema.
- Con carreras: solo esas carreras.
- Con sedes: solo esas sedes.
- Con las dos: tiene que cumplir las dos.

**El administrador no tiene ámbito.** Es el rol que define qué es la facultad
—carreras, planes, sedes—: recortarlo sería dejar a la institución sin nadie
que la vea entera.

Dónde se aplica
---------------
Acá vive la regla y nada más; quien la usa es cada apartado: la Biblioteca
para decidir qué materias se ven y cuáles se moderan, y la Auditoría para
filtrar los eventos. Tener la cuenta en un solo lugar es lo que evita que
dentro de un año una pantalla recorte y la otra no.
"""

from __future__ import annotations

from typing import Any

from .. import datos as d


def de(persona: dict | None) -> dict | None:
    """El ámbito de esa persona, o `None` si alcanza todo el campus."""
    if not persona:
        return None
    if d.tiene_rol(persona, "Administrador"):
        return None

    crudo = persona.get("ambito") or {}
    carreras = [int(c) for c in (crudo.get("carreras") or []) if str(c).lstrip("-").isdigit()]
    sedes = [int(s) for s in (crudo.get("sedes") or []) if str(s).lstrip("-").isdigit()]
    if not carreras and not sedes:
        return None
    return {"carreras": set(carreras), "sedes": set(sedes)}


def recortado(persona: dict | None) -> bool:
    """Si a esta persona le pusieron un ámbito."""
    return de(persona) is not None


def _dentro(valores: set[int], valor: Any) -> bool:
    """Un ámbito que no nombra esa dimensión no la recorta."""
    if not valores:
        return True
    try:
        return int(valor) in valores
    except (TypeError, ValueError):
        # Sin dato no se puede afirmar que esté adentro. Se deja afuera: en un
        # recorte de permisos, la duda no puede resolverse a favor de ver más.
        return False


def alcanza_carrera(persona: dict, carrera_id: Any) -> bool:
    alcance = de(persona)
    return alcance is None or _dentro(alcance["carreras"], carrera_id)


def alcanza_sede(persona: dict, sede_id: Any) -> bool:
    alcance = de(persona)
    return alcance is None or _dentro(alcance["sedes"], sede_id)


def alcanza_materia(persona: dict, materia: dict | None) -> bool:
    """Una materia entra si su carrera entra.

    La materia no tiene sede: la sede es de la comisión que la dicta, y una
    misma materia puede dictarse en varias. Recortar materias por sede
    escondería media cátedra según dónde se dicte, que no es lo que se quiere
    decir con «esta persona lleva la sede Goya».
    """
    alcance = de(persona)
    if alcance is None:
        return True
    if not materia:
        return False
    return _dentro(alcance["carreras"], materia.get("carreraId"))


def materias(persona: dict) -> list[dict]:
    """Las materias del plan que alcanza esa persona."""
    alcance = de(persona)
    if alcance is None:
        return list(d.materias_plan)
    return [m for m in d.materias_plan if alcanza_materia(persona, m)]


def alcanza_evento(persona: dict, evento: dict) -> bool:
    """Si un evento de auditoría cae dentro del ámbito.

    Un evento **sin alcance anotado** —no todos lo tienen, porque no todo lo
    que pasa en el campus pertenece a una carrera— se deja ver: esconderlo
    dejaría a quien supervisa sin la mitad del registro sin decírselo, que es
    peor que mostrarle algo de más.
    """
    alcance = de(persona)
    if alcance is None:
        return True

    carrera = evento.get("carreraId")
    sede = evento.get("sedeId")
    if carrera is None and sede is None:
        return True

    if alcance["carreras"] and carrera is not None:
        if not _dentro(alcance["carreras"], carrera):
            return False
    if alcance["sedes"] and sede is not None:
        if not _dentro(alcance["sedes"], sede):
            return False
    return True


def resumen(persona: dict) -> dict:
    """Lo que la pantalla muestra: qué alcanza y con qué nombres."""
    alcance = de(persona)
    if alcance is None:
        return {"todo": True, "carreras": [], "sedes": []}
    return {
        "todo": False,
        "carreras": [
            {"id": c["id"], "nombre": c["nombre"]}
            for c in d.carreras_institucion
            if c["id"] in alcance["carreras"]
        ],
        "sedes": [
            {"id": s["id"], "nombre": s["nombre"]}
            for s in d.sedes
            if s["id"] in alcance["sedes"]
        ],
    }
