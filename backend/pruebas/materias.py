"""Pruebas de las materias del plan: lo que se configura es lo que pasa.

Son dos pantallas que tienen que decir lo mismo. La institución configura una
materia en **Administración › Materias**: su plan, su cupo, si se ofrece y sus
correlatividades, separadas en las de cursar y las de rendir. El estudiante
ve el resultado en **Inscribirme**, y la cátedra en la mesa de examen.

Lo que se comprueba acá es justamente la juntura: que **el estudiante vea
exactamente lo que se configuró**, ni más permisivo ni más restrictivo. Es
donde un campus se rompe sin que nadie se entere: la pantalla de
administración guarda bien, la del alumno lee de otra manera, y alguien se
anota a una materia para la que no está habilitado —o no puede anotarse a una
para la que sí lo está— hasta que lo descubre un humano meses después.

Por eso cada comprobación hace el camino entero: configura por la API de
administración y pregunta por la API del alumno, nunca tocando la memoria
directamente para leer. Si las dos no coinciden, falla.

Uso (desde backend/):
    python -m pruebas.materias
"""

from __future__ import annotations

import sys


from app import datos as d

from . import escenario
from .cliente import como, crear_cliente

ADMIN = "/api/institucion/materias"
PLAN = "/api/inscripciones/materias"

SANTIAGO = 1  # estudiante, Licenciatura en Sistemas, plan 2023
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


# ===================== Ayudas =====================
def condicion(persona_id: int, materia_id: int, cual: str | None) -> None:
    """Deja a la persona en esa condición en esa materia."""
    d.historial_academico[:] = [
        h
        for h in d.historial_academico
        if not (h["personaId"] == persona_id and h["materiaId"] == materia_id)
    ]
    if cual:
        d.historial_academico.append(
            {
                "personaId": persona_id,
                "materiaId": materia_id,
                "condicion": cual,
                "nota": 8 if cual == "Aprobada" else None,
                "fecha": d.iso(d.ahora()),
            }
        )


def crear(nombre: str, codigo: str, **extra) -> dict:
    """Una materia nueva en el plan de Santiago, como la crea la Secretaría."""
    como(SECRETARIA)
    cuerpo = {
        "nombre": nombre,
        "codigo": codigo,
        "carreraId": 1,
        "planId": 1,
        "anio": 1,
        "cuatrimestre": 1,
        **extra,
    }
    r = cliente.post(ADMIN, json=cuerpo)
    assert r.status_code == 201, (r.status_code, r.text[:200])
    return r.json()["materia"] if "materia" in r.json() else r.json()


def requisito(materia_id: int, cual: str) -> dict:
    return {"materiaId": materia_id, "condicion": cual}


def configurar(materia_id: int, **cuerpo) -> int:
    como(SECRETARIA)
    return cliente.patch(f"{ADMIN}/{materia_id}", json=cuerpo).status_code


def del_plan(materia_id: int) -> dict | None:
    """Lo que ve el estudiante de esa materia, por su propia pantalla."""
    como(SANTIAGO)
    r = cliente.get(PLAN)
    assert r.status_code == 200, r.status_code
    return next((m for m in r.json()["materias"] if m["id"] == materia_id), None)


def anotarse(materia_id: int):
    como(SANTIAGO)
    return cliente.post(f"{PLAN}/{materia_id}")


def correr() -> None:
    print("Pruebas de las materias del plan (en proceso)\n")

    # ------------------------------------------------------------------
    grupo("Quién configura el plan")
    como(MARIA)
    comprobar("un docente no crea materias", cliente.post(ADMIN, json={}).status_code == 403)
    como(SANTIAGO)
    comprobar("un estudiante tampoco", cliente.post(ADMIN, json={}).status_code == 403)
    comprobar("y no puede editar", cliente.patch(f"{ADMIN}/101", json={}).status_code == 403)
    comprobar("ni dar de baja", cliente.delete(f"{ADMIN}/101").status_code == 403)
    como(CLAUDIA)
    comprobar("el supervisor las ve", cliente.get(ADMIN).status_code == 200)
    comprobar("pero no las crea", cliente.post(ADMIN, json={}).status_code == 403)

    # ------------------------------------------------------------------
    grupo("Lo que no puede guardarse")
    base = crear("Química General", "QUI-1")
    comprobar("el código no se repite en el plan", _codigo_repetido("QUI-1") == 409)
    comprobar(
        "una materia no es correlativa de sí misma",
        configurar(base["id"], correlativas={"cursar": {"requisitos": [requisito(base["id"], "Aprobada")]}}) == 400,
    )
    otra = crear("Química Orgánica", "QUI-2",
                 correlativas={"cursar": {"requisitos": [requisito(base["id"], "Aprobada")]}})
    comprobar(
        "ni se arma un círculo A, B, A",
        configurar(base["id"], correlativas={"cursar": {"requisitos": [requisito(otra["id"], "Aprobada")]}}) == 400,
    )
    comprobar(
        "la correlativa tiene que ser del mismo plan",
        configurar(base["id"], correlativas={"cursar": {"requisitos": [requisito(999, "Aprobada")]}}) == 400,
    )

    # ------------------------------------------------------------------
    grupo("Una correlativa Regular se pide regular, no aprobada")
    # Es el error clásico: el plan pide tener la cursada aprobada y el campus
    # exige el final. El estudiante queda trabado por una regla que nadie
    # configuró.
    configurar(otra["id"], correlativas={"cursar": {"modo": "todas", "requisitos": [requisito(base["id"], "Regular")]}})

    condicion(SANTIAGO, base["id"], None)
    visto = del_plan(otra["id"])
    comprobar("sin cursar, está bloqueada", visto["estado"] == "Bloqueada por correlatividad", visto["estado"])
    comprobar(
        "y el motivo dice la condición que se pidió",
        "regular" in (visto["motivo"] or "").lower()
        and "aprobar" not in (visto["motivo"] or "").lower(),
        visto["motivo"],
    )

    condicion(SANTIAGO, base["id"], "Regular")
    visto = del_plan(otra["id"])
    comprobar("con la cursada aprobada, se habilita", visto["estado"] == "Habilitada", visto["estado"])

    condicion(SANTIAGO, base["id"], "Aprobada")
    comprobar(
        "y tener la materia aprobada también alcanza",
        del_plan(otra["id"])["estado"] == "Habilitada",
    )

    condicion(SANTIAGO, base["id"], "En curso")
    comprobar(
        "estar cursándola todavía no alcanza",
        del_plan(otra["id"])["estado"] == "Bloqueada por correlatividad",
    )

    # ------------------------------------------------------------------
    grupo("Con «alguna» alcanza con una")
    equiv = crear("Taller de Lenguajes", "TAL-1")
    configurar(
        otra["id"],
        correlativas={
            "cursar": {
                "modo": "alguna",
                "requisitos": [requisito(base["id"], "Aprobada"), requisito(equiv["id"], "Aprobada")],
            }
        },
    )
    condicion(SANTIAGO, base["id"], None)
    condicion(SANTIAGO, equiv["id"], None)
    visto = del_plan(otra["id"])
    comprobar("sin ninguna de las dos, bloqueada", visto["estado"] == "Bloqueada por correlatividad")
    comprobar(
        "y el motivo avisa que alcanza con una",
        "alguna" in (visto["motivo"] or "").lower(),
        visto["motivo"],
    )
    condicion(SANTIAGO, equiv["id"], "Aprobada")
    comprobar(
        "con una sola de las dos ya se habilita",
        del_plan(otra["id"])["estado"] == "Habilitada",
        del_plan(otra["id"])["motivo"],
    )

    # ------------------------------------------------------------------
    grupo("Para cursar y para rendir son dos requisitos distintos")
    configurar(
        otra["id"],
        correlativas={
            "cursar": {"modo": "todas", "requisitos": [requisito(base["id"], "Regular")]},
            "rendir": {"modo": "todas", "requisitos": [requisito(base["id"], "Aprobada")]},
        },
    )
    condicion(SANTIAGO, base["id"], "Regular")
    visto = del_plan(otra["id"])
    comprobar("con la base regular puede cursar", visto["estado"] == "Habilitada")
    comprobar(
        "la pantalla muestra las dos listas",
        visto["correlativas"]["requisitos"][0]["condicion"] == "Regular"
        and visto["correlativasRendir"]["requisitos"][0]["condicion"] == "Aprobada",
        (visto["correlativas"], visto["correlativasRendir"]),
    )

    # Y la mesa de examen de esa materia pide lo de "rendir"
    mesa = _mesa_para(otra["id"])
    condicion(SANTIAGO, otra["id"], "Regular")
    estado = _estado_de_mesa(mesa)
    comprobar(
        "la mesa exige la correlativa de rendir",
        estado["estado"] == "No habilitado" and "aprobada" in (estado["motivo"] or "").lower(),
        estado,
    )
    condicion(SANTIAGO, base["id"], "Aprobada")
    comprobar(
        "y al aprobar la anterior, puede rendir",
        _estado_de_mesa(mesa)["estado"] == "Disponible",
        _estado_de_mesa(mesa),
    )
    condicion(SANTIAGO, otra["id"], None)

    # ------------------------------------------------------------------
    grupo("El cupo es el que se configuró")
    condicion(SANTIAGO, base["id"], "Aprobada")
    chica = crear("Seminario", "SEM-1", cupo=1)
    d.inscripciones_materias.append(
        {"id": d.nuevo_id_inscripcion_materia(), "personaId": 12,
         "materiaId": chica["id"], "fecha": d.iso(d.ahora())}
    )
    visto = del_plan(chica["id"])
    comprobar("con el cupo lleno no quedan lugares", visto["estado"] == "Sin cupos disponibles", visto["estado"])
    comprobar("y no deja anotarse", anotarse(chica["id"]).status_code == 403)
    comprobar("los lugares se cuentan", visto["lugares"] == 0 and visto["cupo"] == 1, (visto["lugares"], visto["cupo"]))

    libre = crear("Seminario II", "SEM-2", cupo=None)
    visto = del_plan(libre["id"])
    comprobar("sin cupo configurado, no hay límite", visto["cupo"] is None and visto["lugares"] is None, visto)
    comprobar("y se puede anotar igual", visto["estado"] == "Habilitada", visto["estado"])

    # ------------------------------------------------------------------
    grupo("Una materia dada de baja deja de ofrecerse")
    comprobar("estaba en el plan del alumno", del_plan(libre["id"]) is not None)
    configurar(libre["id"], activa=False)
    comprobar("al darla de baja, desaparece del plan", del_plan(libre["id"]) is None)
    comprobar("y el servidor rechaza la inscripción", anotarse(libre["id"]).status_code == 403)

    # Pero si el alumno ya tuvo que ver con ella, la sigue viendo
    condicion(SANTIAGO, libre["id"], "Aprobada")
    visto = del_plan(libre["id"])
    comprobar("quien ya la cursó la sigue viendo", visto is not None and visto["estado"] == "Aprobada", visto)
    condicion(SANTIAGO, libre["id"], None)
    configurar(libre["id"], activa=True)

    # ------------------------------------------------------------------
    grupo("Y tampoco entra por la puerta de atrás")
    # Entrar a una comisión inscribe en las materias que esa comisión dicta.
    # Si una está dada de baja, no tiene que colarse por ahí: la comisión
    # conserva su cuadro de materias aunque el campus deje de ofrecer una.
    de_baja = crear("Cosmografía", "COS-1")
    asociacion = next(a for a in d.asociaciones_academicas if a.get("carreraId") == 1)
    comision = next(c for c in d.comisiones if c.get("carreraId") == 1)
    d.dictados.append(
        {
            "id": max((x["id"] for x in d.dictados), default=0) + 1,
            "comisionId": comision["id"],
            "materiaId": de_baja["id"],
            "docentes": [],
        }
    )
    alumno = asociacion["personaId"]

    # Con la materia en pie, pasar a esa comisión sí la agrega
    como(SECRETARIA)
    r = cliente.patch(
        f"/api/institucion/asignaciones/{asociacion['id']}",
        json={"comisionId": comision["id"]},
    )
    comprobar("entrar a la comisión agrega sus materias", r.status_code == 200, r.status_code)
    comprobar(
        "incluida la nueva",
        any(i["personaId"] == alumno and i["materiaId"] == de_baja["id"]
            for i in d.inscripciones_materias),
        r.json().get("materiasVinculadas"),
    )
    # Lo que el estudiante ve: inscripto **y** con su módulo donde cursarla.
    # Estar anotado a seis materias y tener Módulos vacío es el peor estado
    # posible, porque todo parece andar menos lo único que importa.
    como(alumno)
    mios = cliente.get("/api/cursos")
    nombres = [c["nombre"] for c in mios.json()] if mios.status_code == 200 else []
    comprobar(
        "y la materia aparece en su pantalla de Módulos",
        de_baja["nombre"] in nombres,
        (mios.status_code, nombres[:8]),
    )

    anotado = [
        d.buscar_materia(i["materiaId"])["nombre"]
        for i in d.inscripciones_materias
        if i["personaId"] == alumno and d.buscar_materia(i["materiaId"])
    ]
    comprobar(
        "y no le falta ninguna de las que está inscripto",
        all(x in nombres for x in anotado),
        [x for x in anotado if x not in nombres],
    )

    # Se la da de baja y se repite con otro estudiante de la misma carrera
    configurar(de_baja["id"], activa=False)
    otra_asoc = next(
        a for a in d.asociaciones_academicas
        if a.get("carreraId") == 1 and a["personaId"] != alumno
    )
    otro = otra_asoc["personaId"]
    como(SECRETARIA)
    r = cliente.patch(
        f"/api/institucion/asignaciones/{otra_asoc['id']}",
        json={"comisionId": comision["id"]},
    )
    comprobar("la asignación sigue funcionando", r.status_code == 200, r.status_code)
    comprobar(
        "pero la materia de baja no se cuela",
        not any(i["personaId"] == otro and i["materiaId"] == de_baja["id"]
                for i in d.inscripciones_materias),
        r.json().get("materiasVinculadas"),
    )

    # ------------------------------------------------------------------
    grupo("Anotarse hace lo que dice que hace")
    antes = len(d.inscripciones_materias)
    r = anotarse(libre["id"])
    comprobar("la inscripción se acepta", r.status_code == 201, (r.status_code, r.text[:150]))
    comprobar("queda registrada", len(d.inscripciones_materias) == antes + 1)
    comprobar("y la materia entra a Módulos", r.json()["modulo"]["nombre"] == "Seminario II", r.json().get("modulo"))
    comprobar("el plan ya la muestra inscripta", del_plan(libre["id"])["estado"] == "Inscripto")
    comprobar("no se puede anotar dos veces", anotarse(libre["id"]).status_code == 409)

    comprobar("y queda anotado en la auditoría",
              any(e["modulo"] == "academico" and "Seminario II" in (e.get("elemento") or "")
                  for e in d.auditoria))

    como(SANTIAGO)
    baja = cliente.delete(f"{PLAN}/{libre['id']}")
    comprobar("la baja se acepta", baja.status_code == 200, baja.status_code)
    comprobar("y el módulo que creó se va con ella",
              d.buscar_curso(d.buscar_materia(libre["id"]).get("cursoId")) is None)

    # ------------------------------------------------------------------
    grupo("Una materia de otro plan no se cursa")
    ajena = crear("Anatomía", "ANA-1", carreraId=2, planId=_plan_de_carrera(2))
    if ajena:
        comprobar("no aparece en el plan del alumno", del_plan(ajena["id"]) is None)
        comprobar("y el servidor la rechaza", anotarse(ajena["id"]).status_code == 403)

    # ------------------------------------------------------------------
    grupo("Fuera del período no se anota nadie")
    periodo = dict(d.periodo_inscripcion_materias)
    d.periodo_inscripcion_materias["desde"] = d.iso(d.ahora().replace(year=d.ahora().year - 2))
    d.periodo_inscripcion_materias["hasta"] = d.iso(d.ahora().replace(year=d.ahora().year - 1))
    visto = del_plan(base["id"])
    comprobar("la pantalla lo avisa", not visto["puedeInscribirse"], visto["motivo"])
    comprobar("y el servidor lo rechaza", anotarse(chica["id"]).status_code == 403)
    d.periodo_inscripcion_materias.update(periodo)

    # ------------------------------------------------------------------
    grupo("Dar de baja no rompe lo que ya pasó")
    con_historia = crear("Historia", "HIS-1")
    condicion(SANTIAGO, con_historia["id"], "Aprobada")
    como(SECRETARIA)
    r = cliente.delete(f"{ADMIN}/{con_historia['id']}")
    comprobar("no se elimina: se da de baja", r.status_code == 200 and r.json()["eliminada"] is False, r.json())
    comprobar("la materia sigue existiendo", d.buscar_materia(con_historia["id"]) is not None)
    comprobar("y el historial del alumno queda intacto",
              d.condicion_en(SANTIAGO, con_historia["id"]) == "Aprobada")

    sin_nada = crear("Latín", "LAT-1")
    como(SECRETARIA)
    r = cliente.delete(f"{ADMIN}/{sin_nada['id']}")
    comprobar("una materia sin actividad sí se elimina", r.json()["eliminada"] is True, r.json())
    comprobar("y deja de estar en el plan", d.buscar_materia(sin_nada["id"]) is None)


# ===================== Ayudas que necesitan al cliente =====================
def _codigo_repetido(codigo: str) -> int:
    como(SECRETARIA)
    return cliente.post(
        ADMIN,
        json={"nombre": "Otra", "codigo": codigo, "carreraId": 1, "planId": 1,
              "anio": 1, "cuatrimestre": 1},
    ).status_code


def _plan_de_carrera(carrera_id: int):
    """El plan de esa carrera. Si no tiene, se le crea uno."""
    plan = next((p for p in d.planes_estudio if p.get("carreraId") == carrera_id), None)
    if plan:
        return plan["id"]
    como(SECRETARIA)
    r = cliente.post(
        "/api/institucion/planes",
        json={"carreraId": carrera_id, "nombre": "Plan de prueba", "anio": 2024},
    )
    assert r.status_code == 201, (r.status_code, r.text[:200])
    return next(p for p in d.planes_estudio if p.get("carreraId") == carrera_id)["id"]


def _mesa_para(materia_id: int) -> dict:
    """Una mesa con la inscripción abierta para esa materia."""
    mesa = {
        "id": max((m["id"] for m in d.mesas_examen), default=0) + 1,
        "materiaId": materia_id,
        "fecha": d.a_dias(10),
        "hora": "09:00",
        "lugar": "Aula 12",
        "modalidad": d.MODALIDADES_FINAL[0],
        "llamado": d.LLAMADOS[0],
        "tribunal": [MARIA],
        "cupo": None,
        "estado": "programada",
        "inscripcionDesde": d.a_dias(-2),
        "inscripcionHasta": d.a_dias(5),
        "actaCerrada": False,
    }
    d.mesas_examen.append(mesa)
    return mesa


def _estado_de_mesa(mesa: dict) -> dict:
    from app.servicios import academico as ac

    return ac.estado_de_mesa(SANTIAGO, mesa)


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
