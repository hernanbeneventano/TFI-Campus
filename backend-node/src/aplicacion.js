/**
 * La aplicación, armada y sin escuchar todavía.
 *
 * Va aparte de `servidor.js` para que las pruebas puedan levantarla en un
 * puerto al azar y apagarla, sin tocar el arranque de verdad ni depender de
 * que el 4000 esté libre.
 */

import express from 'express';

import { crearRutas, error500, noEncontrada } from './rutas.js';

export function crearAplicacion() {
  const aplicacion = express();

  // No hace falta nada más: este servicio solo responde GET y nunca recibe un
  // cuerpo. Sin `express.json()` no hay forma de mandarle 20 MB para que los
  // intente parsear.
  aplicacion.disable('x-powered-by');

  aplicacion.use(crearRutas());
  aplicacion.use(noEncontrada);
  aplicacion.use(error500);

  return aplicacion;
}
