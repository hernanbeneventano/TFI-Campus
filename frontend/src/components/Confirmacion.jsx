// Cartel de reconfirmación para las acciones que dejan rastro.
//
// Inscribirse a un final o a una materia no se deshace solo: queda un lugar
// ocupado, la cátedra cuenta con vos y, pasado el período, ya no hay vuelta
// atrás. Un clic de más antes de eso vale la pena. Lo que no lleva cartel es
// lo que se arregla con otro clic —marcar un favorito, abrir una carpeta—,
// porque preguntar por todo enseña a confirmar sin leer.
//
// Mismo comportamiento que el visor de Novedades: se cierra con Escape, con
// clic afuera y con Cancelar, y mientras está abierto la página de atrás no
// se mueve.

import { useEffect, useRef } from 'react';
import { IconoAdvertencia, IconoCerrar } from './Iconos.jsx';

export default function Confirmacion({
  titulo,
  mensaje,
  // Pares { etiqueta, valor } con lo que se está por confirmar: la fecha de
  // la mesa, el horario… Que el dato esté a la vista evita confirmar sobre
  // la mesa equivocada.
  detalles = [],
  textoConfirmar = 'Confirmar',
  peligro = false,
  trabajando = false,
  onConfirmar,
  onCancelar,
}) {
  const aceptar = useRef(null);

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !trabajando) onCancelar();
    }
    window.addEventListener('keydown', alTeclado);

    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // El foco arranca en el botón de confirmar, que es a lo que se vino
    aceptar.current?.focus();

    return () => {
      window.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
  }, [onCancelar, trabajando]);

  return (
    <div
      className="confirmacion-fondo"
      // Clic afuera para cerrar; adentro no, de ahí la comparación
      onClick={(e) => e.target === e.currentTarget && !trabajando && onCancelar()}
      role="presentation"
    >
      <div
        className={peligro ? 'confirmacion peligro' : 'confirmacion'}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirmacion-titulo"
        aria-describedby="confirmacion-mensaje"
      >
        <button
          type="button"
          className="confirmacion-cerrar"
          onClick={onCancelar}
          disabled={trabajando}
          aria-label="Cancelar"
          title="Cancelar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        <span className="confirmacion-icono" aria-hidden="true">
          <IconoAdvertencia width={26} height={26} />
        </span>

        <h2 id="confirmacion-titulo">{titulo}</h2>
        <p id="confirmacion-mensaje">{mensaje}</p>

        {detalles.length > 0 && (
          <dl className="confirmacion-detalles">
            {detalles.map(({ etiqueta, valor }) => (
              <div key={etiqueta}>
                <dt>{etiqueta}</dt>
                <dd>{valor}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="confirmacion-botones">
          <button
            type="button"
            className="boton-suave"
            onClick={onCancelar}
            disabled={trabajando}
          >
            Cancelar
          </button>
          <button
            ref={aceptar}
            type="button"
            className={peligro ? 'boton-principal peligroso' : 'boton-principal'}
            onClick={onConfirmar}
            disabled={trabajando}
          >
            {trabajando ? 'Un momento…' : textoConfirmar}
          </button>
        </div>
      </div>
    </div>
  );
}
