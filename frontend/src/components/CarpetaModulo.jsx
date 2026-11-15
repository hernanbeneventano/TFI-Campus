import {
  IconoFlecha,
  IconoCarpeta,
  IconoPagina,
  IconoArchivo,
  IconoVideo,
  IconoTarea,
  IconoTablero,
  IconoReloj,
  IconoLapiz,
  IconoPapelera,
  IconoMas,
  IconoPersonas,
  IconoCandado,
  IconoArrastrar,
} from './Iconos.jsx';
import { useRef } from 'react';
import BarraProgreso from './BarraProgreso.jsx';
import useArrastre from '../hooks/useArrastre.js';
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
    // El docente puede cerrar o reabrir la entrega a mano, y eso pesa más
    // que la fecha: hay que decirlo, porque si no el plazo que se ve miente.
    if (item.cerrada === true) {
      return (
        <small className="item-estado cerrada">
          <IconoCandado width={13} height={13} />
          Entrega cerrada
        </small>
      );
    }
    if (item.cerrada === false) {
      return <small className="item-estado reabierta">Entrega reabierta</small>;
    }
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

/**
 * El asa para arrastrar, más editar y borrar.
 *
 * Se reordena arrastrando con el mouse, que es lo cómodo. Pero arrastrar no
 * se puede hacer sin mouse, así que el asa también responde a las flechas del
 * teclado cuando tiene el foco: sin eso, reordenar quedaría fuera del alcance
 * de quien navega con teclado.
 */
function Acciones({ etiqueta, onSubir, onBajar, onEditar, onBorrar, tabIndex, arrastrando }) {
  function alTeclado(e) {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      onSubir();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      onBajar();
    }
  }

  return (
    <span className="acciones-editor">
      {/* El arrastre se toma de la caja entera (ver `hooks/useArrastre.js`);
          esto marca que se puede mover y da la forma de hacerlo con teclado,
          que arrastrando no se puede. */}
      <span
        className={arrastrando ? 'asa arrastrando' : 'asa'}
        role="button"
        tabIndex={tabIndex ?? 0}
        onKeyDown={alTeclado}
        title={`Arrastrá la sección para moverla, o usá las flechas del teclado`}
        aria-label={`Reordenar ${etiqueta}`}
      >
        <IconoArrastrar width={15} height={15} />
      </span>

      {onEditar && (
        <button
          type="button"
          onClick={onEditar}
          tabIndex={tabIndex}
          title={`Editar ${etiqueta}`}
          aria-label={`Editar ${etiqueta}`}
        >
          <IconoLapiz width={14} height={14} />
        </button>
      )}
      <button
        type="button"
        className="peligro"
        onClick={onBorrar}
        tabIndex={tabIndex}
        title={`Borrar ${etiqueta}`}
        aria-label={`Borrar ${etiqueta}`}
      >
        <IconoPapelera width={14} height={14} />
      </button>
    </span>
  );
}

/**
 * Una carpeta del módulo.
 *
 * Tiene dos caras según quién mire:
 *
 * - **Alumno**: cada recurso lleva su check y la cabecera muestra cuánto de
 *   ese material marcó como visto.
 * - **Docente**: no hay checks ni avance propio —el material lo subió él—,
 *   sino cuántos de sus alumnos completaron la sección. Con el modo editor
 *   encendido aparecen además los botones para ordenar, editar y borrar.
 */
export default function CarpetaModulo({
  carpeta,
  abierta,
  onAlternar,
  onAbrirItem,
  completados,
  onCompletar,
  // --- docente ---
  gestionando = false,
  editando = false,
  seguimiento = null,
  primera = false,
  ultima = false,
  onEditarSeccion,
  onBorrarSeccion,
  onMoverSeccion,
  onAgregarElemento,
  onEditarElemento,
  onBorrarElemento,
  onMoverElemento,
  onAlternarEntrega,
  onVerEntregas,
  // El arrastre de las secciones lo maneja la pantalla, que es la dueña de
  // la lista; el de los elementos, esta carpeta.
  indice = 0,
  seMueve = false,
  estiloArrastre,
  onTomar,
}) {
  const avance = calcularAvance(carpeta.items, completados);
  const alcanzable = abierta ? 0 : -1;

  const caja = useRef(null);
  const filas = useRef([]);

  // Los elementos de esta carpeta se reordenan con su propio arrastre: son
  // una lista aparte de la de secciones.
  const items = useArrastre({
    activo: editando,
    alSoltar: (desde, hasta) =>
      onMoverElemento(carpeta, carpeta.items[desde], { posicion: hasta }),
  });

  const clases = ['carpeta'];
  if (abierta) clases.push('abierta');
  if (seMueve) clases.push('se-arrastra');

  return (
    <section
      ref={caja}
      className={clases.join(' ')}
      style={estiloArrastre}
      onPointerDown={
        editando && onTomar ? (e) => onTomar(indice, caja.current, e) : undefined
      }
    >
      <div className="carpeta-cabecera">
        <button
          type="button"
          className="carpeta-abrir"
          onClick={onAlternar}
          aria-expanded={abierta}
        >
          <span className="carpeta-flecha">
            <IconoFlecha />
          </span>
          <span className="carpeta-icono">
            <IconoCarpeta />
          </span>
          <span className="carpeta-texto">
            <strong>{carpeta.titulo}</strong>
            {carpeta.descripcion && <small>{carpeta.descripcion}</small>}
          </span>
        </button>

        {gestionando ? (
          <>
            {/* Al docente no le sirve su propio avance: le sirve cuántos de
                sus alumnos completaron esta sección. */}
            {seguimiento && seguimiento.alumnos > 0 ? (
              // Clickeable: el número solo no sirve para corregir. Adentro
              // está quién cumplió, qué entregó cada uno y qué falta.
              <span
                className="carpeta-curso"
                role="button"
                tabIndex={0}
                title={`Ver las entregas: ${seguimiento.completaron} de ${seguimiento.alumnos} alumnos completaron esta sección`}
                onClick={(e) => {
                  e.stopPropagation();
                  onVerEntregas(carpeta);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    e.stopPropagation();
                    onVerEntregas(carpeta);
                  }
                }}
              >
                <IconoPersonas width={14} height={14} />
                <strong>{seguimiento.porcentaje}%</strong>
                <small>
                  {seguimiento.completaron} de {seguimiento.alumnos}
                </small>
              </span>
            ) : (
              <small className="carpeta-cantidad">
                {carpeta.items.length} {carpeta.items.length === 1 ? 'elemento' : 'elementos'}
              </small>
            )}

            {editando && (
              <Acciones
                etiqueta="la sección"
                arrastrando={seMueve}
                onSubir={() => !primera && onMoverSeccion(carpeta, { hacia: 'arriba' })}
                onBajar={() => !ultima && onMoverSeccion(carpeta, { hacia: 'abajo' })}
                onEditar={() => onEditarSeccion(carpeta)}
                onBorrar={() => onBorrarSeccion(carpeta)}
              />
            )}
          </>
        ) : avance.total > 0 ? (
          <BarraProgreso avance={avance} />
        ) : (
          <small className="carpeta-cantidad">
            {carpeta.items.length} {carpeta.items.length === 1 ? 'elemento' : 'elementos'}
          </small>
        )}
      </div>

      {/* Los elementos quedan siempre montados para que la carpeta se pueda
          animar al abrir y al cerrar; de la altura se encarga el CSS. */}
      <div className="carpeta-panel">
        <div className="carpeta-panel-interior">
          <ul className={items.arrastrando ? 'carpeta-items moviendo' : 'carpeta-items'}>
            {carpeta.items.map((item, i) => {
              const Icono = iconoDe(item);
              const completado = completados.includes(item.id);
              return (
                <li
                  key={item.id}
                  ref={(nodo) => (filas.current[i] = nodo)}
                  className={[
                    'item-fila',
                    completado ? 'completado' : '',
                    items.esLaMovida(i) ? 'se-arrastra' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  style={items.estiloDe(i)}
                  onPointerDown={
                    editando ? (e) => items.tomar(i, filas.current[i], e) : undefined
                  }
                >
                  {gestionando ? (
                    <span className="item-check-vacio" aria-hidden="true" />
                  ) : esMarcable(item) ? (
                    <input
                      type="checkbox"
                      className="item-check"
                      checked={completado}
                      tabIndex={alcanzable}
                      onChange={() => onCompletar(item.id)}
                      aria-label={`Marcar «${item.titulo}» como completado`}
                    />
                  ) : (
                    <span className="item-check-vacio" aria-hidden="true" />
                  )}

                  <button
                    type="button"
                    className="item"
                    tabIndex={alcanzable}
                    onClick={() => onAbrirItem(carpeta, item)}
                  >
                    <span className="item-icono">
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

                  {editando && (
                    <>
                      {item.tipo === 'tarea' && (
                        // Muestra en qué estado está, no qué va a hacer:
                        // abierto en verde, cerrado en rojo. Lo que hace el
                        // clic va en la ayuda, porque el dato que se consulta
                        // de un vistazo es si la entrega sigue abierta.
                        <button
                          type="button"
                          className={
                            item.cerrada === true
                              ? 'item-entrega cerrada'
                              : 'item-entrega abierta'
                          }
                          tabIndex={alcanzable}
                          onClick={() => onAlternarEntrega(item)}
                          title={
                            item.cerrada === true
                              ? 'La entrega está cerrada. Tocá para reabrirla.'
                              : 'La entrega está abierta. Tocá para cerrarla.'
                          }
                        >
                          <span className="punto" aria-hidden="true" />
                          {item.cerrada === true ? 'Cerrado' : 'Abierto'}
                        </button>
                      )}
                      <Acciones
                        etiqueta="el elemento"
                        tabIndex={alcanzable}
                        arrastrando={items.esLaMovida(i)}
                        onSubir={() =>
                          i > 0 && onMoverElemento(carpeta, item, { hacia: 'arriba' })
                        }
                        onBajar={() =>
                          i < carpeta.items.length - 1 &&
                          onMoverElemento(carpeta, item, { hacia: 'abajo' })
                        }
                        onEditar={() => onEditarElemento(carpeta, item)}
                        onBorrar={() => onBorrarElemento(carpeta, item)}
                      />
                    </>
                  )}
                </li>
              );
            })}

            {editando && (
              <li className="item-fila agregar">
                <button
                  type="button"
                  className="boton-agregar"
                  tabIndex={alcanzable}
                  onClick={() => onAgregarElemento(carpeta)}
                >
                  <IconoMas width={16} height={16} />
                  Agregar a esta sección
                </button>
              </li>
            )}

            {carpeta.items.length === 0 && !editando && (
              <li className="item-fila">
                <span className="item-check-vacio" aria-hidden="true" />
                <p className="texto-suave carpeta-vacia">Esta sección todavía está vacía.</p>
              </li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
