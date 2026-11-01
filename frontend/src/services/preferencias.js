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

const CLAVE_SUBMENU = 'campustfi:modulos-desplegados';

// Si la lista de módulos del menú lateral queda desplegada
export function leerModulosDesplegados() {
  try {
    return localStorage.getItem(CLAVE_SUBMENU) !== 'no';
  } catch {
    return true;
  }
}

export function guardarModulosDesplegados(abierta) {
  try {
    localStorage.setItem(CLAVE_SUBMENU, abierta ? 'si' : 'no');
  } catch {
    // Sin localStorage arranca desplegada en cada visita.
  }
}

const CLAVE_TIPOS = 'campustfi:tipos-calendario';
const TIPOS_CALENDARIO = ['entrega', 'examen', 'clase', 'evento'];

// Qué tipos de cosas se muestran en el calendario
export function leerTiposCalendario() {
  try {
    const guardado = JSON.parse(localStorage.getItem(CLAVE_TIPOS));
    if (!Array.isArray(guardado)) return TIPOS_CALENDARIO;
    const validos = guardado.filter((t) => TIPOS_CALENDARIO.includes(t));
    return validos.length ? validos : TIPOS_CALENDARIO;
  } catch {
    return TIPOS_CALENDARIO;
  }
}

export function guardarTiposCalendario(tipos) {
  try {
    localStorage.setItem(CLAVE_TIPOS, JSON.stringify(tipos));
  } catch {
    // Sin localStorage se muestran todos en cada visita.
  }
}

const CLAVE_PERIODOS = 'campustfi:periodos-cerrados';

// Qué cuatrimestres están minimizados en la lista de módulos del menú.
// Se guardan los cerrados, así un cuatrimestre nuevo arranca abierto.
export function leerPeriodosCerrados() {
  try {
    const guardado = JSON.parse(localStorage.getItem(CLAVE_PERIODOS));
    return Array.isArray(guardado) ? guardado : [];
  } catch {
    return [];
  }
}

export function guardarPeriodosCerrados(periodos) {
  try {
    localStorage.setItem(CLAVE_PERIODOS, JSON.stringify(periodos));
  } catch {
    // Sin localStorage arrancan todos abiertos en cada visita.
  }
}
