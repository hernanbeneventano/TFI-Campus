/**
 * Dónde vive la interfaz de programación.
 *
 * Mientras se desarrolla, Vite redirige `/api` al servidor local (ver
 * `vite.config.js`), así que la dirección relativa alcanza y conviene: el
 * navegador y el servidor comparten origen y no hay intercambio entre
 * orígenes que configurar.
 *
 * En un despliegue estático —GitHub Pages, por ejemplo— no hay quién
 * redirija: el sitio son archivos servidos tal cual, y un `fetch('/api/…')`
 * iría a buscar la ruta al propio GitHub, que contesta 404. Por eso la
 * dirección del servidor se fija **al construir**, con `VITE_API_URL`.
 *
 * Se guarda sin la barra final para que `api('/cursos')` no termine armando
 * una dirección con dos barras seguidas, que algunos servidores no
 * normalizan.
 */
const DESTINO = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '');

/** La dirección completa de una ruta del campus: `api('/cursos')`. */
export const api = (ruta) => `${DESTINO}/api${ruta}`;
