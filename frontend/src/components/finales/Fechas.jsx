import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Desplegable from '../Desplegable.jsx';
import FormularioMesa from './FormularioMesa.jsx';
import {
  IconoAdvertencia,
  IconoCalendario,
  IconoCerrar,
  IconoLapiz,
  IconoMas,
  IconoNotas,
  IconoPersonas,
  IconoReloj,
  IconoUbicacion,
  IconoUsuario,
} from '../Iconos.jsx';
import { cancelarMesa } from '../../services/api.js';
import { hace, fechaConDia } from '../../services/fechas.js';
import { avisar } from '../../services/avisos.js';
import { EstadoMesa, NombreMateria, Ventana, horario, partesFecha } from './comun.jsx';

const vistas = [
  { id: 'proximas', nombre: 'Próximas', cumple: (m) => !m.tomada && m.estado !== 'cancelada' },
  { id: 'tomadas', nombre: 'Ya tomadas', cumple: (m) => m.tomada && m.estado !== 'cancelada' },
  { id: 'canceladas', nombre: 'Canceladas', cumple: (m) => m.estado === 'cancelada' },
  { id: 'todas', nombre: 'Todas', cumple: () => true },
];

export default function Fechas({ opciones, mesas, onCambio }) {
  const [vista, setVista] = useState('proximas');
  const [materia, setMateria] = useState('');
  // null: cerrado · 'nueva' · o la mesa que se edita
  const [editando, setEditando] = useState(null);
  const [cancelando, setCancelando] = useState(null);

  const materias = useMemo(() => {
    const porId = new Map();
    for (const m of opciones.materias) porId.set(m.id, m);
    for (const mesa of mesas) porId.set(mesa.materia.id, mesa.materia);
    return [
      { valor: '', nombre: 'Todas las materias' },
      ...[...porId.values()].map((m) => ({ valor: String(m.id), nombre: `${m.codigo} · ${m.nombre}` })),
    ];
  }, [opciones, mesas]);

  const deLaMateria = mesas.filter((m) => !materia || String(m.materia.id) === materia);
  const elegida = vistas.find((v) => v.id === vista);
  const visibles = deLaMateria.filter(elegida.cumple);

  return (
    <section className="finales-seccion">
      <div className="finales-filtros">
        <div className="biblioteca-categorias" role="group" aria-label="Qué mesas ver">
          {vistas.map((v) => (
            <button
              key={v.id}
              type="button"
              className={vista === v.id ? 'chip activo' : 'chip'}
              onClick={() => setVista(v.id)}
              aria-pressed={vista === v.id}
            >
              {v.nombre}
              <small>{deLaMateria.filter(v.cumple).length}</small>
            </button>
          ))}
        </div>
        <Desplegable valor={materia} opciones={materias} onCambiar={setMateria} etiqueta="Materia" />
        {opciones.puedeCrear && (
          <button type="button" className="boton-principal finales-nueva" onClick={() => setEditando('nueva')}>
            <IconoMas />
            Nueva mesa
          </button>
        )}
      </div>

      {visibles.length === 0 ? (
        <div className="vacio">
          <IconoCalendario width={34} height={34} />
          <h3>{vista === 'proximas' ? 'No hay mesas programadas' : 'No hay mesas en esta vista'}</h3>
          <p className="texto-suave">
            {opciones.puedeCrear
              ? 'Las mesas que crees para tus materias aparecen acá.'
              : 'Cuando te sumen a un tribunal, la mesa aparece acá.'}
          </p>
          {opciones.puedeCrear && vista === 'proximas' && (
            <button type="button" className="boton-principal" onClick={() => setEditando('nueva')}>
              <IconoMas />
              Crear una mesa
            </button>
          )}
        </div>
      ) : (
        <div className="finales-mesas">
          {visibles.map((mesa, i) => (
            <TarjetaMesa
              key={mesa.id}
              mesa={mesa}
              indice={i}
              onEditar={() => setEditando(mesa)}
              onCancelar={() => setCancelando(mesa)}
            />
          ))}
        </div>
      )}

      {editando && (
        <FormularioMesa
          opciones={opciones}
          mesa={editando === 'nueva' ? null : editando}
          onCerrar={() => setEditando(null)}
          onListo={(texto) => {
            setEditando(null);
            avisar(texto);
            onCambio();
          }}
        />
      )}

      {cancelando && (
        <CancelarMesa
          mesa={cancelando}
          onCerrar={() => setCancelando(null)}
          onListo={() => {
            setCancelando(null);
            avisar(
              cancelando.inscriptos > 0
                ? `Mesa cancelada. Se les avisó a ${cancelando.inscriptos} inscriptos por mensaje.`
                : 'Mesa cancelada.'
            );
            onCambio();
          }}
        />
      )}
    </section>
  );
}

function TarjetaMesa({ mesa, indice, onEditar, onCancelar }) {
  const [verCambios, setVerCambios] = useState(false);
  const { dia, mes, semana } = partesFecha(mesa.fecha);
  const lleno = mesa.cupo ? Math.min(100, Math.round((mesa.inscriptos / mesa.cupo) * 100)) : null;
  const cancelada = mesa.estado === 'cancelada';

  return (
    <article
      className={cancelada ? 'finales-mesa cancelada' : 'finales-mesa'}
      style={{
        '--retraso': `${Math.min(indice, 12) * 35}ms`,
        '--color-materia': mesa.materia.color || 'var(--oscuro)',
      }}
    >
      <div className="finales-mesa-cuerpo">
        {/* Taco de almanaque */}
        <div className="finales-taco" aria-hidden="true">
          <small>{semana}</small>
          <strong>{dia}</strong>
          <small>{mes}</small>
        </div>

        <div className="finales-mesa-datos">
          <NombreMateria materia={mesa.materia} />
          <h3>{mesa.llamado}</h3>
          <ul className="finales-detalles">
            <li>
              <IconoReloj /> {fechaConDia(mesa.fecha)}, {horario(mesa)}
            </li>
            <li>
              <IconoUbicacion /> {mesa.lugar} · {mesa.modalidad} · {mesa.instancia}
            </li>
            <li>
              <IconoUsuario width={16} height={16} /> Tribunal: {mesa.tribunal.map((t) => t.nombre).join(', ')}
            </li>
          </ul>
        </div>
      </div>

      {cancelada ? (
        <p className="finales-motivo">
          <IconoAdvertencia width={16} height={16} />
          {mesa.motivoCancelacion}
        </p>
      ) : (
        <div className="finales-cupo">
          <div className="finales-cupo-texto">
            <EstadoMesa mesa={mesa} />
            <span>
              <strong>{mesa.inscriptos}</strong>
              {mesa.cupo ? ` de ${mesa.cupo} lugares` : ' inscriptos · sin cupo'}
            </span>
          </div>
          {lleno !== null && (
            <span className="barra-pista" aria-hidden="true">
              <span className={`barra-relleno finales-cupo-relleno${lleno >= 100 ? ' lleno' : ''}`} style={{ width: `${lleno}%` }} />
            </span>
          )}
        </div>
      )}

      <div className="finales-mesa-acciones">
        <Link to={`/finales/inscriptos?mesa=${mesa.id}`} className="boton-suave">
          <IconoPersonas width={16} height={16} />
          Inscriptos
        </Link>
        {mesa.tomada && !cancelada && (
          <Link to={`/finales/resultados?mesa=${mesa.id}`} className="boton-suave">
            <IconoNotas width={16} height={16} />
            {mesa.puedeCalificar ? 'Cargar notas' : 'Ver notas'}
          </Link>
        )}
        {mesa.puedeEditar && (
          <>
            <button type="button" className="boton-suave" onClick={onEditar}>
              <IconoLapiz />
              Modificar
            </button>
            <button type="button" className="boton-suave peligro" onClick={onCancelar}>
              <IconoCerrar width={16} height={16} />
              Cancelar
            </button>
          </>
        )}
        {mesa.historial?.length > 0 && (
          <button
            type="button"
            className="finales-cambios-boton"
            onClick={() => setVerCambios((v) => !v)}
            aria-expanded={verCambios}
          >
            {verCambios ? 'Ocultar cambios' : `Cambios (${mesa.historial.length})`}
          </button>
        )}
      </div>

      {verCambios && (
        <ol className="finales-cambios">
          {[...mesa.historial].reverse().map((h, i) => (
            <li key={i}>
              <strong>{h.accion}</strong> · {h.por} · {hace(h.fecha)}
              {h.detalle && <p>{h.detalle}</p>}
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}

function CancelarMesa({ mesa, onCerrar, onListo }) {
  const [motivo, setMotivo] = useState('');
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function confirmar() {
    if (!motivo.trim()) {
      setError('Contá el motivo: les llega a los inscriptos.');
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await cancelarMesa(mesa.id, motivo.trim());
      onListo();
    } catch (e) {
      setError(e.message);
      setEnviando(false);
    }
  }

  return (
    <Ventana
      titulo="Cancelar la mesa"
      bajada={`${mesa.materia.nombre} · ${mesa.llamado} · ${fechaConDia(mesa.fecha)}`}
      onCerrar={onCerrar}
      ocupado={enviando}
      onEnviar={confirmar}
      className="finales-ventana-chica"
    >
      <p className="finales-advertencia">
        <IconoAdvertencia width={18} height={18} />
        {mesa.inscriptos > 0
          ? `Hay ${mesa.inscriptos} ${mesa.inscriptos === 1 ? 'inscripto' : 'inscriptos'}. A cada uno le llega un mensaje con el motivo.`
          : 'Todavía no hay inscriptos. La mesa queda en el listado como cancelada.'}{' '}
        No se puede deshacer.
      </p>

      <div className="aporte-campos">
        <label className="ancho-completo">
          <span>Motivo *</span>
          <textarea
            rows={3}
            value={motivo}
            maxLength={500}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Por ejemplo: se pasa al turno de diciembre por la jornada institucional."
            autoFocus
          />
        </label>
      </div>

      {error && (
        <p className="error aporte-error">
          <IconoAdvertencia width={16} height={16} />
          {error}
        </p>
      )}

      <div className="aporte-pie">
        <button type="button" className="boton-suave" onClick={onCerrar} disabled={enviando}>
          Volver
        </button>
        <button type="submit" className="boton-principal peligroso" disabled={enviando}>
          {enviando ? 'Cancelando…' : 'Cancelar la mesa'}
        </button>
      </div>
    </Ventana>
  );
}
