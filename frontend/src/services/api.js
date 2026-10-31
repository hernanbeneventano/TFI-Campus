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

export const obtenerUsuarioActual = () => pedir('/me');
export const obtenerCursos = () => pedir('/cursos');
export const obtenerModulo = (id) => pedir(`/cursos/${id}/modulo`);
export const obtenerActividad = () => pedir('/actividad');
export const obtenerTareasPendientes = () => pedir('/tareas/pendientes');

// --- Mensajes ---
export const obtenerConversaciones = () => pedir('/mensajes');
export const obtenerConversacion = (id) => pedir(`/mensajes/${id}`);
export const enviarMensaje = (id, texto, adjuntos = []) =>
  enviar(`/mensajes/${id}`, { texto, adjuntos });
export const abrirConversacionCon = (paraId) => enviar('/mensajes', { paraId });
export const obtenerContactos = () => pedir('/mensajes/contactos');
export const obtenerAvisos = () => pedir('/informacion');
export const obtenerNovedades = () => pedir('/novedades');
