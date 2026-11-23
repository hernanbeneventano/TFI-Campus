/**
 * El arranque del servicio de catálogos.
 *
 * Se levanta aparte del campus, en su propio puerto y en su propio proceso.
 * Eso es posible precisamente porque **no comparte memoria con el campus**:
 * no tiene una copia de los módulos, ni de las personas, ni de los
 * materiales, así que no hay nada que se pueda desincronizar.
 *
 * Por qué queda en 127.0.0.1
 * --------------------------
 * El navegador no le habla nunca: le habla al campus, y el campus le habla a
 * este servicio por dentro de la máquina. Publicarlo al mundo no agregaría
 * nada y daría una puerta para gastar el cupo de Google desde afuera.
 *
 * El apagado
 * ----------
 * Se cierra escuchando y se le da tiempo a las búsquedas que están en vuelo.
 * Si no terminan, se corta: una búsqueda a medias no deja nada inconsistente
 * —no hay nada que guardar—, así que no hay motivo para esperar para siempre.
 */

import { crearAplicacion } from './aplicacion.js';
import { config } from './config.js';

const ESPERA_PARA_APAGAR_MS = 5000;

const aplicacion = crearAplicacion();

const servidor = aplicacion.listen(config.puerto, config.host, () => {
  console.log(`[catalogos] escuchando en http://${config.host}:${config.puerto}`);
  if (!config.googleApiKey) {
    console.warn(
      '[catalogos] sin GOOGLE_BOOKS_API_KEY: Google Books va a devolver 429 muy seguido.\n' +
        '            Open Library sigue funcionando y la pantalla lo avisa.',
    );
  }
  if (!config.claveInterna) {
    console.warn(
      '[catalogos] sin CLAVE_INTERNA: cualquiera que alcance este puerto puede buscar.\n' +
        `            Alcanza porque está en ${config.host}; al publicarlo, definila.`,
    );
  }
});

function apagar(senal) {
  console.log(`[catalogos] ${senal}: cerrando`);
  servidor.close(() => process.exit(0));
  setTimeout(() => {
    console.warn('[catalogos] quedaron búsquedas en vuelo; se corta');
    process.exit(0);
  }, ESPERA_PARA_APAGAR_MS).unref();
}

process.on('SIGTERM', () => apagar('SIGTERM'));
process.on('SIGINT', () => apagar('SIGINT'));
