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
  EmailAuthProvider,
  reauthenticateWithCredential,
  updatePassword,
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

/**
 * Cambia la contraseña de quien está conectado.
 *
 * Firebase exige haber iniciado sesión hace poco para aceptar una contraseña
 * nueva, así que primero se vuelve a entrar con la actual. Eso además hace de
 * comprobación: sin la contraseña de ahora no se puede poner otra, y alguien
 * que encuentre la sesión abierta no puede quedarse con la cuenta.
 *
 * La contraseña **no pasa por nuestro servidor** en ningún momento.
 */
export async function cambiarContrasena(actual, nueva) {
  if (!hayConfiguracion || !auth?.currentUser) {
    throw new Error('Hay que iniciar sesión para cambiar la contraseña.');
  }
  if (String(nueva ?? '').length < 6) {
    throw new Error('La contraseña nueva tiene que tener al menos 6 caracteres.');
  }

  const usuario = auth.currentUser;
  try {
    const credencial = EmailAuthProvider.credential(usuario.email, actual);
    await reauthenticateWithCredential(usuario, credencial);
  } catch (error) {
    if (error?.code === 'auth/wrong-password' || error?.code === 'auth/invalid-credential') {
      throw new Error('La contraseña actual no es correcta.');
    }
    throw new Error(explicar(error));
  }

  try {
    await updatePassword(usuario, nueva);
  } catch (error) {
    if (error?.code === 'auth/weak-password') {
      throw new Error('Esa contraseña es demasiado fácil de adivinar.');
    }
    throw new Error(explicar(error));
  }
}
