"""Pruebas de la configuración académica de la facultad.

Dos decisiones que se toman cada cuatrimestre y que hasta ahora solo se
podían cambiar editando un archivo del servidor: **cuándo se puede uno
inscribir a materias** y **cuánta asistencia se exige**.

Lo primero no era un detalle: sin eso la secretaría no podía abrir ni cerrar
el cuatrimestre, que es su trabajo.

Lo que más importa acá es que el valor **mande de verdad**: que cerrar el
período frene la inscripción y que el mínimo que se guarda sea el que usa la
pantalla de Asistencias. Una pantalla de configuración que guarda un número
que después nadie mira es peor que no tenerla, porque hace creer que se
cambió algo.

Uso (desde backend/):
    python -m pruebas.configuracion
"""

from __future__ import annotations

import sys


from app import datos as d
from app.servicios import asistencias as asis

from . import escenario
from .cliente import como, crear_cliente

BASE = "/api/institucion/configuracion"

SANTIAGO = 1  # estudiante
MARIA = 2  # docente
SECRETARIA = 18  # Administrador
CLAUDIA = 19  # Supervisor + Docente

pasadas = 0
fallas: list[str] = []

escenario.cargar()

cliente = crear_cliente()
como(SECRETARIA)


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


def periodo(desde: str, hasta: str):
    return cliente.put(f"{BASE}/periodo", json={"desde": desde, "hasta": hasta})


def correr() -> None:
    print("Pruebas de la configuración académica (en proceso)\n")

    # ------------------------------------------------------------------
    grupo("Quién la ve y quién la cambia")
    como(SANTIAGO)
    comprobar("un estudiante no la ve", cliente.get(BASE).status_code == 403)
    comprobar("ni la cambia", periodo("2026-03-01", "2026-03-20").status_code == 403)

    como(MARIA)
    comprobar("un docente tampoco", cliente.get(BASE).status_code == 403)

    # El supervisor **sí** la cambia: abrir y cerrar el cuatrimestre, fijar
    # el mínimo y cargar las jornadas es el trabajo de la secretaría. Lo que
    # sigue siendo del administrador es la estructura —carreras, planes,
    # materias—, que define qué es la facultad y no cuándo abre.
    como(CLAUDIA)
    r = cliente.get(BASE)
    comprobar("el supervisor la ve", r.status_code == 200, r.status_code)
    comprobar("y puede editarla", r.json()["puedeEditar"] is True, r.json())
    comprobar(
        "y el servidor se lo acepta",
        periodo("2026-03-01", "2026-03-20").status_code == 200,
    )
    comprobar(
        "pero la estructura sigue sin ser suya",
        cliente.post(
            "/api/institucion/carreras", json={"nombre": "Nueva", "codigo": "NUE"}
        ).status_code
        == 403,
    )

    como(SECRETARIA)
    r = cliente.get(BASE)
    comprobar("el administrador la ve y la edita", r.json()["puedeEditar"] is True)

    # ------------------------------------------------------------------
    grupo("Lo que no se puede guardar")
    comprobar("cerrar antes de abrir", periodo("2026-03-20", "2026-03-01").status_code == 400)
    comprobar("sin fecha de apertura", periodo("", "2026-03-20").status_code == 400)
    comprobar("una fecha que no existe", periodo("no-es-fecha", "2026-03-20").status_code == 400)
    comprobar(
        "un mínimo de 150 %",
        cliente.put(f"{BASE}/asistencia",
                    json={"minimoPorDefecto": 150, "justificadaDescuenta": False}).status_code == 400,
    )
    comprobar(
        "un mínimo que no es número",
        cliente.put(f"{BASE}/asistencia",
                    json={"minimoPorDefecto": "mucho", "justificadaDescuenta": False}).status_code == 400,
    )
    comprobar(
        "sin decir si la justificada descuenta",
        cliente.put(f"{BASE}/asistencia", json={"minimoPorDefecto": 70}).status_code == 400,
    )

    # ------------------------------------------------------------------
    grupo("Guardar devuelve lo mismo que leer")
    # La pantalla reemplaza su estado con lo que devuelve cada guardado. Si
    # falta un campo se comporta como si no lo tuviera: faltaba `puedeEditar`
    # y, al guardar el período, se deshabilitaban solos los de asistencia.
    como(SECRETARIA)
    leido = set(cliente.get(BASE).json())
    guardado = set(periodo("2026-03-01", "2026-03-20").json())
    comprobar("el período devuelve los mismos campos", leido == guardado, (leido, guardado))
    otro = set(
        cliente.put(f"{BASE}/asistencia",
                    json={"minimoPorDefecto": 75, "justificadaDescuenta": False}).json()
    )
    comprobar("y la asistencia también", leido == otro, (leido, otro))

    # ------------------------------------------------------------------
    grupo("Un período que ya pasó o que no empezó son datos válidos")
    # La facultad registra lo que hizo y planifica lo que viene.
    comprobar("uno viejo se guarda", periodo("2020-03-01", "2020-03-20").status_code == 200)
    comprobar("y uno futuro también", periodo("2099-03-01", "2099-03-20").status_code == 200)

    # ------------------------------------------------------------------
    grupo("Cerrar el período frena la inscripción")
    # Es lo que hay que cuidar: que el valor mande de verdad.
    hoy = d.ahora()
    periodo(f"{hoy.year - 1}-01-10", f"{hoy.year - 1}-01-20")

    como(SANTIAGO)
    plan = cliente.get("/api/inscripciones/materias")
    if plan.status_code == 200:
        comprobar("el alumno ve el período cerrado", plan.json()["periodo"]["abierto"] is False)
        alguna = next((m for m in plan.json()["materias"] if m["estado"] == "Habilitada"), None)
        if alguna:
            comprobar("y no puede inscribirse", alguna["puedeInscribirse"] is False)
            comprobar("con el motivo puesto", "cerrado" in (alguna["motivo"] or "").lower(),
                      alguna["motivo"])
            r = cliente.post(f"/api/inscripciones/materias/{alguna['id']}")
            comprobar("el servidor lo rechaza", r.status_code == 403, r.status_code)

    # Y al abrirlo vuelve a poder
    como(SECRETARIA)
    periodo(f"{hoy.year}-01-01", f"{hoy.year}-12-31")
    como(SANTIAGO)
    plan = cliente.get("/api/inscripciones/materias")
    if plan.status_code == 200:
        comprobar("al abrirlo, vuelve a estar abierta", plan.json()["periodo"]["abierto"] is True)

    # ------------------------------------------------------------------
    grupo("El mínimo de asistencia es el que usa el campus")
    como(SECRETARIA)
    r = cliente.put(f"{BASE}/asistencia", json={"minimoPorDefecto": 60,
                                                "justificadaDescuenta": True})
    comprobar("se guarda", r.status_code == 200, r.status_code)
    comprobar("y lo devuelve", r.json()["asistencia"]["minimoPorDefecto"] == 60)
    comprobar(
        "el servicio de asistencias usa ese mismo número",
        asis.minimo_exigido() == 60,
        asis.minimo_exigido(),
    )
    comprobar(
        "y lo de las justificadas también",
        asis.configuracion()["justificadaDescuenta"] is True,
    )

    # ------------------------------------------------------------------
    grupo("Queda registrado quién lo cambió")
    # Cambiar cuándo se puede cursar es una decisión institucional: sin
    # registro, "¿quién cerró la inscripción?" no tiene respuesta.
    # El qué pasó va en `detalle` y la cosa en `elemento`: es la convención
    # de `_anotar` en todo el apartado de institución.
    eventos = [
        e for e in d.auditoria
        if "período de inscripción" in (e.get("detalle") or "").lower()
    ]
    comprobar("el cambio de período se anota", len(eventos) > 0, len(d.auditoria))
    if eventos:
        comprobar("con quién lo hizo", eventos[-1].get("quienId") == SECRETARIA,
                  eventos[-1].get("quienId"))
        comprobar("y con el antes y el después",
                  bool(eventos[-1].get("antes")) and bool(eventos[-1].get("despues")))

    # ------------------------------------------------------------------
    grupo("Se guarda en la base como todo lo demás")
    from app.servicios import persistencia as p

    documentos = p._documentos()
    comprobar(
        "el período viaja a la configuración",
        ("configuracion", "periodo_inscripcion_materias") in documentos,
    )
    comprobar(
        "y el mínimo de asistencia también",
        ("configuracion", "CONFIG_ASISTENCIA") in documentos,
    )


def resumir() -> None:
    total = pasadas + len(fallas)
    print(f"\n{'-' * 52}")
    print(f"{pasadas}/{total} comprobaciones pasaron")
    if fallas:
        print("\nFallaron:")
        for f in fallas:
            print(f"  - {f}")
        sys.exit(1)
    print("Todo en orden.")


if __name__ == "__main__":
    correr()
    resumir()
