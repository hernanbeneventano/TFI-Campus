/**
 * Cerrar la sesión cuando el servidor se reinicia.
 *
 * El problema: la sesión de Firebase vive en el navegador, así que reiniciar
 * el backend no la toca. Se seguía entrando como quien hubiera quedado
 * logueado la última vez, aunque el campus se hubiera reiniciado entero.
 *
 * Para probar los roles eso estorba —uno quiere arrancar siempre desde el
 * login, y cambiar de cuenta es media jornada de trabajo— y, con el campus en
 * desarrollo, también evita quedar con media pantalla de datos de antes.
 *
 * Cómo: el servidor genera un identificador al arrancar y lo devuelve en
 * `/api/salud`. Acá se compara con el que se vio la última vez; si cambió, se
 * cierra la sesión.
 *
 * **Las cuentas recordadas no se tocan**: viven en otra clave
 * (`cuentasRecordadas.js`) y son justamente lo que hace cómodo volver a
 * entrar. Se olvida la sesión, no quién sos.
 */

import { salir } from './sesion.js';

const CLAVE = 'campustfi:instancia';

function leer() {
  try {
    return localStorage.getItem(CLAVE);
  } catch {
    return null;
  }
}

function guardar(valor) {
  try {
    localStorage.setItem(CLAVE, valor);
  } catch {
    /* en ventana privada no se puede; no es motivo para romper el arranque */
  }
}

/**
 * Devuelve `true` si se cerró la sesión porque el servidor se reinició.
 *
 * Si el servidor no responde no se cierra nada: quedarse sin backend un
 * instante no tiene por qué echar a nadie.
 */
export async function cerrarSiElServidorReinicio() {
  let instancia;
  try {
    const respuesta = await fetch('/api/salud');
    if (!respuesta.ok) return false;
    instancia = (await respuesta.json()).instancia;
  } catch {
    return false;
  }
  if (!instancia) return false;

  const anterior = leer();
  guardar(instancia);

  // La primera vez no hay con qué comparar: no se cierra nada.
  if (!anterior || anterior === instancia) return false;

  try {
    await salir();
  } catch {
    /* si no había sesión, no hay nada que cerrar */
  }
  return true;
}
