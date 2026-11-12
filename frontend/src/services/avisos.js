// Avisos pasajeros: el cartelito de arriba a la derecha que confirma que algo
// salió bien.
//
// Va por evento y no por props porque lo dispara cualquier pantalla y lo
// muestra un solo componente montado en `App.jsx`. Es el mismo mecanismo que
// `campustfi:cursos` y `campustfi:perfil`: sin esto habría que pasar una
// función de aviso por toda la aplicación para que la use una pantalla.

const AVISO = 'campustfi:aviso';

/**
 * Muestra un aviso.
 * @param texto lo que se le dice al usuario, en una línea
 * @param tipo 'exito' | 'error'
 */
export function avisar(texto, tipo = 'exito') {
  window.dispatchEvent(new CustomEvent(AVISO, { detail: { texto, tipo } }));
}

export function alLlegarAviso(escucha) {
  function manejar(e) {
    escucha(e.detail);
  }
  window.addEventListener(AVISO, manejar);
  return () => window.removeEventListener(AVISO, manejar);
}
