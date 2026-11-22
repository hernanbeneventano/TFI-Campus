"""Pruebas de la persistencia en Firestore y del almacenamiento de archivos.

**No tocan Firestore ni Cloudflare.** Corren contra la memoria del proceso,
igual que las demás suites, y comprueban las decisiones que se pueden
comprobar sin red: qué se guarda, con qué nombre, qué pasa con los
contadores y qué no se sube nunca.

Lo que más importa acá es la primera comprobación: **que ninguna colección
quede sin guardar**. La persistencia funciona por diferencia sobre un mapa de
colecciones; si alguien agrega una lista a `datos.py` y se olvida de anotarla
en ese mapa, el campus la va a usar con normalidad y no la va a guardar
nunca. Nadie se entera hasta que se reinicia el servidor y los datos no
están. Esa prueba es la que lo agarra.

Uso (desde backend/):
    python -m pruebas.persistencia
"""

from __future__ import annotations

import sys

from app import datos as d
from app.servicios import almacenamiento as alm
from app.servicios import persistencia as p

from . import escenario

pasadas = 0
fallas: list[str] = []


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


# Lo que no es del campus sino herramientas del módulo: no son colecciones.
NO_SON_DATOS = {
    "AQUI",
    "usuario_actual",  # quién está probando; no es un dato de la facultad
    "carreras",  # nombres sueltos para el filtro de la Biblioteca (va en configuracion)
    "participantes",  # va en POR_CURSO
    "contenidos",
    "anuncios",
}


def correr() -> None:
    print("Pruebas de la persistencia (en proceso, sin tocar Firestore)\n")
    escenario.cargar()

    # ------------------------------------------------------------------
    grupo("Ninguna colección queda sin guardar")
    cubiertas = (
        {atributo for atributo, _ in p.REGISTROS.values()}
        | set(p.POR_CURSO.values())
        | set(p.CONFIGURACION)
    )

    sueltas = []
    for nombre in dir(d):
        if nombre.startswith("_") or nombre in NO_SON_DATOS or nombre in cubiertas:
            continue
        valor = getattr(d, nombre)
        # Una lista de diccionarios o un diccionario de configuración son
        # datos; una función o una constante suelta, no.
        if isinstance(valor, list) and valor and isinstance(valor[0], dict):
            sueltas.append(nombre)

    comprobar(
        "todas las listas de datos.py están en el mapa",
        not sueltas,
        f"sin guardar: {sueltas}",
    )

    comprobar(
        "y el mapa no nombra nada que no exista",
        all(hasattr(d, atributo) for atributo, _ in p.REGISTROS.values()),
        [a for a, _ in p.REGISTROS.values() if not hasattr(d, a)],
    )

    # ------------------------------------------------------------------
    grupo("Cada registro cae en un documento distinto")
    documentos = p._documentos()
    comprobar("se arma el mapa de documentos", len(documentos) > 0, len(documentos))

    # Si dos registros compartieran clave, uno pisaría al otro en silencio:
    # el campus seguiría andando y un dato desaparecería al reiniciar.
    por_coleccion: dict[str, list[str]] = {}
    for coleccion, documento in documentos:
        por_coleccion.setdefault(coleccion, []).append(documento)
    repetidas = {c: v for c, v in por_coleccion.items() if len(v) != len(set(v))}
    comprobar("ninguna clave se repite dentro de su colección", not repetidas, repetidas)

    comprobar(
        "ninguna clave queda vacía o en None",
        all(doc and "None" not in doc for _, doc in documentos),
        [k for k in documentos if not k[1] or "None" in k[1]][:5],
    )

    # ------------------------------------------------------------------
    # La auditoría no se compara huella por huella: solo se agrega. Es lo que
    # saca el registro —que crece todos los días— del costo de cada petición,
    # pero si el camino aparte se rompiera, los eventos dejarían de guardarse
    # **sin que nada falle**: el campus seguiría andando y el registro
    # quedaría vacío al reiniciar.
    grupo("Las colecciones que solo crecen se guardan igual")
    comprobar(
        "la auditoría no entra en la comparación por huella",
        not any(c == "auditoria" for c, _ in p._documentos()),
    )
    comprobar(
        "pero sigue declarada, así que la cuenta de arriba la cubre",
        "auditoria" in p.REGISTROS and "auditoria" in p.SOLO_AGREGAR,
    )

    p._ya_escritos.clear()
    antes = len(p._lo_nuevo_que_solo_crece())
    comprobar("se ofrecen a guardar los eventos que hay", antes == len(d.auditoria), antes)

    d.auditoria.append({"id": 999999, "accion": "prueba", "modulo": "sesion"})
    ahora = p._lo_nuevo_que_solo_crece()
    comprobar(
        "un evento nuevo entra en lo que hay que escribir",
        any(doc == "999999" for _, doc, _ in ahora),
        [doc for _, doc, _ in ahora][-3:],
    )

    # Y una vez escrito no se vuelve a mandar: si no, cada petición
    # reescribiría el registro entero y la cuenta de Firestore lo notaría.
    for coleccion, doc, _valor in ahora:
        p._ya_escritos.setdefault(coleccion, set()).add(doc)
    comprobar("lo ya escrito no se repite", p._lo_nuevo_que_solo_crece() == [])

    d.auditoria[:] = [e for e in d.auditoria if e.get("id") != 999999]
    p._ya_escritos.clear()

    # ------------------------------------------------------------------
    grupo("Los contadores no pisan lo que ya existe")
    # Es el error más caro: al reiniciar, los contadores arrancan en 100 y la
    # próxima alta reemplazaría una materia que ya estaba.
    d._proximos["materia"] = 1
    d._proximos["comision"] = 1
    p._ajustar_contadores()

    mayor_materia = max((m["id"] for m in d.materias_plan), default=0)
    comprobar(
        "el contador de materias queda por encima del id más alto",
        d._proximos["materia"] > mayor_materia,
        (d._proximos["materia"], mayor_materia),
    )
    mayor_comision = max((c["id"] for c in d.comisiones), default=0)
    comprobar(
        "y el de comisiones también",
        d._proximos["comision"] > mayor_comision,
        (d._proximos["comision"], mayor_comision),
    )
    comprobar(
        "el contador viaja a la base",
        ("configuracion", "contadores") in p._documentos(),
    )

    # ------------------------------------------------------------------
    grupo("Lo que la facultad carga no se inventa")
    antes = {a: len(getattr(d, a)) for a in p.INSTITUCIONALES}
    comprobar("el escenario de prueba tiene estructura", any(antes.values()), antes)
    p.vaciar_lo_institucional()
    comprobar(
        "la siembra deja vacías carreras, sedes, planes, comisiones y materias",
        all(len(getattr(d, a)) == 0 for a in p.INSTITUCIONALES),
        {a: len(getattr(d, a)) for a in p.INSTITUCIONALES},
    )
    comprobar("pero no toca a las personas", len(d.personas) > 0, len(d.personas))
    escenario.cargar()

    # ------------------------------------------------------------------
    grupo("Nada se escribe sin que alguien lo encienda")
    comprobar("en las pruebas la persistencia está apagada", p.activo() is False)
    comprobar("y guardar no hace nada", p.guardar_cambios() == 0)

    # ------------------------------------------------------------------
    grupo("Los archivos: dónde van y cómo se llaman")
    comprobar(
        "cada apartado tiene su carpeta",
        alm.clave(alm.BIBLIOTECA, 7, 42, nombre="apunte.pdf") == "biblioteca/7/42/apunte.pdf",
        alm.clave(alm.BIBLIOTECA, 7, 42, nombre="apunte.pdf"),
    )
    comprobar(
        "sin registro, el archivo va igual a su carpeta",
        alm.clave(alm.PERFILES, nombre="foto.png") == "perfiles/foto.png",
    )
    # El nombre lo limpia `servicios/archivos.nombre_seguro` antes de llegar
    # acá: es lo que evita escribir fuera de la carpeta que corresponde.
    from app.servicios.archivos import nombre_seguro

    comprobar(
        "un nombre con ruta adentro no escapa de su carpeta",
        alm.clave(alm.MODULOS, 1, 2, nombre=nombre_seguro("../../otra/clave.pdf", "pdf"))
        == "modulos/1/2/clave.pdf",
        alm.clave(alm.MODULOS, 1, 2, nombre=nombre_seguro("../../otra/clave.pdf", "pdf")),
    )

    # ------------------------------------------------------------------
    grupo("Sin Cloudflare configurado, el campus sigue andando")
    comprobar("R2 no está configurado en las pruebas", alm.configurado() is False)
    alm.subir("biblioteca/1/1/prueba.pdf", b"%PDF-1.4 hola", "application/pdf")
    comprobar(
        "lo subido se puede volver a leer",
        alm.leer("biblioteca/1/1/prueba.pdf") == b"%PDF-1.4 hola",
    )
    comprobar(
        "no se entrega un enlace que no se puede firmar",
        alm.enlace_temporal("biblioteca/1/1/prueba.pdf") is None,
    )
    comprobar(
        "ni uno de subida",
        alm.enlace_para_subir("biblioteca/1/1/prueba.pdf", "application/pdf") is None,
    )

    # ------------------------------------------------------------------
    grupo("La ficha del archivo")
    ficha = alm.registrar(
        "biblioteca/1/1/prueba.pdf",
        nombre="prueba.pdf",
        tipo="application/pdf",
        tamano=13,
        persona_id=1,
        modulo=alm.BIBLIOTECA,
        registro_id=1,
    )
    comprobar("queda anotada", alm.ficha_de("biblioteca/1/1/prueba.pdf") is not None)
    comprobar("dice quién la subió y de qué registro es",
              ficha["subidoPor"] == 1 and ficha["registroId"] == 1)
    comprobar("y dónde está guardada", ficha["almacen"] == "memoria", ficha["almacen"])
    comprobar(
        "no se guarda ningún byte en la ficha",
        not any(isinstance(v, (bytes, bytearray)) for v in ficha.values()),
    )

    # Volver a subir el mismo archivo actualiza la ficha, no la duplica
    cuantas = len(d.archivos_subidos)
    alm.registrar(
        "biblioteca/1/1/prueba.pdf", nombre="prueba.pdf", tipo="application/pdf",
        tamano=99, persona_id=1, modulo=alm.BIBLIOTECA, registro_id=1,
    )
    comprobar("subirlo de nuevo no duplica la ficha", len(d.archivos_subidos) == cuantas)
    comprobar("y la actualiza", alm.ficha_de("biblioteca/1/1/prueba.pdf")["tamano"] == 99)

    alm.olvidar("biblioteca/1/1/prueba.pdf")
    comprobar("al olvidarlo se va la ficha", alm.ficha_de("biblioteca/1/1/prueba.pdf") is None)
    comprobar("y el archivo", alm.leer("biblioteca/1/1/prueba.pdf") is None)


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
