/**
 * Google Books: cómo se le pregunta y cómo se lee lo que contesta.
 *
 * https://developers.google.com/books/docs/v1/using
 *
 * La regla de la normalización, que vale para los dos catálogos: **solo se
 * ofrece lo que la interfaz dice que se puede hacer de verdad.** Nada de
 * armar un enlace de descarga porque el libro «parece» libre. Si no es de
 * dominio público, va el enlace a la ficha y nada más. Un botón de descarga
 * que lleva a un 404 —o peor, a algo que no tenemos derecho a repartir— es
 * mucho peor que no tener botón.
 */

import { config } from './config.js';

export const GOOGLE = 'https://www.googleapis.com/books/v1/volumes';

/** Google devuelve las portadas en http; el campus va en https y el navegador
 *  bloquearía la imagen por contenido mixto. */
export function aHttps(url) {
  if (typeof url !== 'string') return null;
  return url.replace(/^http:\/\//, 'https://');
}

function soloIsbn(texto) {
  return texto.replace(/[^0-9Xx]/g, '');
}

export function consultaGoogle(texto, campo) {
  const limpio = texto.trim();
  if (campo === 'titulo') return `intitle:${limpio}`;
  if (campo === 'autor') return `inauthor:${limpio}`;
  if (campo === 'isbn') return `isbn:${soloIsbn(limpio)}`;
  if (campo === 'tema') return `subject:${limpio}`;
  return limpio;
}

export function parametrosGoogle(texto, campo, idioma) {
  // Google Books no exige clave para buscar, pero con una el límite es más
  // alto. Si está, se usa; si no, se busca igual.
  const parametros = {
    q: consultaGoogle(texto, campo),
    maxResults: String(config.porFuente),
    printType: 'books',
  };
  if (idioma) parametros.langRestrict = idioma;
  if (config.googleApiKey) parametros.key = config.googleApiKey;
  return parametros;
}

export function desdeGoogle(volumen) {
  const v = volumen.volumeInfo ?? {};
  const acceso = volumen.accessInfo ?? {};
  const isbn = (v.industryIdentifiers ?? []).find((i) =>
    String(i?.type ?? '').startsWith('ISBN'),
  );
  const imagenes = v.imageLinks ?? {};

  const leeCompleto =
    v.viewability === 'ALL_PAGES' || acceso.accessViewStatus === 'FULL_PUBLIC_DOMAIN';
  const pdf = acceso.pdf ?? {};
  const pdfPublico = Boolean(pdf.isAvailable && pdf.downloadLink && acceso.publicDomain);

  const publicado = v.publishedDate;
  const autores = v.authors ?? [];

  return {
    id: `google:${volumen.id}`,
    fuente: 'google',
    nombreFuente: 'Google Books',
    externo: true,
    titulo: v.title || 'Sin título',
    subtitulo: v.subtitle ?? null,
    autor: autores.join(', ') || null,
    descripcion: v.description ?? null,
    editorial: v.publisher ?? null,
    anioPublicacion: publicado ? String(publicado).slice(0, 4) : null,
    isbn: isbn ? (isbn.identifier ?? null) : null,
    idioma: v.language ?? null,
    categorias: v.categories ?? [],
    portada: aHttps(imagenes.thumbnail ?? imagenes.smallThumbnail ?? null),

    // Qué se puede hacer realmente con este libro
    enlaceLectura: leeCompleto ? (v.previewLink ?? null) : null,
    enlaceVistaPrevia: acceso.viewability === 'PARTIAL' ? (v.previewLink ?? null) : null,
    enlaceDescarga: pdfPublico ? pdf.downloadLink : null,
    enlaceFicha: v.infoLink ?? v.canonicalVolumeLink ?? null,
    dominioPublico: Boolean(acceso.publicDomain),
  };
}
