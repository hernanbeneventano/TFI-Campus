/**
 * La configuración, en un solo lugar.
 *
 * Se lee una vez al cargar el módulo y queda congelada. Leer `process.env`
 * desparramado por el código termina en que una variable significa una cosa
 * en un archivo y otra en otro, y en que nadie sabe qué se puede configurar
 * sin buscar en todos lados.
 *
 * Las variables llegan por `--env-file-if-exists=.env` (ver package.json) o
 * del entorno del proceso. Si falta el archivo, no pasa nada: todas tienen
 * un valor por defecto que sirve para desarrollar.
 */

function entero(nombre, pordefecto) {
  const bruto = process.env[nombre];
  if (bruto === undefined || bruto === '') return pordefecto;
  const valor = Number.parseInt(bruto, 10);
  // Un número mal escrito no puede quedar en 0 en silencio: con ESPERA en 0
  // no habría búsqueda, y con CACHE_MAXIMO en 0 no habría caché, sin que
  // nada avisara.
  if (!Number.isFinite(valor) || valor <= 0) {
    throw new Error(`${nombre} tiene que ser un número mayor que cero, y llegó «${bruto}»`);
  }
  return valor;
}

function texto(nombre, pordefecto = null) {
  const valor = process.env[nombre];
  return valor === undefined || valor === '' ? pordefecto : valor;
}

export const config = Object.freeze({
  puerto: entero('PUERTO', 4000),
  host: texto('HOST', '127.0.0.1'),

  // Si está, se exige en cada petición. Si no, el servicio queda abierto a
  // quien lo alcance, y por eso el host viene en 127.0.0.1.
  claveInterna: texto('CLAVE_INTERNA'),

  googleApiKey: texto('GOOGLE_BOOKS_API_KEY'),

  esperaMs: entero('ESPERA_SEGUNDOS', 9) * 1000,
  porFuente: entero('POR_FUENTE', 20),

  cacheSegundos: entero('CACHE_SEGUNDOS', 600),
  cacheMaximo: entero('CACHE_MAXIMO', 200),

  frenoPorMinuto: entero('FRENO_POR_MINUTO', 120),

  // Lo ve Google y Open Library en cada pedido. Las dos interfaces son
  // públicas pero piden identificarse, y un agente genérico es lo primero
  // que limitan.
  agente: 'CampusTFI/0.1 (campus virtual academico)',
});
