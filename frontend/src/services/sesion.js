// Inicio y cierre de sesión con Firebase Authentication.
//
// El navegador es quien habla con Firebase: recibe un token de identidad y se
// lo manda al servidor en cada consulta. El servidor lo verifica con el kit de
// administrador y de ahí saca quién es la persona. La contraseña nunca pasa
// por nuestro backend.

import {
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  setPersistence,
  browserLocalPersistence,
  browserSessionPersistence,
  sendPasswordResetEmail,
} from 'firebase/auth';
import { auth, hayConfiguracion } from './firebase.js';

export { hayConfiguracion };

// Los códigos de Firebase son en inglés y poco claros para quien los lee. El
// mismo mensaje para usuario inexistente y contraseña incorrecta es a
// propósito: decir cuál de los dos falló le confirmaría a un desconocido que
// ese correo tiene cuenta.
const MENSAJES = {
  'auth/invalid-email': 'Ese correo no tiene un formato válido.',
  'auth/invalid-credential': 'El correo o la contraseña no son correctos.',
  'auth/user-not-found': 'El correo o la contraseña no son correctos.',
  'auth/wrong-password': 'El correo o la contraseña no son correctos.',
  'auth/user-disabled': 'Esta cuenta está deshabilitada. Hablá con la facultad.',
  'auth/too-many-requests':
    'Demasiados intentos seguidos. Esperá unos minutos antes de volver a probar.',
  'auth/network-request-failed': 'No se pudo conectar. Revisá tu conexión a internet.',
  'auth/configuration-not-found':
    'El inicio de sesión todavía no está habilitado en Firebase.',
  'auth/operation-not-allowed':
    'El acceso con correo y contraseña no está habilitado en Firebase.',
};

function explicar(error) {
  return MENSAJES[error?.code] ?? 'No se pudo iniciar sesión. Probá de nuevo en un momento.';
}

/**
 * Entra al campus.
 * @param recordarme si la sesión sobrevive al cerrar el navegador
 */
export async function entrar(correo, contrasena, recordarme = true) {
  if (!hayConfiguracion) {
    throw new Error(
      'Falta la configuración de Firebase. Copiá las claves en frontend/.env.local.'
    );
  }

  try {
    // Con "recordarme" la sesión queda guardada en el equipo; sin eso dura
    // hasta que se cierre la pestaña. Conviene en una computadora compartida,
    // como las del laboratorio.
    await setPersistence(auth, recordarme ? browserLocalPersistence : browserSessionPersistence);
    const credencial = await signInWithEmailAndPassword(auth, correo.trim(), contrasena);
    return credencial.user;
  } catch (error) {
    throw new Error(explicar(error));
  }
}

export async function salir() {
  if (auth) await signOut(auth);
}

export async function recuperarContrasena(correo) {
  if (!hayConfiguracion) {
    throw new Error('Falta la configuración de Firebase.');
  }
  try {
    await sendPasswordResetEmail(auth, correo.trim());
  } catch (error) {
    throw new Error(explicar(error));
  }
}

/**
 * Avisa cada vez que cambia quién está conectado, y una vez al arrancar.
 * Devuelve la función para dejar de escuchar.
 */
export function alCambiarSesion(escucha) {
  if (!hayConfiguracion) {
    // Sin configuración no hay sesión posible: se avisa una vez para que la
    // pantalla deje de esperar.
    escucha(null);
    return () => {};
  }
  return onAuthStateChanged(auth, escucha);
}

/**
 * El token de identidad del usuario conectado, o null.
 * Firebase lo renueva solo cuando está por vencer.
 */
export async function obtenerToken() {
  const usuario = auth?.currentUser;
  if (!usuario) return null;
  return usuario.getIdToken();
}
