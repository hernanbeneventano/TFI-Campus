/**
 * Lo que comparten las pruebas por HTTP.
 *
 * El `fetch` global se reemplaza para no salir a internet: una prueba que le
 * pega a Google de verdad falla cuando no hay red, cuando Google devuelve 429
 * y cuando alguien cambia su catálogo, y ninguna de las tres cosas es un
 * error nuestro. Lo que se prueba acá es **nuestro** código.
 *
 * Se guarda el `fetch` de verdad para el cliente de las pruebas, que sí tiene
 * que llegar al servidor que levantamos en 127.0.0.1.
 */

import { once } from 'node:events';

export const fetchReal = globalThis.fetch;

function direccionDe(entrada) {
  if (typeof entrada === 'string') return entrada;
  if (entrada instanceof URL) return entrada.href;
  if (entrada && typeof entrada.url === 'string') return entrada.url;
  return String(entrada);
}

/** Respuesta JSON armada a mano, como la daría una interfaz de verdad. */
export function json(cuerpo, estado = 200) {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Cambia el `fetch` global por `manejador`, salvo para lo que vaya a nuestro
 * propio servidor. Devuelve un contador de cuántas veces se salió «a la red»,
 * que es como se comprueba que la caché está trabajando.
 */
export function reemplazarRed(manejador) {
  const llamadas = [];

  globalThis.fetch = async (entrada, opciones) => {
    const direccion = direccionDe(entrada);
    if (direccion.includes('127.0.0.1') || direccion.includes('localhost')) {
      return fetchReal(entrada, opciones);
    }
    llamadas.push(direccion);
    return manejador(new URL(direccion), opciones);
  };

  return {
    llamadas,
    get cuantas() {
      return llamadas.length;
    },
    restaurar() {
      globalThis.fetch = fetchReal;
    },
  };
}

/** Levanta la aplicación en un puerto libre y dice en cuál. */
export async function levantar(aplicacion) {
  const servidor = aplicacion.listen(0, '127.0.0.1');
  await once(servidor, 'listening');
  const { port } = servidor.address();

  return {
    base: `http://127.0.0.1:${port}`,
    cerrar: () => new Promise((listo) => servidor.close(listo)),
  };
}

// ===================== Respuestas de ejemplo =====================
export const VOLUMEN_GOOGLE = {
  id: 'ABC123',
  volumeInfo: {
    title: 'Clean Code',
    authors: ['Robert C. Martin'],
    description: 'Un libro sobre código',
    publishedDate: '2008',
    industryIdentifiers: [{ type: 'ISBN_13', identifier: '9780132350884' }],
    language: 'en',
    infoLink: 'https://books.google.com/ficha',
  },
  accessInfo: { publicDomain: false, viewability: 'PARTIAL' },
};

export const DOC_OPENLIBRARY = {
  key: '/works/OL1W',
  title: 'The Pragmatic Programmer',
  author_name: ['Andrew Hunt'],
  first_publish_year: 1999,
  isbn: ['9780201616224'],
  ebook_access: 'borrowable',
  ia: ['pragmaticprogra00hunt'],
};
