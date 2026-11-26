/**
 * La búsqueda: las dos fuentes a la vez, unificadas, y con la caché.
 *
 * Por qué este servicio está en Node y el resto del campus no
 * ---------------------------------------------------------------
 * Todo lo que hace este archivo es esperar a dos servidores ajenos al mismo
 * tiempo y juntar lo que contestan. No tiene estado propio, no toca la base
 * del campus y no decide permisos: eso se queda del lado del campus, que es
 * el único que sabe quién pregunta.
 *
 * Es también la única parte del campus que **se cae por culpa de otro**. Si
 * Google tarda 9 segundos, acá se contesta con lo que trajo Open Library y se
 * avisa; en ningún caso se deja la pantalla vacía ni se arrastra al resto del
 * campus.
 *
 * Que una fuente falle es lo normal, no la excepción: Google sin clave
 * devuelve 429 casi siempre. Por eso el estado de cada fuente viaja en la
 * respuesta (`fuentes`) y la pantalla lo muestra, en vez de tragárselo.
 */

import { config } from './config.js';
import { Cache } from './cache.js';
import { GOOGLE, desdeGoogle, parametrosGoogle } from './google.js';
import { OPENLIBRARY, desdeOpenLibrary, parametrosOpenLibrary } from './openlibrary.js';
import { combinar } from './unificar.js';

const cache = new Cache({ segundos: config.cacheSegundos, maximo: config.cacheMaximo });

export function estadoDeCache() {
  return { entradas: cache.tamano, maximo: config.cacheMaximo, segundos: config.cacheSegundos };
}

export function vaciarCache() {
  cache.vaciar();
}

/** Un mensaje que se pueda leer en la pantalla, no un volcado de la excepción. */
function comoMensaje(error) {
  if (error?.name === 'TimeoutError' || error?.name === 'AbortError') {
    return `no contestó en ${config.esperaMs / 1000} s`;
  }
  return error?.message ?? String(error);
}

async function traer(url, parametros) {
  const direccion = new URL(url);
  for (const [clave, valor] of Object.entries(parametros)) {
    direccion.searchParams.set(clave, valor);
  }

  const respuesta = await fetch(direccion, {
    headers: { 'User-Agent': config.agente, Accept: 'application/json' },
    redirect: 'follow',
    signal: AbortSignal.timeout(config.esperaMs),
  });

  if (!respuesta.ok) {
    throw new Error(`respondió ${respuesta.status} ${respuesta.statusText}`.trim());
  }
  return respuesta.json();
}

function resultadoDeFuente({ fuente, nombre, asentado, normalizar }) {
  if (asentado.status === 'rejected') {
    return {
      libros: [],
      estado: { fuente, nombre, estado: 'error', error: comoMensaje(asentado.reason) },
    };
  }
  const libros = normalizar(asentado.value);
  return { libros, estado: { fuente, nombre, estado: 'ok', cuantos: libros.length } };
}

/**
 * Busca en los dos catálogos a la vez y devuelve los resultados unificados.
 *
 * Si una fuente falla o tarda, se informa en `fuentes` y se devuelve lo de la
 * otra: la pantalla avisa, pero no se queda vacía.
 */
export async function buscarLibros(texto, campo = 'todo', idioma = null) {
  const limpio = (texto ?? '').trim();
  // Con una letra, cualquier búsqueda devuelve el catálogo entero y no sirve
  // de nada. Se corta acá y no se gasta cupo.
  if (limpio.length < 2) {
    return { libros: [], fuentes: [], desdeCache: false };
  }

  const clave = `${limpio.toLowerCase()}|${campo}|${idioma ?? ''}`;
  const guardado = cache.obtener(clave);
  if (guardado) {
    return { ...guardado, desdeCache: true };
  }

  // Las dos en paralelo: una lenta no debe arrastrar a la otra. `allSettled`
  // y no `all` justamente porque se espera que una falle.
  const [google, openlibrary] = await Promise.allSettled([
    traer(GOOGLE, parametrosGoogle(limpio, campo, idioma)),
    traer(OPENLIBRARY, parametrosOpenLibrary(limpio, campo)),
  ]);

  const deGoogle = resultadoDeFuente({
    fuente: 'google',
    nombre: 'Google Books',
    asentado: google,
    normalizar: (datos) => (datos.items ?? []).map(desdeGoogle),
  });

  const deOpenLibrary = resultadoDeFuente({
    fuente: 'openlibrary',
    nombre: 'Open Library',
    asentado: openlibrary,
    normalizar: (datos) => (datos.docs ?? []).map(desdeOpenLibrary),
  });

  const fuentes = [deGoogle.estado, deOpenLibrary.estado];
  const datos = { libros: combinar(deGoogle.libros, deOpenLibrary.libros), fuentes };

  // Un resultado vacío porque las dos fallaron no se cachea: conviene
  // reintentar en el próximo pedido, no quedarse diez minutos sin catálogos.
  if (fuentes.some((f) => f.estado === 'ok')) {
    cache.guardar(clave, datos);
  }

  return { ...datos, desdeCache: false };
}

/** Un libro externo por su id («google:xxx» u «openlibrary:/works/OL1W»). */
export async function obtenerLibro(identificador) {
  const bruto = String(identificador ?? '');
  const corte = bruto.indexOf(':');
  if (corte === -1) return null;

  const fuente = bruto.slice(0, corte);
  const resto = bruto.slice(corte + 1);
  if (!resto) return null;

  if (fuente === 'google') {
    const volumen = await traer(`${GOOGLE}/${encodeURIComponent(resto)}`, {});
    return desdeGoogle(volumen);
  }

  if (fuente === 'openlibrary') {
    // La ficha de una obra no trae los autores resueltos; la búsqueda por
    // clave sí. Por eso se busca en vez de pedir la ficha directo.
    const datos = await traer(OPENLIBRARY, { q: `key:${resto}`, limit: '1' });
    const docs = datos.docs ?? [];
    if (docs.length === 0) return null;

    const libro = desdeOpenLibrary(docs[0]);

    // La descripción vive en otro recurso. Sin ella el libro se muestra
    // igual: no es motivo para fallar.
    try {
      const obra = await traer(`https://openlibrary.org${resto}.json`, {});
      const descripcion = obra.description;
      libro.descripcion =
        typeof descripcion === 'string' ? descripcion : (descripcion?.value ?? null);
    } catch {
      // Se queda sin descripción, que es como lo devuelve la búsqueda.
    }
    return libro;
  }

  return null;
}
