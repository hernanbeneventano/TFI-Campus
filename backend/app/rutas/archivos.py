"""Los archivos del campus: subirlos, verlos y saber qué hay.

**Lo atiende Django** (`campus_django/archivos.py`, ver `MIGRADOS` en
`despachador.py`). Estas rutas quedan para volver atrás sin tocar código. Las
cinco llaman a las mismas funciones de `servicios/acceso_archivos.py`, donde
están los permisos de cada carpeta del bucket.
"""

from __future__ import annotations

from ..web import APIRouter, Body, Response

from ..servicios import acceso_archivos as servicio
from ..servicios.autenticacion import UsuarioActual

router = APIRouter(prefix="/api/archivos", tags=["Archivos"])


@router.get("/estado", summary="Si el almacenamiento está configurado")
def estado(yo: dict = UsuarioActual):
    return servicio.estado(yo)


@router.post("/enlace-de-subida", summary="Pedir permiso para subir directo")
def pedir_enlace(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    return servicio.pedir_enlace(cuerpo, yo)


@router.post("/confirmar", summary="Avisar que la subida directa terminó")
def confirmar(cuerpo: dict = Body(...), yo: dict = UsuarioActual):
    return servicio.confirmar(cuerpo, yo)


@router.get("/{objeto:path}/enlace", summary="Un enlace temporal para verlo")
def enlace(objeto: str, yo: dict = UsuarioActual):
    return servicio.enlace(objeto, yo)


# Va **última**: acepta cualquier camino, así que declarada antes se
# comería a las que terminan en algo fijo, como `/enlace`. Es pública: la
# credencial es la dirección firmada (ver `servicios/acceso_archivos.ver`).
@router.get("/{f}/{o:path}", summary="Servir un archivo con la dirección firmada")
def ver(f: str, o: str):
    archivo = servicio.ver(f, o)
    return Response(content=archivo.contenido, media_type=archivo.tipo, headers=archivo.cabeceras)
