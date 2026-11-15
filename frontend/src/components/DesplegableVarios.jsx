import { useEffect, useId, useRef, useState } from 'react';
import { IconoFlecha, IconoCheckChico } from './Iconos.jsx';

// El mismo desplegable de siempre, pero eligiendo varias cosas a la vez.
//
// Se diferencia del de una sola opción en dos cosas: la lista **no se cierra**
// al elegir —se está armando una selección, no tomando una decisión— y arriba
// de todo hay una opción que las borra todas y vuelve a "todas".
//
// Comparte las clases de `Desplegable` a propósito: en la barra de filtros
// tiene que verse como uno más, no como otro control.
export default function DesplegableVarios({
  valores,
  opciones,
  onCambiar,
  etiqueta,
  textoTodas = 'Todas',
  className = '',
}) {
  const [abierto, setAbierto] = useState(false);
  const [resaltada, setResaltada] = useState(0);
  const caja = useRef(null);
  const id = useId();

  const elegidas = opciones.filter((o) => valores.includes(o.valor));

  // Qué dice el botón: cuántas hay elegidas, o la única, o todas
  const resumen =
    elegidas.length === 0
      ? textoTodas
      : elegidas.length === 1
        ? elegidas[0].nombre
        : `${elegidas.length} elegidas`;

  useEffect(() => {
    if (!abierto) return;
    function afuera(e) {
      if (!caja.current?.contains(e.target)) setAbierto(false);
    }
    document.addEventListener('mousedown', afuera);
    return () => document.removeEventListener('mousedown', afuera);
  }, [abierto]);

  function alternar(opcion) {
    onCambiar(
      valores.includes(opcion.valor)
        ? valores.filter((v) => v !== opcion.valor)
        : [...valores, opcion.valor]
    );
  }

  function alTeclado(e) {
    if (!abierto) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        setResaltada(0);
        setAbierto(true);
      }
      return;
    }

    if (e.key === 'Escape' || e.key === 'Tab') {
      setAbierto(false);
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setResaltada((i) => Math.min(i + 1, opciones.length));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setResaltada((i) => Math.max(i - 1, 0));
    }
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      // La 0 es "todas"; de ahí en más, una opción cada una
      if (resaltada === 0) onCambiar([]);
      else alternar(opciones[resaltada - 1]);
    }
  }

  return (
    <div className={`desplegable ${className}`.trim()} ref={caja}>
      <button
        type="button"
        className={abierto ? 'desplegable-boton abierto' : 'desplegable-boton'}
        onClick={() => setAbierto((a) => !a)}
        onKeyDown={alTeclado}
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-controls={`${id}-lista`}
        aria-label={etiqueta}
      >
        <span>{resumen}</span>
        {elegidas.length > 1 && <small className="desplegable-cuenta">{elegidas.length}</small>}
        <IconoFlecha width={15} height={15} />
      </button>

      {abierto && (
        <ul
          className="desplegable-lista ancha"
          id={`${id}-lista`}
          role="listbox"
          aria-multiselectable="true"
          aria-label={etiqueta}
        >
          <li
            id={`${id}-0`}
            role="option"
            aria-selected={valores.length === 0}
            className={[
              'desplegable-opcion',
              'desplegable-todas',
              valores.length === 0 ? 'elegida' : '',
              resaltada === 0 ? 'resaltada' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            onClick={() => onCambiar([])}
            onMouseEnter={() => setResaltada(0)}
          >
            <span>{textoTodas}</span>
            {valores.length === 0 && <IconoCheckChico width={14} height={14} />}
          </li>

          {opciones.map((opcion, i) => {
            const puesta = valores.includes(opcion.valor);
            return (
              <li
                key={opcion.valor}
                id={`${id}-${i + 1}`}
                role="option"
                aria-selected={puesta}
                className={[
                  'desplegable-opcion',
                  puesta ? 'elegida' : '',
                  i + 1 === resaltada ? 'resaltada' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onClick={() => alternar(opcion)}
                onMouseEnter={() => setResaltada(i + 1)}
              >
                {/* La casilla se dibuja a mano, como los checks de los
                    recursos de un módulo: la del navegador no se redondea. */}
                <span className={puesta ? 'casilla puesta' : 'casilla'} aria-hidden="true">
                  {puesta && <IconoCheckChico width={11} height={11} />}
                </span>
                <span className="desplegable-nombre">{opcion.nombre}</span>
                {opcion.detalle != null && (
                  <small className="desplegable-detalle">{opcion.detalle}</small>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
