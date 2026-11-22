"""Guardar el campus en Firestore, sin reescribir las veinte rutas.

El problema
-----------
Toda la aplicación lee y escribe las listas de `datos.py` directamente:
`d.materias_plan.append(...)`, `materia["cupo"] = 30`, `d.cursos.remove(c)`.
Son cientos de lugares, muchos de ellos **mutaciones en el lugar** sobre un
diccionario que ya está en la lista. No hay un punto por el que pasen todas,
así que no alcanza con envolver la lista: un `materia.update(...)` no llama a
ningún método de la lista.

Se podía reescribir cada ruta para que avisara "guardá esto". Son muchas, el
cambio toca todo el servidor a la vez y basta olvidarse de un lugar para que
un dato se pierda en silencio, que es la peor forma de fallar: la pantalla
dice que guardó.

Cómo se resuelve
----------------
**Por diferencia.** Al arrancar se trae todo de Firestore a memoria y se toma
una huella de cada registro. Después de cada petición se vuelve a mirar y se
escribe únicamente lo que cambió: lo nuevo, lo modificado y lo que se fue.

Las rutas no se enteran. Siguen trabajando contra las mismas listas, con la
misma velocidad de siempre, y la base queda al día sin que ninguna tenga que
acordarse de guardar. Un módulo nuevo queda persistido por el solo hecho de
usar `datos.py`.

El costo es recorrer las colecciones una vez por petición. Para un campus
—miles de registros, no millones— son unos milisegundos, y a cambio no hay
ningún camino por el que un dato se escriba en memoria y no llegue a la base.

Cuándo está apagado
-------------------
- Si no hay clave de servicio (`firebase-key.json`).
- Si `FIRESTORE_ACTIVO=no`.
- **En las pruebas**: cargan su propio escenario en memoria y nunca llaman a
  `iniciar()`, así que `_activo` queda en falso y no se escribe nada. Eso es
  a propósito: una prueba no tiene por qué tocar la base de la facultad.
"""

from __future__ import annotations

import json
import os
from datetime import timedelta
from typing import Any, Callable

from .. import datos as d
from . import firestore as fs

# ===================== Qué se guarda y cómo =====================
# Cada colección de Firestore se corresponde con una lista de `datos.py`.
#
# `clave` dice cómo se llama cada documento. Casi todas las listas tienen
# `id` propio y se usa ese. Cinco no lo tienen —son relaciones, no entidades—
# y se arma una clave natural con los campos que las identifican: así el
# mismo registro cae siempre en el mismo documento y no se duplica al
# reescribirlo.
def _por_id(x: dict) -> str:
    return str(x["id"])


def _campos(*nombres: str) -> Callable[[dict], str]:
    def clave(x: dict) -> str:
        return "_".join(str(x.get(n)) for n in nombres)

    return clave


REGISTROS: dict[str, tuple[str, Callable[[dict], str]]] = {
    # Firestore              atributo de datos.py        clave del documento
    "personas": ("personas", _por_id),
    "cursos": ("cursos", _por_id),
    "tareas": ("tareas", _por_id),
    "conversaciones": ("conversaciones", _por_id),
    "publicaciones": ("publicaciones", _por_id),
    "eventos": ("eventos", _por_id),
    "temasForo": ("temas_foro", _por_id),
    "materiales": ("materiales", _por_id),
    "categorias": ("categorias", _por_id),
    "favoritosBiblioteca": ("favoritos_biblioteca", _por_id),
    "moderacionBiblioteca": ("moderacion_biblioteca", _por_id),
    "materiasPlan": ("materias_plan", _por_id),
    "mesasExamen": ("mesas_examen", _por_id),
    "inscripcionesFinales": ("inscripciones_finales", _por_id),
    "resultadosFinales": ("resultados_finales", _por_id),
    "inscripcionesMaterias": ("inscripciones_materias", _por_id),
    "calificaciones": ("calificaciones", _por_id),
    "entregas": ("entregas", _por_id),
    "respuestasCuestionario": ("respuestas_cuestionario", _por_id),
    "carreras": ("carreras_institucion", _por_id),
    "sedes": ("sedes", _por_id),
    "planesEstudio": ("planes_estudio", _por_id),
    "comisiones": ("comisiones", _por_id),
    "dictados": ("dictados", _por_id),
    "asociacionesAcademicas": ("asociaciones_academicas", _por_id),
    "auditoria": ("auditoria", _por_id),
    "clasesAsistencia": ("clases_asistencia", _por_id),
    "asistencias": ("asistencias", _por_id),
    "justificaciones": ("justificaciones", _por_id),
    "historialAsistencia": ("historial_asistencia", _por_id),
    "cierresCursada": ("cierres_cursada", _campos("cursoId", "personaId")),
    # Las fichas de los archivos que viven en Cloudflare R2. El binario no
    # entra nunca acá: solo dónde está y de quién es.
    "archivos": ("archivos_subidos", lambda x: str(x["objectKey"]).replace("/", "__")),
    # Las cinco sin `id` propio: su clave sale de lo que las identifica
    "clases": ("clases", _campos("cursoId", "dia", "desde")),
    "historialAcademico": ("historial_academico", _campos("personaId", "materiaId")),
    "favoritosModulo": ("favoritos_modulo", _campos("personaId", "cursoId")),
    "progresoAlumnos": ("progreso_alumnos", _campos("personaId", "cursoId", "itemId")),
    "planificacionAsistencia": ("planificacion_asistencia", _campos("cursoId")),
}

# ===================== Las que solo crecen =====================
# La auditoría **solo se agrega**: no hay forma de editar ni de borrar un
# evento, ni en el servicio ni en las rutas, y eso es una garantía del
# apartado, no una casualidad.
#
# Comparar huella por huella tiene sentido donde los registros se mutan en el
# lugar, que es el motivo de todo el guardado por diferencia. Acá no pasa, y
# el precio era alto: cada petición —también las de solo lectura— serializaba
# el registro **entero** para descubrir que no había cambiado nada. Con el
# registro creciendo todos los días, el costo de cualquier consulta del campus
# subía con él.
#
# Para estas colecciones se lleva en cambio la lista de lo ya escrito y se
# guarda únicamente lo nuevo. Si alguna vez se editara un evento, ese cambio
# no se guardaría: es exactamente la propiedad que el apartado promete.
SOLO_AGREGAR: frozenset[str] = frozenset({"auditoria"})

# Lo que ya está en Firestore, por colección. No se actualiza si la escritura
# falla: en la próxima petición se vuelve a intentar.
_ya_escritos: dict[str, set[str]] = {}

# ===================== Lo viejo del registro =====================
# El registro de auditoría no se borra nunca —esa es su gracia—, pero tampoco
# hace falta tenerlo entero en memoria: nadie filtra la actividad de hace tres
# años desde la pantalla. Con un número de meses acá, al arrancar se cargan
# solo los últimos y el resto **se queda en Firestore**, entero.
#
# Viene apagado (0 = todo). Prenderlo es una decisión: a partir de ahí la
# pantalla muestra menos de lo que hay, así que avisa desde cuándo tiene datos
# —un registro recortado que no dice que lo está se lee como el registro
# completo, que es la peor forma de equivocarse acá—.
MESES_EN_MEMORIA = int(os.environ.get("AUDITORIA_MESES_EN_MEMORIA") or 0)

# Desde cuándo hay registro en memoria, para que la pantalla lo pueda decir.
_auditoria_desde: str | None = None


def auditoria_desde() -> str | None:
    """La fecha del evento más viejo que quedó cargado, si se recortó."""
    return _auditoria_desde


# Los diccionarios indexados por módulo: `{12: [...], 13: [...]}`. Cada
# módulo es un documento con su lista adentro.
POR_CURSO: dict[str, str] = {
    "contenidos": "contenidos",
    "anuncios": "anuncios",
    "participantes": "participantes",
}

# Las listas cerradas de vocabulario y la configuración general. No son
# datos de la facultad sino cómo se llama cada cosa, así que van todas
# juntas en `configuracion`, un documento cada una.
CONFIGURACION: tuple[str, ...] = (
    "ROLES",
    "TIPOS_MATERIAL",
    "ESTADOS_MATERIAL",
    "MODALIDADES_MATERIA",
    "CONDICIONES_CORRELATIVA",
    "MODOS_CORRELATIVA",
    "CONDICIONES_CURSADA",
    "CONDICIONES_FINAL",
    "MODALIDADES_FINAL",
    "LLAMADOS",
    "INSTANCIAS_FINAL",
    "MODALIDADES_TRABAJO",
    "FORMATOS_TRABAJO",
    "ESTADOS_CUENTA",
    "ESTADOS_ASOCIACION",
    "ESTADOS_CALIFICACION",
    "ESTADOS_ASISTENCIA",
    "ESTADOS_JUSTIFICACION",
    "TURNOS",
    "CONFIG_ASISTENCIA",
    "periodo_inscripcion_materias",
    "carreras",  # los nombres de carrera que usa la Biblioteca para filtrar
)

CONFIGURACION_COL = "configuracion"
CONTADORES = "contadores"

# ===================== Estado =====================
_activo = False
_huellas: dict[tuple[str, str], str] = {}


def activo() -> bool:
    return _activo


def _encendido() -> bool:
    """Si hay que usar Firestore. Apagarlo es una variable, no tocar código."""
    if (os.environ.get("FIRESTORE_ACTIVO") or "si").strip().lower() in ("no", "0", "false"):
        return False
    try:
        fs.obtener_firestore()
        return True
    except RuntimeError:
        return False


# ===================== Huellas =====================
def _huella(valor: Any) -> str:
    """Una firma del contenido, para saber si cambió sin guardar una copia."""
    return json.dumps(valor, sort_keys=True, default=str, ensure_ascii=False)


def _documentos() -> dict[tuple[str, str], Any]:
    """Todo lo que hay en memoria, como pares (colección, documento) → valor."""
    salida: dict[tuple[str, str], Any] = {}

    for coleccion, (atributo, clave) in REGISTROS.items():
        if coleccion in SOLO_AGREGAR:
            continue  # se guardan aparte: ver SOLO_AGREGAR
        for item in getattr(d, atributo):
            try:
                salida[(coleccion, clave(item))] = item
            except (KeyError, TypeError):
                # Un registro sin su clave natural no se puede guardar solo.
                # No se descarta en silencio: se avisa y se sigue.
                print(f"[persistencia] {coleccion}: registro sin clave, no se guarda")

    for coleccion, atributo in POR_CURSO.items():
        for curso_id, lista in getattr(d, atributo).items():
            salida[(coleccion, str(curso_id))] = {"items": lista}

    for nombre in CONFIGURACION:
        valor = getattr(d, nombre, None)
        if valor is None:
            continue
        salida[(CONFIGURACION_COL, nombre)] = valor if isinstance(valor, dict) else {"valores": valor}

    salida[(CONFIGURACION_COL, CONTADORES)] = dict(d._proximos)
    return salida


# ===================== Traer =====================
def base_iniciada() -> bool:
    """Si esta base ya fue usada por el campus.

    Se mira el documento de contadores, que lo escribe la siembra y existe
    desde entonces. Hace falta preguntarlo **antes** de cargar: cargar vacía
    la memoria para dejarla igual que la base, y si la base todavía no tenía
    nada eso borraría lo que había para sembrar. Es lo que pasó la primera
    vez: se subió el vocabulario y ninguna persona.
    """
    documento = (
        fs.obtener_firestore()
        .collection(CONFIGURACION_COL)
        .document(CONTADORES)
        .get()
    )
    return documento.exists


def cargar() -> None:
    """Trae el campus de Firestore a memoria.

    Se reemplaza **el contenido** de cada lista, no la variable: los módulos
    hicieron `from .. import datos as d` y guardaron la referencia, así que
    asignarle otra lista a `d.personas` no los alcanzaría.
    """
    cliente = fs.obtener_firestore()

    global _auditoria_desde
    _auditoria_desde = None

    for coleccion, (atributo, _clave) in REGISTROS.items():
        documentos = [doc.to_dict() for doc in cliente.collection(coleccion).stream()]
        destino = getattr(d, atributo)
        destino[:] = _ordenar(documentos)

    if MESES_EN_MEMORIA > 0 and d.auditoria:
        corte = d.ahora() - timedelta(days=30 * MESES_EN_MEMORIA)
        recientes = [
            e for e in d.auditoria if e.get("cuando") and d.desde_iso(e["cuando"]) >= corte
        ]
        if len(recientes) != len(d.auditoria):
            print(
                f"[datos] Auditoría: {len(d.auditoria) - len(recientes)} eventos de más de "
                f"{MESES_EN_MEMORIA} meses quedan archivados en Firestore."
            )
            d.auditoria[:] = recientes
        _auditoria_desde = d.iso(corte)

    for coleccion, atributo in POR_CURSO.items():
        destino = getattr(d, atributo)
        destino.clear()
        for doc in cliente.collection(coleccion).stream():
            destino[int(doc.id)] = (doc.to_dict() or {}).get("items") or []

    for doc in cliente.collection(CONFIGURACION_COL).stream():
        contenido = doc.to_dict() or {}
        if doc.id == CONTADORES:
            d._proximos.update({k: int(v) for k, v in contenido.items()})
            continue
        actual = getattr(d, doc.id, None)
        if isinstance(actual, list):
            actual[:] = contenido.get("valores") or []
        elif isinstance(actual, dict):
            actual.clear()
            actual.update(contenido)

    _ajustar_contadores()


def _ordenar(documentos: list[dict]) -> list[dict]:
    """Por id cuando lo hay. Firestore devuelve por nombre de documento, que
    es texto: sin esto "10" vendría antes que "9" y las pantallas que no
    ordenan mostrarían el campus desprolijo."""
    if documentos and all(isinstance(x.get("id"), int) for x in documentos):
        return sorted(documentos, key=lambda x: x["id"])
    return documentos


# Qué contador alimenta cada colección. Sin esto, al reiniciar el servidor
# los contadores volverían a 100 y el próximo registro pisaría uno que ya
# existe: el error más caro de todos, porque borra datos buenos.
_CONTADOR_DE = {
    "materiasPlan": "materia",
    "carreras": "carrera",
    "sedes": "sede",
    "planesEstudio": "plan",
    "comisiones": "comision",
    "dictados": "dictado",
    "asociacionesAcademicas": "asociacion",
    "auditoria": "auditoria",
    "publicaciones": "publicacion",
    "temasForo": "tema",
    "materiales": "material",
    "moderacionBiblioteca": "moderacion",
    "conversaciones": "conversacion",
    "inscripcionesMaterias": "inscripcionMateria",
    "inscripcionesFinales": "inscripcionFinal",
    "mesasExamen": "mesa",
    "resultadosFinales": "resultadoFinal",
    "calificaciones": "calificacion",
    "entregas": "entrega",
    "respuestasCuestionario": "respuesta",
    "clasesAsistencia": "clase",
    "asistencias": "asistencia",
    "justificaciones": "justificacion",
    "historialAsistencia": "historialAsistencia",
    "tareas": "tarea",
    "eventos": "evento",
}


def _ajustar_contadores() -> None:
    """Cada contador arranca después del id más alto que ya existe."""
    for coleccion, contador in _CONTADOR_DE.items():
        if contador not in d._proximos:
            continue
        atributo = REGISTROS[coleccion][0]
        ids = [x["id"] for x in getattr(d, atributo) if isinstance(x.get("id"), int)]
        if ids:
            d._proximos[contador] = max(d._proximos[contador], max(ids) + 1)


# ===================== Escribir =====================
LOTE = 400  # Firestore acepta 500 operaciones por lote; se deja margen


def _escribir(cambios: list[tuple[str, str, Any]], bajas: list[tuple[str, str]]) -> None:
    cliente = fs.obtener_firestore()
    pendientes: list[Callable] = []

    for coleccion, documento, valor in cambios:
        ref = cliente.collection(coleccion).document(documento)
        pendientes.append(lambda lote, r=ref, v=valor: lote.set(r, v))
    for coleccion, documento in bajas:
        ref = cliente.collection(coleccion).document(documento)
        pendientes.append(lambda lote, r=ref: lote.delete(r))

    for desde in range(0, len(pendientes), LOTE):
        lote = cliente.batch()
        for operacion in pendientes[desde : desde + LOTE]:
            operacion(lote)
        lote.commit()


def _lo_nuevo_que_solo_crece() -> list[tuple[str, str, Any]]:
    """Los registros de las colecciones de solo agregar que todavía no están.

    No devuelve bajas: un evento que desapareciera de la memoria no se borra
    de la base. Es lo correcto para un registro que no se puede alterar, y lo
    que permite dejar en memoria solo lo reciente sin perder el historial.
    """
    nuevos: list[tuple[str, str, Any]] = []
    for coleccion in SOLO_AGREGAR:
        atributo, clave = REGISTROS[coleccion]
        escritos = _ya_escritos.setdefault(coleccion, set())
        for item in getattr(d, atributo):
            try:
                id_doc = clave(item)
            except (KeyError, TypeError):
                print(f"[persistencia] {coleccion}: registro sin clave, no se guarda")
                continue
            if id_doc not in escritos:
                nuevos.append((coleccion, id_doc, _para_firestore(item)))
    return nuevos


def guardar_cambios() -> int:
    """Escribe lo que cambió desde la última vez. Devuelve cuántos documentos.

    Si Firestore falla, **se avisa y no se actualizan las huellas**: en la
    próxima petición se vuelve a intentar el mismo cambio. Dar por guardado
    algo que no se guardó es justamente lo que no puede pasar.
    """
    if not _activo:
        return 0

    global _huellas
    actuales = _documentos()
    nuevas: dict[tuple[str, str], str] = {}
    cambios: list[tuple[str, str, Any]] = []

    for clave, valor in actuales.items():
        huella = _huella(valor)
        nuevas[clave] = huella
        if _huellas.get(clave) != huella:
            cambios.append((clave[0], clave[1], _para_firestore(valor)))

    bajas = [clave for clave in _huellas if clave not in actuales]

    # Las que solo crecen no se comparan: se escribe lo que todavía no está
    agregados = _lo_nuevo_que_solo_crece()
    cambios.extend(agregados)

    if not cambios and not bajas:
        return 0

    try:
        _escribir(cambios, bajas)
    except Exception as error:  # noqa: BLE001 - se informa y se reintenta después
        print(f"[persistencia] no se pudo guardar en Firestore: {error}")
        return 0

    _huellas = nuevas
    for coleccion, id_doc, _valor in agregados:
        _ya_escritos.setdefault(coleccion, set()).add(id_doc)
    return len(cambios) + len(bajas)


def _para_firestore(valor: Any) -> dict:
    """Firestore guarda documentos, no listas sueltas ni claves numéricas."""
    if not isinstance(valor, dict):
        return {"valores": valor}
    return {str(k): v for k, v in valor.items()}


# ===================== Arranque =====================
def iniciar() -> str:
    """Conecta el campus con Firestore. Devuelve qué hizo, para el registro.

    Tres caminos:
    - **Hay datos**: se cargan y la memoria queda igual a la base.
    - **Está vacía**: se siembra lo mínimo —los roles y el vocabulario— y se
      sube lo que haya en memoria. Las colecciones de la facultad quedan
      vacías a propósito: carreras, materias y sedes se cargan desde el panel
      de administración, no se inventan acá.
    - **No está disponible**: se sigue en memoria, como hasta ahora, y se
      avisa. El campus funciona igual pero no guarda nada.
    """
    global _activo, _huellas

    _ya_escritos.clear()

    if not _encendido():
        _activo = False
        return "Firestore apagado: el campus trabaja solo en memoria."

    try:
        iniciada = base_iniciada()
        if iniciada:
            cargar()
    except Exception as error:  # noqa: BLE001
        _activo = False
        return f"Firestore no respondió ({error}). El campus trabaja solo en memoria."

    _activo = True

    if iniciada:
        _huellas = {clave: _huella(valor) for clave, valor in _documentos().items()}
        # Lo que se acaba de traer ya está en la base: no hay que reescribirlo
        for coleccion in SOLO_AGREGAR:
            atributo, clave = REGISTROS[coleccion]
            _ya_escritos[coleccion] = {
                clave(x) for x in getattr(d, atributo) if isinstance(x, dict) and x.get("id")
            }
        guardados = len(_huellas) + sum(len(v) for v in _ya_escritos.values())
        return f"Campus cargado desde Firestore: {guardados} documentos."

    # Base vacía: se siembra lo mínimo y nada más.
    _huellas = {}
    vaciar_lo_institucional()
    escritos = guardar_cambios()
    return (
        f"Firestore estaba vacío: se sembró la estructura inicial ({escritos} documentos). "
        "Las colecciones de la facultad quedan vacías: se cargan desde Administración, "
        "o con «python -m app.importar_estructura» si querés subir las de prueba."
    )


# Lo que define la facultad y **no se inventa acá**: carreras, sedes, planes,
# comisiones, materias y quién dicta qué. Se cargan desde Administración.
#
# `datos_iniciales.json` trae un juego de ejemplo para poder desarrollar sin
# cargar nada a mano. Sirve en memoria, pero subirlo a la base lo convertiría
# en el plan de estudios de la facultad, que es justo lo que no tiene que
# pasar: nadie sabría después qué materias son de verdad.
INSTITUCIONALES = (
    "carreras_institucion",
    "sedes",
    "planes_estudio",
    "comisiones",
    "materias_plan",
    "dictados",
)


def vaciar_lo_institucional() -> None:
    for atributo in INSTITUCIONALES:
        getattr(d, atributo).clear()
