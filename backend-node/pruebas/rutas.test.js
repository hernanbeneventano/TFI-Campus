/**
 * El servicio por HTTP, de punta a punta: se levanta la aplicación de verdad
 * y se le pega con fetch. Lo único reemplazado es la salida a internet.
 *
 * Lo que más importa de este archivo: **que una fuente caída no deje la
 * pantalla vacía.** Google sin clave devuelve 429 casi siempre, así que ese
 * no es un caso raro, es el de todos los días.
 */

import assert from 'node:assert/strict';
import test, { afterEach, beforeEach } from 'node:test';

import { crearAplicacion } from '../src/aplicacion.js';
import { vaciarCache } from '../src/catalogos.js';
import {
  DOC_OPENLIBRARY,
  VOLUMEN_GOOGLE,
  json,
  levantar,
  reemplazarRed,
} from './ayuda.js';

let servidor;
let red;

beforeEach(async () => {
  vaciarCache();
  servidor = await levantar(crearAplicacion());
});

afterEach(async () => {
  red?.restaurar();
  red = undefined;
  await servidor.cerrar();
});

/** Las dos fuentes contestando bien. */
function redNormal() {
  return reemplazarRed((direccion) => {
    if (direccion.hostname === 'www.googleapis.com') {
      // La búsqueda y la ficha de un volumen son la misma dirección con un
      // segmento más. Hay que distinguirlas, o pedir una ficha devuelve una
      // lista y el libro sale vacío.
      return direccion.pathname.endsWith('/volumes')
        ? json({ items: [VOLUMEN_GOOGLE] })
        : json(VOLUMEN_GOOGLE);
    }
    if (direccion.hostname === 'openlibrary.org' && direccion.pathname === '/search.json') {
      return json({ docs: [DOC_OPENLIBRARY] });
    }
    if (direccion.hostname === 'openlibrary.org') {
      return json({ description: 'La descripción de la obra' });
    }
    return json({ detail: 'no esperado' }, 500);
  });
}

test('la salud contesta sin salir a la red', async () => {
  red = redNormal();
  const respuesta = await fetch(`${servidor.base}/salud`);
  const cuerpo = await respuesta.json();

  assert.equal(respuesta.status, 200);
  assert.equal(cuerpo.estado, 'bien');
  assert.equal(cuerpo.servicio, 'catalogos');
  assert.equal(red.cuantas, 0);
});

test('una búsqueda trae las dos fuentes unificadas', async () => {
  red = redNormal();
  const respuesta = await fetch(`${servidor.base}/catalogos/buscar?texto=codigo%20limpio`);
  const cuerpo = await respuesta.json();

  assert.equal(respuesta.status, 200);
  assert.equal(cuerpo.libros.length, 2, 'son libros distintos, no se unen');
  assert.equal(cuerpo.desdeCache, false);

  const estados = cuerpo.fuentes.map((f) => [f.fuente, f.estado]);
  assert.deepEqual(estados, [
    ['google', 'ok'],
    ['openlibrary', 'ok'],
  ]);

  // Las dos se consultaron a la vez, no una después de la otra
  assert.equal(red.cuantas, 2);
});

test('con menos de dos letras no se sale a la red', async () => {
  red = redNormal();
  const respuesta = await fetch(`${servidor.base}/catalogos/buscar?texto=a`);
  const cuerpo = await respuesta.json();

  assert.deepEqual(cuerpo, { libros: [], fuentes: [], desdeCache: false });
  assert.equal(red.cuantas, 0, 'no se gasta cupo en una búsqueda que no sirve');
});

test('si Google falla, se contesta con Open Library y se avisa', async () => {
  red = reemplazarRed((direccion) => {
    if (direccion.hostname === 'www.googleapis.com') {
      return json({ error: 'cupo agotado' }, 429);
    }
    return json({ docs: [DOC_OPENLIBRARY] });
  });

  const respuesta = await fetch(`${servidor.base}/catalogos/buscar?texto=programacion`);
  const cuerpo = await respuesta.json();

  assert.equal(respuesta.status, 200, 'el servicio no falla porque falle una fuente');
  assert.equal(cuerpo.libros.length, 1, 'queda lo de Open Library');

  const google = cuerpo.fuentes.find((f) => f.fuente === 'google');
  assert.equal(google.estado, 'error');
  assert.match(google.error, /429/, 'el motivo tiene que llegar a la pantalla');

  const open = cuerpo.fuentes.find((f) => f.fuente === 'openlibrary');
  assert.equal(open.estado, 'ok');
  assert.equal(open.cuantos, 1);
});

test('si las dos fallan, no se cachea el vacío', async () => {
  red = reemplazarRed(() => json({ error: 'caído' }, 500));

  const primera = await (await fetch(`${servidor.base}/catalogos/buscar?texto=algoritmos`)).json();
  assert.equal(primera.libros.length, 0);
  assert.ok(primera.fuentes.every((f) => f.estado === 'error'));

  await fetch(`${servidor.base}/catalogos/buscar?texto=algoritmos`);
  assert.equal(red.cuantas, 4, 'se reintenta: 2 fuentes por 2 búsquedas');
});

test('la segunda búsqueda igual sale de la caché', async () => {
  red = redNormal();

  await fetch(`${servidor.base}/catalogos/buscar?texto=codigo%20limpio`);
  assert.equal(red.cuantas, 2);

  const respuesta = await fetch(`${servidor.base}/catalogos/buscar?texto=CODIGO%20LIMPIO`);
  const cuerpo = await respuesta.json();

  assert.equal(cuerpo.desdeCache, true, 'y no distingue mayúsculas');
  assert.equal(red.cuantas, 2, 'no se volvió a salir a la red');
  assert.equal(cuerpo.libros.length, 2);
});

test('un libro de Google por su id', async () => {
  red = redNormal();
  const respuesta = await fetch(`${servidor.base}/catalogos/libro?id=google:ABC123`);
  const cuerpo = await respuesta.json();

  assert.equal(respuesta.status, 200);
  assert.equal(cuerpo.libro.id, 'google:ABC123');
  assert.equal(cuerpo.libro.titulo, 'Clean Code');
});

test('un libro de Open Library trae la descripción del otro recurso', async () => {
  red = redNormal();
  const respuesta = await fetch(
    `${servidor.base}/catalogos/libro?id=${encodeURIComponent('openlibrary:/works/OL1W')}`,
  );
  const cuerpo = await respuesta.json();

  assert.equal(respuesta.status, 200);
  assert.equal(cuerpo.libro.id, 'openlibrary:/works/OL1W');
  assert.equal(cuerpo.libro.descripcion, 'La descripción de la obra');
});

test('sin descripción, el libro se devuelve igual', async () => {
  red = reemplazarRed((direccion) => {
    if (direccion.pathname === '/search.json') return json({ docs: [DOC_OPENLIBRARY] });
    return json({ detail: 'no está' }, 404);
  });

  const respuesta = await fetch(
    `${servidor.base}/catalogos/libro?id=${encodeURIComponent('openlibrary:/works/OL1W')}`,
  );
  const cuerpo = await respuesta.json();

  assert.equal(respuesta.status, 200);
  assert.equal(cuerpo.libro.descripcion, null);
});

test('un libro que no está da 404', async () => {
  red = reemplazarRed((direccion) => {
    if (direccion.pathname === '/search.json') return json({ docs: [] });
    return json({}, 404);
  });

  const respuesta = await fetch(
    `${servidor.base}/catalogos/libro?id=${encodeURIComponent('openlibrary:/works/OLnada')}`,
  );
  assert.equal(respuesta.status, 404);
  assert.deepEqual(await respuesta.json(), { detail: 'No se encontró ese libro' });
});

test('una fuente que no conocemos da 404, no un error', async () => {
  red = redNormal();
  const respuesta = await fetch(`${servidor.base}/catalogos/libro?id=otra:123`);
  assert.equal(respuesta.status, 404);
  assert.equal(red.cuantas, 0);
});

test('sin id, 400', async () => {
  red = redNormal();
  const respuesta = await fetch(`${servidor.base}/catalogos/libro`);
  assert.equal(respuesta.status, 400);
  assert.deepEqual(await respuesta.json(), { detail: 'Falta el id del libro' });
});

test('una dirección que no existe da 404 con el formato del campus', async () => {
  red = redNormal();
  const respuesta = await fetch(`${servidor.base}/lo-que-sea`);
  assert.equal(respuesta.status, 404);
  const cuerpo = await respuesta.json();
  assert.ok(cuerpo.detail, 'el error viaja en «detail», como en el campus');
});
