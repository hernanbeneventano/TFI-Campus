// Funciones para comunicarse con el backend.
// Mientras se desarrolla, Vite redirige /api a http://localhost:3000 (ver
// vite.config.js). En un despliegue estático la dirección del servidor la
// fija VITE_API_URL al construir (ver services/destino.js).

import { obtenerToken } from './sesion.js';
import { api } from './destino.js';

// Cada consulta lleva el token de identidad de Firebase. El servidor lo
// verifica y de ahí saca quién pregunta: nunca se le manda el rol desde acá,
// porque cualquiera podría cambiarlo en el navegador.
//
// Si no hay sesión el token es null y la cabecera no se agrega. Hoy el
// servidor responde igual, como el usuario de prueba; cuando el login sea
// obligatorio devolverá 401.
async function cabeceras(extra = {}) {
  const token = await obtenerToken().catch(() => null);
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

// Cuando algo sale mal, el backend manda { error: "..." } con el motivo en
// castellano. Vale más mostrar eso que un "Error 403" pelado.
async function responderOFallar(respuesta, queHacia) {
  if (respuesta.ok) return respuesta.json();

  let delServidor = null;
  try {
    delServidor = (await respuesta.json())?.error ?? null;
  } catch {
    // Una respuesta sin JSON (un 500 crudo, por ejemplo)
  }
  throw new Error(delServidor ?? `Error ${respuesta.status} al ${queHacia}`);
}

async function pedir(ruta) {
  return responderOFallar(
    await fetch(api(ruta), { headers: await cabeceras() }),
    `pedir ${ruta}`
  );
}

async function bajarArchivo(ruta, nombre) {
  const respuesta = await fetch(api(ruta), { headers: await cabeceras() });
  if (!respuesta.ok) {
    await responderOFallar(respuesta, `descargar ${ruta}`);
  }

  const direccion = URL.createObjectURL(await respuesta.blob());
  const enlace = document.createElement('a');
  enlace.href = direccion;
  enlace.download = nombre || 'archivo';
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  window.setTimeout(() => URL.revokeObjectURL(direccion), 60000);
}

// Las tres que mandan cuerpo JSON se diferencian solo en el método
function conCuerpo(metodo, queHacia) {
  return async (ruta, cuerpo) => {
    const respuesta = await fetch(api(ruta), {
      method: metodo,
      headers: await cabeceras({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(cuerpo),
    });
    return responderOFallar(respuesta, `${queHacia} ${ruta}`);
  };
}

const enviar = conCuerpo('POST', 'enviar a');
const actualizar = conCuerpo('PUT', 'actualizar');
const parchear = conCuerpo('PATCH', 'modificar');

async function borrar(ruta, cuerpo) {
  // Algunas bajas llevan cuerpo: retirar la publicación de otra persona exige
  // el motivo, y ese motivo viaja con el DELETE.
  return responderOFallar(
    await fetch(api(ruta), {
      method: 'DELETE',
      headers: await cabeceras(cuerpo ? { 'Content-Type': 'application/json' } : {}),
      ...(cuerpo ? { body: JSON.stringify(cuerpo) } : {}),
    }),
    `borrar ${ruta}`
  );
}

export const obtenerUsuarioActual = () => pedir('/me');
export const obtenerCursos = () => pedir('/cursos');

// Al cambiar un favorito se avisa: el menú lateral tiene su propia copia de
// los módulos y la pidió una sola vez, al arrancar.
export const marcarFavorito = (id) =>
  enviar(`/cursos/${id}/favorito`, {}).then((curso) => {
    window.dispatchEvent(new CustomEvent('campustfi:cursos'));
    return curso;
  });
export const obtenerModulo = (id) => pedir(`/cursos/${id}/modulo`);

// --- Administración del módulo (solo el docente a cargo) ---
// Las que tocan el contenido devuelven las carpetas enteras, no solo lo que
// cambió: agregar un trabajo toca las carpetas y la lista de tareas a la vez.
export const crearSeccion = (idCurso, datos) => enviar(`/cursos/${idCurso}/carpetas`, datos);
export const editarSeccion = (idCurso, idSeccion, datos) =>
  parchear(`/cursos/${idCurso}/carpetas/${idSeccion}`, datos);
export const borrarSeccion = (idCurso, idSeccion) =>
  borrar(`/cursos/${idCurso}/carpetas/${idSeccion}`);
// `hacia` mueve un lugar (teclado); `posicion` lleva a un lugar concreto,
// que es lo que manda el arrastre con el mouse.
export const moverSeccion = (idCurso, idSeccion, destino) =>
  enviar(`/cursos/${idCurso}/carpetas/${idSeccion}/mover`, destino);

export const crearElemento = (idCurso, idSeccion, datos) =>
  enviar(`/cursos/${idCurso}/carpetas/${idSeccion}/items`, datos);
export const editarElemento = (idCurso, idSeccion, idItem, datos) =>
  parchear(`/cursos/${idCurso}/carpetas/${idSeccion}/items/${idItem}`, datos);
export const borrarElemento = (idCurso, idSeccion, idItem) =>
  borrar(`/cursos/${idCurso}/carpetas/${idSeccion}/items/${idItem}`);
export const moverElemento = (idCurso, idSeccion, idItem, destino) =>
  enviar(`/cursos/${idCurso}/carpetas/${idSeccion}/items/${idItem}/mover`, destino);

// `abierta` manda sobre la fecha límite; con null vuelve a mandar la fecha
export const cambiarEntrega = (idCurso, idTarea, abierta) =>
  enviar(`/cursos/${idCurso}/tareas/${idTarea}/entrega`, { abierta });

export const publicarAnuncio = (idCurso, datos) => enviar(`/cursos/${idCurso}/anuncios`, datos);
export const editarAnuncio = (idCurso, idAnuncio, datos) =>
  parchear(`/cursos/${idCurso}/anuncios/${idAnuncio}`, datos);
export const borrarAnuncio = (idCurso, idAnuncio) =>
  borrar(`/cursos/${idCurso}/anuncios/${idAnuncio}`);

export const obtenerSeguimiento = (idCurso) => pedir(`/cursos/${idCurso}/seguimiento`);
export const obtenerEntregasDeSeccion = (idCurso, idSeccion) =>
  pedir(`/cursos/${idCurso}/carpetas/${idSeccion}/entregas`);
// Las entregas de **un** trabajo, para verlas al abrirlo: la planilla de la
// sección las tiene, pero hay que ir a buscarla.
// Publicar en el tablero de consultas de un módulo. Escribe cualquiera del
// módulo: el tablero es donde se pregunta.
export const publicarEnTablero = (idCurso, idItem, columna, texto) =>
  enviar(`/cursos/${idCurso}/tableros/${idItem}/publicaciones`, { columna, texto });
export const obtenerEntregasDeTarea = (idCurso, idTarea) =>
  pedir(`/cursos/${idCurso}/tareas/${idTarea}/entregas`);
export const obtenerNotas = (idCurso) => pedir(`/cursos/${idCurso}/notas`);
export const guardarNota = (idCurso, datos) => actualizar(`/cursos/${idCurso}/notas`, datos);
// La condición que fija el docente pesa más que el promedio; con
// `condicion: null` vuelve a mandar el cálculo.
export const fijarCierre = (idCurso, datos) => actualizar(`/cursos/${idCurso}/cierre`, datos);
export const obtenerRespuestasCuestionario = (idCurso, idTarea) =>
  pedir(`/cursos/${idCurso}/tareas/${idTarea}/cuestionario`);

// --- Mi cursada (lo que ve cada alumno de lo suyo) ---
// De quién son las notas sale de la sesión: no hay forma de pedir las de
// otro, y el servidor tampoco las daría.
export const obtenerMisNotas = (idCurso) => pedir(`/cursos/${idCurso}/mis-notas`);
export const abrirCuestionario = (idTarea) => pedir(`/tareas/${idTarea}/cuestionario`);
export const responderCuestionario = (idTarea, respuestas) =>
  enviar(`/tareas/${idTarea}/respuestas`, { respuestas });
export const obtenerTareasPendientes = () => pedir('/tareas/pendientes');

// --- Mensajes ---
export const obtenerConversaciones = () => pedir('/mensajes');
export const obtenerConversacion = (id) => pedir(`/mensajes/${id}`);
export const enviarMensaje = (id, texto, adjuntos = []) =>
  enviar(`/mensajes/${id}`, { texto, adjuntos });
export const abrirConversacionCon = (paraId) => enviar('/mensajes', { paraId });

// --- Lo que se puede hacer con un mensaje ---
// Editar y eliminar, solo los propios: en una conversación de a dos, poder
// cambiar lo que dijo el otro convierte el chat en algo que no sirve como
// constancia de nada. Fijar, en cambio, lo puede cualquiera de los dos:
// lo que conviene tener a la vista normalmente lo dijo el docente.
export const editarMensaje = (idConversacion, idMensaje, texto) =>
  parchear(`/mensajes/${idConversacion}/mensajes/${idMensaje}`, { texto });

export const eliminarMensaje = (idConversacion, idMensaje) =>
  borrar(`/mensajes/${idConversacion}/mensajes/${idMensaje}`);

export const fijarMensaje = (idConversacion, idMensaje) =>
  enviar(`/mensajes/${idConversacion}/mensajes/${idMensaje}/fijar`, {});
export const obtenerContactos = () => pedir('/mensajes/contactos');
export const obtenerContadores = () => pedir('/contadores');

// --- Novedades ---
export const obtenerPublicaciones = () => pedir('/novedades');
export const publicarNovedad = (datos) => enviar('/novedades', datos);
export const editarNovedad = (id, datos) => actualizar(`/novedades/${id}`, datos);

// --- Calendario ---
export const obtenerCalendario = (desde, hasta) =>
  pedir(`/calendario?desde=${desde}&hasta=${hasta}`);

// --- Foro ---
export const obtenerForo = () => pedir('/foro');
export const obtenerTema = (id) => pedir(`/foro/${id}`);
export const crearTema = (datos) => enviar('/foro', datos);
export const responderTema = (id, texto) => enviar(`/foro/${id}`, { texto });
export const reaccionar = (id, tipo) => enviar(`/novedades/${id}/reaccion`, { tipo });
export const votarMensaje = (temaId, mensajeId) =>
  enviar(`/foro/${temaId}/mensajes/${mensajeId}/voto`, {});
export const seguirTema = (id) => enviar(`/foro/${id}/seguir`, {});

// --- Finales ---
export const obtenerMesas = () => pedir('/finales/mesas');
export const obtenerProximasMesas = () => pedir('/finales/proximas');
export const obtenerResultadosFinales = () => pedir('/finales/resultados');
export const inscribirseAMesa = (id) => enviar(`/finales/mesas/${id}/inscripcion`, {});
export const cancelarInscripcionMesa = (id) => borrar(`/finales/mesas/${id}/inscripcion`);

// --- Finales: la gestión docente ---
// Cuelga de /finales/gestion porque son los mismos datos vistos con otros
// permisos: el alumno pregunta si puede rendir, la cátedra qué hace con la
// mesa. El servidor decide qué mesas ve cada docente y qué puede hacer con
// ellas: cada mesa trae puedeEditar y puedeCalificar, pero la verificación
// que vale es la de allá.
export const obtenerOpcionesFinales = () => pedir('/finales/gestion/opciones');

export const obtenerMesasGestion = () => pedir('/finales/gestion/mesas');
export const obtenerMesaGestion = (id) => pedir(`/finales/gestion/mesas/${id}`);

export const obtenerInscriptosFinales = (filtros = {}) => {
  const parametros = new URLSearchParams(
    Object.entries(filtros).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  );
  const consulta = parametros.toString();
  return pedir(`/finales/gestion/inscriptos${consulta ? `?${consulta}` : ''}`);
};

export const crearMesa = (datos) => enviar('/finales/gestion/mesas', datos);
export const editarMesa = (id, datos) => actualizar(`/finales/gestion/mesas/${id}`, datos);
export const cancelarMesa = (id, motivo) =>
  enviar(`/finales/gestion/mesas/${id}/cancelar`, { motivo });

export const guardarResultados = (id, resultados) =>
  actualizar(`/finales/gestion/mesas/${id}/resultados`, { resultados });
export const cerrarActa = (id) => enviar(`/finales/gestion/mesas/${id}/cerrar-acta`, {});

// --- Inscripción a materias ---
// Al inscribirse, la materia entra sola a Módulos: el menú lateral tiene su
// propia copia de los módulos, así que hay que avisarle. Es el mismo truco
// que usa `marcarFavorito`.
export const obtenerPlanDeEstudios = () => pedir('/inscripciones/materias');

export const inscribirseAMateria = (id) =>
  enviar(`/inscripciones/materias/${id}`, {}).then((resultado) => {
    window.dispatchEvent(new CustomEvent('campustfi:cursos'));
    return resultado;
  });

export const darDeBajaMateria = (id) =>
  borrar(`/inscripciones/materias/${id}`).then((materia) => {
    window.dispatchEvent(new CustomEvent('campustfi:cursos'));
    return materia;
  });

// --- Perfil, cuentas y estructura institucional ---
// El perfil propio y la administración son rutas distintas a propósito:
// nadie se cambia los roles a sí mismo.
export const obtenerMiPerfil = () => pedir('/usuarios/yo');
export const guardarMiPerfil = (datos) => actualizar('/usuarios/yo', datos);
export const obtenerUsuarios = (filtros = {}) => {
  const p = new URLSearchParams();
  if (filtros.q) p.set('q', filtros.q);
  if (filtros.rol) p.set('rol', filtros.rol);
  const cola = p.toString();
  return pedir(`/usuarios${cola ? `?${cola}` : ''}`);
};
export const crearUsuario = (datos) => enviar('/usuarios', datos);
export const administrarUsuario = (id, datos) => parchear(`/usuarios/${id}`, datos);

// El catálogo lo lee cualquiera; modificarlo es del administrador.
export const obtenerInstitucion = () => pedir('/institucion');
export const crearCarrera = (datos) => enviar('/institucion/carreras', datos);
export const editarCarrera = (id, datos) => parchear(`/institucion/carreras/${id}`, datos);
export const borrarCarrera = (id) => borrar(`/institucion/carreras/${id}`);
export const crearSede = (datos) => enviar('/institucion/sedes', datos);
export const editarSede = (id, datos) => parchear(`/institucion/sedes/${id}`, datos);
export const borrarSede = (id) => borrar(`/institucion/sedes/${id}`);
export const crearPlan = (datos) => enviar('/institucion/planes', datos);
export const editarPlan = (id, datos) => parchear(`/institucion/planes/${id}`, datos);
export const borrarPlan = (id) => borrar(`/institucion/planes/${id}`);
export const crearComision = (datos) => enviar('/institucion/comisiones', datos);
// Las materias de una comisión y quién las dicta
export const obtenerComision = (id) => pedir(`/institucion/comisiones/${id}`);
export const configurarDictado = (idComision, idMateria, datos) =>
  actualizar(`/institucion/comisiones/${idComision}/materias/${idMateria}`, datos);
export const quitarDictado = (idComision, idMateria) =>
  borrar(`/institucion/comisiones/${idComision}/materias/${idMateria}`);
export const editarComision = (id, datos) => parchear(`/institucion/comisiones/${id}`, datos);
export const borrarComision = (id) => borrar(`/institucion/comisiones/${id}`);

// La distribución de estudiantes: del supervisor.
export const obtenerAsignaciones = (filtros = {}) => {
  const p = new URLSearchParams();
  if (filtros.carreraId) p.set('carreraId', filtros.carreraId);
  if (filtros.comisionId) p.set('comisionId', filtros.comisionId);
  if (filtros.sinComision) p.set('sinComision', 'true');
  const cola = p.toString();
  return pedir(`/institucion/asignaciones${cola ? `?${cola}` : ''}`);
};
// El legajo que le tocaría a quien se inscriba a esa carrera. Es para
// mostrarlo en el formulario: el definitivo lo arma el servidor al guardar.
export const legajoSiguiente = (carreraId) =>
  pedir(`/institucion/legajo-siguiente?carreraId=${carreraId}`);
export const crearAsignacion = (datos) => enviar('/institucion/asignaciones', datos);
export const editarAsignacion = (id, datos) =>
  parchear(`/institucion/asignaciones/${id}`, datos);

// --- Asistencias ---
// Del docente: planificar, tomar lista y ver cómo viene el curso.
export const obtenerPlanificacion = (idCurso) =>
  pedir(`/cursos/${idCurso}/asistencias/planificacion`);
export const guardarPlanificacion = (idCurso, clasesPlanificadas) =>
  actualizar(`/cursos/${idCurso}/asistencias/planificacion`, { clasesPlanificadas });
export const obtenerClases = (idCurso) => pedir(`/cursos/${idCurso}/asistencias/clases`);
export const crearClase = (idCurso, datos) =>
  enviar(`/cursos/${idCurso}/asistencias/clases`, datos);
export const obtenerListaDeClase = (idCurso, idClase) =>
  pedir(`/cursos/${idCurso}/asistencias/clases/${idClase}`);
export const guardarLista = (idCurso, idClase, datos) =>
  actualizar(`/cursos/${idCurso}/asistencias/clases/${idClase}`, datos);
export const obtenerAsistenciaDeAlumnos = (idCurso) =>
  pedir(`/cursos/${idCurso}/asistencias/alumnos`);
export const obtenerHistorialAsistencia = (idCurso) =>
  pedir(`/cursos/${idCurso}/asistencias/historial`);

// Del alumno: lo suyo, en una materia o en todas.
export const obtenerMiSituacion = () => pedir('/asistencias/mi-situacion');
export const obtenerMiAsistencia = (idCurso) =>
  pedir(`/cursos/${idCurso}/asistencias/mi-detalle`);

// Justificaciones: el alumno pide, el docente resuelve.
export const obtenerJustificaciones = () => pedir('/asistencias/justificaciones');
export const pedirJustificacion = (datos) => enviar('/asistencias/justificaciones', datos);
export const resolverJustificacion = (id, datos) =>
  actualizar(`/asistencias/justificaciones/${id}`, datos);

// --- Biblioteca ---
// Los ids externos traen dos puntos y barras ("openlibrary:/works/OL1W"), así
// que van codificados o romperían la ruta.
const idEnRuta = (id) => encodeURIComponent(String(id));

export const obtenerOpcionesBiblioteca = () => pedir('/biblioteca/opciones');

export const buscarEnBiblioteca = (filtros) => {
  const parametros = new URLSearchParams();
  for (const [clave, valor] of Object.entries(filtros)) {
    // Una lista vacía quiere decir "sin filtrar", así que no se manda
    if (Array.isArray(valor)) {
      if (valor.length > 0) parametros.set(clave, valor.join(','));
    } else if (valor !== '' && valor != null) {
      parametros.set(clave, valor);
    }
  }
  return pedir(`/biblioteca?${parametros}`);
};

export const obtenerMaterial = (id) => pedir(`/biblioteca/${idEnRuta(id)}`);
export const obtenerMisAportes = () => pedir('/biblioteca/mis-aportes');
export const obtenerPendientesBiblioteca = () => pedir('/biblioteca/pendientes');
export const obtenerFavoritosBiblioteca = () => pedir('/biblioteca/favoritos');

export const aportarMaterial = (datos) => enviar('/biblioteca', datos);
export const editarMaterial = (id, datos) => parchear(`/biblioteca/${idEnRuta(id)}`, datos);
export const retirarMaterial = (id) => borrar(`/biblioteca/${idEnRuta(id)}`);

export const aprobarMaterial = (id) => enviar(`/biblioteca/${idEnRuta(id)}/aprobar`, {});
export const rechazarMaterial = (id, motivo) =>
  enviar(`/biblioteca/${idEnRuta(id)}/rechazar`, { motivo });

export const marcarFavoritoBiblioteca = (id, puesto) =>
  puesto ? enviar(`/biblioteca/${idEnRuta(id)}/favorito`, {}) : borrar(`/biblioteca/${idEnRuta(id)}/favorito`);

export const descargarArchivoBiblioteca = (id, nombre) =>
  bajarArchivo(`/biblioteca/${idEnRuta(id)}/archivo`, nombre);

// El archivo viaja en base64 dentro del JSON. Es lo que se puede hacer sin
// Firebase Storage; cuando esté, sube al bucket y acá queda la referencia.
/**
 * Sube un archivo a la ruta indicada, en base64 dentro del JSON.
 *
 * Es `XMLHttpRequest` y no `fetch` porque es lo único que avisa cómo va la
 * subida, y un PDF de 10 MB sin barra de progreso se siente colgado.
 */
function subirArchivoA(ruta, archivo, alAvanzar, extra = {}) {
  return new Promise((resolve, rechazar) => {
    const lector = new FileReader();
    lector.onerror = () => rechazar(new Error('No se pudo leer el archivo'));
    lector.onload = async () => {
      const peticion = new XMLHttpRequest();
      peticion.open('POST', api(ruta));
      peticion.setRequestHeader('Content-Type', 'application/json');
      const token = await obtenerToken().catch(() => null);
      if (token) peticion.setRequestHeader('Authorization', `Bearer ${token}`);

      peticion.upload.onprogress = (e) => {
        if (e.lengthComputable) alAvanzar?.(Math.round((e.loaded / e.total) * 100));
      };
      peticion.onload = () => {
        let cuerpo = null;
        try {
          cuerpo = JSON.parse(peticion.responseText);
        } catch {
          cuerpo = null;
        }
        if (peticion.status >= 200 && peticion.status < 300) resolve(cuerpo);
        else rechazar(new Error(cuerpo?.error ?? `Error ${peticion.status} al subir el archivo`));
      };
      peticion.onerror = () => rechazar(new Error('No se pudo conectar con el servidor'));

      peticion.send(
        JSON.stringify({
          nombre: archivo.name,
          tipo: archivo.type,
          extension: archivo.name.split('.').pop(),
          // data:application/pdf;base64,XXXX → solo la parte de después de la coma
          contenido: String(lector.result).split(',')[1] ?? '',
          // Lo que viaje junto al archivo: el comentario de una entrega, por
          // ejemplo. Va al final para que nada de acá pise los campos de
          // arriba, que son los que el servidor valida.
          ...extra,
        })
      );
    };
    lector.readAsDataURL(archivo);
  }  );
}

// --- Auditoría ---
// El registro es de solo lectura: no hay función para escribir ni para borrar
// un evento, igual que no hay ruta en el servidor. Los eventos los escribe
// cada módulo del backend al hacer lo suyo.
function parametrosDe(filtros = {}) {
  const parametros = new URLSearchParams();
  for (const [clave, valor] of Object.entries(filtros)) {
    if (valor !== '' && valor != null) parametros.set(clave, valor);
  }
  return parametros;
}

export const obtenerOpcionesAuditoria = () => pedir('/auditoria/opciones');

export const obtenerAuditoria = (filtros) => pedir(`/auditoria?${parametrosDe(filtros)}`);

export const obtenerMovimiento = (id) => pedir(`/auditoria/${id}`);

export const obtenerAuditoriaDeMisMaterias = (filtros) =>
  pedir(`/auditoria/mis-materias?${parametrosDe(filtros)}`);

/** La dirección de descarga, con los filtros puestos: baja lo que se ve. */
export const enlaceExportarAuditoria = (filtros, formato) =>
  api(`/auditoria/exportar?${parametrosDe({ ...filtros, formato })}`);

// --- Panel de control ---
export const obtenerPanel = () => pedir('/panel');
export const obtenerAlertas = () => pedir('/panel/alertas');

// --- Acceso de la cuenta ---
export const obtenerMiAcceso = () => pedir('/usuarios/yo/acceso');
export const cerrarMisSesiones = () => enviar('/usuarios/yo/cerrar-sesiones', {});
export const restablecerContrasena = (id) => enviar(`/usuarios/${id}/contrasena`, {});


// --- Retirar publicaciones ---
// El motivo es obligatorio cuando se retira lo de otra persona; el servidor
// lo vuelve a exigir.
export const retirarNovedad = (id, motivo) => borrar(`/novedades/${id}`, { motivo });

export const retirarTemaForo = (id, motivo) => borrar(`/foro/${id}`, { motivo });

export const retirarRespuestaForo = (idTema, idMensaje, motivo) =>
  borrar(`/foro/${idTema}/mensajes/${idMensaje}`, { motivo });


// --- La configuración académica de la facultad ---
export const obtenerConfiguracionAcademica = () => pedir('/institucion/configuracion');

export const guardarPeriodoInscripcion = (datos) =>
  actualizar('/institucion/configuracion/periodo', datos);

export const guardarConfiguracionAsistencia = (datos) =>
  actualizar('/institucion/configuracion/asistencia', datos);

// --- La imagen de una novedad ---
// Se sube aparte de la novedad porque, al crearla, todavía no hay id al que
// colgar el archivo.
export const subirImagenDeNovedad = (id, archivo, alAvanzar) =>
  subirArchivoA(`/novedades/${id}/imagen`, archivo, alAvanzar);

export const quitarImagenDeNovedad = (id) => borrar(`/novedades/${id}/imagen`);

// --- Los eventos del calendario académico ---
export const obtenerEventos = () => pedir('/institucion/eventos');
export const crearEvento = (datos) => enviar('/institucion/eventos', datos);
export const editarEvento = (id, datos) => actualizar(`/institucion/eventos/${id}`, datos);
export const borrarEvento = (id) => borrar(`/institucion/eventos/${id}`);

// --- Lo que ya vi de un módulo ---
// Las tres devuelven la lista completa, así que la pantalla se queda con lo
// que dice el servidor y no con lo que ella creía: si otra pestaña marcó
// algo, acá aparece.
export const obtenerMiProgreso = () => pedir('/mi-progreso');

export const marcarVisto = (idCurso, idItem) =>
  actualizar(`/cursos/${idCurso}/mi-progreso/${idEnRuta(idItem)}`, {});

export const desmarcarVisto = (idCurso, idItem) =>
  borrar(`/cursos/${idCurso}/mi-progreso/${idEnRuta(idItem)}`);

export const importarMiProgreso = (completados) =>
  enviar('/mi-progreso/importar', { completados });

// --- Entregar un trabajo ---
// Va con `subirArchivoA`, que es lo único que avisa cómo viene la subida: un
// trabajo puede pesar unos megas y una barra quieta parece colgada.
export const obtenerMiEntrega = (idTarea) => pedir(`/tareas/${idTarea}/mi-entrega`);

export const entregarTrabajo = (idTarea, archivo, alAvanzar) =>
  subirArchivoA(`/tareas/${idTarea}/mi-entrega`, archivo, alAvanzar);

export const retirarMiEntrega = (idTarea) => borrar(`/tareas/${idTarea}/mi-entrega`);

// --- La foto de perfil ---
// Va con `subirArchivoA`, igual que el resto: es lo único que avisa cómo
// viene la subida, y una foto del celular puede pesar unos megas.
//
// Al terminar se avisa con `campustfi:perfil`, el mismo truco que el nombre:
// el menú lateral tiene su propia copia del usuario y la pidió una sola vez
// al arrancar. Sin esto, se cambiaba la foto y el menú seguía mostrando la
// anterior hasta recargar la página.
export const subirMiFoto = (archivo, alAvanzar) =>
  subirArchivoA('/usuarios/yo/foto', archivo, alAvanzar).then(avisarPerfil);

export const quitarMiFoto = () => borrar('/usuarios/yo/foto').then(avisarPerfil);

function avisarPerfil(respuesta) {
  window.dispatchEvent(new CustomEvent('campustfi:perfil'));
  return respuesta;
}

export const subirArchivoMaterial = (id, archivo, alAvanzar) =>
  subirArchivoA(`/biblioteca/${idEnRuta(id)}/archivo`, archivo, alAvanzar);

/** El archivo de un elemento de una sección del módulo. */
export const subirArchivoDeElemento = (idCurso, idSeccion, idItem, archivo, alAvanzar) =>
  subirArchivoA(
    `/cursos/${idCurso}/carpetas/${idSeccion}/items/${idEnRuta(idItem)}/archivo`,
    archivo,
    alAvanzar
  );

export const descargarArchivoDeElemento = (idCurso, idSeccion, idItem, nombre) =>
  bajarArchivo(
    `/cursos/${idCurso}/carpetas/${idSeccion}/items/${idEnRuta(idItem)}/archivo`,
    nombre
  );

// --- Días de cursada de un módulo ---
export const agregarDiaDeClase = (idCurso, datos) =>
  enviar(`/cursos/${idCurso}/clases`, datos);

export const quitarDiaDeClase = (idCurso, dia, desde) =>
  borrar(`/cursos/${idCurso}/clases/${dia}/${desde}`);

// --- Materias del plan de estudios ---
export const obtenerMaterias = (filtros = {}) =>
  pedir(`/institucion/materias?${parametrosDe(filtros)}`);

export const crearMateria = (datos) => enviar('/institucion/materias', datos);

export const editarMateria = (id, datos) => parchear(`/institucion/materias/${id}`, datos);

export const borrarMateria = (id) => borrar(`/institucion/materias/${id}`);
