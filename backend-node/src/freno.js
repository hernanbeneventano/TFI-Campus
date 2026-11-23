/**
 * El freno del servicio: cuántas peticiones se aceptan por minuto.
 *
 * No reemplaza al del campus. El campus ya frena por persona (30 búsquedas
 * por minuto cada una), porque es el único que sabe quién pregunta: acá
 * llegan todas con la misma cara. Este es el de último recurso, y lo que
 * protege no es el servicio —aguanta de sobra— sino **el cupo de Google**,
 * que es compartido por todo el campus y se agota para todos a la vez.
 *
 * Ventana fija de un minuto, no deslizante. Es menos preciso en el borde y es
 * una decisión consciente: un contador y una marca de tiempo contra una lista
 * de fechas por cliente, para algo que no tiene que ser exacto.
 */

export class Freno {
  #limite;
  #ventanaMs;
  #ahora;
  #contador = 0;
  #desde = 0;

  constructor({ porMinuto, ahora = () => Date.now() }) {
    this.#limite = porMinuto;
    this.#ventanaMs = 60 * 1000;
    this.#ahora = ahora;
    this.#desde = ahora();
  }

  /** `true` si la petición pasa; `false` si hay que contestarle 429. */
  permite() {
    const ahora = this.#ahora();
    if (ahora - this.#desde >= this.#ventanaMs) {
      this.#contador = 0;
      this.#desde = ahora;
    }
    if (this.#contador >= this.#limite) return false;
    this.#contador += 1;
    return true;
  }

  /** Cuántos segundos faltan para que la ventana se renueve. */
  segundosQueFaltan() {
    const pasado = this.#ahora() - this.#desde;
    return Math.max(1, Math.ceil((this.#ventanaMs - pasado) / 1000));
  }
}
