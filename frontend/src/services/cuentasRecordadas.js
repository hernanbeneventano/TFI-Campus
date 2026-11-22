/**
 * Las cuentas con las que ya se entró en este equipo.
 *
 * Para qué: en el campus se cambia de cuenta todo el tiempo mientras se
 * prueba —y en la vida real una secretaría atiende desde la misma
 * computadora—, y escribir el correo institucional entero cada vez es
 * tedioso y se presta a errores de tipeo que parecen "contraseña incorrecta".
 *
 * **Nunca se guarda la contraseña.** Solo el correo, el nombre y la foto, que
 * es lo que hace falta para reconocer la cuenta en una lista; la contraseña
 * se escribe siempre. Es la misma idea que el selector de cuentas de
 * cualquier servicio: recordar *quién*, no *cómo entrar*.
 *
 * Vive en `localStorage` y no en el servidor a propósito: es una comodidad de
 * este equipo. En una máquina compartida se borra desde la X de cada cuenta,
 * y no deja nada en la base.
 */

const CLAVE = 'campustfi:cuentas';
const MAXIMO = 5;

function leerCrudo() {
  try {
    const guardado = JSON.parse(localStorage.getItem(CLAVE) ?? '[]');
    return Array.isArray(guardado) ? guardado : [];
  } catch {
    // Un `localStorage` bloqueado o con basura adentro no puede dejar sin
    // login a nadie: se sigue sin cuentas recordadas.
    return [];
  }
}

function guardar(cuentas) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(cuentas.slice(0, MAXIMO)));
  } catch {
    /* sin espacio o en ventana privada: no es un error que valga contar */
  }
}

export function cuentasRecordadas() {
  return leerCrudo().filter((c) => c && typeof c.correo === 'string');
}

/** Anota la cuenta con la que se acaba de entrar, adelante de las demás. */
export function recordarCuenta({ correo, nombre, foto, rol }) {
  if (!correo) return;
  const limpio = correo.trim().toLowerCase();
  const resto = cuentasRecordadas().filter((c) => c.correo.toLowerCase() !== limpio);
  guardar([{ correo: correo.trim(), nombre, foto, rol }, ...resto]);
}

export function olvidarCuenta(correo) {
  const limpio = String(correo).trim().toLowerCase();
  guardar(cuentasRecordadas().filter((c) => c.correo.toLowerCase() !== limpio));
}
