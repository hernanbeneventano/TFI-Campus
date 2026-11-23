/**
 * Las rutas del servicio.
 *
 * No son rutas del campus: el navegador nunca las llama. Las llama el
 * backend de Python, que ya comprobó quién pregunta y si tiene permiso. Por
 * eso acá no hay token de Firebase, no hay CORS y no hay roles —y no los
 * tiene que haber, porque duplicar la capa de permisos en otro lenguaje es
 * la forma más segura de que las dos digan cosas distintas.
 *
 * Lo único que se comprueba es el secreto compartido, y solo si está
 * configurado: no es autenticación de usuarios, es que nadie más que el
 * campus pueda gastar el cupo de Google.
 *
 * Los errores salen como `{ "detail": "..." }`, el mismo formato que usa el
 * campus, para que el cliente de Python no tenga que traducir nada.
 */

import express from 'express';

import { config } from './config.js';
import { Freno } from './freno.js';
import { buscarLibros, estadoDeCache, obtenerLibro } from './catalogos.js';

const freno = new Freno({ porMinuto: config.frenoPorMinuto });

export function crearRutas() {
  const rutas = express.Router();

  // ===================== El secreto compartido =====================
  rutas.use((peticion, respuesta, seguir) => {
    if (!config.claveInterna) return seguir();
    // Comparación simple a propósito: el secreto no se deriva de un dato del
    // usuario y el servicio está en 127.0.0.1, así que no hay un canal de
    // tiempos que valga la pena cerrar acá.
    if (peticion.get('X-Clave-Interna') === config.claveInterna) return seguir();
    return respuesta.status(401).json({ detail: 'Clave interna incorrecta' });
  });

  // ===================== El freno =====================
  rutas.use((peticion, respuesta, seguir) => {
    // La salud no cuenta: es lo que se consulta para saber si el servicio
    // está vivo, y frenarla haría parecer caído algo que anda bien.
    if (peticion.path === '/salud') return seguir();

    if (freno.permite()) return seguir();
    respuesta.set('Retry-After', String(freno.segundosQueFaltan()));
    return respuesta.status(429).json({ detail: 'Demasiadas búsquedas, probá en un momento' });
  });

  // ===================== Las rutas =====================
  rutas.get('/salud', (_peticion, respuesta) => {
    respuesta.json({
      estado: 'bien',
      servicio: 'catalogos',
      conClaveDeGoogle: Boolean(config.googleApiKey),
      cache: estadoDeCache(),
    });
  });

  rutas.get('/catalogos/buscar', async (peticion, respuesta) => {
    const { texto, campo, idioma } = peticion.query;

    // Un campo desconocido no es un error: se busca en todo, que es lo que
    // hacía el campus antes de que este servicio existiera.
    const resultado = await buscarLibros(
      typeof texto === 'string' ? texto : '',
      typeof campo === 'string' && campo ? campo : 'todo',
      typeof idioma === 'string' && idioma ? idioma : null,
    );
    respuesta.json(resultado);
  });

  rutas.get('/catalogos/libro', async (peticion, respuesta) => {
    const { id } = peticion.query;
    if (typeof id !== 'string' || !id) {
      return respuesta.status(400).json({ detail: 'Falta el id del libro' });
    }

    const libro = await obtenerLibro(id);
    if (!libro) {
      return respuesta.status(404).json({ detail: 'No se encontró ese libro' });
    }
    return respuesta.json({ libro });
  });

  return rutas;
}

/** El 404 de una ruta que no existe, con el formato del campus. */
export function noEncontrada(_peticion, respuesta) {
  respuesta.status(404).json({ detail: 'No se encontró esa dirección' });
}

/**
 * El 500. Lo que sale a la respuesta es un mensaje fijo; el detalle va al
 * registro del servidor. Un error con la traza adentro de la respuesta es lo
 * que cuenta la configuración del servidor a cualquiera que la pida.
 */
export function error500(fallo, _peticion, respuesta, _seguir) {
  console.error('[catalogos] error no esperado:', fallo);
  respuesta.status(500).json({ detail: 'Error en el servicio de catálogos' });
}
