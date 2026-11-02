import { useEffect, useId, useRef, useState } from 'react';
import { IconoFlecha, IconoCheckChico } from './Iconos.jsx';

// Reemplazo del <select>: la lista que abre el navegador no se puede estilar,
// así que acá se dibuja a mano. Sigue el patrón de combobox: el foco se queda
// en el botón y la opción activa se señala con aria-activedescendant.
export default function Desplegable({ valor, opciones, onCambiar, etiqueta, className = '' }) {
  const [abierto, setAbierto] = useState(false);
  const [resaltada, setResaltada] = useState(0);
  const caja = useRef(null);
  const id = useId();

  const elegida = opciones.find((o) => o.valor === valor) ?? opciones[0];
  const posicionActual = Math.max(
    opciones.findIndex((o) => o.valor === valor),
    0
  );

  // Cerrar al tocar afuera
  useEffect(() => {
    if (!abierto) return;
    function afuera(e) {
      if (!caja.current?.contains(e.target)) setAbierto(false);
    }
    document.addEventListener('mousedown', afuera);
    return () => document.removeEventListener('mousedown', afuera);
  }, [abierto]);

  function abrir() {
    setResaltada(posicionActual);
    setAbierto(true);
  }

  function elegir(opcion) {
    onCambiar(opcion.valor);
    setAbierto(false);
  }

  function alTeclado(e) {
    if (!abierto) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        abrir();
      }
      return;
    }

    if (e.key === 'Escape' || e.key === 'Tab') {
      setAbierto(false);
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setResaltada((i) => Math.min(i + 1, opciones.length - 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setResaltada((i) => Math.max(i - 1, 0));
    }
    if (e.key === 'Home') {
      e.preventDefault();
      setResaltada(0);
    }
    if (e.key === 'End') {
      e.preventDefault();
      setResaltada(opciones.length - 1);
    }
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      elegir(opciones[resaltada]);
    }
  }

  return (
    <div className={`desplegable ${className}`.trim()} ref={caja}>
      <button
        type="button"
        className={abierto ? 'desplegable-boton abierto' : 'desplegable-boton'}
        onClick={() => (abierto ? setAbierto(false) : abrir())}
        onKeyDown={alTeclado}
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-controls={`${id}-lista`}
        aria-activedescendant={abierto ? `${id}-${resaltada}` : undefined}
        aria-label={etiqueta}
      >
        <span>{elegida?.nombre}</span>
        <IconoFlecha width={15} height={15} />
      </button>

      {abierto && (
        <ul className="desplegable-lista" id={`${id}-lista`} role="listbox" aria-label={etiqueta}>
          {opciones.map((opcion, i) => (
            <li
              key={opcion.valor}
              id={`${id}-${i}`}
              role="option"
              aria-selected={opcion.valor === valor}
              className={[
                'desplegable-opcion',
                opcion.valor === valor ? 'elegida' : '',
                i === resaltada ? 'resaltada' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => elegir(opcion)}
              onMouseEnter={() => setResaltada(i)}
            >
              <span>{opcion.nombre}</span>
              {opcion.valor === valor && <IconoCheckChico width={14} height={14} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
