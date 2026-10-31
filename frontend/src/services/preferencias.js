// Preferencias de la interfaz que se recuerdan entre visitas.
// Viven en el navegador: no hacen falta en la base de datos.

const CLAVE_MENU = 'campustfi:menu-cerrado';

export function leerMenuCerrado() {
  try {
    return localStorage.getItem(CLAVE_MENU) === 'si';
  } catch {
    return false;
  }
}

export function guardarMenuCerrado(cerrado) {
  try {
    localStorage.setItem(CLAVE_MENU, cerrado ? 'si' : 'no');
  } catch {
    // Si el navegador no deja guardar, el menú arranca abierto la próxima vez.
  }
}

const CLAVE_AGRUPAR = 'campustfi:agrupar-por-periodo';

// Módulos separados por cuatrimestre (lo normal) o todos juntos en una grilla.
// El interruptor va a vivir en Ajustes cuando esa pantalla exista.
export function leerAgruparPorPeriodo() {
  try {
    return localStorage.getItem(CLAVE_AGRUPAR) !== 'no';
  } catch {
    return true;
  }
}

export function guardarAgruparPorPeriodo(agrupar) {
  try {
    localStorage.setItem(CLAVE_AGRUPAR, agrupar ? 'si' : 'no');
  } catch {
    // Sin localStorage se usa el valor por defecto en cada visita.
  }
}
