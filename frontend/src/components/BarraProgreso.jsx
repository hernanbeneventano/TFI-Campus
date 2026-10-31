import { nivel } from '../services/progreso.js';
import { IconoAdvertencia, IconoCheckChico } from './Iconos.jsx';

// Barra de avance. El dato va escrito arriba, así que la barra es decorativa.
// El texto acompaña el color de la barra: mientras falte material lleva un
// triángulo de advertencia, y al llegar al verde pasa a un check.
export default function BarraProgreso({ avance, detalle = true }) {
  const estado = nivel(avance.porcentaje);
  const Icono = estado === 'alto' ? IconoCheckChico : IconoAdvertencia;

  return (
    <span className="carpeta-progreso">
      <small className={`estado ${estado}`}>
        <Icono />
        {detalle && (
          <span className="detalle">
            {avance.hechos} de {avance.total} ·{' '}
          </span>
        )}
        {avance.porcentaje}%
      </small>
      <span className="barra-pista" aria-hidden="true">
        <span className={`barra-relleno ${estado}`} style={{ width: `${avance.porcentaje}%` }} />
      </span>
    </span>
  );
}
