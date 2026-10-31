// Recursos que el alumno marcó como completados, y las cuentas de avance.
// Por ahora se guardan en el navegador: cuando haya base de datos y login,
// esto pasa a ser una llamada al backend con el progreso de cada usuario.

const CLAVE = 'campustfi:completados';

export function leerCompletados() {
  try {
    const guardado = JSON.parse(localStorage.getItem(CLAVE));
    return Array.isArray(guardado) ? guardado : [];
  } catch {
    return [];
  }
}

export function guardarCompletados(ids) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(ids));
  } catch {
    // Si el navegador no deja guardar (modo privado), el progreso vive
    // solo mientras la pantalla esté abierta.
  }
}

// Las tareas no se marcan a mano: se dan por completadas cuando se entregan.
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
