import {
  IconoFlecha,
  IconoCarpeta,
  IconoPagina,
  IconoArchivo,
  IconoVideo,
  IconoTarea,
  IconoTablero,
  IconoReloj,
} from './Iconos.jsx';
import BarraProgreso from './BarraProgreso.jsx';
import { esMarcable, calcularAvance } from '../services/progreso.js';

const DIA = 24 * 60 * 60 * 1000;

// Ícono según el tipo de elemento (los videos llevan uno propio)
function iconoDe(item) {
  if (item.tipo === 'pagina') return IconoPagina;
  if (item.tipo === 'tarea') return IconoTarea;
  if (item.tipo === 'tablero') return IconoTablero;
  return item.formato === 'Video' ? IconoVideo : IconoArchivo;
}

function textoPlazo(fechaIso) {
  const dias = Math.round((new Date(fechaIso) - new Date()) / DIA);
  if (dias < 0) return dias === -1 ? 'Venció ayer' : `Venció hace ${-dias} días`;
  if (dias === 0) return 'Vence hoy';
  if (dias === 1) return 'Vence mañana';
  return `Vence en ${dias} días`;
}

// Debajo del título: datos del archivo, o el estado de la tarea
function Detalle({ item }) {
  if (item.tipo === 'tarea') {
    if (item.entregada) {
      return <small className="item-estado entregada">Entregada</small>;
    }
    const atrasada = new Date(item.fechaLimite) < new Date();
    return (
      <small className={atrasada ? 'item-estado atrasada' : 'item-estado'}>
        <IconoReloj />
        {textoPlazo(item.fechaLimite)}
      </small>
    );
  }

  if (item.tipo === 'archivo') {
    return (
      <small className="item-estado">
        {item.formato} · {item.tamano}
      </small>
    );
  }

  return null;
}

// Una carpeta del módulo. Se abre y se cierra mostrando los elementos de adentro,
// y en la cabecera muestra cuánto de su material marcó el alumno.
export default function CarpetaModulo({
  carpeta,
  abierta,
  onAlternar,
  onAbrirItem,
  completados,
  onCompletar,
  color,
}) {
  const avance = calcularAvance(carpeta.items, completados);

  return (
    <section className={abierta ? 'carpeta abierta' : 'carpeta'}>
      <button type="button" className="carpeta-cabecera" onClick={onAlternar} aria-expanded={abierta}>
        <span className="carpeta-flecha">
          <IconoFlecha />
        </span>
        <span className="carpeta-icono" style={{ color }}>
          <IconoCarpeta />
        </span>
        <span className="carpeta-texto">
          <strong>{carpeta.titulo}</strong>
          {carpeta.descripcion && <small>{carpeta.descripcion}</small>}
        </span>

        {avance.total > 0 ? (
          <BarraProgreso avance={avance} />
        ) : (
          <small className="carpeta-cantidad">
            {carpeta.items.length} {carpeta.items.length === 1 ? 'elemento' : 'elementos'}
          </small>
        )}
      </button>

      {/* Los elementos quedan siempre montados para que la carpeta se pueda
          animar al abrir y al cerrar; de la altura se encarga el CSS. */}
      <div className="carpeta-panel">
        <div className="carpeta-panel-interior">
          <ul className="carpeta-items">
            {carpeta.items.map((item) => {
              const Icono = iconoDe(item);
              const completado = completados.includes(item.id);
              return (
                <li key={item.id} className={completado ? 'item-fila completado' : 'item-fila'}>
                  {esMarcable(item) ? (
                    <input
                      type="checkbox"
                      className="item-check"
                      checked={completado}
                      tabIndex={abierta ? 0 : -1}
                      onChange={() => onCompletar(item.id)}
                      aria-label={`Marcar «${item.titulo}» como completado`}
                    />
                  ) : (
                    <span className="item-check-vacio" aria-hidden="true" />
                  )}

                  <button
                    type="button"
                    className="item"
                    tabIndex={abierta ? 0 : -1}
                    onClick={() => onAbrirItem(carpeta, item)}
                  >
                    <span className="item-icono" style={{ color }}>
                      <Icono />
                    </span>
                    <span className="item-texto">
                      <strong>{item.titulo}</strong>
                      <Detalle item={item} />
                    </span>
                    <span className="item-flecha">
                      <IconoFlecha />
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}
