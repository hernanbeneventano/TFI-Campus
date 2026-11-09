"""Pruebas de la Biblioteca.

Se ejecutan contra el servidor en marcha, porque lo que interesa comprobar no
es una función aislada sino el camino completo: la ruta, los permisos, la
validación y la respuesta. Un archivo que el controlador rechaza pero que la
ruta nunca le entrega no prueba nada sobre el comportamiento real.

Uso:
    1. En una terminal:  python -m app.main
    2. En otra:          python -m pruebas.biblioteca
"""

from __future__ import annotations

import base64
import os
import sys

import httpx

BASE = os.environ.get("API_URL") or "http://127.0.0.1:3000/api/biblioteca"

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


class Respuesta:
    """Lo que devuelve cada pedido: el código, el cuerpo y las cabeceras."""

    def __init__(self, r: httpx.Response):
        self.estado = r.status_code
        self.cabeceras = r.headers
        tipo = r.headers.get("content-type", "")
        if "application/json" in tipo:
            self.cuerpo = r.json()
            self.bytes = None
        else:
            # La descarga devuelve bytes, no JSON
            self.cuerpo = None
            self.bytes = r.content


def pedir(metodo: str, ruta: str, cuerpo=None) -> Respuesta:
    with httpx.Client(timeout=60) as cliente:
        return Respuesta(cliente.request(metodo, BASE + ruta, json=cuerpo))


# Un PDF mínimo pero válido. Alcanza para que la comprobación de los primeros
# bytes lo reconozca, que es lo que se quiere probar.
PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def en_base64(datos: bytes) -> str:
    return base64.b64encode(datos).decode()


def correr() -> None:
    print(f"Pruebas de la Biblioteca contra {BASE}\n")

    # ------------------------------------------------------------------
    grupo("Permisos del usuario de prueba (estudiante)")

    r = pedir("GET", "/opciones")
    comprobar("puede aportar material", r.cuerpo.get("puedeAportar") is True, r.cuerpo)
    comprobar("no puede moderar", r.cuerpo.get("puedeModerar") is False, r.cuerpo)

    r = pedir("GET", "/pendientes")
    comprobar("la cola de revisión le responde 403", r.estado == 403, r.estado)

    # ------------------------------------------------------------------
    # El servidor limita los aportes a diez por hora y los cuenta en memoria.
    # Correr esta batería varias veces seguidas agota el cupo y todas las
    # comprobaciones de alta empiezan a responder 429. No es un fallo del
    # servidor: conviene avisarlo en vez de dar siete falsos negativos.
    sonda = pedir("POST", "", {"titulo": ""})
    if sonda.estado == 429:
        print()
        print("El servidor alcanzó el límite de aportes por hora.")
        print("Reinicialo (el contador vive en memoria) y volvé a correr las pruebas.")
        sys.exit(2)

    grupo("Validación al aportar")

    r = pedir("POST", "", {"titulo": "", "autorizado": True})
    comprobar("sin título responde 400", r.estado == 400, r.cuerpo)

    r = pedir("POST", "", {"titulo": "Prueba sin autorizar"})
    comprobar("sin confirmar la autorización responde 400", r.estado == 400, r.cuerpo)

    r = pedir("POST", "", {"titulo": "Prueba", "autorizado": True, "enlace": "javascript:alert(1)"})
    comprobar("un enlace que no es http responde 400", r.estado == 400, r.cuerpo)

    r = pedir("POST", "", {"titulo": "Prueba", "autorizado": True, "categoria": "inventada"})
    comprobar("una categoría inexistente responde 400", r.estado == 400, r.cuerpo)

    r = pedir("POST", "", {"titulo": "Prueba", "autorizado": True, "isbn": "no-es-un-isbn"})
    comprobar("un ISBN mal formado responde 400", r.estado == 400, r.cuerpo)

    # ------------------------------------------------------------------
    grupo("Alta de un aporte")

    r = pedir(
        "POST",
        "",
        {
            "titulo": "Apunte de prueba automática",
            "descripcion": "Creado por el conjunto de pruebas",
            "tipo": "apunte",
            "categoria": "programacion",
            "materia": "Programación II",
            "idioma": "es",
            "autorizado": True,
            "enlace": "https://exa.unne.edu.ar/",
        },
    )
    comprobar("se crea y responde 201", r.estado == 201, r.cuerpo)
    identificador = (r.cuerpo or {}).get("id")
    comprobar(
        "queda pendiente de moderación",
        (r.cuerpo or {}).get("estado") == "pendiente",
        (r.cuerpo or {}).get("estado"),
    )

    if identificador is None:
        print("\nNo se pudo crear el material de prueba. Se interrumpe acá.")
        return resumir()

    # ------------------------------------------------------------------
    grupo("Validación del archivo")

    r = pedir(
        "POST",
        f"/{identificador}/archivo",
        {
            "nombre": "trucho.pdf",
            "extension": "pdf",
            "tipo": "application/pdf",
            "contenido": en_base64(b"esto es texto plano, no un PDF"),
        },
    )
    comprobar("un .pdf que no es un PDF responde 415", r.estado == 415, r.cuerpo)

    r = pedir(
        "POST",
        f"/{identificador}/archivo",
        {
            "nombre": "programa.exe",
            "extension": "exe",
            "tipo": "application/octet-stream",
            "contenido": en_base64(b"MZ\x90\x00"),
        },
    )
    comprobar("un ejecutable responde 415", r.estado == 415, r.cuerpo)

    r = pedir(
        "POST",
        f"/{identificador}/archivo",
        {
            "nombre": "pagina.html",
            "extension": "html",
            "tipo": "text/html",
            "contenido": en_base64(b"<script>alert(1)</script>"),
        },
    )
    comprobar("un documento HTML responde 415", r.estado == 415, r.cuerpo)

    r = pedir(
        "POST",
        f"/{identificador}/archivo",
        {"nombre": "vacio.pdf", "extension": "pdf", "tipo": "application/pdf", "contenido": ""},
    )
    comprobar("un archivo vacío responde 400", r.estado == 400, r.cuerpo)

    r = pedir(
        "POST",
        f"/{identificador}/archivo",
        {
            "nombre": "../../../etc/passwd",
            "extension": "pdf",
            "tipo": "application/pdf",
            "contenido": en_base64(PDF),
        },
    )
    comprobar("un PDF válido responde 201", r.estado == 201, r.cuerpo)
    comprobar(
        "el nombre con rutas se depura",
        ((r.cuerpo or {}).get("archivo") or {}).get("nombre") == "passwd.pdf",
        (r.cuerpo or {}).get("archivo"),
    )
    comprobar(
        "al alojar el archivo se descarta el enlace",
        (r.cuerpo or {}).get("enlace") is None,
        (r.cuerpo or {}).get("enlace"),
    )

    # ------------------------------------------------------------------
    grupo("Descarga")

    r = pedir("GET", f"/{identificador}/archivo")
    comprobar("la descarga responde 200", r.estado == 200, r.estado)
    comprobar("devuelve los mismos bytes", r.bytes == PDF, len(r.bytes or b""))
    comprobar(
        "se entrega como archivo adjunto",
        "attachment" in r.cabeceras.get("content-disposition", ""),
        r.cabeceras.get("content-disposition"),
    )
    comprobar(
        "indica no inferir el tipo",
        r.cabeceras.get("x-content-type-options") == "nosniff",
        r.cabeceras.get("x-content-type-options"),
    )
    comprobar(
        "declara el tipo application/pdf",
        r.cabeceras.get("content-type", "").startswith("application/pdf"),
        r.cabeceras.get("content-type"),
    )

    # ------------------------------------------------------------------
    grupo("Visibilidad de lo pendiente")

    r = pedir("GET", "?porPagina=50")
    ids = [m["id"] for m in r.cuerpo["materiales"]]
    comprobar("un material pendiente no aparece en el catálogo", identificador not in ids, ids)

    r = pedir("GET", "/mis-aportes")
    comprobar(
        "pero sí aparece entre los aportes propios",
        any(m["id"] == identificador for m in r.cuerpo["materiales"]),
    )

    # ------------------------------------------------------------------
    grupo("Acceso a material de otra persona")

    # El material 7 lo aportó otra persona y está pendiente de moderación
    r = pedir("GET", "/7")
    comprobar("consultar un pendiente ajeno responde 403", r.estado == 403, r.cuerpo)

    r = pedir("GET", "/7/archivo")
    comprobar("descargar un pendiente ajeno responde 403", r.estado == 403, r.cuerpo)

    r = pedir("DELETE", "/3")
    comprobar("retirar material ajeno responde 403", r.estado == 403, r.cuerpo)

    r = pedir("POST", "/7/aprobar", {})
    comprobar("aprobar sin ser docente responde 403", r.estado == 403, r.cuerpo)

    # ------------------------------------------------------------------
    grupo("Favoritos")

    r = pedir("POST", f"/{identificador}/favorito", {})
    comprobar("marcar un favorito responde 201", r.estado == 201, r.cuerpo)

    r = pedir("GET", "/favoritos")
    comprobar(
        "aparece entre los guardados",
        any(m["id"] == identificador for m in r.cuerpo["materiales"]),
    )

    r = pedir("DELETE", f"/{identificador}/favorito")
    comprobar("quitarlo responde 200", r.estado == 200, r.cuerpo)

    r = pedir("GET", "/favoritos")
    comprobar(
        "ya no aparece", not any(m["id"] == identificador for m in r.cuerpo["materiales"])
    )

    r = pedir("POST", "/google:zyTCAlFPjgYC/favorito", {})
    comprobar("se puede guardar un libro de un catálogo externo", r.estado == 201, r.cuerpo)
    pedir("DELETE", "/google:zyTCAlFPjgYC/favorito")

    # ------------------------------------------------------------------
    grupo("Búsqueda y filtros")

    r = pedir("GET", "?q=normalizacion&fuente=campus")
    comprobar("la búsqueda ignora las tildes", r.cuerpo["total"] >= 1, r.cuerpo["total"])

    r = pedir("GET", "?q=Ruiz&campo=autor&fuente=campus")
    comprobar("busca por autor", r.cuerpo["total"] >= 2, r.cuerpo["total"])

    r = pedir("GET", "?categoria=programacion&fuente=campus")
    comprobar(
        "filtra por categoría",
        all(m["categoria"] == "programacion" for m in r.cuerpo["materiales"]),
        r.cuerpo["total"],
    )

    r = pedir("GET", "?fuente=campus&porPagina=2&pagina=2")
    comprobar(
        "pagina los resultados",
        r.cuerpo["pagina"] == 2 and len(r.cuerpo["materiales"]) <= 2,
        {"pagina": r.cuerpo["pagina"], "paginas": r.cuerpo["paginas"]},
    )

    r = pedir("GET", "?q=python&fuente=externos")
    fuentes = r.cuerpo["fuentes"]
    comprobar("consulta los dos catálogos externos", len(fuentes) == 2, fuentes)
    print(
        "         estado de las fuentes: "
        + ", ".join(f"{f.get('fuente')}={f.get('estado')}" for f in fuentes)
    )
    comprobar(
        "si una fuente falla, responde igual con la otra",
        any(f.get("estado") == "ok" for f in fuentes) or len(r.cuerpo["externos"]) == 0,
        fuentes,
    )

    # ------------------------------------------------------------------
    grupo("Limpieza")

    r = pedir("DELETE", f"/{identificador}")
    comprobar("se retira el material de prueba", r.estado == 200, r.cuerpo)

    r = pedir("GET", f"/{identificador}")
    comprobar("ya no existe", r.estado == 404, r.estado)

    resumir()


def resumir() -> None:
    total = pasadas + len(fallas)
    print("\n" + "=" * 58)
    print(f"{pasadas} de {total} comprobaciones correctas")
    if fallas:
        print("\nFallaron:")
        for f in fallas:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        correr()
    except httpx.ConnectError:
        print("\nNo se pudo conectar con el servidor.")
        print('¿Está levantado? Probá con "python -m app.main" en otra terminal.')
        sys.exit(1)
