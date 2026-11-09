"""Hace que las bibliotecas de Google confíen en el almacén de certificados
del sistema operativo.

El problema. Firebase trae dos clientes con almacenes de confianza propios:
`google-auth` verifica con el paquete de `certifi` (el de Mozilla) y gRPC con
el suyo, compilado adentro. Ninguno de los dos mira el almacén del sistema.

En cualquier equipo donde algo inspeccione el tráfico HTTPS y lo vuelva a
firmar — un antivirus con escaneo web, o el proxy de una institución — la raíz
de ese intermediario está en el almacén del sistema pero no en los otros dos.
El resultado es que Firestore se queda reintentando y la verificación de
tokens falla, las dos con el mismo mensaje:

    CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate

La solución **no** es desactivar la verificación, sino apuntar esas
bibliotecas a las autoridades en las que el sistema ya confía. Es lo mismo
que hace el navegador.

En Linux y macOS Python ya usa el almacén del sistema, así que esto no hace
nada. En Windows hay que exportarlo a un archivo, porque las bibliotecas de
Google esperan una ruta y no saben leer el almacén nativo.
"""

from __future__ import annotations

import os
import ssl
import sys
from pathlib import Path

# Se guarda junto al código del servidor. Está en el .gitignore: es un
# volcado del equipo de cada uno, no algo que deba viajar por el repositorio.
RUTA_PAQUETE = Path(__file__).resolve().parents[2] / "ca-sistema.pem"

# Las tres variables que leen las bibliotecas involucradas.
VARIABLES = (
    "SSL_CERT_FILE",            # ssl y, por él, google-auth
    "REQUESTS_CA_BUNDLE",       # requests, que usa google-auth para los tokens
    "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH",  # gRPC, que usa Firestore
)


def _exportar_almacen_de_windows(destino: Path) -> bool:
    """Vuelca las autoridades de confianza de Windows a un archivo PEM."""
    certificados = []
    for almacen in ("ROOT", "CA"):
        try:
            for datos, codificacion, _ in ssl.enum_certificates(almacen):
                if codificacion == "x509_asn":
                    certificados.append(ssl.DER_cert_to_PEM_cert(datos))
        except (OSError, PermissionError):
            # Un almacén inaccesible no es motivo para abortar: con el otro
            # suele alcanzar.
            continue

    if not certificados:
        return False

    destino.write_text("".join(certificados), encoding="ascii")
    return True


def configurar() -> Path | None:
    """Deja preparado el paquete de certificados y devuelve su ruta.

    Hay que llamarla **antes** de crear cualquier cliente de Google: las
    bibliotecas leen estas variables una sola vez, al construir su contexto.

    Si el entorno ya trae las variables puestas, se respetan: puede ser una
    configuración deliberada de quien despliega.
    """
    if sys.platform != "win32":
        return None

    if all(os.environ.get(v) for v in VARIABLES):
        return Path(os.environ["SSL_CERT_FILE"])

    if not RUTA_PAQUETE.is_file() and not _exportar_almacen_de_windows(RUTA_PAQUETE):
        print(
            "Aviso: no se pudo exportar el almacén de certificados de Windows. "
            "Si Firebase falla con CERTIFICATE_VERIFY_FAILED, ver "
            "backend/README.md."
        )
        return None

    for variable in VARIABLES:
        os.environ.setdefault(variable, str(RUTA_PAQUETE))

    return RUTA_PAQUETE
