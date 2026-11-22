// Qué material marcó el alumno como visto, y las cuentas de avance.
//
// **Vive en el servidor**, no en el navegador. Antes era `localStorage`, y
// eso tenía dos problemas: el alumno perdía su avance al cambiar de equipo o
// de navegador, y el docente —que mira esto para saber cómo viene el curso—
// veía siempre cero, porque el dato nunca salía de la máquina del alumno.
//
// Lo que queda acá son las cuentas, que son puras: no hablan con nadie.

import { obtenerMiProgreso, importarMiProgreso } from './api.js';

const CLAVE_VIEJA = 'campustfi:completados';

/** Lo marcado, de todos los módulos. */
export async function leerCompletados() {
  const { completados } = await obtenerMiProgreso();
  return completados ?? [];
}

/**
 * Sube una sola vez lo que había quedado guardado en este navegador.
 *
 * Es para no hacerle perder al alumno lo que ya tenía marcado cuando esto
 * vivía en `localStorage`. Se corre al entrar, se borra la clave vieja y no
 * vuelve a pasar: si falla, se deja la clave para reintentarlo la próxima.
 */
export async function migrarProgresoDelNavegador() {
  let viejos;
  try {
    viejos = JSON.parse(localStorage.getItem(CLAVE_VIEJA));
  } catch {
    viejos = null;
  }
  if (!Array.isArray(viejos) || viejos.length === 0) {
    try {
      localStorage.removeItem(CLAVE_VIEJA);
    } catch {
      /* en ventana privada no se puede; tampoco hay nada que migrar */
    }
    return null;
  }

  const { completados } = await importarMiProgreso(viejos);
  try {
    localStorage.removeItem(CLAVE_VIEJA);
  } catch {
    /* si no se puede borrar, la próxima vez se vuelve a subir lo mismo y el
       servidor lo ignora: no duplica */
  }
  return completados;
}

// Las tareas no se marcan a mano: se dan por completadas cuando se entregan.
// La misma regla la aplica el servidor en `datos.es_marcable`.
export function esMarcable(item) {
  return item.tipo !== 'tarea';
}

// Color de la barra según cuánto se avanzó: el verde se reserva para
// cuando falta poco o nada, así no aparece apenas se marca la mitad.
export function nivel(porcentaje) {
  if (porcentaje >= 80) return 'alto';
  if (porcentaje >= 40) return 'medio';
  return 'bajo';
}

// Cuánto se completó de una lista de elementos (una carpeta o todo el módulo)
export function calcularAvance(items, completados) {
  const marcables = items.filter(esMarcable);
  const hechos = marcables.filter((item) => completados.includes(item.id)).length;
  return {
    hechos,
    total: marcables.length,
    porcentaje: marcables.length ? Math.round((hechos / marcables.length) * 100) : 0,
  };
}

// Cuánto falta en el apartado donde vive una tarea pendiente. A diferencia de
// calcularAvance, acá las tareas también cuentan: lo que importa es todo lo
// que al alumno le queda por hacer en esa carpeta.
export function avanceDeApartado(apartado, completados) {
  if (!apartado || apartado.items.length === 0) return null;

  const hechos = apartado.items.filter((item) =>
    item.tipo === 'tarea' ? item.entregada : completados.includes(item.id)
  ).length;

  return {
    hechos,
    total: apartado.items.length,
    porcentaje: Math.round((hechos / apartado.items.length) * 100),
  };
}
