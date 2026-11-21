"""El registro de auditoría: consultarlo y exportarlo.

**No hay POST, ni PUT, ni DELETE.** Es a propósito: los eventos los escribe
`servicios/auditoria.registrar` desde cada módulo, y desde afuera el registro
solo se lee. Que no exista la ruta es más fuerte que prohibirla.

Quién ve qué
------------
- **Administrador**: todo.
- **Supervisor**: lo académico. No ve `usuarios`, que es donde se cambian
  roles y se suspenden cuentas: eso es del administrador.
- **Docente**: no entra al registro general (403). Tiene `/mis-materias`, que
  le devuelve lo de las materias que dicta y nada más.
- **Estudiante**: 403 en todo.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from .. import datos as d
from ..servicios import ambito
from ..servicios import auditoria as a
from ..servicios import persistencia
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/auditoria", tags=["Auditoría"])

# Lo académico, que es el ámbito del supervisor
MODULOS_ACADEMICOS = {
    "academico", "asistencias", "calificaciones", "finales", "biblioteca", "modulos",
}


def _de_su_ambito(yo: dict, eventos: list[dict]) -> list[dict]:
    """Recorta el registro al ámbito de quien pregunta.

    El administrador lo ve entero; a quien supervisa se le muestra lo de sus
    carreras y sedes, si la facultad se las fijó. Ver `servicios/ambito.py`.
    """
    if not ambito.recortado(yo):
        return eventos
    return [e for e in eventos if ambito.alcanza_evento(yo, e)]


def _modulos_que_ve(yo: dict) -> set[str] | None:
    """Los módulos del registro general. `None` quiere decir todos."""
    if d.tiene_rol(yo, "Administrador"):
        return None
    if d.tiene_rol(yo, "Supervisor"):
        return set(MODULOS_ACADEMICOS)
    return set()


def _exigir_acceso(yo: dict) -> set[str] | None:
    permitidos = _modulos_que_ve(yo)
    if permitidos is not None and not permitidos:
        raise HTTPException(
            403, "El registro de auditoría es para la administración y la supervisión"
        )
    return permitidos


def _paginar(lista: list[dict], p: dict) -> dict:
    """Miles de eventos no entran en una pantalla ni en una respuesta."""
    try:
        pagina = max(1, int(p.get("pagina") or 1))
    except ValueError:
        pagina = 1
    try:
        por_pagina = min(200, max(1, int(p.get("porPagina") or 25)))
    except ValueError:
        por_pagina = 25

    desde = (pagina - 1) * por_pagina
    return {
        "pagina": pagina,
        "porPagina": por_pagina,
        "paginas": max(1, -(-len(lista) // por_pagina)),
        "recortada": lista[desde : desde + por_pagina],
    }


# ===================== Rutas con nombre fijo =====================
# Antes de /{id}, si no "opciones" se tomaría como el id de un evento.


@router.get("/opciones", summary="Los filtros y qué puede ver quien pregunta")
def opciones(yo: dict = UsuarioActual):
    permitidos = _exigir_acceso(yo)

    return {
        "acciones": [{"id": k, "nombre": v} for k, v in a.ACCIONES.items()],
        "modulos": [
            {"id": k, "nombre": v}
            for k, v in a.MODULOS.items()
            if permitidos is None or k in permitidos
        ],
        "resultados": [{"id": k, "nombre": v} for k, v in a.RESULTADOS.items()],
        "roles": d.ROLES,
        # Los filtros también se recortan al ámbito: ofrecer una carrera que
        # no se puede mirar es prometer un resultado vacío y hacer dudar de si
        # no pasó nada o si no se ve.
        "carreras": [
            {"id": c["id"], "nombre": c["nombre"]}
            for c in d.carreras_institucion
            if ambito.alcanza_carrera(yo, c["id"])
        ],
        "sedes": [
            {"id": s["id"], "nombre": s["nombre"]}
            for s in d.sedes
            if ambito.alcanza_sede(yo, s["id"])
        ],
        "comisiones": [
            {
                "id": c["id"],
                "nombre": c["nombre"],
                "carreraId": c.get("carreraId"),
                "sedeId": c.get("sedeId"),
            }
            for c in d.comisiones
            if ambito.alcanza_carrera(yo, c.get("carreraId"))
            and ambito.alcanza_sede(yo, c.get("sedeId"))
        ],
        # Para el desplegable de "Usuario": solo quienes dejaron huella, que
        # es mucho más corto que todo el campus y más útil.
        "usuarios": sorted(
            (
                {"id": i, "nombre": n}
                for i, n in {
                    e["quienId"]: e["quien"]
                    for e in _de_su_ambito(yo, a.buscar({}, permitidos))
                    if e.get("quienId")
                }.items()
            ),
            key=lambda u: u["nombre"].lower(),
        ),
        "puedeExportar": True,
        # Para que la pantalla pueda decir hasta dónde llega lo que se está
        # mirando. Un registro recortado que no avisa que lo está se lee como
        # el registro entero.
        "ambito": ambito.resumen(yo),
        # Si la facultad configuró dejar en memoria solo lo reciente, desde
        # cuándo hay datos acá. La pantalla tiene que decirlo: un registro
        # recortado que no avisa se lee como el registro entero, y entonces
        # "no pasó nada" y "no lo tengo cargado" se confunden.
        "desde": persistencia.auditoria_desde(),
    }


@router.get("/mis-materias", summary="Lo que pasó en las materias que dicta")
def mis_materias(request: Request, yo: dict = UsuarioActual):
    """La vista del docente.

    No es el registro general recortado: es solo lo de **sus** materias, y por
    eso tiene su propia ruta. Un docente no tiene por qué saber qué hizo la
    secretaría con las cuentas.
    """
    if not d.tiene_rol(yo, "Docente"):
        raise HTTPException(403, "Esto es para los docentes de una materia")

    mias = {m["id"] for m in d.materias_que_dicta(yo["id"])}
    if not mias:
        return {"eventos": [], "resumen": a.resumir([]), "materias": [], "total": 0,
                "pagina": 1, "paginas": 1, "porPagina": 25}

    p = dict(request.query_params)
    eventos = [
        e
        for e in a.buscar(p, {"asistencias", "calificaciones", "biblioteca", "modulos", "finales"})
        if e.get("materiaId") in mias
    ]

    paginacion = _paginar(eventos, p)
    recortada = paginacion.pop("recortada")

    return {
        "eventos": [a.con_nombres(e) for e in recortada],
        "resumen": a.resumir(eventos),
        "total": len(eventos),
        **paginacion,
        "materias": [
            {"id": m["id"], "nombre": m["nombre"], "codigo": m["codigo"]}
            for m in d.materias_que_dicta(yo["id"])
        ],
    }


@router.get("/exportar", summary="Bajar lo que se está viendo")
def exportar(request: Request, yo: dict = UsuarioActual):
    """Exporta **lo filtrado**, no todo el registro: lo que se ve es lo que baja.

    CSV y XLSX. El PDF lo hace el navegador al imprimir la pantalla: pagina,
    respeta los acentos y no hace falta una biblioteca más en el servidor.
    """
    permitidos = _exigir_acceso(yo)
    p = dict(request.query_params)
    formato = (p.get("formato") or "csv").lower()

    eventos = [a.con_nombres(e) for e in _de_su_ambito(yo, a.buscar(p, permitidos))]

    # Quien exporta también queda registrado: es una salida de datos.
    a.registrar(
        yo,
        "descarga",
        "usuarios",
        elemento="Registro de auditoría",
        elemento_tipo="auditoria",
        detalle=f"Exportó {len(eventos)} eventos en {formato.upper()}",
        peticion=request,
    )

    columnas = [
        ("cuando", "Fecha y hora"),
        ("quien", "Usuario"),
        ("rol", "Rol"),
        ("nombreAccion", "Acción"),
        ("nombreModulo", "Módulo"),
        ("elemento", "Elemento afectado"),
        ("afectada", "Persona afectada"),
        ("nombreResultado", "Resultado"),
        ("antes", "Valor anterior"),
        ("despues", "Valor nuevo"),
        ("detalle", "Detalle"),
        ("ip", "Dirección IP"),
    ]

    filas = [
        [_texto_plano(e.get(clave)) for clave, _ in columnas] for e in eventos
    ]
    titulos = [nombre for _, nombre in columnas]
    nombre_archivo = f"auditoria-{d.iso(d.ahora())[:10]}"

    if formato == "xlsx":
        return Response(
            content=_xlsx(titulos, filas),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{nombre_archivo}.xlsx"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    # CSV con punto y coma y BOM, para que Excel en castellano lo abra bien
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    escritor.writerow(titulos)
    escritor.writerows(filas)

    return Response(
        content="﻿" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_archivo}.csv"',
            "X-Content-Type-Options": "nosniff",
        },
    )


def _texto_plano(valor: Any) -> str:
    """Un valor cualquiera, como texto de una celda."""
    if valor is None:
        return ""
    if isinstance(valor, dict):
        return " · ".join(f"{k}: {_texto_plano(v)}" for k, v in valor.items())
    if isinstance(valor, (list, tuple)):
        return " · ".join(_texto_plano(v) for v in valor)
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    return str(valor)


# ===================== El .xlsx, a mano =====================
# Un .xlsx es un ZIP con unos XML adentro. Escribirlo con `zipfile` evita
# sumar openpyxl al proyecto por una sola pantalla. Son cadenas en línea
# (`inlineStr`), así no hace falta la tabla de textos compartidos.
def _escapar(texto: str) -> str:
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        # Excel no acepta los caracteres de control en el XML
        .translate({c: None for c in range(32) if c not in (9, 10, 13)})
    )


def _columna(n: int) -> str:
    """1 → A, 27 → AA."""
    nombre = ""
    while n > 0:
        n, resto = divmod(n - 1, 26)
        nombre = chr(65 + resto) + nombre
    return nombre


def _xlsx(titulos: list[str], filas: list[list[str]]) -> bytes:
    import zipfile

    def celda(ref: str, texto: str) -> str:
        return (
            f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
            f"{_escapar(texto)}</t></is></c>"
        )

    renglones = []
    for numero, fila in enumerate([titulos] + filas, start=1):
        celdas = "".join(
            celda(f"{_columna(i)}{numero}", valor) for i, valor in enumerate(fila, 1)
        )
        renglones.append(f'<row r="{numero}">{celdas}</row>')

    hoja = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(renglones)}</sheetData></worksheet>"
    )

    paquete = io.BytesIO()
    with zipfile.ZipFile(paquete, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Auditoría" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        z.writestr("xl/worksheets/sheet1.xml", hoja)

    return paquete.getvalue()


# ===================== El registro =====================
@router.get("", summary="El registro de actividad")
def listar(request: Request, yo: dict = UsuarioActual):
    permitidos = _exigir_acceso(yo)
    p = dict(request.query_params)

    eventos = _de_su_ambito(yo, a.buscar(p, permitidos))
    paginacion = _paginar(eventos, p)
    recortada = paginacion.pop("recortada")

    return {
        "eventos": [a.con_nombres(e) for e in recortada],
        # El resumen es de **lo filtrado**: si estás mirando una comisión, los
        # números de arriba tienen que ser los de esa comisión.
        "resumen": a.resumir(eventos),
        "total": len(eventos),
        **paginacion,
    }


@router.get("/{id_evento}", summary="El detalle de un movimiento")
def ver(id_evento: int, yo: dict = UsuarioActual):
    permitidos = _exigir_acceso(yo)

    evento = next((e for e in d.auditoria if e["id"] == id_evento), None)
    fuera = (
        not evento
        or (permitidos is not None and evento["modulo"] not in permitidos)
        or not ambito.alcanza_evento(yo, evento)
    )
    if fuera:
        # Fuera de alcance se niega como inexistente, igual que en Biblioteca
        # y en Finales.
        raise HTTPException(404, "Ese movimiento no existe")

    return a.con_nombres(evento)
