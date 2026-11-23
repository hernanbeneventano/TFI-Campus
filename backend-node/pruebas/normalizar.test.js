/**
 * Que de cada catálogo salga siempre la misma forma de ficha, y sobre todo
 * que **no se ofrezca lo que la fuente no ofrece**.
 *
 * Esa es la regla que importa acá: un botón de descarga inventado lleva a un
 * 404 o, peor, a repartir algo que no tenemos derecho a repartir. Varias de
 * estas pruebas existen solo para eso.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import { desdeGoogle } from '../src/google.js';
import { desdeOpenLibrary } from '../src/openlibrary.js';

test('Google: una ficha completa se lee entera', () => {
  const libro = desdeGoogle({
    id: 'ABC123',
    volumeInfo: {
      title: 'Clean Code',
      subtitle: 'A Handbook',
      authors: ['Robert C. Martin', 'Otro'],
      description: 'Un libro sobre código',
      publisher: 'Prentice Hall',
      publishedDate: '2008-08-01',
      industryIdentifiers: [
        { type: 'OTHER', identifier: 'xx' },
        { type: 'ISBN_13', identifier: '9780132350884' },
      ],
      language: 'en',
      categories: ['Computers'],
      imageLinks: { thumbnail: 'http://books.google.com/tapa.jpg' },
      infoLink: 'https://books.google.com/ficha',
    },
    accessInfo: {},
  });

  assert.equal(libro.id, 'google:ABC123');
  assert.equal(libro.titulo, 'Clean Code');
  assert.equal(libro.autor, 'Robert C. Martin, Otro');
  assert.equal(libro.anioPublicacion, '2008');
  assert.equal(libro.isbn, '9780132350884');
  // La portada tiene que salir en https o el navegador la bloquea
  assert.equal(libro.portada, 'https://books.google.com/tapa.jpg');
  assert.equal(libro.externo, true);
});

test('Google: sin datos, la ficha no se rompe', () => {
  const libro = desdeGoogle({ id: 'X' });
  assert.equal(libro.titulo, 'Sin título');
  assert.equal(libro.autor, null);
  assert.equal(libro.isbn, null);
  assert.equal(libro.portada, null);
  assert.deepEqual(libro.categorias, []);
  assert.equal(libro.dominioPublico, false);
});

test('Google: no hay descarga si el libro no es de dominio público', () => {
  const libro = desdeGoogle({
    id: 'X',
    volumeInfo: { title: 'Un libro', previewLink: 'https://books.google.com/vista' },
    accessInfo: {
      publicDomain: false,
      viewability: 'PARTIAL',
      pdf: { isAvailable: true, downloadLink: 'https://books.google.com/bajar.pdf' },
    },
  });

  assert.equal(libro.enlaceDescarga, null, 'no se puede ofrecer la descarga');
  assert.equal(libro.enlaceLectura, null, 'tampoco la lectura completa');
  assert.equal(libro.enlaceVistaPrevia, 'https://books.google.com/vista');
});

test('Google: con dominio público sí hay descarga y lectura', () => {
  const libro = desdeGoogle({
    id: 'X',
    volumeInfo: { title: 'Un clásico', previewLink: 'https://books.google.com/vista', viewability: 'ALL_PAGES' },
    accessInfo: {
      publicDomain: true,
      viewability: 'ALL_PAGES',
      pdf: { isAvailable: true, downloadLink: 'https://books.google.com/bajar.pdf' },
    },
  });

  assert.equal(libro.enlaceDescarga, 'https://books.google.com/bajar.pdf');
  assert.equal(libro.enlaceLectura, 'https://books.google.com/vista');
  assert.equal(libro.dominioPublico, true);
});

test('Open Library: una ficha completa se lee entera', () => {
  const libro = desdeOpenLibrary({
    key: '/works/OL1W',
    title: 'Clean Code',
    author_name: ['Robert Martin'],
    first_publish_year: 2008,
    isbn: ['9780132350884', '0132350882'],
    cover_i: 12345,
    language: ['eng'],
    subject: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
    publisher: ['Prentice Hall', 'Otra'],
    ebook_access: 'no_ebook',
  });

  assert.equal(libro.id, 'openlibrary:/works/OL1W');
  assert.equal(libro.anioPublicacion, '2008');
  assert.equal(libro.isbn, '9780132350884');
  assert.equal(libro.editorial, 'Prentice Hall');
  assert.equal(libro.idioma, 'eng');
  assert.equal(libro.portada, 'https://covers.openlibrary.org/b/id/12345-M.jpg');
  assert.equal(libro.enlaceFicha, 'https://openlibrary.org/works/OL1W');
  // Se cortan en seis: la lista entera es ruido en la ficha
  assert.equal(libro.categorias.length, 6);
});

test('Open Library: «borrowable» da préstamo, no lectura', () => {
  const libro = desdeOpenLibrary({
    key: '/works/OL1W',
    title: 'Un libro',
    ebook_access: 'borrowable',
    ia: ['unlibro00mart'],
  });

  assert.equal(libro.enlacePrestamo, 'https://archive.org/details/unlibro00mart');
  assert.equal(libro.enlaceLectura, null);
  assert.equal(libro.dominioPublico, false);
});

test('Open Library: «public» da lectura, no préstamo', () => {
  const libro = desdeOpenLibrary({
    key: '/works/OL1W',
    title: 'Un clásico',
    ebook_access: 'public',
    ia: ['unclasico00'],
  });

  assert.equal(libro.enlaceLectura, 'https://archive.org/details/unclasico00');
  assert.equal(libro.enlacePrestamo, null);
  assert.equal(libro.dominioPublico, true);
});

test('Open Library: sin copia en Archive no hay enlace, aunque diga público', () => {
  const libro = desdeOpenLibrary({ key: '/works/OL1W', title: 'Un libro', ebook_access: 'public' });
  assert.equal(libro.enlaceLectura, null);
  assert.equal(libro.enlacePrestamo, null);
});

test('Open Library: nunca ofrece descarga', () => {
  const libro = desdeOpenLibrary({
    key: '/works/OL1W',
    title: 'Un libro',
    ebook_access: 'public',
    ia: ['x'],
  });
  assert.equal(libro.enlaceDescarga, null);
});
