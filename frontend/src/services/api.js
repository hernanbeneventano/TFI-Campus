// Funciones para comunicarse con el backend.
// Vite redirige /api a http://localhost:3000 (ver vite.config.js).

async function pedir(ruta) {
  const respuesta = await fetch(`/api${ruta}`);
  if (!respuesta.ok) {
    throw new Error(`Error ${respuesta.status} al pedir ${ruta}`);
  }
  return respuesta.json();
}

export const obtenerUsuarioActual = () => pedir('/me');
export const obtenerCursos = () => pedir('/cursos');
export const obtenerActividad = () => pedir('/actividad');
export const obtenerTareasPendientes = () => pedir('/tareas/pendientes');
