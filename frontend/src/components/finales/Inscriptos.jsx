import { Fragment, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Desplegable from '../Desplegable.jsx';
import {
  IconoBuscar,
  IconoDescargar,
  IconoEstudiante,
  IconoFlecha,
  IconoMensaje,
  IconoPersonas,
  IconoReloj,
  IconoUbicacion,
} from '../Iconos.jsx';
import { obtenerInscriptosFinales } from '../../services/api.js';
import { fechaConDia } from '../../services/fechas.js';
import {
  Condicion,
  EstadoMesa,
  NombreMateria,
  descargarCsv,
  fechaNumerica,
  horario,
} from './comun.jsx';

// Sin tildes ni mayúsculas, para que "garcia" encuentre a "García"
const normalizar = (texto) =>
  String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

export default function Inscriptos({ mesas }) {
  const [parametros, setParametros] = useSearchParams();
  // ?mesa=ID llega desde Fechas ("Ver inscriptos") y deja el enlace compartible
  const mesaElegida = parametros.get('mesa');

  const [materia, setMateria] = useState(() => {
    const mesa = mesas.find((m) => String(m.id) === mesaElegida);
    return mesa ? String(mesa.materia.id) : '';
  });
  const [fecha, setFecha] = useState(mesaElegida ? `mesa:${mesaElegida}` : 'proximas');
  const [comision, setComision] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [verCancelados, setVerCancelados] = useState(false);
  const [abierto, setAbierto] = useState(null);

  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  // Materia, mesa y comisión las filtra el servidor; la búsqueda por nombre
  // y las próximas/tomadas, acá.
  useEffect(() => {
    let vigente = true;
    setCargando(true);
    obtenerInscriptosFinales({
      materiaId: materia,
      mesaId: fecha.startsWith('mesa:') ? fecha.slice(5) : '',
      comision,
    })
      .then((r) => vigente && (setDatos(r), setError(null)))
      .catch((e) => vigente && setError(e.message))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [materia, fecha, comision]);

  function elegirFecha(valor) {
    setFecha(valor);
    // La URL acompaña a la mesa elegida, y se limpia si se elige otra cosa
    const siguiente = new URLSearchParams(parametros);
    if (valor.startsWith('mesa:')) siguiente.set('mesa', valor.slice(5));
    else siguiente.delete('mesa');
    setParametros(siguiente, { replace: true });
  }

  function elegirMateria(valor) {
    setMateria(valor);
    // Una mesa de otra materia ya no tendría sentido
    if (fecha.startsWith('mesa:')) elegirFecha('proximas');
  }

  // ---------- Opciones de los filtros ----------
  const materias = useMemo(() => {
    const vistas = new Map();
    for (const mesa of mesas) vistas.set(mesa.materia.id, mesa.materia);
    return [
      { valor: '', nombre: 'Todas las materias' },
      ...[...vistas.values()].map((m) => ({ valor: String(m.id), nombre: `${m.codigo} · ${m.nombre}` })),
    ];
  }, [mesas]);

  const fechas = useMemo(
    () => [
      { valor: 'proximas', nombre: 'Próximas mesas' },
      { valor: 'tomadas', nombre: 'Mesas ya tomadas' },
      { valor: '', nombre: 'Todas las fechas' },
      ...mesas
        .filter((m) => !materia || String(m.materia.id) === materia)
        .map((m) => ({
          valor: `mesa:${m.id}`,
          nombre: `${fechaNumerica(m.fecha)} · ${m.materia.codigo}${m.estado === 'cancelada' ? ' (cancelada)' : ''}`,
        })),
    ],
    [mesas, materia]
  );

  const comisiones = [
    { valor: '', nombre: 'Todas las comisiones' },
    ...(datos?.comisiones ?? []).map((c) => ({ valor: c, nombre: `Comisión ${c}` })),
  ];

  // ---------- Lo que se ve ----------
  const grupos = useMemo(() => {
    if (!datos) return [];
    const buscado = normalizar(busqueda.trim());
    return datos.grupos
      .filter(({ mesa }) => {
        if (fecha === 'proximas') return !mesa.tomada;
        if (fecha === 'tomadas') return mesa.tomada;
        return true;
      })
      .map((grupo) => ({
        ...grupo,
        inscriptos: grupo.inscriptos.filter(
          (f) =>
            (verCancelados || f.estado === 'Inscripto') &&
            (!buscado ||
              normalizar(f.alumno.nombre).includes(buscado) ||
              normalizar(f.alumno.legajo).includes(buscado))
        ),
      }))
      // Buscando, las mesas sin coincidencias sobran
      .filter((g) => !buscado || g.inscriptos.length > 0);
  }, [datos, fecha, busqueda, verCancelados]);

  const total = grupos.reduce(
    (suma, g) => suma + g.inscriptos.filter((f) => f.estado === 'Inscripto').length,
    0
  );
  const libres = grupos.reduce(
    (suma, g) => suma + g.inscriptos.filter((f) => f.estado === 'Inscripto' && f.condicion === 'Libre').length,
    0
  );

  function exportar() {
    const columnas = [
      'Materia', 'Código', 'Llamado', 'Fecha', 'Horario', 'Lugar',
      'Alumno', 'Legajo', 'Carrera', 'Comisión', 'Condición', 'Inscripto el', 'Estado',
    ];
    const filas = grupos.flatMap(({ mesa, inscriptos }) =>
      inscriptos.map((f) => [
        mesa.materia.nombre, mesa.materia.codigo, mesa.llamado, fechaNumerica(mesa.fecha),
        horario(mesa), mesa.lugar, f.alumno.nombre, f.alumno.legajo, f.alumno.carrera,
        f.comision, f.condicion, fechaNumerica(f.fecha), f.estado,
      ])
    );
    const hoy = new Date().toISOString().slice(0, 10);
    descargarCsv(`inscriptos-finales-${hoy}.csv`, columnas, filas);
  }

  const hayFiltros = materia || fecha !== 'proximas' || comision || busqueda;

  return (
    <section className="finales-seccion">
      {/* ---------- Resumen ---------- */}
      <div className="finales-resumen">
        <div className="finales-dato">
          <strong>{cargando && !datos ? '…' : total}</strong>
          <span>{total === 1 ? 'alumno inscripto' : 'alumnos inscriptos'}</span>
        </div>
        <div className="finales-dato">
          <strong>{grupos.length}</strong>
          <span>{grupos.length === 1 ? 'mesa en la vista' : 'mesas en la vista'}</span>
        </div>
        <div className="finales-dato">
          <strong>{libres}</strong>
          <span>{libres === 1 ? 'rinde libre' : 'rinden libres'}</span>
        </div>
        <button
          type="button"
          className="boton-principal finales-exportar"
          onClick={exportar}
          disabled={total === 0 && !verCancelados}
          title="Descarga lo que se ve, con los filtros puestos"
        >
          <IconoDescargar />
          Exportar listado
        </button>
      </div>

      {/* ---------- Filtros ---------- */}
      <div className="finales-filtros">
        <label className="barra-busqueda finales-busqueda">
          <IconoBuscar />
          <input
            type="search"
            placeholder="Buscar por nombre o legajo"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            aria-label="Buscar por nombre o legajo"
          />
        </label>
        <Desplegable valor={materia} opciones={materias} onCambiar={elegirMateria} etiqueta="Materia" />
        <Desplegable valor={fecha} opciones={fechas} onCambiar={elegirFecha} etiqueta="Fecha" />
        <Desplegable valor={comision} opciones={comisiones} onCambiar={setComision} etiqueta="Comisión" />
        <label className="finales-casilla">
          <input
            type="checkbox"
            className="interruptor"
            checked={verCancelados}
            onChange={(e) => setVerCancelados(e.target.checked)}
          />
          Ver bajas
        </label>
        {hayFiltros && (
          <button
            type="button"
            className="boton-suave"
            onClick={() => {
              setMateria('');
              setComision('');
              setBusqueda('');
              elegirFecha('proximas');
            }}
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {error && <p className="aviso-error">{error}</p>}

      {!cargando && grupos.length === 0 && (
        <div className="vacio">
          <IconoPersonas width={34} height={34} />
          <h3>No hay inscriptos para mostrar</h3>
          <p className="texto-suave">
            {busqueda ? 'Nadie coincide con esa búsqueda.' : 'Probá con otra fecha o sacá algún filtro.'}
          </p>
        </div>
      )}

      {/* ---------- Una tarjeta por mesa ---------- */}
      {grupos.map(({ mesa, inscriptos }, i) => {
        const activos = inscriptos.filter((f) => f.estado === 'Inscripto').length;
        return (
          <article
            key={mesa.id}
            className={mesa.estado === 'cancelada' ? 'finales-grupo cancelada' : 'finales-grupo'}
            style={{
              '--retraso': `${Math.min(i, 12) * 35}ms`,
              '--color-materia': mesa.materia.color || 'var(--oscuro)',
            }}
          >
            <header className="finales-grupo-cabecera">
              <div>
                <NombreMateria materia={mesa.materia} />
                <h3>{mesa.llamado}</h3>
                <p className="finales-datos-mesa">
                  <span>
                    <IconoReloj /> {fechaConDia(mesa.fecha)}, {horario(mesa)}
                  </span>
                  <span>
                    <IconoUbicacion /> {mesa.lugar} · {mesa.modalidad}
                  </span>
                </p>
              </div>
              <div className="finales-grupo-cuenta">
                <EstadoMesa mesa={mesa} />
                <strong>
                  {mesa.inscriptos}
                  {mesa.cupo ? <small> / {mesa.cupo}</small> : null}
                </strong>
                <small>{mesa.cupo ? 'inscriptos sobre el cupo' : 'inscriptos · sin cupo'}</small>
              </div>
            </header>

            {inscriptos.length === 0 ? (
              <p className="texto-suave finales-sin-gente">Todavía no se anotó nadie.</p>
            ) : (
              <table className="finales-tabla">
                <thead>
                  <tr>
                    <th scope="col">Alumno</th>
                    <th scope="col">Legajo</th>
                    <th scope="col">Comisión</th>
                    <th scope="col">Condición</th>
                    <th scope="col">Inscripto el</th>
                    <th scope="col">
                      <span className="oculto">Detalle</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {inscriptos.map((f) => {
                    const desplegado = abierto === f.id;
                    return (
                      <Fragment key={f.id}>
                        <tr className={f.estado === 'Cancelado' ? 'baja' : undefined}>
                          <td data-etiqueta="Alumno">
                            <span className="finales-alumno">
                              <span className={`finales-avatar avatar-estado ${f.alumno.estado}`}>
                                <IconoEstudiante width={18} height={18} />
                              </span>
                              <span>
                                <strong>{f.alumno.nombre}</strong>
                                <small>{f.alumno.carrera}</small>
                              </span>
                            </span>
                          </td>
                          <td data-etiqueta="Legajo">{f.alumno.legajo ?? '—'}</td>
                          <td data-etiqueta="Comisión">{f.comision}</td>
                          <td data-etiqueta="Condición">
                            <Condicion condicion={f.condicion} />
                            {f.estado === 'Cancelado' && <span className="finales-baja">Se dio de baja</span>}
                          </td>
                          <td data-etiqueta="Inscripto el">{fechaNumerica(f.fecha)}</td>
                          <td className="finales-celda-boton">
                            <button
                              type="button"
                              className={desplegado ? 'finales-ver abierto' : 'finales-ver'}
                              onClick={() => setAbierto(desplegado ? null : f.id)}
                              aria-expanded={desplegado}
                              aria-label={`Datos académicos de ${f.alumno.nombre}`}
                              title="Datos académicos"
                            >
                              <IconoFlecha width={15} height={15} />
                            </button>
                          </td>
                        </tr>
                        {desplegado && (
                          <tr className="finales-ficha-fila">
                            <td colSpan={6}>
                              <FichaAcademica fila={f} materia={mesa.materia.nombre} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            )}

            {activos > 0 && inscriptos.length !== mesa.inscriptos && !verCancelados && (
              <p className="texto-suave finales-sin-gente">
                Con los filtros se ven {activos} de {mesa.inscriptos}.
              </p>
            )}
          </article>
        );
      })}
    </section>
  );
}

function FichaAcademica({ fila, materia }) {
  const { alumno } = fila;
  return (
    <div className="finales-ficha">
      <dl>
        <div>
          <dt>Carrera</dt>
          <dd>{alumno.carrera ?? '—'}</dd>
        </div>
        <div>
          <dt>Ingreso</dt>
          <dd>{alumno.ingreso ?? '—'}</dd>
        </div>
        <div>
          <dt>Finales aprobados</dt>
          <dd>{alumno.aprobadas}</dd>
        </div>
        <div>
          <dt>Promedio</dt>
          <dd>{alumno.promedio ?? '—'}</dd>
        </div>
        <div>
          <dt>Correo</dt>
          <dd>{alumno.correo}</dd>
        </div>
      </dl>

      <div className="finales-intentos">
        <h4>Veces anteriores en {materia}</h4>
        {alumno.intentos.length === 0 ? (
          <p className="texto-suave">Es la primera vez que se presenta.</p>
        ) : (
          <ul>
            {alumno.intentos.map((intento, i) => (
              <li key={i}>
                <span>{fechaNumerica(intento.fecha)}</span>
                <span className={`condicion ${intento.resultado.toLowerCase()}`}>
                  {intento.resultado}
                  {intento.nota !== null && intento.nota !== undefined ? ` · ${intento.nota}` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Reutiliza Mensajes: abre la charla con esa persona o la crea */}
      <Link to={`/mensajes?con=${alumno.id}`} className="boton-suave finales-escribir">
        <IconoMensaje width={16} height={16} />
        Escribirle
      </Link>
    </div>
  );
}
