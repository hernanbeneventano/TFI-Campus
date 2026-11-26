"""Pruebas de la entrega de trabajos.

Es el circuito central de un campus —entregar algo y que lo corrijan— y
hasta ahora no existía: el botón estaba deshabilitado y la colección
`entregas` no la escribía nadie, aunque tres pantallas la leyeran.

Lo que más importa acá es que **«entregada» sea de cada alumno**. Antes era
un solo booleano del trabajo, igual para todo el curso: con entregas de
verdad, eso le mostraba «Entregada» a quien no entregó nada y le sacaba el
pendiente de la lista. Es un error que no se ve probando con un solo alumno.

Uso (desde backend/):
    python -m pruebas.entregas
"""

from __future__ import annotations

import base64
import sys


from app import datos as d

from . import escenario
from .cliente import como, crear_cliente

SANTIAGO = 1  # estudiante
OTRO = 3  # otro estudiante del mismo módulo
MARIA = 2  # docente

PDF = base64.b64encode(b"%PDF-1.4\n% trabajo\n%%EOF\n").decode()

pasadas = 0
fallas: list[str] = []

escenario.cargar()

cliente = crear_cliente()
como(SANTIAGO)


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


def subir(id_tarea: int, nombre: str = "tp.pdf", comentario=None, contenido=PDF, extension="pdf",
          tipo="application/pdf"):
    return cliente.post(
        f"/api/tareas/{id_tarea}/mi-entrega",
        json={"nombre": nombre, "tipo": tipo, "extension": extension,
              "contenido": contenido, "comentario": comentario},
    )


def un_trabajo_entregable() -> dict:
    """Un trabajo virtual de entrega, y **que esté dentro de una carpeta**.

    Lo segundo importa: las pantallas muestran los trabajos desde el
    contenido del módulo, así que una tarea suelta —que exista en `tareas`
    pero que ninguna carpeta referencie— no aparece en ningún lado y la
    prueba no comprobaría nada.
    """
    mios = {
        c["id"]
        for c in d.cursos
        if any(p["id"] == SANTIAGO for p in d.participantes_de_curso(c))
    }
    for curso_id in sorted(mios):
        curso = d.buscar_curso(curso_id)
        for carpeta in d.carpetas_de_curso(curso):
            for item in carpeta["items"]:
                if item.get("tipo") != "tarea":
                    continue
                t = d.buscar_tarea(item.get("tareaId"))
                if (
                    t
                    and t.get("formato", "entrega") != "cuestionario"
                    and t.get("modalidad", "virtual") != "presencial"
                ):
                    return t
    raise SystemExit("El escenario no tiene ningún trabajo entregable en una carpeta")


def correr() -> None:
    print("Pruebas de la entrega de trabajos (en proceso)\n")
    tarea = un_trabajo_entregable()
    idt = tarea["id"]
    # Que no arrastre nada de antes
    d.entregas[:] = [e for e in d.entregas if e["tareaId"] != idt]
    tarea["cerrada"] = False  # abierta, sin pelear con la fecha del escenario

    # ------------------------------------------------------------------
    grupo("Entregar")
    como(SANTIAGO)
    antes = cliente.get(f"/api/tareas/{idt}/mi-entrega").json()
    comprobar("al principio no hay nada entregado", antes["entrega"] is None, antes)
    comprobar("y la entrega está abierta", antes["abierta"] is True)

    r = subir(idt, comentario="Subo el punto 4 aparte.")
    comprobar("se acepta el trabajo", r.status_code == 201, (r.status_code, r.text[:140]))
    entrega = r.json()["entrega"]
    comprobar("queda el archivo con su nombre", entrega["archivo"]["nombre"] == "tp.pdf", entrega)
    comprobar("y el comentario", entrega["comentario"] == "Subo el punto 4 aparte.")
    comprobar("con una dirección para bajarlo", bool(entrega["archivo"].get("url")))

    # ------------------------------------------------------------------
    grupo("«Entregada» es de cada alumno, no del curso")
    # Es el error que no se ve probando con uno solo.
    curso = d.buscar_curso(tarea["cursoId"])

    def entregada_para(persona_id):
        como(persona_id)
        datos = cliente.get(f"/api/cursos/{curso['id']}/modulo").json()
        for carpeta in datos["carpetas"]:
            for item in carpeta["items"]:
                if item.get("tareaId") == idt:
                    return item["entregada"]
        return None

    comprobar("quien entregó la ve entregada", entregada_para(SANTIAGO) is True)
    otro = next(
        (p["id"] for p in d.participantes_de_curso(curso)
         if d.tiene_rol(p, "Estudiante") and p["id"] != SANTIAGO),
        None,
    )
    if otro:
        comprobar("y quien no entregó, no", entregada_para(otro) is False)

    como(SANTIAGO)
    pend = cliente.get("/api/tareas/pendientes").json()
    titulos = [t["titulo"] for t in pend["recientes"] + pend["atrasadas"]]
    comprobar("sale de los pendientes de quien entregó", tarea["titulo"] not in titulos, titulos)
    if otro:
        como(otro)
        pend = cliente.get("/api/tareas/pendientes").json()
        titulos = [t["titulo"] for t in pend["recientes"] + pend["atrasadas"]]
        comprobar("y sigue pendiente para el que no", tarea["titulo"] in titulos, titulos)

    # ------------------------------------------------------------------
    grupo("Los pendientes son los de uno")
    como(SANTIAGO)
    pend = cliente.get("/api/tareas/pendientes").json()
    mios = {
        c["id"]
        for c in d.cursos
        if any(p["id"] == SANTIAGO for p in d.participantes_de_curso(c))
    }
    ajenas = [
        t["titulo"]
        for t in pend["recientes"] + pend["atrasadas"]
        if t["cursoId"] not in mios
    ]
    comprobar("no aparecen tareas de módulos que no cursa", not ajenas, ajenas)

    # ------------------------------------------------------------------
    grupo("Vale la última")
    r = subir(idt, nombre="tp-corregido.pdf")
    comprobar("se puede volver a entregar", r.status_code == 201, r.status_code)
    comprobar(
        "y reemplaza a la anterior",
        r.json()["entrega"]["archivo"]["nombre"] == "tp-corregido.pdf",
    )
    comprobar(
        "sin duplicar la entrega",
        sum(1 for e in d.entregas if e["tareaId"] == idt and e["personaId"] == SANTIAGO) == 1,
    )

    # ------------------------------------------------------------------
    grupo("Lo que no se acepta")
    r = subir(idt, nombre="virus.exe", extension="exe", tipo="application/x-msdownload",
              contenido=base64.b64encode(b"MZ\x90\x00").decode())
    comprobar("un ejecutable se rechaza", r.status_code == 415, r.status_code)

    r = subir(idt, nombre="trucho.pdf", contenido=base64.b64encode(b"MZ\x90\x00").decode())
    comprobar("y un .exe renombrado a .pdf también", r.status_code == 415, r.status_code)

    como(MARIA)
    r = subir(idt)
    comprobar("el docente no entrega su propio trabajo", r.status_code in (400, 403), r.status_code)

    # ------------------------------------------------------------------
    grupo("El docente la ve")
    como(MARIA)
    datos = cliente.get(f"/api/cursos/{curso['id']}/modulo").json()
    vista = None
    for carpeta in datos["carpetas"]:
        r = cliente.get(f"/api/cursos/{curso['id']}/carpetas/{carpeta['id']}/entregas")
        if r.status_code != 200:
            continue
        for fila in r.json()["alumnos"]:
            for t in fila["detalle"]:
                if t["tareaId"] == idt and t["entregado"]:
                    vista = (fila, t)
    comprobar("aparece en «quién cumplió»", vista is not None)
    if vista:
        comprobar("con el archivo que subió el alumno",
                  (vista[1].get("archivo") or {}).get("nombre") == "tp-corregido.pdf",
                  vista[1].get("archivo"))

    # ------------------------------------------------------------------
    grupo("Retirar")
    como(SANTIAGO)
    r = cliente.delete(f"/api/tareas/{idt}/mi-entrega")
    comprobar("se puede retirar mientras siga abierta", r.status_code == 200, r.status_code)
    comprobar("y vuelve a no haber nada", cliente.get(f"/api/tareas/{idt}/mi-entrega").json()["entrega"] is None)
    comprobar("retirar dos veces no se puede",
              cliente.delete(f"/api/tareas/{idt}/mi-entrega").status_code == 409)

    # ------------------------------------------------------------------
    grupo("Con la entrega cerrada")
    tarea["cerrada"] = True
    comprobar("no se entrega", subir(idt).status_code == 403)
    estado = cliente.get(f"/api/tareas/{idt}/mi-entrega").json()
    comprobar("y la pantalla lo sabe", estado["abierta"] is False)

    # Lo que ya estaba entregado no se retira después del cierre
    tarea["cerrada"] = False
    subir(idt)
    tarea["cerrada"] = True
    comprobar("lo ya entregado tampoco se retira",
              cliente.delete(f"/api/tareas/{idt}/mi-entrega").status_code == 403)

    # ------------------------------------------------------------------
    grupo("Un trabajo que no se sube")
    cuestionario = next(
        (t for t in d.tareas if t.get("formato") == "cuestionario" and t["cursoId"] in mios), None
    )
    if cuestionario:
        comprobar("un cuestionario no se entrega como archivo",
                  subir(cuestionario["id"]).status_code == 400)
    presencial = next(
        (t for t in d.tareas if t.get("modalidad") == "presencial" and t["cursoId"] in mios), None
    )
    if presencial:
        comprobar("un presencial tampoco", subir(presencial["id"]).status_code == 400)

    # ------------------------------------------------------------------
    grupo("De un módulo ajeno, nada")
    ajena = next((t for t in d.tareas if t["cursoId"] not in mios), None)
    if ajena:
        comprobar("no se entrega en un módulo que no se cursa",
                  subir(ajena["id"]).status_code == 403)


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
