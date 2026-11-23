/**
 * El freno del servicio, por HTTP.
 *
 * Archivo propio por el mismo motivo que el de la clave: el límite se lee al
 * cargar el módulo, y acá hace falta que sea chico para poder pasarlo.
 */

process.env.FRENO_POR_MINUTO = '2';
delete process.env.CLAVE_INTERNA;

import assert from 'node:assert/strict';
import test, { after, before } from 'node:test';

import { json, levantar, reemplazarRed } from './ayuda.js';

const { crearAplicacion } = await import('../src/aplicacion.js');

let servidor;
let red;

before(async () => {
  red = reemplazarRed(() => json({ items: [], docs: [] }));
  servidor = await levantar(crearAplicacion());
});

after(async () => {
  red.restaurar();
  await servidor.cerrar();
});

test('pasado el límite, 429 con Retry-After', async () => {
  const primera = await fetch(`${servidor.base}/catalogos/buscar?texto=uno`);
  const segunda = await fetch(`${servidor.base}/catalogos/buscar?texto=dos`);
  assert.equal(primera.status, 200);
  assert.equal(segunda.status, 200);

  const tercera = await fetch(`${servidor.base}/catalogos/buscar?texto=tres`);
  assert.equal(tercera.status, 429);
  assert.deepEqual(await tercera.json(), {
    detail: 'Demasiadas búsquedas, probá en un momento',
  });

  // Sin esto, el cliente no sabe cuánto esperar y reintenta en el acto
  const esperar = Number(tercera.headers.get('Retry-After'));
  assert.ok(esperar >= 1 && esperar <= 60, `Retry-After raro: ${esperar}`);
});

test('la salud no la frena, para poder ver si está vivo', async () => {
  const respuesta = await fetch(`${servidor.base}/salud`);
  assert.equal(respuesta.status, 200);
});
