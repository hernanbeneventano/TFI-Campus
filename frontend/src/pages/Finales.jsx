// Finales: las tres pantallas del estudiante.
//
// Inscripciones (las mesas y el botón para anotarse), Fechas próximas (lo que
// se viene, en orden) y Resultados (el historial de finales rendidos).
//
// Las tres viven en esta ruta porque comparten la cabecera y las pestañas, y
// porque los datos de una son los de la otra vistos de otro modo. Cuál se
// muestra sale de la URL (`/finales/:vista`), no del estado: así el enlace a
// una pestaña se puede compartir y sobrevive a recargar la página.

import { useCallback, useEffect, useState } from 'react';
import { NavLink, useParams, Navigate } from 'react-router-dom';
import { Link } from 'react-router-dom';
import {
  obtenerMesas,
  obtenerProximasMesas,
  obtenerResultadosFinales,
  inscribirseAMesa,
  cancelarInscripcionMesa,
} from '../services/api.js';
import { fechaConDia, fechaLarga, enDias, diasHasta } from '../services/fechas.js';
import Encabezado from '../components/Encabezado.jsx';
import Confirmacion from '../components/Confirmacion.jsx';
import { avisar } from '../services/avisos.js';
import {
  IconoFinales,
  IconoCalendario,
  IconoNotas,
  IconoReloj,
  IconoCheckCirculo,
  IconoAdvertencia,
  IconoPersonas,
  IconoVolver,
} from '../components/Iconos.jsx';

const VISTAS = [
  { id: 'inscripciones', nombre: 'Inscripciones', Icono: IconoFinales },
  { id: 'fechas', nombre: 'Fechas próximas', Icono: IconoCalendario },
  { id: 'resultados', nombre: 'Resultados', Icono: IconoNotas },
];

// Cada estado tiene su color y su ícono. El rojo quiere decir "prestá
// atención", no "error": lo que no se puede hacer va en gris.
const ESTADOS = {
  Disponible: { clase: 'puede', Icono: IconoCheckCirculo },
  Inscripto: { clase: 'hecho', Icono: IconoCheckCirculo },
  Pendiente: { clase: 'espera', Icono: IconoReloj },
  Cerrada: { clase: 'apagado', Icono: IconoReloj },
  Cancelado: { clase: 'espera', Icono: IconoAdvertencia },
  'Sin cupos disponibles': { clase: 'apagado', Icono: IconoAdvertencia, corto: 'Sin cupos' },
  'No habilitado': { clase: 'apagado', Icono: IconoAdvertencia },
};

// El estado entero queda en el `title`: en la etiqueta no entra y el motivo
// de abajo ya lo explica con todas las letras.
function Etiqueta({ estado }) {
  const { clase, Icono, corto } = ESTADOS[estado] ?? ESTADOS['No habilitado'];
  return (
    <span className={`estado-final ${clase}`} title={estado}>
      <Icono width={14} height={14} />
      {corto ?? estado}
    </span>
  );
}

// ===================== Una mesa de examen =====================
function Mesa({ mesa, onInscribirse, onCancelar, trabajando }) {
  const faltan = diasHasta(mesa.fecha);

  return (
    <article className={`mesa ${mesa.inscripto || mesa.estado === 'Inscripto' ? 'tomada' : ''}`}>
      <div className="mesa-dia" aria-hidden="true">
        <strong>{new Date(mesa.fecha).getDate()}</strong>
        <small>
          {new Intl.DateTimeFormat('es-AR', { month: 'short' }).format(new Date(mesa.fecha))}
        </small>
      </div>

      <div className="mesa-cuerpo">
        <header className="mesa-cabecera">
          <div>
            <h3>{mesa.materia}</h3>
            <p className="mesa-codigo">
              {mesa.codigo}
              {mesa.llamado && <> · {mesa.llamado}</>}
            </p>
          </div>
          <Etiqueta estado={mesa.estado} />
        </header>

        <dl className="mesa-datos">
          <div>
            <dt>Fecha</dt>
            <dd>
              {fechaConDia(mesa.fecha)}
              <small> · {enDias(mesa.fecha)}</small>
            </dd>
          </div>
          <div>
            <dt>Horario</dt>
            <dd>
              {mesa.desde} a {mesa.hasta}
            </dd>
          </div>
          <div>
            <dt>Modalidad</dt>
            <dd>
              {mesa.modalidad}
              {mesa.lugar && <small> · {mesa.lugar}</small>}
            </dd>
          </div>
          <div>
            <dt>Tribunal</dt>
            <dd>{mesa.tribunal.length ? mesa.tribunal.join(', ') : 'A confirmar'}</dd>
          </div>
          <div>
            <dt>Inscripción hasta</dt>
            <dd>{fechaLarga(mesa.inscripcionHasta)}</dd>
          </div>
          <div>
            <dt>Lugares</dt>
            <dd>
              <IconoPersonas width={14} height={14} /> {mesa.inscriptos} de {mesa.cupo}
            </dd>
          </div>
        </dl>

        {mesa.motivo && <p className="mesa-motivo">{mesa.motivo}</p>}

        <footer className="mesa-pie">
          {mesa.cursoId && (
            <Link className="boton-suave" to={`/modulos/${mesa.cursoId}`}>
              Ir al módulo
            </Link>
          )}

          {mesa.puedeInscribirse && (
            <button
              type="button"
              className="boton-principal"
              onClick={() => onInscribirse(mesa)}
              disabled={trabajando}
            >
              Inscribirme
            </button>
          )}

          {mesa.puedeCancelar && (
            <button
              type="button"
              className="boton-suave peligro"
              onClick={() => onCancelar(mesa)}
              disabled={trabajando}
            >
              Dar de baja
            </button>
          )}

          {faltan >= 0 && mesa.estado === 'Inscripto' && (
            <span className="mesa-aviso">
              <IconoCheckCirculo width={15} height={15} />
              Estás anotado
            </span>
          )}
        </footer>
      </div>
    </article>
  );
}

// ===================== Inscripciones =====================
function Inscripciones({ datos, recargar }) {
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);
  // Lo que se está por confirmar, o null si no hay cartel abierto
  const [aConfirmar, setAConfirmar] = useState(null);

  async function accionar(accion, id, exito) {
    setTrabajando(true);
    setError(null);
    try {
      await accion(id);
      await recargar();
      avisar(exito);
    } catch (e) {
      // El error va en los dos lados: el aviso se va solo y el texto de la
      // pantalla queda, por si llegó mientras mirabas para otro lado.
      setError(e.message);
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
      setAConfirmar(null);
    }
  }

  // Los datos de la mesa van en el cartel: confirmar "una mesa" sin ver cuál
  // es lo mismo que no confirmar nada.
  function detallesDe(mesa) {
    return [
      { etiqueta: 'Materia', valor: `${mesa.materia} (${mesa.codigo})` },
      { etiqueta: 'Fecha', valor: `${fechaConDia(mesa.fecha)}, ${mesa.desde} a ${mesa.hasta}` },
      { etiqueta: 'Modalidad', valor: `${mesa.modalidad}${mesa.lugar ? ` · ${mesa.lugar}` : ''}` },
      { etiqueta: 'Inscripción hasta', valor: fechaLarga(mesa.inscripcionHasta) },
    ];
  }

  function pedirInscripcion(mesa) {
    setAConfirmar({
      titulo: '¿Te inscribís a esta mesa?',
      mensaje:
        'Vas a ocupar un lugar en la mesa de examen. Podés darte de baja mientras el período de inscripción siga abierto.',
      detalles: detallesDe(mesa),
      textoConfirmar: 'Sí, inscribirme',
      peligro: false,
      ejecutar: () =>
        accionar(
          inscribirseAMesa,
          mesa.id,
          `Te inscribiste a la mesa de ${mesa.materia}.`
        ),
    });
  }

  function pedirBaja(mesa) {
    setAConfirmar({
      titulo: '¿Das de baja tu inscripción?',
      mensaje:
        'Dejás libre tu lugar en esta mesa. Podés volver a anotarte mientras el período siga abierto; una vez que cierre, no.',
      detalles: detallesDe(mesa),
      textoConfirmar: 'Sí, darme de baja',
      peligro: true,
      ejecutar: () =>
        accionar(
          cancelarInscripcionMesa,
          mesa.id,
          `Diste de baja tu inscripción a ${mesa.materia}.`
        ),
    });
  }

  const mesas = datos?.mesas ?? [];
  const puede = mesas.filter((m) => m.estado !== 'No habilitado');
  const noPuede = mesas.filter((m) => m.estado === 'No habilitado');

  return (
    <>
      {error && <p className="aviso-error">{error}</p>}

      {puede.length === 0 && noPuede.length === 0 && (
        <p className="vacio">Por ahora no hay mesas de examen cargadas.</p>
      )}

      {puede.length > 0 && (
        <section className="bloque-mesas">
          <h2 className="titulo-bloque">
            Podés rendir
            <small>{puede.length}</small>
          </h2>
          <div className="lista-mesas">
            {puede.map((mesa) => (
              <Mesa
                key={mesa.id}
                mesa={mesa}
                trabajando={trabajando}
                onInscribirse={pedirInscripcion}
                onCancelar={pedirBaja}
              />
            ))}
          </div>
        </section>
      )}

      {noPuede.length > 0 && (
        <section className="bloque-mesas">
          <h2 className="titulo-bloque">
            Todavía no habilitadas
            <small>{noPuede.length}</small>
          </h2>
          <p className="nota-bloque">
            Para rendir un final tenés que tener la cursada de esa materia aprobada.
          </p>
          <div className="lista-mesas">
            {noPuede.map((mesa) => (
              <Mesa
                key={mesa.id}
                mesa={mesa}
                trabajando={trabajando}
                onInscribirse={() => {}}
                onCancelar={() => {}}
              />
            ))}
          </div>
        </section>
      )}

      {aConfirmar && (
        <Confirmacion
          titulo={aConfirmar.titulo}
          mensaje={aConfirmar.mensaje}
          detalles={aConfirmar.detalles}
          textoConfirmar={aConfirmar.textoConfirmar}
          peligro={aConfirmar.peligro}
          trabajando={trabajando}
          onConfirmar={aConfirmar.ejecutar}
          onCancelar={() => setAConfirmar(null)}
        />
      )}
    </>
  );
}

// ===================== Fechas próximas =====================
function Fechas({ datos }) {
  const mesas = datos?.mesas ?? [];
  if (mesas.length === 0) {
    return <p className="vacio">No hay mesas de examen próximas.</p>;
  }

  // Agrupadas por mes: una lista larga de fechas sueltas se lee mal
  const porMes = new Map();
  for (const mesa of mesas) {
    const mes = new Intl.DateTimeFormat('es-AR', { month: 'long', year: 'numeric' }).format(
      new Date(mesa.fecha)
    );
    if (!porMes.has(mes)) porMes.set(mes, []);
    porMes.get(mes).push(mesa);
  }

  return (
    <>
      <p className="nota-bloque">
        {datos.inscripto > 0
          ? `Estás inscripto en ${datos.inscripto} ${
              datos.inscripto === 1 ? 'mesa' : 'mesas'
            }. Van destacadas.`
          : 'Todavía no estás inscripto en ninguna mesa.'}
      </p>

      {[...porMes.entries()].map(([mes, delMes]) => (
        <section key={mes} className="bloque-mesas">
          <h2 className="titulo-bloque mes">
            {mes}
            <small>{delMes.length}</small>
          </h2>
          <ul className="agenda">
            {delMes.map((mesa) => (
              <li key={mesa.id} className={mesa.inscripto ? 'agenda-item tomada' : 'agenda-item'}>
                <div className="agenda-fecha">
                  <strong>{new Date(mesa.fecha).getDate()}</strong>
                  <small>
                    {new Intl.DateTimeFormat('es-AR', { weekday: 'short' }).format(
                      new Date(mesa.fecha)
                    )}
                  </small>
                </div>
                <div className="agenda-cuerpo">
                  <h3>{mesa.materia}</h3>
                  <p>
                    {mesa.codigo} · {mesa.desde} a {mesa.hasta} · {mesa.modalidad}
                    {mesa.lugar && <> · {mesa.lugar}</>}
                  </p>
                  <p className="agenda-tribunal">
                    Tribunal: {mesa.tribunal.length ? mesa.tribunal.join(', ') : 'a confirmar'}
                  </p>
                </div>
                <div className="agenda-estado">
                  <Etiqueta estado={mesa.estado} />
                  <small>{enDias(mesa.fecha)}</small>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}

// ===================== Resultados =====================
const CONDICION = {
  Aprobado: 'aprobado',
  Desaprobado: 'desaprobado',
  Ausente: 'ausente',
};

function Resultados({ datos }) {
  const resultados = datos?.resultados ?? [];
  const resumen = datos?.resumen;

  if (resultados.length === 0) {
    return <p className="vacio">Todavía no rendiste ningún final.</p>;
  }

  return (
    <>
      <div className="resumen-notas">
        <div>
          <strong>{resumen.rendidos}</strong>
          <small>rendidos</small>
        </div>
        <div className="bien">
          <strong>{resumen.aprobados}</strong>
          <small>aprobados</small>
        </div>
        <div>
          <strong>{resumen.desaprobados}</strong>
          <small>desaprobados</small>
        </div>
        <div>
          <strong>{resumen.ausentes}</strong>
          <small>ausentes</small>
        </div>
        <div className="destacado">
          <strong>{resumen.promedio ?? '—'}</strong>
          <small>promedio</small>
        </div>
      </div>

      <table className="tabla-notas">
        <caption className="oculto">Historial de finales rendidos</caption>
        <thead>
          <tr>
            <th scope="col">Materia</th>
            <th scope="col">Fecha</th>
            <th scope="col">Llamado</th>
            <th scope="col">Nota</th>
            <th scope="col">Condición</th>
          </tr>
        </thead>
        <tbody>
          {resultados.map((r) => (
            <tr key={r.id}>
              <th scope="row">
                <strong>{r.materia}</strong>
                <small>{r.codigo}</small>
              </th>
              <td>{fechaLarga(r.fecha)}</td>
              <td>{r.llamado ?? '—'}</td>
              <td className="nota">{r.nota ?? '—'}</td>
              <td>
                <span className={`condicion ${CONDICION[r.condicion] ?? ''}`}>{r.condicion}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

// ===================== La pantalla =====================
const DESCRIPCIONES = {
  inscripciones: 'Las mesas de examen de las materias que tenés en condiciones de rendir.',
  fechas: 'Todo lo que se viene, en orden. Lo que ya tomaste va destacado.',
  resultados: 'Los finales que rendiste, con su nota y su condición.',
};

export default function Finales() {
  const { vista } = useParams();
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const valida = VISTAS.some((v) => v.id === vista);

  const traer = useCallback(async () => {
    if (!valida) return;
    const pedido = {
      inscripciones: obtenerMesas,
      fechas: obtenerProximasMesas,
      resultados: obtenerResultadosFinales,
    }[vista];

    setCargando(true);
    setError(null);
    try {
      setDatos(await pedido());
    } catch (e) {
      setError(e.message);
      setDatos(null);
    } finally {
      setCargando(false);
    }
  }, [vista, valida]);

  useEffect(() => {
    traer();
  }, [traer]);

  // Una vista inventada en la URL vuelve a la primera
  if (!valida) return <Navigate to="/finales/inscripciones" replace />;

  return (
    <div className="pagina">
      <Encabezado titulo="Finales" descripcion={DESCRIPCIONES[vista]} />

      <nav className="pestanas" aria-label="Secciones de Finales">
        {VISTAS.map(({ id, nombre, Icono }) => (
          <NavLink
            key={id}
            to={`/finales/${id}`}
            className={({ isActive }) => (isActive ? 'pestana activa' : 'pestana')}
          >
            <Icono width={16} height={16} />
            {nombre}
          </NavLink>
        ))}
      </nav>

      {cargando && <p className="vacio">Cargando…</p>}

      {error && (
        <p className="aviso-error">
          {error}{' '}
          <button type="button" className="boton-suave" onClick={traer}>
            <IconoVolver width={15} height={15} /> Reintentar
          </button>
        </p>
      )}

      {!cargando && !error && datos && (
        <div className="cuerpo-finales">
          {vista === 'inscripciones' && <Inscripciones datos={datos} recargar={traer} />}
          {vista === 'fechas' && <Fechas datos={datos} />}
          {vista === 'resultados' && <Resultados datos={datos} />}
        </div>
      )}
    </div>
  );
}
