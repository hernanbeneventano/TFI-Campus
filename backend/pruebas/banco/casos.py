"""Qué peticiones se le hacen a las dos aplicaciones.

Un caso es **una secuencia**, no una petición suelta. Hace falta así porque
muchas cosas solo se pueden mirar después de crearlas: para comparar la
respuesta de «ver la carrera recién creada» hay que crearla antes, y las dos
aplicaciones tienen que recibir exactamente los mismos pasos en el mismo
orden. Entre caso y caso el campus se repone a cero (ver `estado.py`).

De dónde salen
--------------
De dos lugares, a propósito:

- **Automáticos**: todos los GET sin parámetros, sacados de la tabla de rutas
  de la aplicación de referencia. Son gratis y cubren la mitad del campus sin
  escribir nada. Como la lista sale de FastAPI, una ruta que exista allá y no
  en Django aparece sola como un 404 del lado de Django, que es justo lo que
  queremos detectar.
- **Escritos a mano**: los que llevan parámetros —hay que saber qué
  identificador existe en el escenario— y los que escriben. Estos últimos
  son los que más importan: una migración rompe más fácil un POST que un GET.

Quién hace cada petición
------------------------
Casi todo el campus depende de quién pregunta, así que cada paso dice con qué
persona se hace. Una comparación hecha siempre como administrador no probaría
los permisos, que son la mitad de la lógica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Las personas del escenario (ver `pruebas/datos_de_prueba.json`)
SANTIAGO = 1    # estudiante
MARIA = 2       # docente de Programación II
HERNAN = 3      # estudiante
PABLO = 7       # docente de otra materia
SECRETARIA = 18  # Administrador
CLAUDIA = 19    # Supervisor + Docente

CURSO = 1
MATERIA = 109


@dataclass
class Paso:
    metodo: str
    camino: str
    quien: int = SECRETARIA
    cuerpo: Any = None
    # Campos que en este paso hay que normalizar además de los de siempre
    variables: frozenset[str] = frozenset()

    @property
    def etiqueta(self) -> str:
        return f"{self.metodo} {self.camino}"


@dataclass
class Caso:
    nombre: str
    pasos: list[Paso] = field(default_factory=list)


def _ver(camino: str, quien: int = SECRETARIA) -> Paso:
    return Paso("GET", camino, quien)


def automaticos(rutas: list[tuple[str, str]]) -> list[Caso]:
    """Un caso por cada GET sin parámetros, mirado por tres roles distintos.

    Tres y no uno porque lo que devuelve casi cualquier pantalla depende de
    quién pregunta: con un solo rol se compararía la mitad del campus.
    """
    casos = []
    for metodo, camino in sorted(rutas):
        if metodo != "GET" or "{" in camino:
            continue
        casos.append(
            Caso(
                f"GET {camino}",
                [
                    _ver(camino, SECRETARIA),
                    _ver(camino, MARIA),
                    _ver(camino, SANTIAGO),
                ],
            )
        )
    return casos


# ===================== Los archivos =====================
def _caso_archivos() -> Caso:
    """Archivos de verdad, pedidos por su dirección firmada.

    La firma sale de un secreto que se sortea en cada proceso. El banco corre
    las dos aplicaciones en el mismo, así que se calcula acá y vale para las
    dos. Sin R2 los archivos quedan en la memoria del servidor, que es lo que
    se compara.
    """
    import base64
    import io
    import zipfile

    from app.servicios import fotos

    def direccion(objeto: str) -> str:
        return f"/api/archivos/{fotos.firma(objeto)}/{objeto}"

    def subida(nombre: str, extension: str, tipo: str, crudo: bytes) -> dict:
        return {"nombre": nombre, "extension": extension, "tipo": tipo,
                "contenido": base64.b64encode(crudo).decode()}

    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    paquete = io.BytesIO()
    with zipfile.ZipFile(paquete, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
    docx = paquete.getvalue()

    del_pdf = f"entregas/{CURSO}/{TAREA}/{SANTIAGO}/trabajo.pdf"
    del_docx = f"entregas/{CURSO}/{TAREA}/{SANTIAGO}/trabajo.docx"
    del_png = f"entregas/{CURSO}/{TAREA}/{HERNAN}/captura.png"
    entregar = f"/api/tareas/{TAREA}/mi-entrega"

    return Caso("Los archivos, a fondo", [
        _ver("/api/archivos/estado", SANTIAGO),
        _ver("/api/archivos/estado", SECRETARIA),
        # Se suben por la entrega (Mi cursada, todavía FastAPI) y se piden por
        # la dirección firmada, sin sesión: un PDF y una imagen se ven adentro
        Paso("POST", entregar, SANTIAGO, subida("trabajo.pdf", "pdf", "application/pdf", pdf)),
        Paso("POST", entregar, HERNAN, subida("captura.png", "png", "image/png", png)),
        _ver(direccion(del_pdf), None),
        _ver(direccion(del_png), None),
        # Con otra firma, sin firma, sin objeto, o firmado y sin archivo: 404
        _ver(f"/api/archivos/000000000000/{del_pdf}", None),
        _ver(f"/api/archivos/{fotos.firma(del_pdf)}/", None),
        _ver(f"/api/archivos/{fotos.firma('no/existe.pdf')}/no/existe.pdf", None),
        _ver("/api/archivos/solo-un-tramo", None),
        # Reemplazar por un Word: el PDF viejo se borra y el Word se baja
        Paso("POST", entregar, SANTIAGO,
             subida("trabajo.docx", "docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", docx)),
        _ver(direccion(del_pdf), None),
        _ver(direccion(del_docx), None),
        # El enlace temporal: sin R2 no hay (503); ajeno o inexistente, 404
        _ver(f"/api/archivos/{del_docx}/enlace", SANTIAGO),
        _ver(f"/api/archivos/{del_docx}/enlace", HERNAN),
        _ver(f"/api/archivos/{del_docx}/enlace", SECRETARIA),
        _ver("/api/archivos/no/existe.pdf/enlace", SANTIAGO),
        _ver("/api/archivos//enlace", SANTIAGO),
        _ver(f"/api/archivos/{del_docx}/enlace", None),
        # Pedir permiso para subir directo: cada error, y el bueno da 503 sin R2
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO, {"modulo": "otra-cosa"}),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO,
             {"modulo": "perfiles", "registroId": MARIA, "extension": "png", "tamano": 10}),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO,
             {"modulo": "perfiles", "registroId": SANTIAGO, "extension": "exe", "tamano": 10}),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO,
             {"modulo": "perfiles", "registroId": SANTIAGO, "extension": "png"}),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO,
             {"modulo": "perfiles", "registroId": SANTIAGO, "extension": "png", "tamano": "10"}),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO,
             {"modulo": "perfiles", "registroId": SANTIAGO, "extension": "png", "tamano": 10**10}),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO,
             {"modulo": "perfiles", "registroId": SANTIAGO, "extension": "PNG", "tamano": 10,
              "nombre": "../../otro/foto.png"}),
        Paso("POST", "/api/archivos/enlace-de-subida", MARIA,
             {"modulo": "modulos", "registroId": CURSO, "extension": "pdf", "tamano": 10}),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO,
             {"modulo": "modulos", "registroId": CURSO, "extension": "pdf", "tamano": 10}),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO),
        Paso("POST", "/api/archivos/enlace-de-subida", SANTIAGO, ["no", "es", "un", "objeto"]),
        # Confirmar: sin objeto o ajeno 404; propio pero que no llegó, 409
        Paso("POST", "/api/archivos/confirmar", SANTIAGO, {}),
        Paso("POST", "/api/archivos/confirmar", SANTIAGO,
             {"objeto": "perfiles/2/foto.png", "registroId": MARIA}),
        Paso("POST", "/api/archivos/confirmar", SANTIAGO,
             {"objeto": f"perfiles/{SANTIAGO}/nunca-subida.png", "registroId": SANTIAGO}),
        # Sin sesión, los métodos y las barras
        _ver("/api/archivos/estado", None),
        Paso("POST", "/api/archivos/confirmar", None, {}),
        Paso("POST", "/api/archivos/estado", SANTIAGO, {}),
        _ver("/api/archivos/enlace-de-subida", SANTIAGO),
        _ver("/api/archivos/estado/", SANTIAGO),
        _ver("/api/archivos", SANTIAGO),
        Paso("POST", f"/api/archivos/{del_docx}/enlace", SANTIAGO, {}),
        Paso("POST", direccion(del_docx), None, {}),
        Paso("HEAD", direccion(del_docx), None),
    ])


# ===================== Los que llevan parámetros =====================
def con_parametros() -> list[Caso]:
    return [
        Caso("Un módulo y su pantalla", [
            _ver(f"/api/cursos/{CURSO}", SANTIAGO),
            _ver(f"/api/cursos/{CURSO}/modulo", SANTIAGO),
            _ver(f"/api/cursos/{CURSO}/modulo", MARIA),
            # Y uno ajeno, que tiene que dar 404 en las dos
            _ver("/api/cursos/5/modulo", SANTIAGO),
            _ver("/api/cursos/99999/modulo", SECRETARIA),
        ]),
        Caso("Las notas y el seguimiento del módulo", [
            _ver(f"/api/cursos/{CURSO}/notas", MARIA),
            _ver(f"/api/cursos/{CURSO}/seguimiento", MARIA),
            _ver(f"/api/cursos/{CURSO}/asistencias/clases", MARIA),
            _ver(f"/api/cursos/{CURSO}/asistencias/alumnos", MARIA),
            _ver(f"/api/cursos/{CURSO}/asistencias/mi-detalle", SANTIAGO),
        ]),
        Caso("El calendario, con y sin rango", [
            _ver("/api/calendario", SANTIAGO),
            _ver("/api/calendario?desde=2026-01-01&hasta=2026-12-31", SANTIAGO),
            _ver("/api/calendario?desde=no-es-una-fecha", SANTIAGO),
        ]),
        # El primer módulo que pasó a Django: los bordes donde dos frameworks
        # suelen contestar distinto aunque la lógica sea la misma.
        Caso("El calendario, a fondo", [
            # Lo que ve cada uno depende de quién es: «entregada» es de cada alumno
            _ver("/api/calendario?desde=2026-03-01&hasta=2026-07-31", SANTIAGO),
            _ver("/api/calendario?desde=2026-03-01&hasta=2026-07-31", HERNAN),
            _ver("/api/calendario?desde=2026-03-01&hasta=2026-07-31", MARIA),
            _ver("/api/calendario?desde=2026-03-01&hasta=2026-07-31", SECRETARIA),
            # Una semana, un día, fechas ISO completas
            _ver("/api/calendario?desde=2026-04-06&hasta=2026-04-12", SANTIAGO),
            _ver("/api/calendario?desde=2026-04-08&hasta=2026-04-08", SANTIAGO),
            _ver("/api/calendario?desde=2026-04-06T00:00:00Z&hasta=2026-04-12T23:59:59Z", SANTIAGO),
            # Solo uno de los dos, vacío, repetido (gana el último), y con acentos
            _ver("/api/calendario?hasta=2026-12-31", SANTIAGO),
            _ver("/api/calendario?desde=&hasta=", SANTIAGO),
            _ver("/api/calendario?desde=1999-01-01&desde=2026-03-01&hasta=2026-03-31", SANTIAGO),
            _ver("/api/calendario?desde=2026-03-01&hasta=2026-03-31&otro=ñandú", SANTIAGO),
            # Los 400: al revés, inválida, mes 13
            _ver("/api/calendario?desde=2026-12-31&hasta=2026-01-01", SANTIAGO),
            _ver("/api/calendario?hasta=mañana", SANTIAGO),
            _ver("/api/calendario?desde=2026-13-01", SANTIAGO),
            # Sin sesión: 401, y antes que el 400
            _ver("/api/calendario", None),
            _ver("/api/calendario?desde=no-es-una-fecha", None),
            # La barra final (307), y los métodos que no tiene (405)
            _ver("/api/calendario/", SANTIAGO),
            _ver("/api/calendario/otra-cosa", SANTIAGO),
            Paso("POST", "/api/calendario", SANTIAGO, {}),
            Paso("HEAD", "/api/calendario", SANTIAGO),
            Paso("DELETE", "/api/calendario", None),
        ]),
        # El panel lo ven quien administra y quien supervisa, y no ven lo
        # mismo: la actividad de quien supervisa no trae el módulo `usuarios`.
        Caso("El panel, a fondo", [
            _ver("/api/panel", SECRETARIA),
            _ver("/api/panel/alertas", SECRETARIA),
            _ver("/api/panel", CLAUDIA),
            _ver("/api/panel/alertas", CLAUDIA),
            # Los demás: 403
            _ver("/api/panel", MARIA),
            _ver("/api/panel/alertas", SANTIAGO),
            # Algo de usuarios y algo académico: el administrador ve los dos en
            # la actividad, el supervisor solo el segundo
            Paso("POST", "/api/usuarios", SECRETARIA,
                 {"nombre": "Alguien del panel", "correo": "panel@campus.test"}),
            Paso("POST", "/api/institucion/eventos", CLAUDIA,
                 {"titulo": "Jornada del panel", "fecha": "2027-06-10", "tipo": "evento"}),
            _ver("/api/panel", SECRETARIA),
            _ver("/api/panel", CLAUDIA),
            _ver("/api/panel/alertas", SECRETARIA),
            # Sin sesión: 401, y antes que el 403
            _ver("/api/panel", None),
            _ver("/api/panel/alertas", None),
            # Parámetros que no usa, la barra final, lo que no existe y los métodos
            _ver("/api/panel?desde=2026-01-01&x=ñ", SECRETARIA),
            _ver("/api/panel/", SECRETARIA),
            _ver("/api/panel/alertas/", SECRETARIA),
            _ver("/api/panel/otra-cosa", SECRETARIA),
            Paso("POST", "/api/panel", SECRETARIA, {}),
            Paso("HEAD", "/api/panel/alertas", SECRETARIA),
            Paso("DELETE", "/api/panel", None),
        ]),
        # Las tareas pendientes van a Django por su camino exacto; lo que
        # cuelga de `/api/tareas/` es de Mi cursada y tiene que seguir igual.
        Caso("Las tareas pendientes, a fondo", [
            # Son de cada uno: el alumno ve las suyas, el docente y la secretaría no cursan
            _ver("/api/tareas/pendientes", SANTIAGO),
            _ver("/api/tareas/pendientes", HERNAN),
            _ver("/api/tareas/pendientes", MARIA),
            _ver("/api/tareas/pendientes", CLAUDIA),
            # Entregar le saca la tarea de la lista, y retirarla la devuelve
            Paso("POST", f"/api/tareas/{TAREA}/mi-entrega", SANTIAGO,
                 {"nombre": "trabajo.pdf", "extension": "pdf", "tipo": "application/pdf",
                  "contenido": "JVBERi0xLjQKJcOkw7zDtsOfCjEgMCBvYmoKPDw+PgplbmRvYmoKdHJhaWxlcgo8PD4+CiUlRU9G"}),
            _ver("/api/tareas/pendientes", SANTIAGO),
            Paso("DELETE", f"/api/tareas/{TAREA}/mi-entrega", SANTIAGO),
            _ver("/api/tareas/pendientes", SANTIAGO),
            # Sin sesión, parámetros que no usa, la barra final y los métodos
            _ver("/api/tareas/pendientes", None),
            _ver("/api/tareas/pendientes?desde=2026-01-01&x=ñ", SANTIAGO),
            _ver("/api/tareas/pendientes/", SANTIAGO),
            Paso("POST", "/api/tareas/pendientes", SANTIAGO, {}),
            Paso("HEAD", "/api/tareas/pendientes", SANTIAGO),
            Paso("DELETE", "/api/tareas/pendientes", None),
            # Lo que cuelga de ella es de Mi cursada (FastAPI): «pendientes» como id
            _ver("/api/tareas/pendientes/mi-entrega", SANTIAGO),
            _ver("/api/tareas/pendientes/cuestionario", SANTIAGO),
            _ver("/api/tareas/pendientes/mi-entrega", None),
            _ver("/api/tareas/pendientes/otra-cosa", SANTIAGO),
            _ver(f"/api/tareas/{TAREA}/mi-entrega", SANTIAGO),
            _ver("/api/tareas", SANTIAGO),
        ]),
        # La auditoría: cinco rutas de lectura, dos de ellas archivos. El
        # escenario no trae eventos, así que primero se generan.
        Caso("La auditoría, a fondo", [
            # Un evento de `usuarios` (solo lo ve quien administra) y uno académico
            Paso("POST", "/api/usuarios", SECRETARIA,
                 {"nombre": "Alguien de la auditoría", "correo": "auditoria@campus.test"}),
            Paso("POST", "/api/institucion/eventos", CLAUDIA,
                 {"titulo": "Jornada de la auditoría", "fecha": "2027-07-10", "tipo": "evento"}),
            # El registro según quién mira
            _ver("/api/auditoria", SECRETARIA),
            _ver("/api/auditoria", CLAUDIA),
            _ver("/api/auditoria", MARIA),
            _ver("/api/auditoria", SANTIAGO),
            _ver("/api/auditoria/opciones", SECRETARIA),
            _ver("/api/auditoria/opciones", CLAUDIA),
            _ver("/api/auditoria/opciones", SANTIAGO),
            _ver("/api/auditoria/mis-materias", MARIA),
            _ver("/api/auditoria/mis-materias?pagina=2&porPagina=1", CLAUDIA),
            _ver("/api/auditoria/mis-materias", SANTIAGO),
            # El detalle: el de usuarios lo ve el administrador y no el supervisor (404)
            _ver("/api/auditoria/1", SECRETARIA),
            _ver("/api/auditoria/1", CLAUDIA),
            _ver("/api/auditoria/2", CLAUDIA),
            _ver("/api/auditoria/999999", SECRETARIA),
            _ver("/api/auditoria/abc", SECRETARIA),
            _ver("/api/auditoria/1", SANTIAGO),
            # Los filtros, uno por uno y juntos
            _ver("/api/auditoria?modulo=usuarios", SECRETARIA),
            _ver("/api/auditoria?modulo=usuarios", CLAUDIA),
            _ver("/api/auditoria?accion=creacion&resultado=exito&rol=Administrador", SECRETARIA),
            _ver("/api/auditoria?q=jornada", SECRETARIA),
            _ver("/api/auditoria?q=JORNADA%20de%20la", SECRETARIA),
            _ver("/api/auditoria?usuarioId=18", SECRETARIA),
            _ver("/api/auditoria?desde=2020-01-01&hasta=2099-12-31", SECRETARIA),
            _ver("/api/auditoria?desde=no-es-fecha", SECRETARIA),
            _ver("/api/auditoria?carreraId=1&sedeId=1&comisionId=1", SECRETARIA),
            _ver("/api/auditoria?carreraId=abc", SECRETARIA),
            # La paginación, con valores raros
            _ver("/api/auditoria?pagina=2&porPagina=1", SECRETARIA),
            _ver("/api/auditoria?pagina=0&porPagina=9999", SECRETARIA),
            _ver("/api/auditoria?pagina=abc&porPagina=", SECRETARIA),
            # Repetido gana el último; vacío; acentos; más de mil parámetros
            _ver("/api/auditoria?modulo=academico&modulo=usuarios", SECRETARIA),
            _ver("/api/auditoria?q=&modulo=", SECRETARIA),
            _ver("/api/auditoria?q=auditor%C3%ADa&x=%C3%B1and%C3%BA", SECRETARIA),
            _ver("/api/auditoria?" + "&".join(f"p{i}=1" for i in range(1100)), SECRETARIA),
            # Exportar: CSV y XLSX, filtrados, y queda anotado
            _ver("/api/auditoria/exportar", SECRETARIA),
            _ver("/api/auditoria/exportar?formato=csv&modulo=academico", CLAUDIA),
            _ver("/api/auditoria/exportar?formato=xlsx", SECRETARIA),
            _ver("/api/auditoria/exportar?formato=XLSX&q=jornada", SECRETARIA),
            _ver("/api/auditoria/exportar?formato=pdf", SECRETARIA),
            _ver("/api/auditoria/exportar", SANTIAGO),
            _ver("/api/auditoria?accion=descarga", SECRETARIA),
            # Sin sesión, la barra final y los métodos que no existen
            _ver("/api/auditoria", None),
            _ver("/api/auditoria/abc", None),
            _ver("/api/auditoria/exportar", None),
            _ver("/api/auditoria/", SECRETARIA),
            _ver("/api/auditoria/1/otra", SECRETARIA),
            Paso("POST", "/api/auditoria", SECRETARIA, {}),
            Paso("PUT", "/api/auditoria/1", SECRETARIA, {}),
            Paso("DELETE", "/api/auditoria/1", SECRETARIA),
            Paso("HEAD", "/api/auditoria/exportar", SECRETARIA),
        ]),
        # La inscripción a materias: el primer módulo migrado que escribe. Se
        # compara además qué quedó guardado: la inscripción, el módulo que se
        # crea al anotarse y el que se borra al darse de baja.
        Caso("La inscripción a materias, a fondo", [
            # Con el período cerrado: el plan se ve y no se puede anotar. Se
            # cierra a propósito: el escenario lo trae abierto.
            Paso("PUT", "/api/institucion/configuracion/periodo", CLAUDIA,
                 {"desde": "2020-01-01", "hasta": "2020-12-31"}),
            _ver("/api/inscripciones/materias", SANTIAGO),
            Paso("POST", "/api/inscripciones/materias/113", SANTIAGO),
            Paso("DELETE", "/api/inscripciones/materias/119", SANTIAGO),
            # Se abre el período (lo hace la secretaría, todavía en FastAPI)
            Paso("PUT", "/api/institucion/configuracion/periodo", CLAUDIA,
                 {"desde": "2020-01-01", "hasta": "2099-12-31"}),
            _ver("/api/inscripciones/materias", SANTIAGO),
            # Habilitada: entra, y el módulo aparece en su grilla
            Paso("POST", "/api/inscripciones/materias/113", SANTIAGO),
            _ver("/api/cursos", SANTIAGO),
            # Otra vez: 409. Bloqueada, sin cupo, aprobada: 403. No existe: 404
            Paso("POST", "/api/inscripciones/materias/113", SANTIAGO),
            Paso("POST", "/api/inscripciones/materias/114", SANTIAGO),
            Paso("POST", "/api/inscripciones/materias/116", SANTIAGO),
            Paso("POST", "/api/inscripciones/materias/101", SANTIAGO),
            Paso("POST", "/api/inscripciones/materias/99999", SANTIAGO),
            Paso("POST", "/api/inscripciones/materias/abc", SANTIAGO),
            # Darse de baja: la recién anotada (se lleva el módulo si era el
            # único) y la que ya tenía; y una en la que no está: 409
            Paso("DELETE", "/api/inscripciones/materias/113", SANTIAGO),
            Paso("DELETE", "/api/inscripciones/materias/119", SANTIAGO),
            Paso("DELETE", "/api/inscripciones/materias/119", SANTIAGO),
            Paso("DELETE", "/api/inscripciones/materias/99999", SANTIAGO),
            _ver("/api/inscripciones/materias", SANTIAGO),
            _ver("/api/cursos", SANTIAGO),
            # Otro alumno, el docente y la secretaría (no cursan: 404 y 403)
            _ver("/api/inscripciones/materias", HERNAN),
            Paso("POST", "/api/inscripciones/materias/113", HERNAN),
            _ver("/api/inscripciones/materias", MARIA),
            Paso("POST", "/api/inscripciones/materias/113", MARIA),
            Paso("DELETE", "/api/inscripciones/materias/113", SECRETARIA),
            # Sin sesión (401 antes que el 400), un cuerpo que no se usa,
            # la barra final y los métodos que no tiene
            _ver("/api/inscripciones/materias", None),
            Paso("POST", "/api/inscripciones/materias/abc", None),
            Paso("POST", "/api/inscripciones/materias/113", SANTIAGO, {"algo": "que no se usa"}),
            _ver("/api/inscripciones/materias/", SANTIAGO),
            _ver("/api/inscripciones/materias/113", SANTIAGO),
            Paso("PUT", "/api/inscripciones/materias/113", SANTIAGO, {}),
            Paso("POST", "/api/inscripciones/materias", SANTIAGO),
            _ver("/api/inscripciones", SANTIAGO),
            Paso("HEAD", "/api/inscripciones/materias", SANTIAGO),
        ]),
        # Finales, la mitad del alumno. La gestión docente sigue en FastAPI y
        # se mira al final: lo que hace el alumno tiene que verse igual del
        # otro lado.
        Caso("Los finales del alumno, a fondo", [
            _ver("/api/finales/mesas", SANTIAGO),
            _ver("/api/finales/proximas", SANTIAGO),
            _ver("/api/finales/resultados", SANTIAGO),
            _ver("/api/finales/mesas", HERNAN),
            _ver("/api/finales/resultados", HERNAN),
            _ver("/api/finales/mesas", MARIA),
            _ver("/api/finales/proximas", SECRETARIA),
            # Disponible: entra; otra vez 409; baja; otra baja 409; vuelve (misma fila)
            Paso("POST", "/api/finales/mesas/1/inscripcion", SANTIAGO),
            Paso("POST", "/api/finales/mesas/1/inscripcion", SANTIAGO),
            _ver("/api/finales/proximas", SANTIAGO),
            Paso("DELETE", "/api/finales/mesas/1/inscripcion", SANTIAGO),
            Paso("DELETE", "/api/finales/mesas/1/inscripcion", SANTIAGO),
            Paso("POST", "/api/finales/mesas/1/inscripcion", SANTIAGO),
            # La que ya tenía (2), una cancelada (8), una que no abrió (3), una
            # sin habilitación (7), una que no existe y un id que no es número
            Paso("DELETE", "/api/finales/mesas/2/inscripcion", SANTIAGO),
            Paso("POST", "/api/finales/mesas/8/inscripcion", SANTIAGO),
            Paso("POST", "/api/finales/mesas/3/inscripcion", SANTIAGO),
            Paso("POST", "/api/finales/mesas/7/inscripcion", SANTIAGO),
            Paso("DELETE", "/api/finales/mesas/3/inscripcion", SANTIAGO),
            Paso("POST", "/api/finales/mesas/99999/inscripcion", SANTIAGO),
            Paso("DELETE", "/api/finales/mesas/abc/inscripcion", SANTIAGO),
            _ver("/api/finales/mesas", SANTIAGO),
            # Lo ve la cátedra (gestión, todavía FastAPI): la planilla de la mesa 1.
            # `/gestion/inscriptos?mesaId=1` no va: se cae con un 500 en los dos
            # frameworks, porque la inscripción que crea el alumno no trae el
            # campo `comision` que esa pantalla da por sentado. Es un error de
            # antes de la migración; se arregla con la gestión docente.
            _ver("/api/finales/gestion/mesas/1", SECRETARIA),
            # Sin sesión, un cuerpo que no se usa, la barra final, lo que no existe
            _ver("/api/finales/mesas", None),
            Paso("POST", "/api/finales/mesas/abc/inscripcion", None),
            Paso("POST", "/api/finales/mesas/1/inscripcion", HERNAN, {"no": "se usa"}),
            _ver("/api/finales/mesas/", SANTIAGO),
            _ver("/api/finales/mesas/1", SANTIAGO),
            _ver("/api/finales/mesas/1/inscripcion", SANTIAGO),
            _ver("/api/finales", SANTIAGO),
            Paso("PUT", "/api/finales/mesas/1/inscripcion", SANTIAGO, {}),
            Paso("POST", "/api/finales/proximas", SANTIAGO),
            Paso("HEAD", "/api/finales/resultados", SANTIAGO),
        ]),
        _caso_archivos(),
        # El foro. El tema 1 es de Hernán (3), en el módulo 1; la respuesta 3 es de María
        Caso("El foro, a fondo", [
            _ver("/api/foro", SANTIAGO),
            _ver("/api/foro", SECRETARIA),
            _ver("/api/foro/1", SANTIAGO),
            _ver("/api/foro/99999", SANTIAGO),
            _ver("/api/foro/abc", SANTIAGO),
            # Abrir: bien, sin asignatura, sin texto, de un módulo ajeno
            Paso("POST", "/api/foro", SANTIAGO, {"cursoId": CURSO, "titulo": "Duda del TP", "texto": "¿Se entrega en PDF?"}),
            Paso("POST", "/api/foro", SANTIAGO, {"titulo": "Sin asignatura", "texto": "x"}),
            Paso("POST", "/api/foro", SANTIAGO, {"cursoId": CURSO, "titulo": "", "texto": ""}),
            Paso("POST", "/api/foro", SANTIAGO, {"cursoId": 99999, "titulo": "x", "texto": "x"}),
            Paso("POST", "/api/foro", SANTIAGO),
            # Responder, seguir, votar
            Paso("POST", "/api/foro/1", SANTIAGO, {"texto": "Yo también tengo esa duda"}),
            Paso("POST", "/api/foro/1", SANTIAGO, {"texto": "  "}),
            Paso("POST", "/api/foro/99999", SANTIAGO, {"texto": "x"}),
            Paso("POST", "/api/foro/1/seguir", SANTIAGO),
            Paso("POST", "/api/foro/1/seguir", SANTIAGO),
            Paso("POST", "/api/foro/1/mensajes/3/voto", SANTIAGO),
            Paso("POST", "/api/foro/1/mensajes/3/voto", SANTIAGO),
            Paso("POST", "/api/foro/1/mensajes/99999/voto", SANTIAGO),
            _ver("/api/foro/1", HERNAN),
            # Retirar: la respuesta ajena sin motivo (403 o 400), con motivo quien modera
            Paso("DELETE", "/api/foro/1/mensajes/3", SANTIAGO, {}),
            Paso("DELETE", "/api/foro/1/mensajes/3", MARIA),
            Paso("DELETE", "/api/foro/1/mensajes/2", SECRETARIA, {}),
            Paso("DELETE", "/api/foro/1/mensajes/2", SECRETARIA, {"motivo": "Fuera de tema"}),
            Paso("DELETE", "/api/foro/2", SANTIAGO, {}),
            Paso("DELETE", "/api/foro/2", CLAUDIA, {"motivo": "Duplicado"}),
            Paso("DELETE", "/api/foro/2", CLAUDIA, {"motivo": "Duplicado"}),
            _ver("/api/foro", SANTIAGO),
            # Sin sesión, barras y métodos
            _ver("/api/foro", None),
            Paso("POST", "/api/foro/1", None, {"texto": "x"}),
            _ver("/api/foro/", SANTIAGO),
            Paso("PUT", "/api/foro/1", SANTIAGO, {}),
            _ver("/api/foro/1/seguir", SANTIAGO),
            Paso("HEAD", "/api/foro", SANTIAGO),
        ]),
        # Novedades. La 1 es de María (2) y está destacada; la 2 es de otro docente (8)
        Caso("Las novedades, a fondo", [
            _ver("/api/novedades", SANTIAGO),
            _ver("/api/novedades", MARIA),
            # Publicar: el docente sí, el alumno 403, sin título 400; destacar desancla la anterior
            Paso("POST", "/api/novedades", MARIA, {"titulo": "Cambio de aula", "cuerpo": "Nos vemos en el 12",
                                                   "categoria": "Académico", "ambito": "Programación II", "anclada": True}),
            Paso("POST", "/api/novedades", SANTIAGO, {"titulo": "No", "cuerpo": "No"}),
            Paso("POST", "/api/novedades", MARIA, {"titulo": "", "cuerpo": ""}),
            Paso("POST", "/api/novedades", MARIA),
            _ver("/api/novedades", SANTIAGO),
            # Editar: la propia sí, la ajena 403, inexistente 404
            Paso("PUT", "/api/novedades/1", MARIA, {"titulo": "Editada", "cuerpo": "Otro texto"}),
            Paso("PUT", "/api/novedades/2", MARIA, {"titulo": "No", "cuerpo": "No"}),
            Paso("PUT", "/api/novedades/99999", MARIA, {"titulo": "x", "cuerpo": "x"}),
            Paso("PUT", "/api/novedades/abc", MARIA, {"titulo": "x", "cuerpo": "x"}),
            # La imagen: PNG sí, otra cosa 415, ajena 403; quitarla
            Paso("POST", "/api/novedades/1/imagen", MARIA,
                 {"nombre": "portada.png", "extension": "png", "tipo": "image/png", "contenido": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="}),
            Paso("POST", "/api/novedades/1/imagen", MARIA,
                 {"nombre": "x.svg", "extension": "svg", "tipo": "image/svg+xml", "contenido": "PHN2Zy8+"}),
            Paso("POST", "/api/novedades/2/imagen", MARIA,
                 {"nombre": "portada.png", "extension": "png", "tipo": "image/png", "contenido": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="}),
            Paso("POST", "/api/novedades/1/imagen", MARIA),
            _ver("/api/novedades", SANTIAGO),
            Paso("DELETE", "/api/novedades/1/imagen", MARIA),
            Paso("DELETE", "/api/novedades/1/imagen", MARIA),
            # Reacciones: una por persona, otra la reemplaza, la misma la saca
            Paso("POST", "/api/novedades/1/reaccion", SANTIAGO, {"tipo": "util"}),
            Paso("POST", "/api/novedades/1/reaccion", SANTIAGO, {"tipo": "dudas"}),
            Paso("POST", "/api/novedades/1/reaccion", SANTIAGO, {"tipo": "dudas"}),
            Paso("POST", "/api/novedades/1/reaccion", SANTIAGO, {"tipo": "inventada"}),
            Paso("POST", "/api/novedades/1/reaccion", SANTIAGO, {"tipo": None}),
            Paso("POST", "/api/novedades/99999/reaccion", SANTIAGO, {"tipo": "util"}),
            # Retirar: la propia, la ajena sin motivo 400, con motivo quien supervisa
            Paso("DELETE", "/api/novedades/2", CLAUDIA, {}),
            Paso("DELETE", "/api/novedades/2", CLAUDIA, {"motivo": "Información vieja"}),
            Paso("DELETE", "/api/novedades/3", SANTIAGO, {"motivo": "No"}),
            Paso("DELETE", "/api/novedades/3", MARIA),
            _ver("/api/novedades", SANTIAGO),
            # Sin sesión, barras y métodos
            _ver("/api/novedades", None),
            Paso("PUT", "/api/novedades/1", None, {"titulo": "x"}),
            _ver("/api/novedades/", SANTIAGO),
            _ver("/api/novedades/1", SANTIAGO),
            Paso("PATCH", "/api/novedades/1", MARIA, {}),
            Paso("HEAD", "/api/novedades", SANTIAGO),
        ]),
        # Mensajes: conversaciones de a dos. La 1 es de Santiago (1) y María (2);
        # el mensaje 1 es de Santiago y el 2 de María.
        Caso("Los mensajes, a fondo", [
            _ver("/api/mensajes", SANTIAGO),
            _ver("/api/mensajes", MARIA),
            _ver("/api/mensajes/contactos", SANTIAGO),
            _ver("/api/mensajes/contactos", SECRETARIA),
            # Ajena (la 2 es de Santiago con Hernán): 404, no 403
            _ver("/api/mensajes/2", MARIA),
            _ver("/api/mensajes/1", SANTIAGO),
            _ver("/api/mensajes/abc", SANTIAGO),
            # Mandar: texto, vacío, con una imagen y con un adjunto que no se acepta
            Paso("POST", "/api/mensajes/1", SANTIAGO, {"texto": "  Hola, profe  "}),
            Paso("POST", "/api/mensajes/1", SANTIAGO, {"texto": "   "}),
            Paso("POST", "/api/mensajes/1", SANTIAGO),
            Paso("POST", "/api/mensajes/1", SANTIAGO, {"texto": "", "adjuntos": [
                {"nombre": "foto.png", "extension": "png", "tipo": "image/png",
                 "contenido": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="}]}),
            Paso("POST", "/api/mensajes/1", SANTIAGO, {"adjuntos": [
                {"nombre": "virus.exe", "extension": "exe", "contenido": "TVo="}]}),
            Paso("POST", "/api/mensajes/2", MARIA, {"texto": "No es mía"}),
            # Editar: el propio sí (queda marcado), el ajeno 403, inexistente 404
            Paso("PATCH", "/api/mensajes/1/mensajes/1", SANTIAGO, {"texto": "Hola (editado)"}),
            Paso("PATCH", "/api/mensajes/1/mensajes/2", SANTIAGO, {"texto": "No"}),
            Paso("PATCH", "/api/mensajes/1/mensajes/1", SANTIAGO, {"texto": ""}),
            Paso("PATCH", "/api/mensajes/1/mensajes/99999", SANTIAGO, {"texto": "x"}),
            Paso("PATCH", "/api/mensajes/1/mensajes/abc", SANTIAGO, {"texto": "x"}),
            # Fijar: cualquiera de los dos, uno solo; tocarlo de nuevo lo suelta
            Paso("POST", "/api/mensajes/1/mensajes/2/fijar", SANTIAGO),
            Paso("POST", "/api/mensajes/1/mensajes/3/fijar", MARIA),
            _ver("/api/mensajes/1", MARIA),
            Paso("POST", "/api/mensajes/1/mensajes/3/fijar", MARIA),
            Paso("POST", "/api/mensajes/2/mensajes/4/fijar", MARIA),
            # Eliminar: el propio, el ajeno 403, y el fijado se suelta
            Paso("POST", "/api/mensajes/1/mensajes/1/fijar", SANTIAGO),
            Paso("DELETE", "/api/mensajes/1/mensajes/1", SANTIAGO),
            Paso("DELETE", "/api/mensajes/1/mensajes/2", SANTIAGO),
            Paso("DELETE", "/api/mensajes/1/mensajes/1", SANTIAGO),
            _ver("/api/mensajes/1", SANTIAGO),
            # Abrir con alguien: la existente, una nueva, consigo mismo, inexistente, roto
            Paso("POST", "/api/mensajes", SANTIAGO, {"paraId": MARIA}),
            Paso("POST", "/api/mensajes", SANTIAGO, {"paraId": PABLO}),
            Paso("POST", "/api/mensajes", SANTIAGO, {"paraId": SANTIAGO}),
            Paso("POST", "/api/mensajes", SANTIAGO, {"paraId": 99999}),
            Paso("POST", "/api/mensajes", SANTIAGO, {"paraId": "abc"}),
            Paso("POST", "/api/mensajes", SANTIAGO),
            _ver("/api/mensajes", SANTIAGO),
            # Mismo camino, otro método: «contactos» cae en POST /{id} (400)
            Paso("POST", "/api/mensajes/contactos", SANTIAGO, {"texto": "x"}),
            Paso("DELETE", "/api/mensajes/contactos", SANTIAGO),
            # Sin sesión, barras y métodos
            _ver("/api/mensajes", None),
            Paso("POST", "/api/mensajes/1", None, {"texto": "x"}),
            _ver("/api/mensajes/", SANTIAGO),
            Paso("PUT", "/api/mensajes/1", SANTIAGO, {}),
            Paso("GET", "/api/mensajes/1/mensajes/2", SANTIAGO),
            Paso("HEAD", "/api/mensajes", SANTIAGO),
        ]),
        # La salud del servidor: la abierta y la de Firestore (solo administración)
        Caso("La salud, a fondo", [
            _ver("/api/salud", None),
            _ver("/api/salud?x=1", SANTIAGO),
            _ver("/api/salud/", None),
            Paso("POST", "/api/salud", None, {}),
            Paso("HEAD", "/api/salud", None),
            _ver("/api/salud/firestore", SECRETARIA),
            _ver("/api/salud/firestore", CLAUDIA),
            _ver("/api/salud/firestore", MARIA),
            _ver("/api/salud/firestore", None),
            _ver("/api/salud/firestore/", SECRETARIA),
            Paso("DELETE", "/api/salud/firestore", SECRETARIA),
        ]),
        # Quién soy y las campanitas: las piden todas las pantallas
        Caso("La sesión y las campanitas, a fondo", [
            _ver("/api/me", SANTIAGO),
            _ver("/api/me", MARIA),
            _ver("/api/me", SECRETARIA),
            _ver("/api/me", CLAUDIA),
            _ver("/api/contadores", SANTIAGO),
            _ver("/api/contadores", MARIA),
            _ver("/api/contadores", SECRETARIA),
            # Algo nuevo para Santiago: un mensaje sin leer y una novedad
            Paso("POST", "/api/mensajes", MARIA, {"paraId": SANTIAGO}),
            Paso("POST", f"/api/mensajes/{CONVERSACION}", MARIA, {"texto": "¿Viste la consigna?"}),
            Paso("POST", "/api/novedades", MARIA,
                 {"titulo": "Novedad de las campanitas", "cuerpo": "Texto", "ambito": "Programación II"}),
            _ver("/api/contadores", SANTIAGO),
            # Leerlo baja la campanita
            _ver(f"/api/mensajes/{CONVERSACION}", SANTIAGO),
            _ver("/api/contadores", SANTIAGO),
            # Sin sesión, parámetros, barras, lo que no existe y los métodos
            _ver("/api/me", None),
            _ver("/api/contadores", None),
            _ver("/api/me?x=1", SANTIAGO),
            _ver("/api/me/", SANTIAGO),
            _ver("/api/contadores/", SANTIAGO),
            _ver("/api/me/otra-cosa", SANTIAGO),
            Paso("PUT", "/api/me", SANTIAGO, {"nombre": "No va"}),
            Paso("POST", "/api/contadores", SANTIAGO, {}),
            Paso("HEAD", "/api/me", SANTIAGO),
        ]),
        Caso("La biblioteca y sus filtros", [
            _ver("/api/biblioteca?orden=titulo", CLAUDIA),
            _ver("/api/biblioteca?q=programacion&pagina=1&porPagina=5", CLAUDIA),
            _ver("/api/biblioteca?pagina=abc", CLAUDIA),
            _ver("/api/biblioteca/pendientes", MARIA),
            _ver("/api/biblioteca/mis-aportes", SANTIAGO),
        ]),
        Caso("La auditoría y sus filtros", [
            _ver("/api/auditoria?porPagina=5", SECRETARIA),
            _ver("/api/auditoria?modulo=usuarios", SECRETARIA),
            _ver("/api/auditoria?modulo=usuarios", CLAUDIA),
            _ver("/api/auditoria/mis-materias", MARIA),
            _ver("/api/auditoria/99999999", SECRETARIA),
        ]),
        Caso("Finales, las dos mitades", [
            _ver("/api/finales/mesas", SANTIAGO),
            _ver("/api/finales/proximas", SANTIAGO),
            _ver("/api/finales/resultados", SANTIAGO),
            _ver("/api/finales/gestion/mesas", MARIA),
            _ver("/api/finales/gestion/inscriptos", MARIA),
            _ver("/api/finales/gestion/mesas", SANTIAGO),
        ]),
        Caso("El plan y las inscripciones", [
            _ver("/api/inscripciones/materias", SANTIAGO),
            _ver(f"/api/institucion/materias?carreraId=1&anio=1", SECRETARIA),
            _ver("/api/institucion/materias?estado=inventado", SECRETARIA),
        ]),
        Caso("Una persona y su ficha", [
            _ver(f"/api/usuarios/{MARIA}/foto", SANTIAGO),
            _ver("/api/usuarios?rol=Docente", SECRETARIA),
            _ver("/api/usuarios?q=sosa", SECRETARIA),
        ]),
        Caso("Mensajes y foro", [
            _ver("/api/mensajes", SANTIAGO),
            _ver("/api/mensajes/contactos", SANTIAGO),
            _ver("/api/foro", SANTIAGO),
            _ver("/api/mensajes/99999", SANTIAGO),
        ]),
    ]


# ===================== Los que escriben =====================
# Son los que más importan: una migración rompe más fácil un POST que un GET,
# y acá se compara además **qué quedó guardado**, no solo qué contestó.
def escriben() -> list[Caso]:
    return [
        Caso("Marcar y desmarcar un favorito", [
            Paso("POST", f"/api/cursos/{CURSO}/favorito", SANTIAGO),
            _ver("/api/cursos", SANTIAGO),
            Paso("POST", f"/api/cursos/{CURSO}/favorito", SANTIAGO),
            _ver("/api/cursos", SANTIAGO),
            # Y uno ajeno: 404 en las dos
            Paso("POST", "/api/cursos/5/favorito", SANTIAGO),
        ]),
        Caso("Abrir un tema del foro y contestarlo", [
            Paso("POST", "/api/foro", SANTIAGO, {
                "asignatura": "Programación II",
                "titulo": "Consulta del banco",
                "texto": "¿Esto se compara igual en los dos?",
            }),
            _ver("/api/foro", SANTIAGO),
        ]),
        Caso("Crear una carrera, editarla y darla de baja", [
            Paso("POST", "/api/institucion/carreras", SECRETARIA,
                 {"nombre": "Carrera del banco", "codigo": "BNC"}),
            _ver("/api/institucion/carreras", SECRETARIA),
            # Repetir el código: 409 en las dos
            Paso("POST", "/api/institucion/carreras", SECRETARIA,
                 {"nombre": "Otra", "codigo": "BNC"}),
            # Sin nombre: 400 en las dos
            Paso("POST", "/api/institucion/carreras", SECRETARIA, {"codigo": "XX"}),
            # Y sin permiso: 403 en las dos
            Paso("POST", "/api/institucion/carreras", MARIA,
                 {"nombre": "No va", "codigo": "NOV"}),
        ]),
        Caso("Cambiar la configuración académica", [
            Paso("PUT", "/api/institucion/configuracion/asistencia", CLAUDIA,
                 {"minimoPorDefecto": 80, "justificadaDescuenta": True}),
            _ver("/api/institucion/configuracion", CLAUDIA),
            Paso("PUT", "/api/institucion/configuracion/asistencia", CLAUDIA,
                 {"minimoPorDefecto": 500, "justificadaDescuenta": True}),
            Paso("PUT", "/api/institucion/configuracion/periodo", SANTIAGO,
                 {"desde": "2026-03-01", "hasta": "2026-03-20"}),
        ]),
        Caso("Publicar una novedad y reaccionar", [
            Paso("POST", "/api/novedades", MARIA, {
                "titulo": "Aviso del banco",
                "cuerpo": "Texto de prueba",
                "categoria": "General",
                "ambito": "Institucional",
            }),
            _ver("/api/novedades", SANTIAGO),
        ]),
        Caso("Cambiarle el rol a alguien", [
            Paso("PATCH", "/api/usuarios/3", SECRETARIA, {"roles": ["Estudiante", "Docente"]}),
            _ver("/api/usuarios", SECRETARIA),
            # A sí mismo: 403 en las dos
            Paso("PATCH", "/api/usuarios/18", SECRETARIA, {"roles": ["Estudiante"]}),
            # Un rol que no existe: 400
            Paso("PATCH", "/api/usuarios/3", SECRETARIA, {"roles": ["Rector"]}),
        ]),
        Caso("Editar el perfil propio", [
            Paso("PUT", "/api/usuarios/yo", SANTIAGO, {"telefono": "3794-000111"}),
            _ver("/api/usuarios/yo", SANTIAGO),
            # Lo que no se puede: 403
            Paso("PUT", "/api/usuarios/yo", SANTIAGO, {"roles": ["Administrador"]}),
            # Fecha imposible: 400
            Paso("PUT", "/api/usuarios/yo", SANTIAGO, {"fechaNacimiento": "2090-01-01"}),
        ]),
        Caso("El progreso del alumno", [
            Paso("PUT", f"/api/cursos/{CURSO}/mi-progreso/1-1", SANTIAGO),
            _ver("/api/mi-progreso", SANTIAGO),
            Paso("DELETE", f"/api/cursos/{CURSO}/mi-progreso/1-1", SANTIAGO),
            _ver("/api/mi-progreso", SANTIAGO),
            # Un identificador inventado: tiene que rechazarse igual
            Paso("PUT", f"/api/cursos/{CURSO}/mi-progreso/no-existe", SANTIAGO),
        ]),
        Caso("El ámbito de quien supervisa", [
            Paso("PATCH", "/api/usuarios/19", SECRETARIA,
                 {"ambito": {"carreras": [1], "sedes": []}}),
            _ver("/api/biblioteca/opciones", CLAUDIA),
            _ver("/api/auditoria/opciones", CLAUDIA),
            Paso("PATCH", "/api/usuarios/19", SECRETARIA,
                 {"ambito": {"carreras": [999999], "sedes": []}}),
        ]),
        Caso("Lo que ya no existe", [
            Paso("PUT", "/api/me", SECRETARIA, {"nombre": "X", "apellido": "Y"}),
            _ver("/api/actividad", SECRETARIA),
            _ver("/api/informacion", SECRETARIA),
        ]),
    ]


# ===================== El resto de los apartados =====================
# Separados de `escriben()` solo para que cada bloque se lea: son igual de
# importantes. Los identificadores salen del escenario (`datos_de_prueba.json`),
# no están inventados: un caso que da 404 en las dos aplicaciones compara que
# las dos se equivoquen igual, que no es lo que se quiere mirar.
TEMA = 1
CONVERSACION = 1
NOVEDAD = 1
TAREA = 1
MESA = 1
COMISION = 1


def apartados() -> list[Caso]:
    return [
        Caso("Un tema del foro, abierto y contestado", [
            _ver(f"/api/foro/{TEMA}", SANTIAGO),
            Paso("POST", f"/api/foro/{TEMA}", SANTIAGO, {"texto": "Una respuesta"}),
            _ver(f"/api/foro/{TEMA}", MARIA),
            Paso("DELETE", f"/api/foro/{TEMA}", SANTIAGO),
            _ver("/api/foro", SANTIAGO),
        ]),
        Caso("Una conversación: abrir, escribir, editar y borrar", [
            _ver(f"/api/mensajes/{CONVERSACION}", SANTIAGO),
            Paso("POST", f"/api/mensajes/{CONVERSACION}", SANTIAGO, {"texto": "Hola"}),
            Paso("POST", "/api/mensajes", SANTIAGO, {"paraId": 5}),
            _ver("/api/mensajes", SANTIAGO),
            # De otro: 404 en las dos
            _ver(f"/api/mensajes/{CONVERSACION}", PABLO),
        ]),
        Caso("Una novedad: reaccionar, editar y retirar", [
            Paso("POST", f"/api/novedades/{NOVEDAD}/reaccion", SANTIAGO, {"tipo": "lei"}),
            _ver("/api/novedades", SANTIAGO),
            Paso("POST", f"/api/novedades/{NOVEDAD}/reaccion", SANTIAGO, None),
            Paso("PUT", f"/api/novedades/{NOVEDAD}", MARIA,
                 {"titulo": "Editada", "cuerpo": "Otro texto"}),
            # De otro docente: 403 en las dos
            Paso("PUT", f"/api/novedades/{NOVEDAD}", PABLO, {"titulo": "No va"}),
            Paso("DELETE", f"/api/novedades/{NOVEDAD}", MARIA),
        ]),
        Caso("Un trabajo: verlo, entregarlo y retirarlo", [
            _ver(f"/api/tareas/{TAREA}/mi-entrega", SANTIAGO),
            # El docente no entrega: 403 en las dos
            _ver(f"/api/tareas/{TAREA}/mi-entrega", MARIA),
            _ver(f"/api/cursos/{CURSO}/tareas/{TAREA}/entregas", MARIA),
            Paso("DELETE", f"/api/tareas/{TAREA}/mi-entrega", SANTIAGO),
            _ver("/api/tareas/pendientes", SANTIAGO),
        ]),
        Caso("Las mesas de final", [
            _ver(f"/api/finales/gestion/mesas/{MESA}", MARIA),
            _ver(f"/api/finales/gestion/mesas/{MESA}", SANTIAGO),
            Paso("POST", f"/api/finales/mesas/{MESA}/inscripcion", SANTIAGO),
            _ver("/api/finales/mesas", SANTIAGO),
            Paso("DELETE", f"/api/finales/mesas/{MESA}/inscripcion", SANTIAGO),
            # Crear una mesa sin ser titular: 403 en las dos
            Paso("POST", "/api/finales/gestion/mesas", PABLO,
                 {"materiaId": MATERIA, "fecha": "2027-03-01", "hora": "09:00"}),
        ]),
        Caso("Inscribirse a una materia y darse de baja", [
            _ver("/api/inscripciones/materias", SANTIAGO),
            Paso("POST", "/api/inscripciones/materias/102", SANTIAGO),
            _ver("/api/inscripciones/materias", SANTIAGO),
            Paso("DELETE", "/api/inscripciones/materias/102", SANTIAGO),
            # Una que no existe: 404 en las dos
            Paso("POST", "/api/inscripciones/materias/999999", SANTIAGO),
        ]),
        Caso("La estructura: planes, sedes y comisiones", [
            Paso("POST", "/api/institucion/sedes", SECRETARIA, {"nombre": "Sede del banco"}),
            Paso("POST", "/api/institucion/planes", SECRETARIA,
                 {"nombre": "Plan del banco", "carreraId": 1}),
            _ver(f"/api/institucion/comisiones/{COMISION}", SECRETARIA),
            Paso("PATCH", f"/api/institucion/comisiones/{COMISION}", SECRETARIA,
                 {"nombre": "Comisión editada"}),
            _ver("/api/institucion/comisiones", SECRETARIA),
            Paso("DELETE", f"/api/institucion/comisiones/{COMISION}", MARIA),
        ]),
        Caso("Las materias del plan", [
            Paso("POST", "/api/institucion/materias", SECRETARIA, {
                "carreraId": 1, "planId": 1, "codigo": "BNC-1",
                "nombre": "Materia del banco", "anio": 1, "cuatrimestre": 1,
            }),
            _ver("/api/institucion/materias?q=banco", SECRETARIA),
            Paso("PATCH", "/api/institucion/materias/101", SECRETARIA, {"anio": 2}),
            # Año imposible: 400 en las dos
            Paso("PATCH", "/api/institucion/materias/101", SECRETARIA, {"anio": 99}),
            Paso("DELETE", "/api/institucion/materias/101", SECRETARIA),
            # Sin permiso: 403
            Paso("DELETE", "/api/institucion/materias/102", MARIA),
        ]),
        Caso("Alta de una cuenta y su historial", [
            Paso("POST", "/api/usuarios", SECRETARIA,
                 {"nombre": "Alguien del banco", "correo": "banco@campus.test"}),
            _ver("/api/usuarios?q=banco", SECRETARIA),
            _ver("/api/usuarios/historial", SECRETARIA),
            # Repetido: 409 en las dos
            Paso("POST", "/api/usuarios", SECRETARIA,
                 {"nombre": "Otro", "correo": "banco@campus.test"}),
        ]),
        Caso("Los eventos del calendario", [
            Paso("POST", "/api/institucion/eventos", CLAUDIA,
                 {"titulo": "Jornada del banco", "fecha": "2027-05-10", "tipo": "evento"}),
            _ver("/api/institucion/eventos", CLAUDIA),
            _ver("/api/calendario?desde=2027-05-01&hasta=2027-05-31", SANTIAGO),
            # Sin permiso: 403 en las dos
            Paso("POST", "/api/institucion/eventos", SANTIAGO,
                 {"titulo": "No va", "fecha": "2027-05-10", "tipo": "evento"}),
        ]),
        Caso("Las asignaciones de estudiantes", [
            _ver("/api/institucion/asignaciones", CLAUDIA),
            _ver("/api/institucion/legajo-siguiente?carreraId=1", CLAUDIA),
            _ver("/api/institucion/legajo-siguiente?carreraId=999999", CLAUDIA),
        ]),
        Caso("Los archivos, sin subir nada", [
            Paso("POST", "/api/archivos/enlace-de-subida", MARIA,
                 {"modulo": "modulos", "nombre": "x.pdf", "tipo": "application/pdf"}),
            Paso("POST", "/api/archivos/confirmar", MARIA, {"objeto": "inventado"}),
            _ver("/api/archivos/inventado/enlace", MARIA),
        ]),
    ]


# ===================== El barrido =====================
def barrido(rutas: list[tuple[str, str]]) -> list[Caso]:
    """Cuatro pedidos a cada ruta que escribe o que lleva parámetros.

    No buscan el camino feliz —para eso están los casos de cada apartado—
    sino lo que una migración rompe sin que se note: la sesión, la
    conversión de los parámetros, el cuerpo, los permisos y el orden de los
    errores. Como administración con un cuerpo vacío, como docente, sin
    sesión y con un identificador que no es un número.

    Una ruta por caso: el campus se repone entre uno y otro, así que una
    escritura no arrastra a las demás y la diferencia queda en su ruta.
    """
    import re

    salida = []
    for metodo, camino in sorted(rutas):
        con_parametros_de_camino = "{" in camino
        if metodo == "GET" and not con_parametros_de_camino:
            continue  # ya los mira `automaticos`
        concreto = re.sub(r"\{[^}]+\}", "1", camino)
        pasos = [
            Paso(metodo, concreto, SECRETARIA, {} if metodo != "GET" else None),
            Paso(metodo, concreto, MARIA, {} if metodo != "GET" else None),
            Paso(metodo, concreto, None, {} if metodo != "GET" else None),
        ]
        if con_parametros_de_camino:
            no_numero = re.sub(r"\{[^}]+\}", "abc", camino, count=1)
            pasos.append(Paso(metodo, re.sub(r"\{[^}]+\}", "1", no_numero), MARIA,
                              {} if metodo != "GET" else None))
        salida.append(Caso(f"Barrido {metodo} {camino}", pasos))
    return salida


def todos(rutas: list[tuple[str, str]]) -> list[Caso]:
    return automaticos(rutas) + con_parametros() + escriben() + apartados() + barrido(rutas)
