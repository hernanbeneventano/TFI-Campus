import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

// Las claves viven en `frontend/.env.local`, que está ignorado y no viaja por
// el repositorio. Si falta, Vite deja los valores en `undefined` y Firebase
// falla con un error que no dice nada útil. Conviene detectarlo acá y que la
// pantalla de login pueda explicarlo.
export const hayConfiguracion = Boolean(firebaseConfig.apiKey && firebaseConfig.projectId);

export const app = hayConfiguracion ? initializeApp(firebaseConfig) : null;

export const auth = app ? getAuth(app) : null;
