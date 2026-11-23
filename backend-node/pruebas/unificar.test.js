/**
 * Que el mismo libro de las dos fuentes quede como uno solo.
 *
 * Es lo que más vale probar de este servicio: si la unificación falla, el
 * usuario ve la misma edición repetida con dos fichas incompletas y no tiene
 * forma de darse cuenta de que es la misma.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import { combinar, huella, sinTildes, unir } from '../src/unificar.js';

function libro(datos) {
  return {
    id: 'x',
    fuente: 'google',
    nombreFuente: 'Google Books',
    titulo: 'Sin título',
    autor: null,
    descripcion: null,
    editorial: null,
    anioPublicacion: null,
    isbn: null,
    idioma: null,
    portada: null,
    enlaceLectura: null,
    enlaceFicha: null,
    ...datos,
  };
}

test('sinTildes deja minúsculas sin acentos ni signos', () => {
  assert.equal(sinTildes('Álgebra Lineal'), 'algebra lineal');
  assert.equal(sinTildes('Programación: ¡Teoría!'), 'programacion teoria');
  assert.equal(sinTildes('C++  (3.ª ed.)'), 'c 3 ed');
  assert.equal(sinTildes(null), '');
});

test('la huella por ISBN ignora guiones y mayúsculas', () => {
  assert.equal(huella(libro({ isbn: '978-0-13-235088-4' })), 'isbn:9780132350884');
  assert.equal(huella(libro({ isbn: '097522980x' })), 'isbn:097522980X');
});

test('sin ISBN, la huella usa título y las dos primeras palabras del autor', () => {
  // Que un catálogo liste coautores y el otro no, da igual: se miran dos
  // palabras. Y las mayúsculas y los signos tampoco cuentan.
  const deGoogle = libro({ titulo: 'Clean Code', autor: 'Robert Martin' });
  const deOpen = libro({ titulo: 'Clean code', autor: 'Robert Martin, Andrew Hunt' });
  assert.equal(huella(deGoogle), huella(deOpen));

  const conTildes = libro({ titulo: 'Álgebra Lineal', autor: 'José Pérez' });
  const sinTildes = libro({ titulo: 'algebra lineal', autor: 'Jose Perez' });
  assert.equal(huella(conTildes), huella(sinTildes));
});

test('la inicial del medio separa dos fichas del mismo libro', () => {
  // Limitación conocida, heredada del campus: «Robert C. Martin» da
  // «robert c» y «Robert Martin» da «robert martin», así que sin ISBN el
  // mismo libro aparece dos veces.
  //
  // Queda documentada en una prueba, y no arreglada, por dos motivos: casi
  // todos los libros traen ISBN y entonces la huella ni mira el autor, y
  // esta misma regla es la que detecta duplicados en la Biblioteca del
  // campus. Cambiarla acá solamente haría que las dos pantallas opinen
  // distinto sobre qué es «el mismo libro».
  const conInicial = libro({ titulo: 'Clean Code', autor: 'Robert C. Martin' });
  const sinInicial = libro({ titulo: 'Clean Code', autor: 'Robert Martin' });
  assert.notEqual(huella(conInicial), huella(sinInicial));

  // Con ISBN, el autor no se mira y el problema no existe
  assert.equal(
    huella(libro({ titulo: 'Clean Code', autor: 'Robert C. Martin', isbn: '9780132350884' })),
    huella(libro({ titulo: 'Clean Code', autor: 'Robert Martin', isbn: '978-0-13-235088-4' })),
  );
});

test('unir completa los huecos del preferido y anota la otra fuente', () => {
  const deGoogle = libro({
    titulo: 'Clean Code',
    descripcion: 'Un libro sobre código',
    editorial: null,
    isbn: null,
  });
  const deOpen = libro({
    fuente: 'openlibrary',
    nombreFuente: 'Open Library',
    titulo: 'Clean Code',
    descripcion: 'otra descripción',
    editorial: 'Prentice Hall',
    isbn: '9780132350884',
    enlacePrestamo: 'https://archive.org/details/cleancode',
    enlaceFicha: 'https://openlibrary.org/works/OL1W',
  });

  const unido = unir(deGoogle, deOpen);

  // Lo que el preferido ya tenía no se pisa
  assert.equal(unido.descripcion, 'Un libro sobre código');
  // Los huecos se llenan
  assert.equal(unido.editorial, 'Prentice Hall');
  assert.equal(unido.isbn, '9780132350884');
  // Google no trae la clave `enlacePrestamo` en absoluto: también es un hueco
  assert.equal(unido.enlacePrestamo, 'https://archive.org/details/cleancode');
  // Y queda dicho de dónde salió lo demás
  assert.equal(unido.tambienEn, 'Open Library');
  assert.equal(unido.enlaceOtraFuente, 'https://openlibrary.org/works/OL1W');
});

test('combinar deduplica por ISBN y deja ganar a Google', () => {
  const deGoogle = [libro({ id: 'google:A', isbn: '9780132350884', descripcion: 'de Google' })];
  const deOpen = [
    libro({
      id: 'openlibrary:/works/OL1W',
      fuente: 'openlibrary',
      nombreFuente: 'Open Library',
      isbn: '978-0-13-235088-4',
      descripcion: 'de Open Library',
    }),
  ];

  const juntos = combinar(deGoogle, deOpen);

  assert.equal(juntos.length, 1);
  assert.equal(juntos[0].id, 'google:A');
  assert.equal(juntos[0].descripcion, 'de Google');
  assert.equal(juntos[0].tambienEn, 'Open Library');
});

test('combinar conserva el orden de Google al unir', () => {
  const deGoogle = [
    libro({ id: 'google:1', isbn: '1111111111' }),
    libro({ id: 'google:2', isbn: '2222222222' }),
    libro({ id: 'google:3', isbn: '3333333333' }),
  ];
  // El de Open Library coincide con el del medio: el unido tiene que quedar
  // en el medio, no al final.
  const deOpen = [
    libro({ id: 'openlibrary:/works/OLx', fuente: 'openlibrary', nombreFuente: 'Open Library', isbn: '2222222222' }),
  ];

  const juntos = combinar(deGoogle, deOpen);

  assert.deepEqual(
    juntos.map((l) => l.id),
    ['google:1', 'google:2', 'google:3'],
  );
  assert.equal(juntos[1].tambienEn, 'Open Library');
});

test('lo que solo está en una fuente se mantiene', () => {
  const juntos = combinar(
    [libro({ id: 'google:A', isbn: '1111111111' })],
    [libro({ id: 'openlibrary:/works/OLb', isbn: '2222222222' })],
  );
  assert.equal(juntos.length, 2);
  assert.equal(juntos[0].tambienEn, undefined);
});
