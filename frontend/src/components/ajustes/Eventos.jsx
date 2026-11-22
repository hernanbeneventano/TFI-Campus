/**
 * Los eventos del calendario académico.
 *
 * Lo que pasa en el campus y no es una clase, una entrega ni un examen de
 * cátedra: una jornada, un acto, una suspensión de actividades. Estaban en el
 * calendario de todos pero no había forma de cargarlos, así que la colección
 * iba a quedar vacía para siempre y uno de los cuatro tipos del calendario no
 * se podía usar.
 *
 * Los carga quien administra; quien supervisa los ve.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  obtenerEventos,
  crearEvento,
  editarEvento,
  borrarEvento,
} from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import { fechaConDia } from '../../services/fechas.js';
import Confirmacion from '../Confirmacion.jsx';
import {
  IconoCalendario,
  IconoMas,
  IconoLapiz,
  IconoPapelera,
  IconoUbicacion,
  IconoReloj,
} from '../Iconos.jsx';

const NOMBRE_TIPO = { evento: 'Evento de la facultad', examen: 'Examen' };

function paraElCampo(iso) {
  if (!iso) return '';
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return '';
  const mes = String(f.getMonth() + 1).padStart(2, '0');
  const dia = String(f.getDate()).padStart(2, '0');
  return `${f.getFullYear()}-${mes}-${dia}`;
}

export default function Eventos() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [formulario, setFormulario] = useState(null);
  const [aBorrar, setABorrar] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  const traer = () =>
    obtenerEventos()
      .then(setDatos)
      .catch((e) => setError(e.message));

  useEffect(() => {
    traer();
  }, []);

  // Los que todavía no pasaron van arriba: son los que importan. Los pasados
  // se siguen mostrando porque la facultad registra lo que hizo.
  const { proximos, pasados } = useMemo(() => {
    const ahora = new Date();
    const todos = datos?.eventos ?? [];
    return {
      proximos: todos.filter((e) => new Date(e.fecha) >= ahora).reverse(),
      pasados: todos.filter((e) => new Date(e.fecha) < ahora),
    };
  }, [datos]);

  async function accionar(accion, exito) {
    setTrabajando(true);
    try {
      await accion();
      await traer();
      setFormulario(null);
      setABorrar(null);
      avisar(exito);
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  return (
    <section className="bloque-ajustes">
      <h3>
        <IconoCalendario width={17} height={17} />
        Eventos del calendario
      </h3>

      <p className="texto-suave eventos-bajada">
        Jornadas, actos y suspensiones de actividad. Aparecen en el calendario de todo el campus.
      </p>

      {datos.puedeEditar && !formulario && (
        <div className="editor-botones">
          <button
            type="button"
            className="boton-principal"
            onClick={() => setFormulario({ evento: null })}
          >
            <IconoMas width={16} height={16} />
            Agregar un evento
          </button>
        </div>
      )}

      {formulario && (
        <Formulario
          evento={formulario.evento}
          tipos={datos.tipos}
          trabajando={trabajando}
          onCancelar={() => setFormulario(null)}
          onGuardar={(valores) =>
            accionar(
              () =>
                formulario.evento
                  ? editarEvento(formulario.evento.id, valores)
                  : crearEvento(valores),
              formulario.evento ? 'Evento modificado.' : 'Evento agregado.'
            )
          }
        />
      )}

      {proximos.length === 0 && pasados.length === 0 ? (
        <p className="vacio">
          Todavía no hay eventos cargados. Los que agregues acá aparecen en el calendario de
          todo el campus.
        </p>
      ) : (
        <>
          <Grupo
            titulo="Próximos"
            eventos={proximos}
            puedeEditar={datos.puedeEditar}
            onEditar={(e) => setFormulario({ evento: e })}
            onBorrar={setABorrar}
          />
          <Grupo
            titulo="Ya pasaron"
            eventos={pasados}
            puedeEditar={datos.puedeEditar}
            onEditar={(e) => setFormulario({ evento: e })}
            onBorrar={setABorrar}
          />
        </>
      )}

      {aBorrar && (
        <Confirmacion
          titulo="¿Quitar el evento?"
          mensaje="Deja de aparecer en el calendario del campus. No se puede deshacer."
          detalles={[
            { etiqueta: 'Evento', valor: aBorrar.titulo },
            { etiqueta: 'Fecha', valor: fechaConDia(aBorrar.fecha) },
          ]}
          textoConfirmar="Sí, quitarlo"
          peligro
          trabajando={trabajando}
          onConfirmar={() => accionar(() => borrarEvento(aBorrar.id), 'Evento quitado.')}
          onCancelar={() => setABorrar(null)}
        />
      )}
    </section>
  );
}

function Grupo({ titulo, eventos, puedeEditar, onEditar, onBorrar }) {
  if (eventos.length === 0) return null;
  return (
    <>
      <h4 className="comision-titulo">{titulo}</h4>
      <ul className="catalogo">
        {eventos.map((e) => (
          <li key={e.id} className="fila-catalogo">
            <div className="fila-texto">
              <strong>{e.titulo}</strong>
              <small className="texto-suave">
                {fechaConDia(e.fecha)}
                {e.desde && (
                  <>
                    {' · '}
                    <IconoReloj width={12} height={12} /> {e.desde}
                    {e.hasta ? ` a ${e.hasta}` : ''}
                  </>
                )}
                {e.lugar && (
                  <>
                    {' · '}
                    <IconoUbicacion width={12} height={12} /> {e.lugar}
                  </>
                )}
                {e.curso && ` · ${e.curso}`}
              </small>
            </div>

            <span className={`etiqueta-rol tipo-${e.tipo}`}>
              {NOMBRE_TIPO[e.tipo] ?? e.tipo}
            </span>

            {puedeEditar && (
              <div className="fila-acciones">
                <button type="button" className="boton-suave" onClick={() => onEditar(e)}>
                  <IconoLapiz width={14} height={14} />
                </button>
                <button
                  type="button"
                  className="boton-suave peligro"
                  onClick={() => onBorrar(e)}
                >
                  <IconoPapelera width={14} height={14} />
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}

function Formulario({ evento, tipos, trabajando, onGuardar, onCancelar }) {
  const [v, setV] = useState({
    titulo: evento?.titulo ?? '',
    tipo: evento?.tipo ?? 'evento',
    fecha: paraElCampo(evento?.fecha),
    desde: evento?.desde ?? '',
    hasta: evento?.hasta ?? '',
    lugar: evento?.lugar ?? '',
  });
  const cambio = (c) => setV((x) => ({ ...x, ...c }));
  const falta = !v.titulo.trim() || !v.fecha;

  return (
    <form
      className="editor-seccion"
      onSubmit={(e) => {
        e.preventDefault();
        onGuardar({
          titulo: v.titulo.trim(),
          tipo: v.tipo,
          fecha: v.fecha,
          desde: v.desde || null,
          hasta: v.hasta || null,
          lugar: v.lugar.trim() || null,
        });
      }}
    >
      <label>
        <span>Título *</span>
        <input
          type="text"
          value={v.titulo}
          maxLength={120}
          autoFocus
          placeholder="Jornada de Ciencias Exactas"
          onChange={(e) => cambio({ titulo: e.target.value })}
        />
      </label>

      <div className="editor-fila">
        <label>
          <span>Fecha *</span>
          <input
            type="date"
            value={v.fecha}
            onChange={(e) => cambio({ fecha: e.target.value })}
          />
        </label>
        <label>
          <span>Tipo</span>
          <select value={v.tipo} onChange={(e) => cambio({ tipo: e.target.value })}>
            {tipos.map((x) => (
              <option key={x} value={x}>
                {NOMBRE_TIPO[x] ?? x}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="editor-fila">
        <label>
          <span>
            Desde <small>opcional</small>
          </span>
          <input type="time" value={v.desde} onChange={(e) => cambio({ desde: e.target.value })} />
        </label>
        <label>
          <span>
            Hasta <small>opcional</small>
          </span>
          <input type="time" value={v.hasta} onChange={(e) => cambio({ hasta: e.target.value })} />
        </label>
      </div>

      <label>
        <span>
          Lugar <small>opcional</small>
        </span>
        <input
          type="text"
          value={v.lugar}
          maxLength={120}
          placeholder="Pabellón central"
          onChange={(e) => cambio({ lugar: e.target.value })}
        />
      </label>

      <div className="editor-botones">
        <button type="button" className="boton-suave" onClick={onCancelar} disabled={trabajando}>
          Cancelar
        </button>
        <button type="submit" className="boton-principal" disabled={trabajando || falta}>
          {evento ? 'Guardar los cambios' : 'Agregar el evento'}
        </button>
      </div>
    </form>
  );
}
