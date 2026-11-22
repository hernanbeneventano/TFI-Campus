"""Dónde viven los archivos del campus: Cloudflare R2.

Por qué R2 y no Firebase Storage
---------------------------------
Firebase sigue siendo la base de datos y el inicio de sesión. Los archivos,
en cambio, van a Cloudflare R2: el almacenamiento cuesta parecido pero R2 no
cobra por sacar los datos, y un campus se pasa el día sirviendo apuntes y
PDF. Para una facultad eso es la diferencia entre una factura previsible y
una que crece con cada parcial.

R2 habla el mismo idioma que Amazon S3, así que se usa `boto3` y nada más.

Qué se guarda dónde
-------------------
- **El archivo** va a R2, en un solo bucket, ordenado por carpetas según de
  dónde viene (`biblioteca/`, `modulos/`, `perfiles/`…). Un bucket por módulo
  multiplicaría credenciales y reglas sin ganar nada.
- **La ficha** —nombre original, clave en R2, tipo, tamaño, quién lo subió y
  a qué registro pertenece— va a Firestore, en `archivos`. Ahí se consulta y
  se cruza con el resto del campus. En Firestore no entra ningún byte.

Las dos formas de subir
-----------------------
1. **Por el servidor** (`subir`): el navegador manda el archivo al backend,
   que lo valida mirando los bytes y recién entonces lo escribe en R2. Es el
   camino de la Biblioteca y del contenido de un módulo, donde lo que se
   sube es material que la facultad aloja y publica: ahí querés que el
   servidor haya visto el archivo antes de aceptarlo.
2. **Directo al bucket** (`enlace_para_subir`): el backend comprueba el
   permiso y devuelve un enlace firmado que vale unos minutos; el navegador
   escribe contra R2 sin pasar por el servidor. Es el camino para archivos
   grandes, donde hacer pasar cien megas por el backend solo agrega una copia
   y un tiempo de espera.

Los archivos **nunca son públicos**. El bucket no se abre: para mostrar o
descargar algo se pide un enlace firmado de corta duración, y ese enlace se
entrega solo después de comprobar que quien pregunta puede verlo. Es la misma
regla que ya aplica la Biblioteca, que contesta 404 —no 403— cuando el
material es de una materia ajena.

Si R2 no está configurado
-------------------------
El campus **sigue funcionando**: se usa el guardado en memoria de siempre, se
avisa en el arranque y nada se rompe. Sirve para desarrollar y para que las
pruebas no necesiten credenciales. Lo que no hace es persistir: al reiniciar,
esos archivos se pierden. `configurado()` dice en cuál de los dos modos está.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from .. import datos as d

try:  # boto3 es opcional: sin él, el campus trabaja en memoria
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    _HAY_BOTO = True
except ImportError:  # pragma: no cover
    _HAY_BOTO = False
    BotoCoreError = ClientError = Exception  # type: ignore[assignment,misc]


# ===================== Configuración =====================
VARIABLES = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
)

_cliente: Any = None
_configurado = False


def _valor(nombre: str) -> str:
    return (os.environ.get(nombre) or "").strip()


def _extremo() -> str:
    """La dirección del bucket. Se puede dar entera o solo la cuenta."""
    explicito = _valor("R2_ENDPOINT")
    if explicito:
        return explicito.rstrip("/")
    return f"https://{_valor('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com"


def bucket() -> str:
    return _valor("R2_BUCKET_NAME")


def configurado() -> bool:
    return _configurado


def iniciar() -> str:
    """Prepara el cliente. Devuelve qué pasó, para decirlo en el arranque."""
    global _cliente, _configurado

    faltan = [v for v in VARIABLES if not _valor(v)]
    if faltan:
        _configurado = False
        return (
            "Cloudflare R2 sin configurar (falta "
            + ", ".join(faltan)
            + "). Los archivos quedan en memoria y se pierden al reiniciar."
        )

    if not _HAY_BOTO:
        _configurado = False
        return "Falta boto3 (pip install -r requirements.txt). Archivos en memoria."

    _cliente = boto3.client(
        "s3",
        endpoint_url=_extremo(),
        aws_access_key_id=_valor("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_valor("R2_SECRET_ACCESS_KEY"),
        # R2 no tiene regiones como S3, pero la firma v4 pide una.
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
    )
    _configurado = True
    return f"Cloudflare R2 conectado (bucket «{bucket()}»)."


def _c():
    if not _configurado:
        raise RuntimeError("Cloudflare R2 no está configurado")
    return _cliente


# ===================== Las carpetas del bucket =====================
# Un solo bucket, ordenado por de dónde viene el archivo. El prefijo es
# también lo que permite mirar el bucket y entender qué hay adentro.
BIBLIOTECA = "biblioteca"
MODULOS = "modulos"
PERFILES = "perfiles"
NOVEDADES = "novedades"
MENSAJES = "mensajes"
# Lo que entrega un alumno. Carpeta propia y no dentro de `modulos/` porque
# el material de cátedra y el trabajo de un alumno no se miran igual: uno se
# publica y el otro lo ve su docente y nadie más.
ENTREGAS = "entregas"
INSTITUCION = "institucion"
SOLICITUDES = "solicitudes"


def clave(modulo: str, *partes: Any, nombre: str) -> str:
    """La ruta del objeto dentro del bucket.

    El nombre ya viene limpio de `servicios/archivos.nombre_seguro`, que le
    saca las barras y los acentos: es lo que evita que alguien suba un
    `../../otra-materia/x.pdf` y escriba donde no debe.
    """
    camino = "/".join(str(p) for p in partes if p is not None)
    return f"{modulo}/{camino}/{nombre}" if camino else f"{modulo}/{nombre}"


# ===================== Las operaciones =====================
def subir(objeto: str, contenido: bytes, tipo: str) -> None:
    """Escribe el archivo. Si falla, lanza: quien llama no da por guardado."""
    if not _configurado:
        d.guardar_archivo(objeto, contenido)
        return
    _c().put_object(
        Bucket=bucket(),
        Key=objeto,
        Body=contenido,
        ContentType=tipo,
        # Nada de lectura pública: se sirve siempre con enlace firmado.
        CacheControl="private, max-age=0",
    )


def leer(objeto: str) -> bytes | None:
    if not _configurado:
        return d.leer_archivo(objeto)
    try:
        respuesta = _c().get_object(Bucket=bucket(), Key=objeto)
        return respuesta["Body"].read()
    except (ClientError, BotoCoreError):
        return None


def borrar(objeto: str) -> None:
    if not _configurado:
        d.borrar_archivo(objeto)
        return
    try:
        _c().delete_object(Bucket=bucket(), Key=objeto)
    except (ClientError, BotoCoreError) as error:  # noqa: BLE001
        print(f"[r2] no se pudo borrar {objeto}: {error}")


def metadatos(objeto: str) -> dict | None:
    """Tamaño, tipo y última modificación, sin bajar el archivo."""
    if not _configurado:
        contenido = d.leer_archivo(objeto)
        return None if contenido is None else {"tamano": len(contenido)}
    try:
        cabeza = _c().head_object(Bucket=bucket(), Key=objeto)
        return {
            "tamano": cabeza.get("ContentLength"),
            "tipo": cabeza.get("ContentType"),
            "modificado": cabeza.get("LastModified"),
        }
    except (ClientError, BotoCoreError):
        return None


MINUTOS_DE_ENLACE = 10


def enlace_temporal(objeto: str, *, nombre: str | None = None, segundos: int | None = None) -> str | None:
    """Un enlace firmado para ver o bajar el archivo, que vence solo.

    Vence a propósito: un enlace eterno es un archivo público con una
    dirección más larga. Si alguien lo reenvía, deja de servir enseguida.
    """
    if not _configurado:
        return None
    parametros: dict[str, Any] = {"Bucket": bucket(), "Key": objeto}
    if nombre:
        parametros["ResponseContentDisposition"] = f'attachment; filename="{nombre}"'
    try:
        return _c().generate_presigned_url(
            "get_object",
            Params=parametros,
            ExpiresIn=segundos or MINUTOS_DE_ENLACE * 60,
        )
    except (ClientError, BotoCoreError) as error:  # noqa: BLE001
        print(f"[r2] no se pudo firmar {objeto}: {error}")
        return None


def enlace_para_subir(objeto: str, tipo: str, *, segundos: int | None = None) -> dict | None:
    """Un enlace firmado para que el navegador escriba directo en R2.

    Lo entrega el backend **después** de comprobar el permiso: sin esa
    comprobación, un enlace de subida es permiso de escritura para cualquiera.
    El tipo queda firmado, así que el navegador no puede mandar otra cosa.
    """
    if not _configurado:
        return None
    try:
        url = _c().generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket(), "Key": objeto, "ContentType": tipo},
            ExpiresIn=segundos or MINUTOS_DE_ENLACE * 60,
        )
    except (ClientError, BotoCoreError) as error:  # noqa: BLE001
        print(f"[r2] no se pudo firmar la subida de {objeto}: {error}")
        return None
    return {"url": url, "metodo": "PUT", "cabeceras": {"Content-Type": tipo}, "objeto": objeto}


# ===================== La ficha en Firestore =====================
def registrar(
    objeto: str,
    *,
    nombre: str,
    tipo: str,
    tamano: int,
    persona_id: int | None,
    modulo: str,
    registro_id: Any = None,
) -> dict:
    """Deja anotado en `archivos` qué se subió, quién y para qué.

    La ficha vive en Firestore y el archivo en R2. Sin la ficha, el bucket es
    una pila de objetos sin dueño: no se puede saber de qué materia es un PDF
    ni quién lo subió, que es lo primero que hay que poder contestar.
    """
    ficha = {
        "id": objeto,  # la clave en R2 identifica al archivo sin ambigüedad
        "objectKey": objeto,
        "nombre": nombre,
        "tipo": tipo,
        "tamano": tamano,
        "subidoPor": persona_id,
        "modulo": modulo,
        "registroId": registro_id,
        "fecha": d.iso(d.ahora()),
        "almacen": "r2" if _configurado else "memoria",
    }
    previa = ficha_de(objeto)
    if previa:
        previa.update(ficha)
        return previa
    d.archivos_subidos.append(ficha)
    return ficha


def ficha_de(objeto: str) -> dict | None:
    return next((a for a in d.archivos_subidos if a.get("objectKey") == objeto), None)


def olvidar(objeto: str) -> None:
    """Saca la ficha y el archivo. Se usa al retirar el registro dueño."""
    ficha = ficha_de(objeto)
    if ficha:
        d.archivos_subidos.remove(ficha)
    borrar(objeto)


def ahora_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
