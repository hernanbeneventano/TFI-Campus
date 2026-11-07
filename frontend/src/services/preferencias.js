// Preferencias de la interfaz que se recuerdan entre visitas.
// Viven en el navegador: no hacen falta en la base de datos.
//
// Al guardar cualquiera se avisa con un evento. Sin eso, cambiar algo desde
// Ajustes no se vería hasta recargar: el menú lateral no se vuelve a montar
// al navegar, así que lee su preferencia una sola vez.

const CAMBIO = 'campustfi:preferencias';

function avisar() {
  window.dispatchEvent(new CustomEvent(CAMBIO));
}

export function alCambiarPreferencias(escucha) {
  window.addEventListener(CAMBIO, escucha);
  return () => window.removeEventListener(CAMBIO, escucha);
}

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
    avisar();
  } catch {
    // Si el navegador no deja guardar, el menú arranca abierto la próxima vez.
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
    avisar();
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
    avisar();
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
    avisar();
  } catch {
    // Sin localStorage arrancan todos abiertos en cada visita.
  }
}
