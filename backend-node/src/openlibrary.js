/**
 * Open Library: cómo se le pregunta y cómo se lee lo que contesta.
 *
 * https://openlibrary.org/dev/docs/api/search
 *
 * No pide clave de ningún tipo, lo que la vuelve la fuente confiable de las
 * dos: Google sin clave devuelve 429 casi siempre. A cambio trae menos datos
 * —casi nunca descripción— y por eso, cuando un libro está en las dos, gana
 * el de Google y esta completa los huecos (ver `unificar.js`).
 *
 * De los accesos que declara, «public» y «borrowable» son los únicos que dan
 * algo real. El resto son fichas sin libro atrás.
 */

import { config } from './config.js';

export const OPENLIBRARY = 'https://openlibrary.org/search.json';

// Pedir solo los campos que se usan: la respuesta completa es enorme y la
// mayor parte no se mira nunca.
const CAMPOS =
  'key,title,author_name,first_publish_year,isbn,cover_i,language,' +
  'subject,publisher,ebook_access,ia';

export function parametrosOpenLibrary(texto, campo) {
  const limpio = texto.trim();
  const parametros = {};

  if (campo === 'titulo') parametros.title = limpio;
  else if (campo === 'autor') parametros.author = limpio;
  else if (campo === 'isbn') parametros.isbn = limpio.replace(/[^0-9Xx]/g, '');
  else if (campo === 'tema') parametros.subject = limpio;
  else parametros.q = limpio;

  parametros.limit = String(config.porFuente);
  parametros.fields = CAMPOS;
  return parametros;
}

export function desdeOpenLibrary(doc) {
  const isbns = doc.isbn ?? [];
  const acceso = doc.ebook_access;
  const prestable = acceso === 'borrowable';
  const libre = acceso === 'public';
  const ia = (doc.ia ?? [null])[0];
  const anio = doc.first_publish_year;
  const autores = doc.author_name ?? [];

  return {
    id: `openlibrary:${doc.key}`,
    fuente: 'openlibrary',
    nombreFuente: 'Open Library',
    externo: true,
    titulo: doc.title || 'Sin título',
    subtitulo: null,
    autor: autores.join(', ') || null,
    descripcion: null,
    editorial: (doc.publisher ?? [null])[0] ?? null,
    anioPublicacion: anio ? String(anio) : null,
    isbn: isbns.length > 0 ? isbns[0] : null,
    idioma: (doc.language ?? [null])[0] ?? null,
    categorias: (doc.subject ?? []).slice(0, 6),
    portada: doc.cover_i ? `https://covers.openlibrary.org/b/id/${doc.cover_i}-M.jpg` : null,

    enlaceLectura: libre && ia ? `https://archive.org/details/${ia}` : null,
    enlacePrestamo: prestable && ia ? `https://archive.org/details/${ia}` : null,
    enlaceVistaPrevia: null,
    enlaceDescarga: null,
    enlaceFicha: `https://openlibrary.org${doc.key}`,
    dominioPublico: Boolean(libre),
  };
}
