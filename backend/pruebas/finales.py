"""Pruebas de Finales (gestión docente).

A diferencia de las de la Biblioteca, estas corren **dentro del proceso**, con
el cliente de pruebas de FastAPI: hace falta actuar como personas distintas
(un estudiante, la titular de una materia, otro docente) y sin login real el
servidor en marcha siempre responde como el usuario de prueba, que es
estudiante. Acá se reemplaza la identificación por la persona que se quiera.

Recorren el camino completo igual: la ruta, los permisos, la validación y la
respuesta. Modifican los datos en memoria de este proceso, no los del servidor.

Las mesas son de una **materia del plan** (`materiasPlan`), no de un módulo:
por eso los identificadores son 107, 109, 110… y no 1, 2, 3.

Uso (desde backend/):
    python -m pruebas.finales
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app import datos as d
from app.main import app
from app.servicios.autenticacion import identificar

BASE = "/api/finales/gestion"

# Personas de los datos de prueba
ESTUDIANTE = 1
MARIA = 2  # titular de Programación II y tribunal de Algoritmos
PABLO = 7  # titular de Bases de Datos

# Materias del plan
PROG2 = 109
PROG3 = 115  # también de María: el plan la tiene, pero sin mesas
ALGORITMOS = 107
BASES = 110

pasadas = 0
fallas: list[str] = []

_quien = {"id": MARIA}
app.dependency_overrides[identificar] = lambda: d.buscar_persona(_quien["id"])
cliente = TestClient(app)


def como(persona_id: int) -> None:
    _quien["id"] = persona_id


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


def en_dias(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def error_de(r) -> str:
    try:
        return r.json().get("error", "")
    except ValueError:
        return ""


def mensajes_totales() -> int:
    return sum(len(c["mensajes"]) for c in d.conversaciones)


def correr() -> None:
    print("Pruebas de Finales (en proceso)\n")

    # ------------------------------------------------------------------
    grupo("Permisos")
    como(ESTUDIANTE)
    r = cliente.get(f"{BASE}/mesas")
    comprobar("un estudiante no entra a la gestión", r.status_code == 403, r.status_code)

    como(MARIA)
    mesas = cliente.get(f"{BASE}/mesas").json()
    ids = {m["id"] for m in mesas}
    comprobar(
        "ve las mesas de su materia y las de su tribunal",
        ids == {1, 3, 5, 6, 7, 8, 9, 10},
        ids,
    )
    comprobar(
        "una mesa ajena no existe para ella (404, no 403)",
        cliente.get(f"{BASE}/mesas/2").status_code == 404,
    )
    algoritmos = next(m for m in mesas if m["id"] == 1)
    comprobar("en el tribunal ajeno no edita", not algoritmos["puedeEditar"])
    comprobar(
        "y el servidor lo rechaza aunque lo intente",
        cliente.put(f"{BASE}/mesas/1", json={}).status_code == 403,
    )
    opciones = cliente.get(f"{BASE}/opciones").json()
    comprobar(
        "solo puede crear mesas de las materias que tiene a cargo",
        [m["id"] for m in opciones["materias"]] == [PROG2, PROG3],
        opciones["materias"],
    )

    como(PABLO)
    ids = {m["id"] for m in cliente.get(f"{BASE}/mesas").json()}
    comprobar("otro docente ve solo lo suyo", ids == {2, 4}, ids)
    como(MARIA)

    # ------------------------------------------------------------------
    grupo("Inscriptos")
    r = cliente.get(f"{BASE}/inscriptos", params={"materiaId": PROG2}).json()
    comprobar("cuenta el total de inscriptos", r["total"] > 0, r["total"])
    comprobar("devuelve las comisiones para filtrar", r["comisiones"] == ["A", "B"], r["comisiones"])
    r = cliente.get(f"{BASE}/inscriptos", params={"mesaId": 6, "comision": "B"}).json()
    filas = [f for g in r["grupos"] for f in g["inscriptos"]]
    comprobar("filtra por mesa y comisión", filas and all(f["comision"] == "B" for f in filas))
    alumno = filas[0]["alumno"]
    comprobar(
        "trae los datos académicos",
        all(k in alumno for k in ("legajo", "carrera", "aprobadas", "promedio", "intentos")),
        alumno.keys(),
    )
    comprobar(
        "la condición sale del historial académico, no de la inscripción",
        all(f["condicion"] in ("Regular", "Libre", "Aprobada", "En curso") for f in filas),
        [f["condicion"] for f in filas],
    )

    # ------------------------------------------------------------------
    grupo("Fechas: crear")
    base = {
        "materiaId": PROG2,
        "llamado": "Turno de prueba",
        "fecha": en_dias(30),
        "desde": "16:00",
        "hasta": "19:00",
        "modalidad": "Presencial",
        "instancia": "Escrito",
        "lugar": "Aula 1",
        "inscripcionDesde": en_dias(5),
        "inscripcionHasta": en_dias(25),
        "cupo": 10,
        "tribunal": [11],
    }
    r = cliente.post(f"{BASE}/mesas", json={**base, "materiaId": BASES})
    comprobar("no crea en una materia que no tiene a cargo", r.status_code == 403, r.status_code)
    r = cliente.post(f"{BASE}/mesas", json={**base, "inscripcionHasta": en_dias(30)})
    comprobar("la inscripción cierra antes del día del examen", r.status_code == 400, error_de(r))
    r = cliente.post(f"{BASE}/mesas", json={**base, "fecha": en_dias(-1)})
    comprobar("no acepta una fecha pasada", r.status_code == 400, error_de(r))
    r = cliente.post(f"{BASE}/mesas", json={**base, "desde": "19:00", "hasta": "18:00"})
    comprobar("no acepta el horario al revés", r.status_code == 400, error_de(r))
    r = cliente.post(f"{BASE}/mesas", json={**base, "tribunal": [ESTUDIANTE]})
    comprobar("en el tribunal solo hay docentes", r.status_code == 400, error_de(r))
    r = cliente.post(f"{BASE}/mesas", json={**base, "cupo": 0})
    comprobar("el cupo es al menos 1", r.status_code == 400, error_de(r))
    r = cliente.post(f"{BASE}/mesas", json=base)
    comprobar("crea la mesa", r.status_code == 201, error_de(r))
    nueva = r.json()
    comprobar("la titular queda primera en el tribunal", nueva["tribunal"][0]["id"] == MARIA)
    r = cliente.post(f"{BASE}/mesas", json=base)
    comprobar("no repite mesa de la misma materia el mismo día", r.status_code == 409, r.status_code)

    # ------------------------------------------------------------------
    grupo("Fechas: reprogramar y cancelar")
    mesa10 = next(m for m in mesas if m["id"] == 10)
    datos10 = {
        **base,
        "llamado": mesa10["llamado"],
        "fecha": en_dias(14),
        "inscripcionDesde": en_dias(-4),
        "inscripcionHasta": en_dias(8),
        "cupo": 25,
    }
    antes = mensajes_totales()
    r = cliente.put(f"{BASE}/mesas/10", json=datos10)
    comprobar("reprograma", r.status_code == 200, error_de(r))
    comprobar(
        "avisa por mensaje a cada inscripto",
        mensajes_totales() - antes == mesa10["inscriptos"],
        mensajes_totales() - antes,
    )
    comprobar("queda en el historial de la mesa", r.json()["historial"][-1]["accion"] == "Reprogramó la mesa")
    r = cliente.put(f"{BASE}/mesas/10", json={**datos10, "cupo": 1})
    comprobar("el cupo no baja de los inscriptos", r.status_code == 400, error_de(r))

    r = cliente.post(f"{BASE}/mesas/{nueva['id']}/cancelar", json={})
    comprobar("cancelar exige motivo", r.status_code == 400, error_de(r))
    r = cliente.post(f"{BASE}/mesas/{nueva['id']}/cancelar", json={"motivo": "Prueba"})
    comprobar("cancela", r.status_code == 200 and r.json()["estado"] == "cancelada")
    r = cliente.put(f"{BASE}/mesas/{nueva['id']}", json=base)
    comprobar("una cancelada no se modifica", r.status_code == 409, r.status_code)

    # ------------------------------------------------------------------
    grupo("Resultados")
    r = cliente.put(f"{BASE}/mesas/10/resultados", json={"resultados": []})
    comprobar("no se califica antes del examen", r.status_code == 409, error_de(r))
    r = cliente.put(f"{BASE}/mesas/7/resultados", json={"resultados": []})
    comprobar("un acta cerrada no se toca", r.status_code == 409, error_de(r))

    planilla = cliente.get(f"{BASE}/mesas/6").json()["inscriptos"]
    activos = [i for i in planilla if i["estado"] == "Inscripto"]
    de_baja = next(i for i in planilla if i["estado"] == "Cancelado")
    uno = activos[0]["id"]

    def cargar(resultado, nota=None, inscripcion=uno):
        fila = {"inscripcionId": inscripcion, "resultado": resultado, "nota": nota}
        return cliente.put(f"{BASE}/mesas/6/resultados", json={"resultados": [fila]})

    r = cargar("Aprobado", 5)
    comprobar("no aprueba por debajo de la nota mínima", r.status_code == 400, error_de(r))
    r = cargar("Desaprobado", 8)
    comprobar("no desaprueba con nota de aprobado", r.status_code == 400, error_de(r))
    r = cargar("Aprobado", 7.5)
    comprobar("la nota es entera", r.status_code == 400, error_de(r))
    r = cargar("Aprobado", None)
    comprobar("quien se presentó necesita nota", r.status_code == 400, error_de(r))
    r = cargar("Ausente", inscripcion=de_baja["id"])
    comprobar("una baja no entra en la planilla", r.status_code == 400, error_de(r))

    r = cliente.post(f"{BASE}/mesas/6/cerrar-acta")
    comprobar("el acta no se cierra incompleta", r.status_code == 400, error_de(r))

    filas = [{"inscripcionId": i["id"], "resultado": "Aprobado", "nota": 8} for i in activos]
    filas[-1] = {"inscripcionId": activos[-1]["id"], "resultado": "Ausente", "nota": 8}
    r = cliente.put(f"{BASE}/mesas/6/resultados", json={"resultados": filas})
    comprobar("guarda la planilla entera", r.status_code == 200, error_de(r))
    ausente = next(i for i in r.json()["inscriptos"] if i["id"] == activos[-1]["id"])
    comprobar("un ausente no guarda nota", ausente["nota"] is None, ausente["nota"])

    como(PABLO)
    r = cliente.post(f"{BASE}/mesas/6/cerrar-acta")
    comprobar("alguien de afuera no cierra el acta", r.status_code == 404, r.status_code)
    como(MARIA)

    resultados = len(d.resultados_finales)
    antes = mensajes_totales()
    aprobado = activos[0]["alumno"]["id"]
    r = cliente.post(f"{BASE}/mesas/6/cerrar-acta")
    comprobar("cierra el acta", r.status_code == 200 and r.json()["mesa"]["actaCerrada"], error_de(r))
    comprobar(
        "los resultados quedan en los finales rendidos",
        len(d.resultados_finales) - resultados == len(activos),
    )
    comprobar(
        "quien aprobó queda con la materia aprobada en el historial",
        d.condicion_en(aprobado, PROG2) == "Aprobada",
        d.condicion_en(aprobado, PROG2),
    )
    comprobar("cada alumno recibe su resultado", mensajes_totales() - antes == len(activos))
    r = cargar("Aprobado", 9)
    comprobar("después del cierre no se modifica", r.status_code == 409, error_de(r))

    # ------------------------------------------------------------------
    grupo("La mitad del alumno, con las mesas de la gestión")
    como(ESTUDIANTE)
    mesas_alumno = cliente.get("/api/finales/mesas").json()["mesas"]
    cancelada = next((m for m in mesas_alumno if m["id"] == 8), None)
    comprobar(
        "una mesa cancelada no se puede rendir",
        cancelada is not None
        and cancelada["estado"] == "Mesa cancelada"
        and not cancelada["puedeInscribirse"],
        cancelada and cancelada["estado"],
    )
    r = cliente.post("/api/finales/mesas/8/inscripcion")
    comprobar("y el servidor rechaza la inscripción", r.status_code == 403, r.status_code)
    como(MARIA)

    resumir()


def resumir() -> None:
    total = pasadas + len(fallas)
    print("\n" + "=" * 58)
    print(f"{pasadas} de {total} comprobaciones correctas")
    if fallas:
        print("\nFallaron:")
        for f in fallas:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    correr()
