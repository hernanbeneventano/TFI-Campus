"""Pruebas de las asistencias: la cuenta con la que alguien regulariza o no.

Es el número más caro del campus. No se discute en una pantalla: se discute
meses después, cuando un alumno queda libre y hay que explicarle por qué. Era
el módulo más grande sin una sola prueba.

Lo que se cuida:

- **La cuenta.** Que el porcentaje, el cupo de faltas y el semáforo salgan de
  lo que de verdad se dictó, y que una clase suspendida no le genere falta a
  nadie.
- **El mínimo manda.** El que fija la facultad en Administración → Académico
  tiene que ser el que usa esta cuenta; si no, la pantalla de configuración
  guarda un número que nadie mira.
- **Quién toma lista.** El docente de esa materia y nadie más.
- **La lista se guarda entera o no se guarda.** Una lista a medias es peor
  que no haberla tomado, porque parece completa.
- **Una corrección deja rastro.** Cambiar una falta ya cerrada sin que quede
  anotado es justo lo que no puede pasar.

Uso (desde backend/):
    python -m pruebas.asistencias
"""

from __future__ import annotations

import sys


from app import datos as d
from app.servicios import asistencias as asis
from app.servicios import frenos

from . import escenario
from .cliente import como, crear_cliente

SANTIAGO = 1  # estudiante del módulo 1
MARIA = 2  # docente del módulo 1
PABLO = 7  # docente de otra materia
SECRETARIA = 18  # Administrador

pasadas = 0
fallas: list[str] = []

escenario.cargar()
frenos.olvidar_todo()

cliente = crear_cliente()
como(MARIA)

CURSO = 1


def comprobar(nombre: str, condicion: bool, detalle=None) -> None:
    global pasadas
    if condicion:
        pasadas += 1
        print(f"  ok     {nombre}")
    else:
        fallas.append(nombre)
        extra = f"  -> {detalle}" if detalle is not None else ""
        print(f"  FALLA  {nombre}{extra}")


def grupo(titulo: str) -> None:
    print(f"\n== {titulo} ==")


def alumnos_del_curso() -> list[int]:
    curso = d.buscar_curso(CURSO)
    return [
        p["id"]
        for p in d.participantes_de_curso(curso)
        if d.tiene_rol(p, "Estudiante")
    ]


def dia_libre(desde: int = 1) -> int:
    """Un día pasado en el que el módulo todavía no tenga clase.

    El escenario ya trae veintiséis clases cargadas: elegir un número fijo de
    días atrás choca con alguna y el campus contesta 409, con razón.
    """
    usados = {d.clave_dia(c["fecha"]) for c in asis.clases_de(CURSO)}
    for atras in range(desde, 400):
        if d.clave_dia(d.a_dias(-atras)) not in usados:
            return atras
    raise AssertionError("no quedan días libres")


def crear_clase(dias_atras: int, estado: str = "dictada", tema: str = "Clase"):
    """Registra una clase y devuelve `(respuesta, id)`."""
    previas = {c["id"] for c in asis.clases_de(CURSO)}
    r = cliente.post(
        f"/api/cursos/{CURSO}/asistencias/clases",
        json={"fecha": d.a_dias(-dias_atras), "estado": estado, "tema": tema},
    )
    nuevas = {c["id"] for c in asis.clases_de(CURSO)} - previas
    return r, (nuevas.pop() if nuevas else None)


def tomar_lista(id_clase: int, estados: dict[int, str], motivo: str | None = None):
    cuerpo = {
        "asistencias": [{"personaId": p, "estado": e} for p, e in estados.items()],
    }
    if motivo:
        cuerpo["motivo"] = motivo
    return cliente.put(f"/api/cursos/{CURSO}/asistencias/clases/{id_clase}", json=cuerpo)


def correr() -> None:
    print("Pruebas de las asistencias (en proceso)\n")
    alumnos = alumnos_del_curso()
    if len(alumnos) < 2:
        print("El escenario necesita al menos dos estudiantes en el módulo 1")
        sys.exit(1)
    uno, dos = alumnos[0], alumnos[1]

    # ------------------------------------------------------------------
    grupo("Quién toma lista")
    libre = dia_libre()
    como(SANTIAGO)
    comprobar("un estudiante no registra clases", crear_clase(libre)[0].status_code in (403, 404))
    como(PABLO)
    comprobar(
        "un docente de otra materia tampoco",
        crear_clase(libre)[0].status_code in (403, 404),
    )
    como(MARIA)
    primera, id_primera = crear_clase(libre, tema="Listas enlazadas")
    comprobar("el docente de la materia sí", primera.status_code == 201, primera.json())
    comprobar("y la clase queda registrada", id_primera is not None)

    # ------------------------------------------------------------------
    grupo("Lo que no se acepta al registrar una clase")
    comprobar(
        "una clase que todavía no pasó",
        cliente.post(
            f"/api/cursos/{CURSO}/asistencias/clases",
            json={"fecha": d.a_dias(5), "estado": "dictada"},
        ).status_code
        == 400,
    )
    comprobar("dos clases el mismo día", crear_clase(libre)[0].status_code == 409)
    comprobar(
        "un estado inventado",
        cliente.post(
            f"/api/cursos/{CURSO}/asistencias/clases",
            json={"fecha": d.a_dias(-dia_libre()), "estado": "feriado"},
        ).status_code
        == 400,
    )

    # ------------------------------------------------------------------
    grupo("La lista se guarda entera o no se guarda")
    cuantas = len(d.asistencias)
    mala = cliente.put(
        f"/api/cursos/{CURSO}/asistencias/clases/{id_primera}",
        json={
            "asistencias": [
                {"personaId": uno, "estado": "presente"},
                {"personaId": dos, "estado": "inventado"},
            ]
        },
    )
    comprobar("un estado inválido corta todo", mala.status_code == 400, mala.json())
    comprobar("y no se escribió nada", len(d.asistencias) == cuantas, len(d.asistencias))

    ajena = cliente.put(
        f"/api/cursos/{CURSO}/asistencias/clases/{id_primera}",
        json={"asistencias": [{"personaId": 99999, "estado": "presente"}]},
    )
    comprobar("alguien que no cursa se rechaza", ajena.status_code == 400)

    repetido = cliente.put(
        f"/api/cursos/{CURSO}/asistencias/clases/{id_primera}",
        json={
            "asistencias": [
                {"personaId": uno, "estado": "presente"},
                {"personaId": uno, "estado": "ausente"},
            ]
        },
    )
    comprobar("un alumno repetido también", repetido.status_code == 400)

    buena = tomar_lista(id_primera, {uno: "presente", dos: "ausente"})
    comprobar("la lista completa sí se guarda", buena.status_code == 200, buena.json())

    # ------------------------------------------------------------------
    # La cuenta es lo que después se discute con un alumno en la ventanilla.
    # Se mira **la diferencia**, no el número absoluto: el escenario ya trae
    # veintiséis clases cargadas, y una prueba atada a un total concreto falla
    # el día que alguien agrega una clase a los datos de ejemplo.
    grupo("La cuenta sale de lo que se dictó")
    presente_uno = asis.situacion_de(uno, CURSO)
    ausente_dos = asis.situacion_de(dos, CURSO)
    comprobar("cuenta la clase dictada", presente_uno["registradas"] >= 1, presente_uno["registradas"])

    otro_libre = dia_libre()
    antes_uno = asis.situacion_de(uno, CURSO)["inasistencias"]
    antes_dos = asis.situacion_de(dos, CURSO)["inasistencias"]
    _, id_segunda = crear_clase(otro_libre, tema="Otra clase")
    tomar_lista(id_segunda, {uno: "presente", dos: "ausente"})

    comprobar(
        "un presente no suma inasistencia",
        asis.situacion_de(uno, CURSO)["inasistencias"] == antes_uno,
    )
    comprobar(
        "y un ausente suma una",
        asis.situacion_de(dos, CURSO)["inasistencias"] == antes_dos + 1,
    )

    # Una clase suspendida deja constancia de por qué no hubo clase, y
    # justamente por eso no puede generarle una falta a nadie.
    antes_de_suspender = asis.situacion_de(dos, CURSO)["inasistencias"]
    suspendida, id_suspendida = crear_clase(
        dia_libre(), estado="suspendida", tema="Paro de transporte"
    )
    comprobar("se registra una clase suspendida", suspendida.status_code == 201, suspendida.json())
    comprobar(
        "y no le suma falta a nadie",
        asis.situacion_de(dos, CURSO)["inasistencias"] == antes_de_suspender,
    )
    comprobar(
        "a una clase suspendida no se le toma lista",
        tomar_lista(id_suspendida, {uno: "presente"}).status_code == 400,
    )

    # ------------------------------------------------------------------
    grupo("El mínimo que fija la facultad es el que manda")
    como(SECRETARIA)
    r = cliente.put(
        "/api/institucion/configuracion/asistencia",
        json={"minimoPorDefecto": 90, "justificadaDescuenta": True},
    )
    comprobar("se puede cambiar el mínimo", r.status_code == 200, r.json())
    comprobar("y la cuenta lo usa", asis.minimo_exigido() == 90, asis.minimo_exigido())
    comprobar(
        "la situación del alumno también",
        asis.situacion_de(uno, CURSO)["minimoAsistencia"] == 90,
    )

    # Ojo con la palabra: acá **«descontar» quiere decir que no pesa**. Con
    # `justificadaDescuenta` en verdadero la falta justificada se le descuenta
    # al alumno y no le resta asistencia; en falso cuenta como inasistencia,
    # que es lo que pide el pliego por defecto: aprobar una justificación deja
    # constancia de por qué faltó, no le devuelve el porcentaje.
    como(MARIA)
    tomar_lista(id_primera, {uno: "justificada", dos: "ausente"}, motivo="Corrección de prueba")
    con_descuento = asis.situacion_de(uno, CURSO)

    como(SECRETARIA)
    cliente.put(
        "/api/institucion/configuracion/asistencia",
        json={"minimoPorDefecto": 75, "justificadaDescuenta": False},
    )
    sin_descuento = asis.situacion_de(uno, CURSO)

    comprobar(
        "la justificada quedó registrada",
        con_descuento["justificadas"] >= 1,
        con_descuento["justificadas"],
    )
    comprobar(
        "con «descuentan», la justificada deja de pesar",
        con_descuento["inasistencias"]
        == sin_descuento["inasistencias"] - con_descuento["justificadas"],
        (con_descuento["inasistencias"], sin_descuento["inasistencias"]),
    )
    comprobar(
        "y sin «descuentan» vuelve a contar, que es lo que pide el pliego",
        sin_descuento["inasistencias"] > con_descuento["inasistencias"],
    )
    comprobar(
        "y el mínimo guardado es el que se usa",
        sin_descuento["minimoAsistencia"] == 75,
        sin_descuento["minimoAsistencia"],
    )

    # ------------------------------------------------------------------
    grupo("El cupo de faltas y el semáforo")
    limites = asis.limite_de_inasistencias(40, 75)
    comprobar(
        "con 40 clases y 75 % puede faltar 10",
        limites == {"minimasNecesarias": 30, "maximoInasistencias": 10},
        limites,
    )
    comprobar(
        "sin planificación no hay cupo",
        asis.limite_de_inasistencias(None, 75)["maximoInasistencias"] is None,
    )
    comprobar(
        "un mínimo del 100 % no deja faltar",
        asis.limite_de_inasistencias(10, 100)["maximoInasistencias"] == 0,
    )

    # ------------------------------------------------------------------
    grupo("Corregir una falta deja rastro")
    cambios = [
        h
        for h in d.historial_asistencia
        if h.get("claseId") == id_primera and h.get("personaId") == uno
    ]
    comprobar("el cambio quedó anotado", bool(cambios), len(cambios))
    comprobar(
        "con el estado anterior y el nuevo",
        any(c.get("de") and c.get("a") for c in cambios),
        cambios[:1],
    )
    comprobar(
        "y con el motivo de la corrección",
        any(c.get("motivo") for c in cambios),
        cambios[:1],
    )
    comprobar(
        "y también en la auditoría del campus",
        any(e["modulo"] == "asistencias" for e in d.auditoria),
    )

    # ------------------------------------------------------------------
    grupo("Lo que ve el alumno es lo mismo que cuenta el servidor")
    como(SANTIAGO)
    mia = cliente.get(f"/api/cursos/{CURSO}/asistencias/mi-detalle")
    comprobar("puede ver su propia asistencia", mia.status_code == 200, mia.status_code)
    if mia.status_code == 200:
        propia = asis.situacion_de(SANTIAGO, CURSO)
        comprobar(
            "y el número coincide con el del servicio",
            mia.json()["situacion"]["inasistencias"] == propia["inasistencias"],
            (mia.json()["situacion"]["inasistencias"], propia["inasistencias"]),
        )
    comprobar(
        "pero no la planilla del curso",
        cliente.get(f"/api/cursos/{CURSO}/asistencias/alumnos").status_code in (403, 404),
    )

    # ------------------------------------------------------------------
    print("\n" + "-" * 52)
    total = pasadas + len(fallas)
    print(f"{pasadas}/{total} comprobaciones pasaron")
    if fallas:
        print("\nFallaron:")
        for f in fallas:
            print(f"  - {f}")
        sys.exit(1)
    print("Todo en orden.")


if __name__ == "__main__":
    correr()
