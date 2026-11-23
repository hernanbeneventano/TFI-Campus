/**
 * Un libro que está en los dos catálogos tiene que verse como uno solo.
 *
 * Sin esto, buscar «Clean Code» devuelve la misma edición dos veces con
 * distinto id, y el usuario no tiene forma de saber que es la misma. Peor: la
 * de Google trae descripción y la de Open Library trae el préstamo, así que
 * las dos fichas están incompletas de maneras distintas.
 *
 * Cómo se decide que son el mismo libro: por **ISBN** cuando lo hay, que es
 * el identificador de verdad. Cuando no, por título y autor sin tildes, sin
 * signos y sin mayúsculas, que es lo único que queda. Del autor se toman solo
 * las dos primeras palabras: un catálogo dice «Robert C. Martin» y el otro
 * «Robert Martin», y comparar el nombre entero los dejaría separados.
 *
 * Es la misma regla con la que la Biblioteca del campus detecta duplicados
 * dentro de una materia, a propósito: dos criterios distintos para «el mismo
 * libro» en la misma pantalla sería inexplicable.
 */

/** Minúsculas, sin tildes y sin nada que no sea letra o número. */
export function sinTildes(texto) {
  return (texto ?? '')
    .normalize('NFD')
    .replace(/\p{Mn}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

export function huella(libro) {
  if (libro.isbn) {
    return 'isbn:' + libro.isbn.replace(/[^0-9Xx]/g, '').toUpperCase();
  }
  const autor = sinTildes(libro.autor).split(' ').slice(0, 2).join(' ');
  return `t:${sinTildes(libro.titulo)}|a:${autor}`;
}

/** Un campo está vacío tanto si vale `null` como si no está. Google no trae
 *  `enlacePrestamo` en absoluto, y eso también es un hueco que llenar. */
function esHueco(valor) {
  return valor === null || valor === undefined;
}

const SE_COMPLETAN = ['descripcion', 'editorial', 'anioPublicacion', 'isbn', 'idioma', 'portada'];
const ENLACES = ['enlaceLectura', 'enlacePrestamo'];

/**
 * Se queda el preferido —el de Google, que trae descripción y portada más
 * seguido— y se le tapan los huecos con el otro. Las dos fuentes quedan
 * anotadas: el usuario tiene derecho a saber de dónde salió cada cosa y a ir
 * a la otra ficha.
 */
export function unir(preferido, otro) {
  const unido = { ...preferido };

  for (const campo of SE_COMPLETAN) {
    if (esHueco(unido[campo])) unido[campo] = otro[campo] ?? null;
  }
  for (const campo of ENLACES) {
    if (esHueco(unido[campo])) unido[campo] = otro[campo] ?? null;
  }

  unido.tambienEn = otro.nombreFuente;
  unido.enlaceOtraFuente = otro.enlaceFicha ?? null;
  return unido;
}

/**
 * Google primero, para que sea el preferido en los empates. Se usa un Map y
 * no un objeto porque conserva el orden de inserción incluso al reemplazar
 * una clave que ya estaba: el libro unido queda donde estaba el de Google, y
 * el orden de los resultados no se altera al unir.
 */
export function combinar(deGoogle, deOpenLibrary) {
  const porHuella = new Map();

  for (const libro of deGoogle) {
    porHuella.set(huella(libro), libro);
  }

  for (const libro of deOpenLibrary) {
    const clave = huella(libro);
    const yaEsta = porHuella.get(clave);
    porHuella.set(clave, yaEsta ? unir(yaEsta, libro) : libro);
  }

  return [...porHuella.values()];
}
