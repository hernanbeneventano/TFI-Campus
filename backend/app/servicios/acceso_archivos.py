"""Los archivos del campus: subirlos, verlos y saber qué hay.

Todo pasa por `servicios/almacenamiento.py`, que habla con Cloudflare R2. Esta
ruta no guarda nada por su cuenta: comprueba **quién pide y para qué**, y
recién entonces firma.

Por qué hace falta una ruta aparte
----------------------------------
Hay dos maneras de subir y las dos tienen su lugar:

- Por el servidor, que es lo que ya hacen la Biblioteca y el contenido de un
  módulo: el backend recibe los bytes, los mira y los escribe. Es lo correcto
  para material que la facultad publica, porque nada entra sin revisar.
- Directo al bucket, con un enlace firmado. Para archivos grandes, hacer
  pasar cien megas por el servidor solo agrega una copia y una espera.

El enlace firmado **es permiso de escritura**. Por eso se entrega después de
comprobar el permiso del módulo al que va dirigido, nunca antes, y vale unos
minutos. Un enlace sin esa comprobación es el bucket abierto con un paso más.

Un archivo fuera de alcance responde **404, no 403**, como en el resto del
campus: un 403 ya confirma que existe.

Vive acá y no en la ruta para que FastAPI y Django contesten **con la misma
función** mientras dure la migración: cada framework lee lo que llega y la
llama. `ver` devuelve un `Archivo` y no una respuesta: cada framework arma la
suya con él.
"""

from __future__ import annotations

import hmac

from fastapi import HTTPException

from .. import datos as d
from . import almacenamiento as alm
from . import archivos as validacion
from . import auditoria
from . import fotos
from .archivos import Archivo


# ===================== Quién puede escribir en cada carpeta =====================
# Cada carpeta del bucket tiene su dueño. La comprobación vive acá para que
# firmar un enlace y escribir por el servidor exijan exactamente lo mismo.
def _puede_escribir(yo: dict, modulo: str, registro_id) -> bool:
    if modulo == alm.PERFILES:
        # La foto propia. El administrador puede la de cualquiera.
        return str(registro_id) == str(yo["id"]) or d.tiene_rol(yo, "Administrador", "Supervisor")

    if modulo == alm.MODULOS:
        from ..rutas.gestion_modulo import puede_gestionar

        curso = d.buscar_curso(registro_id)
        return bool(curso) and puede_gestionar(yo, curso)

    if modulo == alm.BIBLIOTECA:
        # Cualquiera que curse o dicte puede aportar; lo revisa el docente.
        return bool(d.tiene_rol(yo, "Estudiante", "Docente", "Administrador", "Supervisor"))

    if modulo in (alm.NOVEDADES, alm.INSTITUCION):
        return bool(d.tiene_rol(yo, "Docente", "Administrador", "Supervisor"))

    if modulo in (alm.MENSAJES, alm.SOLICITUDES):
        return True  # son propios de quien los manda

    return False


def _mia(yo: dict, ficha: dict) -> bool:
    """Si esa persona puede ver ese archivo."""
    if d.tiene_rol(yo, "Administrador", "Supervisor"):
        return True
    if ficha.get("subidoPor") == yo["id"]:
        return True
    modulo = ficha.get("modulo")
    if modulo == alm.PERFILES:
        return True  # las fotos de perfil las ve todo el campus
    if modulo == alm.MODULOS:
        curso = d.buscar_curso(ficha.get("registroId"))
        return bool(curso) and any(p["id"] == yo["id"] for p in d.participantes_de_curso(curso))
    return False


def estado(yo: dict) -> dict:
    """Para que la pantalla sepa si puede ofrecer subir algo.

    Sin R2 el campus funciona igual, pero lo que se suba se pierde al
    reiniciar: más vale decirlo que dejar a alguien subir su tesis a la nada.
    """
    return {
        "configurado": alm.configurado(),
        "maximoMb": validacion.maximo_mb(),
        "formatos": sorted(validacion.FORMATOS),
    }



def pedir_enlace(cuerpo: dict, yo: dict) -> dict:
    """Devuelve un enlace firmado para escribir en R2 desde el navegador."""
    modulo = str(cuerpo.get("modulo") or "")
    if modulo not in (
        alm.BIBLIOTECA, alm.MODULOS, alm.PERFILES,
        alm.NOVEDADES, alm.MENSAJES, alm.INSTITUCION, alm.SOLICITUDES,
    ):
        raise HTTPException(400, "Ese apartado no existe")

    registro_id = cuerpo.get("registroId")
    if not _puede_escribir(yo, modulo, registro_id):
        raise HTTPException(404, "No se encontró eso")

    extension = str(cuerpo.get("extension") or "").lower().lstrip(".")
    formato = validacion.FORMATOS.get(extension)
    if not formato:
        raise HTTPException(415, "Ese tipo de archivo no se acepta")

    # El tamaño se declara y se comprueba: R2 no sabe de nuestros límites.
    tamano = cuerpo.get("tamano")
    tope = validacion.maximo_mb() * 1024 * 1024
    if not isinstance(tamano, int) or tamano <= 0:
        raise HTTPException(400, "Falta el tamaño del archivo")
    if tamano > tope:
        raise HTTPException(413, f"El archivo supera los {validacion.maximo_mb()} MB")

    if not alm.configurado():
        raise HTTPException(
            503,
            "El almacenamiento de archivos todavía no está configurado. "
            "Subí el archivo por el formulario, o configurá Cloudflare R2.",
        )

    nombre = validacion.nombre_seguro(cuerpo.get("nombre"), extension)
    objeto = alm.clave(modulo, registro_id, nombre=nombre)
    enlace = alm.enlace_para_subir(objeto, formato["mime"])
    if not enlace:
        raise HTTPException(502, "No se pudo preparar la subida")

    return {**enlace, "nombre": nombre, "tipo": formato["mime"]}



def confirmar(cuerpo: dict, yo: dict) -> dict:
    """Anota la ficha del archivo recién subido.

    **Se comprueba contra R2 antes de darlo por bueno.** Que el navegador
    diga que terminó no prueba nada: si el objeto no está en el bucket, no
    hay archivo, y anotar la ficha igual dejaría una referencia a la nada.
    """
    objeto = str(cuerpo.get("objeto") or "")
    modulo = objeto.split("/")[0] if "/" in objeto else ""
    registro_id = cuerpo.get("registroId")
    if not objeto or not _puede_escribir(yo, modulo, registro_id):
        raise HTTPException(404, "No se encontró eso")

    datos_objeto = alm.metadatos(objeto)
    if not datos_objeto:
        raise HTTPException(409, "El archivo no llegó al almacenamiento")

    ficha = alm.registrar(
        objeto,
        nombre=str(cuerpo.get("nombre") or objeto.rsplit("/", 1)[-1]),
        tipo=str(datos_objeto.get("tipo") or "application/octet-stream"),
        tamano=int(datos_objeto.get("tamano") or 0),
        persona_id=yo["id"],
        modulo=modulo,
        registro_id=registro_id,
    )

    auditoria.registrar(
        yo, "creacion", "modulos" if modulo == alm.MODULOS else "biblioteca",
        elemento=ficha["nombre"], elemento_id=objeto, elemento_tipo="archivo",
        detalle=f"Subió un archivo a {modulo}",
    )
    return ficha



def enlace(objeto: str, yo: dict) -> dict:
    """Firma un enlace de lectura que vence solo.

    Nunca se devuelve una dirección permanente: sería el archivo público con
    una dirección más larga.
    """
    ficha = alm.ficha_de(objeto)
    if not ficha or not _mia(yo, ficha):
        raise HTTPException(404, "No se encontró el archivo")

    url = alm.enlace_temporal(objeto, nombre=ficha.get("nombre"))
    if not url:
        raise HTTPException(503, "El almacenamiento de archivos no está disponible")
    return {"url": url, "venceEnSegundos": alm.MINUTOS_DE_ENLACE * 60, "nombre": ficha["nombre"]}



def ver(f: str, o: str) -> Archivo:
    """Devuelve los bytes, sin pedir la cabecera de sesión.

    Hace falta porque una etiqueta `<img>` no manda `Authorization`: una
    imagen de un mensaje no se podría mostrar nunca. La credencial es la
    **dirección**, firmada con un secreto del servidor, igual que los enlaces
    firmados de R2 y que la foto de perfil.

    La firma se entrega únicamente dentro de respuestas que ya pasaron por el
    control de permisos —el mensaje solo lo ve quien está en esa
    conversación—, y cambia si cambia el archivo.
    """
    if not o or not hmac.compare_digest(f or "", fotos.firma(o)):
        raise HTTPException(404, "No se encontró el archivo")

    contenido = alm.leer(o)
    if contenido is None:
        raise HTTPException(404, "No se encontró el archivo")

    ficha = alm.ficha_de(o) or {}
    tipo = ficha.get("tipo") or "application/octet-stream"
    nombre = ficha.get("nombre") or o.rsplit("/", 1)[-1]

    # Las imágenes y los PDF se muestran; cualquier otra cosa se baja. Un PDF
    # es lo que más se sube a un módulo y bajar cada apunte para ver de qué
    # se trata es trabajo al pedo.
    #
    # Va con `Content-Security-Policy: sandbox`, que apaga los scripts y los
    # formularios del documento incrustado: un PDF puede traer JavaScript
    # adentro, así que se mira pero no se le da permiso de hacer nada. El
    # resto de los formatos no se abre dentro del campus.
    adentro = tipo.startswith("image/") or tipo == "application/pdf"
    cabeceras = {
        "Content-Disposition": "inline" if adentro else f'attachment; filename="{nombre}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=300",
    }
    if tipo == "application/pdf":
        cabeceras["Content-Security-Policy"] = "sandbox"

    return Archivo(contenido=contenido, tipo=tipo, cabeceras=cabeceras)
