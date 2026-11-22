"""Pruebas del panel de control.

En proceso, como las demás: lo que hay que comprobar es quién puede abrirlo y,
sobre todo, que **los números salgan de los datos de verdad**. Un tablero que
muestra cifras inventadas es peor que no tener tablero, así que cada
comprobación contrasta lo que devuelve el panel contra la colección de la que
tendría que salir.

Uso (desde backend/):
    python -m pruebas.panel
"""

from __future__ import annotations

import sys


from app import datos as d

from . import escenario
from .cliente import como, crear_cliente
from app.servicios import panel as p

BASE = "/api/panel"

SANTIAGO = 1  # estudiante
MARIA = 2  # docente
SECRETARIA = 18  # Administrador
CLAUDIA = 19  # Supervisor + Docente

pasadas = 0
fallas: list[str] = []

# El campus arranca vacío, así que las pruebas cargan el suyo. Ver
# `escenario.py`: no toca ningún archivo, solo la memoria de este proceso.
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


def correr() -> None:
    print("Pruebas del panel de control (en proceso)\n")

    # ------------------------------------------------------------------
    grupo("Quién puede abrirlo")
    como(SANTIAGO)
    comprobar("un estudiante recibe 403", cliente.get(BASE).status_code == 403)
    comprobar("y en las alertas también", cliente.get(f"{BASE}/alertas").status_code == 403)

    como(MARIA)
    comprobar("un docente también recibe 403", cliente.get(BASE).status_code == 403)

    como(CLAUDIA)
    comprobar("el supervisor entra", cliente.get(BASE).status_code == 200)

    como(SECRETARIA)
    r = cliente.get(BASE)
    comprobar("el administrador entra", r.status_code == 200, r.status_code)
    panel = r.json()

    # ------------------------------------------------------------------
    grupo("Los números salen de los datos, no de ninguna parte")
    i = panel["indicadores"]

    activas = [a for a in d.asociaciones_academicas if a.get("estado", "activa") == "activa"]
    comprobar(
        "los estudiantes son los inscriptos a una carrera",
        i["estudiantes"] == len({a["personaId"] for a in activas}),
        (i["estudiantes"], len({a["personaId"] for a in activas})),
    )
    comprobar(
        "los docentes son los que tienen ese rol",
        i["docentes"] == sum(1 for x in d.personas if d.tiene_rol(x, "Docente")),
        i["docentes"],
    )
    comprobar(
        "las carreras son las activas",
        i["carreras"] == sum(1 for c in d.carreras_institucion if c.get("activa", True)),
        i["carreras"],
    )
    comprobar(
        "las materias son las del plan",
        i["materias"] == len(d.materias_plan),
        i["materias"],
    )
    comprobar(
        "los aportes pendientes son los de la biblioteca",
        i["aportesPendientes"] == sum(1 for m in d.materiales if m["estado"] == "pendiente"),
        i["aportesPendientes"],
    )

    # ------------------------------------------------------------------
    grupo("Las distribuciones cierran")
    dis = panel["distribuciones"]

    comprobar(
        "la suma por carrera da el total de inscripciones",
        sum(c["cantidad"] for c in dis["porCarrera"])
        == len([a for a in activas if a.get("carreraId")]),
        sum(c["cantidad"] for c in dis["porCarrera"]),
    )
    comprobar(
        "la suma por sede también",
        sum(c["cantidad"] for c in dis["porSede"])
        == len([a for a in activas if a.get("sedeId")]),
    )
    comprobar(
        "los ingresantes por año suman lo mismo",
        sum(m["cantidad"] for m in dis["matricula"])
        == len([a for a in activas if isinstance(a.get("ingreso"), int)]),
        dis["matricula"],
    )
    comprobar(
        "las comisiones del gráfico tienen gente",
        all(c["cantidad"] > 0 for c in dis["porComision"]),
        dis["porComision"],
    )

    # ------------------------------------------------------------------
    grupo("La asistencia se cuenta como en su pantalla")
    asistencia = dis["asistencia"]
    dictadas = {c["id"] for c in d.clases_asistencia if c.get("dictada", True)}
    registros = [a for a in d.asistencias if a["claseId"] in dictadas]
    presentes = sum(1 for a in registros if a["estado"] in ("presente", "justificada"))

    comprobar(
        "cuenta solo las clases dictadas",
        asistencia["registros"] == len(registros),
        (asistencia["registros"], len(registros)),
    )
    comprobar(
        "y el porcentaje es el que corresponde",
        asistencia["porcentaje"] == round(presentes * 100 / len(registros)),
        asistencia["porcentaje"],
    )
    comprobar("con el mínimo institucional", asistencia["minimo"] == 75, asistencia["minimo"])

    # ------------------------------------------------------------------
    grupo("Las alertas")
    r = cliente.get(f"{BASE}/alertas")
    comprobar("responden 200", r.status_code == 200, r.status_code)
    alertas = r.json()["alertas"]

    comprobar("ninguna viene en cero", all(a["cantidad"] > 0 for a in alertas), alertas)
    comprobar(
        "todas llevan a alguna pantalla",
        all(a["ruta"].startswith("/") and a["accion"] for a in alertas),
    )
    comprobar(
        "y cada detalle también",
        all(x["ruta"].startswith("/") for a in alertas for x in a["items"]),
    )

    sin_docente = next((a for a in alertas if a["id"] == "sin-docente"), None)
    esperadas = sum(
        1
        for x in d.dictados
        if not x.get("docentes")
        and (c := d.buscar_en(d.comisiones, x["comisionId"]))
        and c.get("activa", True)
    )
    if esperadas:
        comprobar(
            "las materias sin docente son las que no tienen a nadie",
            sin_docente and sin_docente["cantidad"] == esperadas,
            (sin_docente["cantidad"] if sin_docente else None, esperadas),
        )

    # ------------------------------------------------------------------
    grupo("Una alerta desaparece cuando se resuelve")
    vacias_antes = next((a for a in alertas if a["id"] == "comisiones-vacias"), None)
    if vacias_antes:
        # Se le asigna un estudiante a una comisión vacía y la cuenta baja
        comision_vacia = int(vacias_antes["items"][0]["id"])
        alguien = next(a for a in d.asociaciones_academicas if a.get("comisionId"))
        antes = alguien["comisionId"]
        alguien["comisionId"] = comision_vacia

        ahora = cliente.get(f"{BASE}/alertas").json()["alertas"]
        vacias_ahora = next((a for a in ahora if a["id"] == "comisiones-vacias"), None)
        comprobar(
            "al llenar una comisión baja la cuenta",
            vacias_ahora is None or vacias_ahora["cantidad"] == vacias_antes["cantidad"] - 1,
            (vacias_antes["cantidad"], vacias_ahora["cantidad"] if vacias_ahora else 0),
        )
        alguien["comisionId"] = antes

    # ------------------------------------------------------------------
    grupo("El supervisor no ve lo de las cuentas en la actividad")
    como(CLAUDIA)
    suyo = cliente.get(BASE).json()
    comprobar(
        "su actividad reciente es solo académica",
        all(e["modulo"] != "usuarios" for e in suyo["actividad"]),
        {e["modulo"] for e in suyo["actividad"]},
    )
    comprobar("y sabe que no es administrador", suyo["esAdministrador"] is False)

    # ------------------------------------------------------------------
    grupo("El panel no escribe nada")
    for metodo in ("post", "put", "patch"):
        r = getattr(cliente, metodo)(BASE, json={})
        comprobar(f"{metodo.upper()} no existe", r.status_code == 405, r.status_code)
    comprobar("DELETE tampoco", cliente.delete(BASE).status_code == 405)


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
