/**
 * La caché y el freno. Los dos dependen del reloj, así que las pruebas le
 * pasan uno propio: esperar diez minutos de verdad no es una prueba.
 */

import assert from 'node:assert/strict';
import test from 'node:test';

import { Cache } from '../src/cache.js';
import { Freno } from '../src/freno.js';

function relojFalso(inicio = 0) {
  let ahora = inicio;
  return { ahora: () => ahora, avanzar: (ms) => (ahora += ms) };
}

test('la caché devuelve lo guardado', () => {
  const cache = new Cache({ segundos: 600, maximo: 10 });
  cache.guardar('a', { libros: [1] });
  assert.deepEqual(cache.obtener('a'), { libros: [1] });
  assert.equal(cache.obtener('b'), null);
});

test('lo guardado vence y se borra', () => {
  const reloj = relojFalso();
  const cache = new Cache({ segundos: 600, maximo: 10, ahora: reloj.ahora });

  cache.guardar('a', { libros: [1] });
  reloj.avanzar(599 * 1000);
  assert.notEqual(cache.obtener('a'), null, 'antes de los 10 minutos sigue');

  reloj.avanzar(2 * 1000);
  assert.equal(cache.obtener('a'), null, 'pasados los 10 minutos ya no');
  assert.equal(cache.tamano, 0, 'y no queda ocupando lugar');
});

test('al llegar al tope se va el más viejo', () => {
  const cache = new Cache({ segundos: 600, maximo: 2 });
  cache.guardar('a', 1);
  cache.guardar('b', 2);
  cache.guardar('c', 3);

  assert.equal(cache.obtener('a'), null, 'el primero se fue');
  assert.equal(cache.obtener('b'), 2);
  assert.equal(cache.obtener('c'), 3);
  assert.equal(cache.tamano, 2);
});

test('reescribir una clave que ya está no expulsa a nadie', () => {
  const cache = new Cache({ segundos: 600, maximo: 2 });
  cache.guardar('a', 1);
  cache.guardar('b', 2);
  cache.guardar('a', 99);

  assert.equal(cache.obtener('a'), 99);
  assert.equal(cache.obtener('b'), 2);
  assert.equal(cache.tamano, 2);
});

test('el freno corta al llegar al límite y se renueva con la ventana', () => {
  const reloj = relojFalso();
  const freno = new Freno({ porMinuto: 3, ahora: reloj.ahora });

  assert.equal(freno.permite(), true);
  assert.equal(freno.permite(), true);
  assert.equal(freno.permite(), true);
  assert.equal(freno.permite(), false, 'la cuarta no pasa');

  reloj.avanzar(59 * 1000);
  assert.equal(freno.permite(), false, 'dentro del minuto sigue cortado');

  reloj.avanzar(2 * 1000);
  assert.equal(freno.permite(), true, 'pasado el minuto vuelve a pasar');
});

test('el freno dice cuántos segundos faltan', () => {
  const reloj = relojFalso();
  const freno = new Freno({ porMinuto: 1, ahora: reloj.ahora });
  freno.permite();
  reloj.avanzar(20 * 1000);
  assert.equal(freno.segundosQueFaltan(), 40);
});
