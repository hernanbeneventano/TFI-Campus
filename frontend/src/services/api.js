// Funciones para comunicarse con el backend.
// Vite redirige /api a http://localhost:3000 (ver vite.config.js).

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
  return responderOFallar(await fetch(`/api${ruta}`), `pedir ${ruta}`);
}

// Las tres que mandan cuerpo JSON se diferencian solo en el método
function conCuerpo(metodo, queHacia) {
  return async (ruta, cuerpo) => {
    const respuesta = await fetch(`/api${ruta}`, {
      method: metodo,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cuerpo),
    });
    return responderOFallar(respuesta, `${queHacia} ${ruta}`);
  };
}

const enviar = conCuerpo('POST', 'enviar a');
const actualizar = conCuerpo('PUT', 'actualizar');
const parchear = conCuerpo('PATCH', 'modificar');

async function borrar(ruta) {
  return responderOFallar(await fetch(`/api${ruta}`, { method: 'DELETE' }), `borrar ${ruta}`);
}

export const obtenerUsuarioActual = () => pedir('/me');
// Al guardar el perfil se avisa: el menú lateral tiene el nombre y lo pidió
// una sola vez, al arrancar.
export const guardarPerfil = (datos) =>
  actualizar('/me', datos).then((usuario) => {
    window.dispatchEvent(new CustomEvent('campustfi:perfil'));
    return usuario;
  });
export const obtenerCursos = () => pedir('/cursos');

// Al cambiar un favorito se avisa: el menú lateral tiene su propia copia de
// los módulos y la pidió una sola vez, al arrancar.
export const marcarFavorito = (id) =>
  enviar(`/cursos/${id}/favorito`, {}).then((curso) => {
    window.dispatchEvent(new CustomEvent('campustfi:cursos'));
    return curso;
  });
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
export const votarMensaje = (temaId, mensajeId) =>
  enviar(`/foro/${temaId}/mensajes/${mensajeId}/voto`, {});
export const seguirTema = (id) => enviar(`/foro/${id}/seguir`, {});
