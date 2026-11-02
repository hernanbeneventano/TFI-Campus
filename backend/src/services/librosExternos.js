// Búsqueda de libros en catálogos públicos: Google Books y Open Library.
//
// Va del lado del servidor a propósito. Así la clave de Google (si se usa)
// no viaja al navegador, se puede cachear entre usuarios y, si una fuente se
// cae, la pantalla sigue funcionando con la otra y con la biblioteca propia.
//
// Documentación:
//   https://developers.google.com/books/docs/v1/using
//   https://openlibrary.org/dev/docs/api/search

const GOOGLE = 'https://www.googleapis.com/books/v1/volumes';
const OPENLIBRARY = 'https://openlibrary.org/search.json';

// Las dos APIs son públicas pero piden moderación. El tiempo de espera está
// medido contra Open Library, que ronda los 4 s: si una tarda más, se
// responde con lo que haya llegado de la otra en vez de dejar esperando.
const ESPERA_MS = 9000;
const POR_FUENTE = 20;

// Caché en memoria. Las mismas búsquedas se repiten muchísimo (alguien
// escribe, borra una letra y vuelve a escribir) y las APIs tienen límites.
const CACHE_MS = 10 * 60 * 1000;
const CACHE_MAX = 200;
const cache = new Map();

function deCache(clave) {
  const guardado = cache.get(clave);
  if (!guardado) return null;
  if (Date.now() - guardado.cuando > CACHE_MS) {
    cache.delete(clave);
    return null;
  }
  return guardado.datos;
}

function aCache(clave, datos) {
  // El más viejo primero: un Map recorre en orden de inserción
  if (cache.size >= CACHE_MAX) cache.delete(cache.keys().next().value);
  cache.set(clave, { cuando: Date.now(), datos });
}

async function traerJson(url) {
  const respuesta = await fetch(url, {
    signal: AbortSignal.timeout(ESPERA_MS),
    headers: { 'User-Agent': 'CampusTFI/0.1 (proyecto academico FaCENA-UNNE)' },
  });
  if (!respuesta.ok) {
    throw new Error(`${respuesta.status} ${respuesta.statusText}`);
  }
  return respuesta.json();
}

// La búsqueda se puede acotar por campo. Google y Open Library usan nombres
// distintos para lo mismo, así que cada una arma su consulta.
function consultaGoogle({ texto, campo }) {
  const limpio = texto.trim();
  if (campo === 'titulo') return `intitle:${limpio}`;
  if (campo === 'autor') return `inauthor:${limpio}`;
  if (campo === 'isbn') return `isbn:${limpio.replace(/[^0-9Xx]/g, '')}`;
  if (campo === 'tema') return `subject:${limpio}`;
  return limpio;
}

function urlOpenLibrary({ texto, campo }) {
  const url = new URL(OPENLIBRARY);
  const limpio = texto.trim();
  if (campo === 'titulo') url.searchParams.set('title', limpio);
  else if (campo === 'autor') url.searchParams.set('author', limpio);
  else if (campo === 'isbn') url.searchParams.set('isbn', limpio.replace(/[^0-9Xx]/g, ''));
  else if (campo === 'tema') url.searchParams.set('subject', limpio);
  else url.searchParams.set('q', limpio);

  url.searchParams.set('limit', String(POR_FUENTE));
  // Pedir solo los campos que se usan: la respuesta completa es enorme
  url.searchParams.set(
    'fields',
    'key,title,author_name,first_publish_year,isbn,cover_i,language,subject,publisher,ebook_access,ia'
  );
  return url;
}

// Google Books no exige clave para buscar, pero con una el límite es más
// alto. Si está, se usa; si no, se busca igual.
function urlGoogle(opciones) {
  const url = new URL(GOOGLE);
  url.searchParams.set('q', consultaGoogle(opciones));
  url.searchParams.set('maxResults', String(POR_FUENTE));
  url.searchParams.set('printType', 'books');
  if (opciones.idioma) url.searchParams.set('langRestrict', opciones.idioma);
  if (process.env.GOOGLE_BOOKS_API_KEY) {
    url.searchParams.set('key', process.env.GOOGLE_BOOKS_API_KEY);
  }
  return url;
}

// Google devuelve las portadas en http; el campus va en https y el navegador
// bloquearía la imagen por contenido mixto.
function aHttps(url) {
  return typeof url === 'string' ? url.replace(/^http:\/\//, 'https://') : null;
}

// Los dos catálogos se normalizan a la misma forma que los materiales
// propios, para que la pantalla no tenga que saber de dónde vino cada uno.
function desdeGoogle(volumen) {
  const v = volumen.volumeInfo ?? {};
  const acceso = volumen.accessInfo ?? {};
  const isbn = (v.industryIdentifiers ?? []).find((i) => i.type?.startsWith('ISBN'));

  // Solo lo que la API dice que se puede leer de verdad. Nada de inventar
  // enlaces de descarga: si no es de dominio público, va el enlace a la ficha.
  const leeCompleto = v.viewability === 'ALL_PAGES' || acceso.accessViewStatus === 'FULL_PUBLIC_DOMAIN';
  const pdfPublico = acceso.pdf?.isAvailable && acceso.pdf?.downloadLink && acceso.publicDomain;

  return {
    id: `google:${volumen.id}`,
    fuente: 'google',
    nombreFuente: 'Google Books',
    externo: true,
    titulo: v.title ?? 'Sin título',
    subtitulo: v.subtitle ?? null,
    autor: (v.authors ?? []).join(', ') || null,
    descripcion: v.description ?? null,
    editorial: v.publisher ?? null,
    anioPublicacion: v.publishedDate ? String(v.publishedDate).slice(0, 4) : null,
    isbn: isbn?.identifier ?? null,
    idioma: v.language ?? null,
    categorias: v.categories ?? [],
    portada: aHttps(v.imageLinks?.thumbnail ?? v.imageLinks?.smallThumbnail),
    // Qué se puede hacer realmente con este libro
    enlaceLectura: leeCompleto ? (v.previewLink ?? null) : null,
    enlaceVistaPrevia: acceso.viewability === 'PARTIAL' ? (v.previewLink ?? null) : null,
    enlaceDescarga: pdfPublico ? acceso.pdf.downloadLink : null,
    enlaceFicha: v.infoLink ?? v.canonicalVolumeLink ?? null,
    dominioPublico: Boolean(acceso.publicDomain),
  };
}

function desdeOpenLibrary(doc) {
  const isbn = (doc.isbn ?? [])[0] ?? null;
  // "borrowable" y "public" son los únicos accesos que dan algo real
  const prestable = doc.ebook_access === 'borrowable';
  const libre = doc.ebook_access === 'public';

  return {
    id: `openlibrary:${doc.key}`,
    fuente: 'openlibrary',
    nombreFuente: 'Open Library',
    externo: true,
    titulo: doc.title ?? 'Sin título',
    subtitulo: null,
    autor: (doc.author_name ?? []).join(', ') || null,
    descripcion: null,
    editorial: (doc.publisher ?? [])[0] ?? null,
    anioPublicacion: doc.first_publish_year ? String(doc.first_publish_year) : null,
    isbn,
    idioma: (doc.language ?? [])[0] ?? null,
    categorias: (doc.subject ?? []).slice(0, 6),
    portada: doc.cover_i ? `https://covers.openlibrary.org/b/id/${doc.cover_i}-M.jpg` : null,
    enlaceLectura: libre && doc.ia?.[0] ? `https://archive.org/details/${doc.ia[0]}` : null,
    enlacePrestamo: prestable && doc.ia?.[0] ? `https://archive.org/details/${doc.ia[0]}` : null,
    enlaceVistaPrevia: null,
    enlaceDescarga: null,
    enlaceFicha: `https://openlibrary.org${doc.key}`,
    dominioPublico: libre,
  };
}

// Para detectar el mismo libro en las dos fuentes: el ISBN si lo hay y, si
// no, título y autor sin tildes, signos ni mayúsculas.
function huella(libro) {
  if (libro.isbn) return `isbn:${libro.isbn.replace(/[^0-9Xx]/g, '').toUpperCase()}`;
  const normal = (t) =>
    (t ?? '')
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  return `t:${normal(libro.titulo)}|a:${normal(libro.autor).split(' ').slice(0, 2).join(' ')}`;
}

// Cuando un libro está en las dos, se queda el de Google (trae descripción y
// portada más seguido) pero se completan los huecos con el de Open Library y
// se anotan las dos fuentes.
function unir(preferido, otro) {
  const unido = { ...preferido };
  for (const campo of ['descripcion', 'editorial', 'anioPublicacion', 'isbn', 'idioma', 'portada']) {
    unido[campo] ??= otro[campo];
  }
  unido.enlaceLectura ??= otro.enlaceLectura;
  unido.enlacePrestamo ??= otro.enlacePrestamo;
  unido.tambienEn = otro.nombreFuente;
  unido.enlaceOtraFuente = otro.enlaceFicha;
  return unido;
}

function combinar(deGoogle, deOpenLibrary) {
  const porHuella = new Map();

  for (const libro of deGoogle) porHuella.set(huella(libro), libro);

  for (const libro of deOpenLibrary) {
    const clave = huella(libro);
    const yaEsta = porHuella.get(clave);
    porHuella.set(clave, yaEsta ? unir(yaEsta, libro) : libro);
  }

  return [...porHuella.values()];
}

/**
 * Busca en los dos catálogos a la vez y devuelve los resultados unificados.
 * Si una fuente falla o tarda, se informa en `fuentes` y se devuelve lo de la
 * otra: la pantalla avisa, pero no se queda vacía.
 */
export async function buscarLibrosExternos({ texto, campo = 'todo', idioma = null }) {
  const limpio = (texto ?? '').trim();
  if (limpio.length < 2) {
    return { libros: [], fuentes: [], desdeCache: false };
  }

  const clave = JSON.stringify({ limpio: limpio.toLowerCase(), campo, idioma });
  const guardado = deCache(clave);
  if (guardado) return { ...guardado, desdeCache: true };

  const opciones = { texto: limpio, campo, idioma };

  // Las dos en paralelo: una lenta no debe arrastrar a la otra
  const [google, openlibrary] = await Promise.allSettled([
    traerJson(urlGoogle(opciones)),
    traerJson(urlOpenLibrary(opciones)),
  ]);

  const fuentes = [];

  let librosGoogle = [];
  if (google.status === 'fulfilled') {
    librosGoogle = (google.value.items ?? []).map(desdeGoogle);
    fuentes.push({ fuente: 'google', nombre: 'Google Books', estado: 'ok', cuantos: librosGoogle.length });
  } else {
    fuentes.push({ fuente: 'google', nombre: 'Google Books', estado: 'error', error: String(google.reason?.message ?? google.reason) });
  }

  let librosOpen = [];
  if (openlibrary.status === 'fulfilled') {
    librosOpen = (openlibrary.value.docs ?? []).map(desdeOpenLibrary);
    fuentes.push({ fuente: 'openlibrary', nombre: 'Open Library', estado: 'ok', cuantos: librosOpen.length });
  } else {
    fuentes.push({ fuente: 'openlibrary', nombre: 'Open Library', estado: 'error', error: String(openlibrary.reason?.message ?? openlibrary.reason) });
  }

  const datos = { libros: combinar(librosGoogle, librosOpen), fuentes };

  // Un resultado vacío porque las dos fallaron no se cachea: conviene
  // reintentar en el próximo pedido.
  if (fuentes.some((f) => f.estado === 'ok')) aCache(clave, datos);

  return { ...datos, desdeCache: false };
}

/** Un libro externo por su id ("google:xxx" u "openlibrary:/works/OL1W"). */
export async function obtenerLibroExterno(id) {
  const [fuente, ...resto] = String(id).split(':');
  const identificador = resto.join(':');

  if (fuente === 'google') {
    const volumen = await traerJson(`${GOOGLE}/${encodeURIComponent(identificador)}`);
    return desdeGoogle(volumen);
  }

  if (fuente === 'openlibrary') {
    // La ficha de una obra no trae autores resueltos; la búsqueda por clave sí
    const url = new URL(OPENLIBRARY);
    url.searchParams.set('q', `key:${identificador}`);
    url.searchParams.set('limit', '1');
    const datos = await traerJson(url);
    const doc = (datos.docs ?? [])[0];
    if (!doc) return null;

    const libro = desdeOpenLibrary(doc);
    // La descripción vive en otro recurso
    try {
      const obra = await traerJson(`https://openlibrary.org${identificador}.json`);
      libro.descripcion =
        typeof obra.description === 'string' ? obra.description : (obra.description?.value ?? null);
    } catch {
      // Sin descripción se muestra igual: no es motivo para fallar
    }
    return libro;
  }

  return null;
}
