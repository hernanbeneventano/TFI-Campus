/**
 * El secreto compartido.
 *
 * Va en su propio archivo porque la configuración se lee una sola vez al
 * cargar el módulo: para probar el servicio **con** clave hay que definirla
 * antes de importarlo. El corredor de pruebas de Node ejecuta cada archivo en
 * su propio proceso, así que acá se puede.
 */

process.env.CLAVE_INTERNA = 'un-secreto-de-prueba';
process.env.FRENO_POR_MINUTO = '1000';

import assert from 'node:assert/strict';
import test, { after, before } from 'node:test';

import { json, levantar, reemplazarRed } from './ayuda.js';

// Dinámico: tiene que cargarse después de tocar el entorno de arriba.
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

test('sin la clave, 401', async () => {
  const respuesta = await fetch(`${servidor.base}/catalogos/buscar?texto=algo`);
  assert.equal(respuesta.status, 401);
  assert.deepEqual(await respuesta.json(), { detail: 'Clave interna incorrecta' });
});

test('con la clave equivocada, 401', async () => {
  const respuesta = await fetch(`${servidor.base}/catalogos/buscar?texto=algo`, {
    headers: { 'X-Clave-Interna': 'otra' },
  });
  assert.equal(respuesta.status, 401);
});

test('con la clave correcta, pasa', async () => {
  const respuesta = await fetch(`${servidor.base}/catalogos/buscar?texto=algo`, {
    headers: { 'X-Clave-Interna': 'un-secreto-de-prueba' },
  });
  assert.equal(respuesta.status, 200);
});

test('la salud también queda detrás de la clave', async () => {
  // No expone datos, pero decir «estoy vivo y tengo clave de Google» a
  // cualquiera que pregunte no suma nada.
  const respuesta = await fetch(`${servidor.base}/salud`);
  assert.equal(respuesta.status, 401);
});
