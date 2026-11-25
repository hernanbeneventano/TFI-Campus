"""El registro de auditoría: consultarlo y exportarlo.

**No hay POST, ni PUT, ni DELETE.** Es a propósito: los eventos los escribe
`servicios/auditoria.registrar` desde cada módulo, y desde afuera el registro
solo se lee. Que no exista la ruta es más fuerte que prohibirla.

**Lo atiende Django** (`campus_django/auditoria.py`, ver `MIGRADOS` en
`despachador.py`). Estas rutas quedan para volver atrás sin tocar código. Las
dos llaman a las mismas funciones, en `servicios/consulta_auditoria.py`.
"""

from __future__ import annotations

from ..web import APIRouter, Request, Response

from ..servicios import consulta_auditoria as consulta
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/auditoria", tags=["Auditoría"])


# ===================== Rutas con nombre fijo =====================
# Antes de /{id}, si no "opciones" se tomaría como el id de un evento.


@router.get("/opciones", summary="Los filtros y qué puede ver quien pregunta")
def opciones(yo: dict = UsuarioActual):
    return consulta.opciones(yo)


@router.get("/mis-materias", summary="Lo que pasó en las materias que dicta")
def mis_materias(request: Request, yo: dict = UsuarioActual):
    return consulta.mis_materias(yo, dict(request.query_params))


@router.get("/exportar", summary="Bajar lo que se está viendo")
def exportar(request: Request, yo: dict = UsuarioActual):
    archivo = consulta.exportar(yo, dict(request.query_params))
    return Response(content=archivo.contenido, media_type=archivo.tipo, headers=archivo.cabeceras)


# ===================== El registro =====================
@router.get("", summary="El registro de actividad")
def listar(request: Request, yo: dict = UsuarioActual):
    return consulta.listar(yo, dict(request.query_params))


@router.get("/{id_evento}", summary="El detalle de un movimiento")
def ver(id_evento: int, yo: dict = UsuarioActual):
    return consulta.ver(yo, id_evento)
