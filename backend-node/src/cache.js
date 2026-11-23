/**
 * Caché en memoria, con vencimiento y con tope.
 *
 * Las mismas búsquedas se repiten muchísimo: alguien escribe «algoritm»,
 * borra una letra, la vuelve a escribir, y eso son tres consultas idénticas a
 * dos interfaces que tienen cupo. La caché es lo que hace que el cupo de
 * Google alcance.
 *
 * Vive en memoria del proceso a propósito. No es un dato del campus: si se
 * pierde al reiniciar, lo único que pasa es que la primera búsqueda vuelve a
 * salir a la red. Guardarla en Firestore sería darle un dueño de datos a este
 * servicio, que es exactamente lo que no tiene que tener.
 */

export class Cache {
  #entradas = new Map();
  #vidaMs;
  #maximo;
  #ahora;

  /** `ahora` se puede reemplazar en las pruebas para no esperar diez minutos. */
  constructor({ segundos, maximo, ahora = () => Date.now() }) {
    this.#vidaMs = segundos * 1000;
    this.#maximo = maximo;
    this.#ahora = ahora;
  }

  obtener(clave) {
    const guardado = this.#entradas.get(clave);
    if (!guardado) return null;

    if (this.#ahora() - guardado.cuando > this.#vidaMs) {
      this.#entradas.delete(clave);
      return null;
    }
    return guardado.datos;
  }

  guardar(clave, datos) {
    // El más viejo primero. Un Map conserva el orden de inserción, así que el
    // primero que devuelve `keys()` es el que entró antes.
    if (!this.#entradas.has(clave) && this.#entradas.size >= this.#maximo) {
      const masViejo = this.#entradas.keys().next().value;
      this.#entradas.delete(masViejo);
    }
    this.#entradas.set(clave, { cuando: this.#ahora(), datos });
  }

  get tamano() {
    return this.#entradas.size;
  }

  vaciar() {
    this.#entradas.clear();
  }
}
