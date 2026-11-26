"""Los archivos del campus: subirlos, verlos y saber qué hay.

Las vistas de Django delegan en estas funciones; los permisos de cada
carpeta del bucket están en `servicios/acceso_archivos.py`.
"""

from __future__ import annotations

from campus_django.respuestas import descargar

from ..servicios import acceso_archivos as servicio



def estado(yo: dict ):
    return servicio.estado(yo)


def pedir_enlace(cuerpo: dict , yo: dict ):
    return servicio.pedir_enlace(cuerpo, yo)


def confirmar(cuerpo: dict , yo: dict ):
    return servicio.confirmar(cuerpo, yo)


def enlace(objeto: str, yo: dict ):
    return servicio.enlace(objeto, yo)


# Va **última**: acepta cualquier camino, así que declarada antes se
# comería a las que terminan en algo fijo, como `/enlace`. Es pública: la
# credencial es la dirección firmada (ver `servicios/acceso_archivos.ver`).
def ver(f: str, o: str):
    archivo = servicio.ver(f, o)
    return descargar(archivo.contenido, archivo.tipo, archivo.cabeceras)
