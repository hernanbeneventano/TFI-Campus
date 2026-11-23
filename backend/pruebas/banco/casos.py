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


def todos(rutas: list[tuple[str, str]]) -> list[Caso]:
    return automaticos(rutas) + con_parametros() + escriben() + apartados()
