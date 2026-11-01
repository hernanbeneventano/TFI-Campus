// Funciones para comunicarse con el backend.
// Vite redirige /api a http://localhost:3000 (ver vite.config.js).

async function pedir(ruta) {
  const respuesta = await fetch(`/api${ruta}`);
  if (!respuesta.ok) {
    throw new Error(`Error ${respuesta.status} al pedir ${ruta}`);
  }
  return respuesta.json();
}

// POST con cuerpo JSON
async function enviar(ruta, cuerpo) {
  const respuesta = await fetch(`/api${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  });
  if (!respuesta.ok) {
    throw new Error(`Error ${respuesta.status} al enviar a ${ruta}`);
  }
  return respuesta.json();
}

// PUT con cuerpo JSON
async function actualizar(ruta, cuerpo) {
  const respuesta = await fetch(`/api${ruta}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  });
  if (!respuesta.ok) {
    throw new Error(`Error ${respuesta.status} al actualizar ${ruta}`);
  }
  return respuesta.json();
}

export const obtenerUsuarioActual = () => pedir('/me');
export const obtenerCursos = () => pedir('/cursos');
export const obtenerModulo = (id) => pedir(`/cursos/${id}/modulo`);
export const obtenerTareasPendientes = () => pedir('/tareas/pendientes');

// --- Mensajes ---
export const obtenerConversaciones = () => pedir('/mensajes');
export const obtenerConversacion = (id) => pedir(`/mensajes/${id}`);
export const enviarMensaje = (id, texto, adjuntos = []) =>
  enviar(`/mensajes/${id}`, { texto, adjuntos });
export const abrirConversacionCon = (paraId) => enviar('/mensajes', { paraId });
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
