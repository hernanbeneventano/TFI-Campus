// El registro de actividad del campus: quién hizo qué y qué cambió.
//
// Es una pantalla de **solo lectura**, y se nota: no hay un solo botón que
// escriba. Eso es parte de lo que se pide, no un descuido.
//
// Quién la ve lo decide el servidor, no esta pantalla: un estudiante que
// escriba /auditoria en la barra recibe un 403 y acá se muestra el motivo.
// Esconder la opción del menú no es un control de acceso.

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  obtenerOpcionesAuditoria,
  obtenerAuditoria,
  obtenerAuditoriaDeMisMaterias,
  obtenerMovimiento,
  enlaceExportarAuditoria,
} from '../services/api.js';
import Encabezado from '../components/Encabezado.jsx';
import Desplegable from '../components/Desplegable.jsx';
import { fechaConDia, hace } from '../services/fechas.js';
import {
  IconoBuscar,
  IconoCerrar,
  IconoDescargar,
  IconoAdvertencia,
  IconoActividad,
} from '../components/Iconos.jsx';

import useTitulo from '../hooks/useTitulo';
const FILTROS_VACIOS = {
  q: '',
  usuarioId: '',
  rol: '',
  accion: '',
  modulo: '',
  resultado: '',
  carreraId: '',
  sedeId: '',
  comisionId: '',
  desde: '',
  hasta: '',
};

// Los números de arriba. El orden es el del pliego, de lo general a lo raro:
// lo último que se mira es lo que falló, y es lo que más importa cuando pasa.
const TARJETAS = [
  { id: 'total', nombre: 'Actividades registradas' },
  { id: 'hoy', nombre: 'De hoy' },
  { id: 'modificaciones', nombre: 'Modificaciones' },
  { id: 'administrativas', nombre: 'Administrativas' },
  { id: 'fallidas', nombre: 'Fallidas', alerta: true },
];

function fechaYHora(iso) {
  if (!iso) return '—';
  const f = new Date(iso);
  return `${fechaConDia(iso)} · ${String(f.getHours()).padStart(2, '0')}:${String(
    f.getMinutes()
  ).padStart(2, '0')}`;
}

/** Un valor del detalle, que puede ser texto o un objeto con varias claves. */
function Valor({ dato }) {
  if (dato == null || dato === '') return <span className="texto-suave">—</span>;
  if (typeof dato !== 'object') return <span>{String(dato)}</span>;

  return (
    <ul className="movimiento-valores">
      {Object.entries(dato).map(([clave, valor]) => (
        <li key={clave}>
          <span>{clave}</span>
          <strong>{Array.isArray(valor) ? valor.join(', ') || '—' : String(valor ?? '—')}</strong>
        </li>
      ))}
    </ul>
  );
}

function Dato({ nombre, children }) {
  if (children == null || children === '') return null;
  return (
    <div className="movimiento-dato">
      <span>{nombre}</span>
      <strong>{children}</strong>
    </div>
  );
}

/** El detalle de un movimiento, con el antes y el después. */
function Movimiento({ id, onCerrar }) {
  const [evento, setEvento] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerMovimiento(id).then(setEvento).catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape') onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
  }, [onCerrar]);

  const cambio = evento && (evento.antes != null || evento.despues != null);

  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && onCerrar()}
      role="presentation"
    >
      <section className="correccion ancha" role="dialog" aria-modal="true">
        <button
          type="button"
          className="correccion-cerrar"
          onClick={onCerrar}
          aria-label="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        {error && <p className="aviso-error">{error}</p>}
        {!evento && !error && <p className="texto-suave">Cargando…</p>}

        {evento && (
          <>
            <h3>{evento.nombreAccion}</h3>
            <p className="correccion-trabajo">
              {evento.nombreModulo}
              {evento.elemento ? ` · ${evento.elemento}` : ''}
            </p>

            <div className="movimiento-datos">
              <Dato nombre="Usuario">{evento.quien}</Dato>
              <Dato nombre="Rol">{evento.rol}</Dato>
              <Dato nombre="Módulo">{evento.nombreModulo}</Dato>
              <Dato nombre="Acción">{evento.nombreAccion}</Dato>
              <Dato nombre="Persona afectada">{evento.afectada}</Dato>
              <Dato nombre="Materia">{evento.materia}</Dato>
              <Dato nombre="Carrera">{evento.carrera}</Dato>
              <Dato nombre="Sede">{evento.sede}</Dato>
              <Dato nombre="Comisión">{evento.comision}</Dato>
              <Dato nombre="Fecha y hora">{fechaYHora(evento.cuando)}</Dato>
              <Dato nombre="Dirección IP">{evento.ip}</Dato>
              <Dato nombre="Resultado">
                <span className={`resultado ${evento.resultado}`}>{evento.nombreResultado}</span>
              </Dato>
            </div>

            {evento.detalle && <p className="movimiento-detalle">{evento.detalle}</p>}

            {/* Lo más importante del detalle: qué había y qué quedó */}
            {cambio && (
              <div className="movimiento-cambio">
                <div>
                  <h4>Valor anterior</h4>
                  <Valor dato={evento.antes} />
                </div>
                <div>
                  <h4>Valor nuevo</h4>
                  <Valor dato={evento.despues} />
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}

export default function Auditoria({ dentroDeAdministracion = false }) {
  useTitulo(dentroDeAdministracion ? 'Administración' : 'Actividad');
  const [opciones, setOpciones] = useState(null);
  const [filtros, setFiltros] = useState(FILTROS_VACIOS);
  const [escrito, setEscrito] = useState('');
  const [pagina, setPagina] = useState(1);
  const [masFiltros, setMasFiltros] = useState(false);

  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [abierto, setAbierto] = useState(null);

  // Quién ve qué lo decide el servidor, no esta pantalla. En vez de mirar el
  // rol del usuario —que llega más tarde y puede no estar—, se le pregunta:
  // si las opciones del registro general dan 403, es alguien que solo puede
  // ver lo de sus materias.
  //
  // `null` mientras no se sabe: así no se pide nada con la respuesta
  // equivocada y después hay que deshacerlo.
  const [soloMisMaterias, setSoloMisMaterias] = useState(null);

  useEffect(() => {
    obtenerOpcionesAuditoria()
      .then((o) => {
        setOpciones(o);
        setSoloMisMaterias(false);
      })
      .catch(() => setSoloMisMaterias(true));
  }, []);

  // Se espera a que pare de teclear, como en la Biblioteca
  useEffect(() => {
    const reloj = setTimeout(() => {
      setFiltros((f) => (f.q === escrito ? f : { ...f, q: escrito }));
      setPagina(1);
    }, 350);
    return () => clearTimeout(reloj);
  }, [escrito]);

  const traer = useCallback(() => {
    if (soloMisMaterias === null) return;
    setCargando(true);
    const pedir = soloMisMaterias ? obtenerAuditoriaDeMisMaterias : obtenerAuditoria;
    pedir({ ...filtros, pagina })
      .then((r) => {
        setDatos(r);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [filtros, pagina, soloMisMaterias]);

  useEffect(traer, [traer]);

  function cambiarFiltro(campo, valor) {
    setFiltros((f) => {
      const nuevo = { ...f, [campo]: valor };
      // Cambiar de carrera o de sede deja una comisión que ya no corresponde
      if (campo === 'carreraId' || campo === 'sedeId') nuevo.comisionId = '';
      return nuevo;
    });
    setPagina(1);
  }

  function limpiar() {
    setFiltros(FILTROS_VACIOS);
    setEscrito('');
    setPagina(1);
  }

  const hayFiltros = useMemo(
    () => Object.keys(FILTROS_VACIOS).some((c) => filtros[c] !== FILTROS_VACIOS[c]),
    [filtros]
  );

  // Las comisiones que pueden tener algo con los otros filtros puestos
  const comisiones = (opciones?.comisiones ?? []).filter(
    (c) =>
      (!filtros.carreraId || String(c.carreraId) === filtros.carreraId) &&
      (!filtros.sedeId || String(c.sedeId) === filtros.sedeId)
  );

  const eventos = datos?.eventos ?? [];
  const resumen = datos?.resumen;

  if (soloMisMaterias === null) {
    return (
      <div className="pagina">
        <Encabezado titulo="Registro de actividad" />
        <p className="texto-suave">Cargando…</p>
      </div>
    );
  }

  if (error && !datos) {
    return (
      <div className="pagina">
        <Encabezado titulo="Registro de actividad" />
        <div className="biblioteca-vacio">
          <IconoAdvertencia width={34} height={34} />
          <h3>No podés ver este apartado</h3>
          <p className="texto-suave">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pagina auditoria">
      {/* Dentro de Administración la cabecera ya la puso esa pantalla */}
      {!dentroDeAdministracion && (
        <Encabezado
          titulo={soloMisMaterias ? 'Actividad de mis materias' : 'Registro de actividad'}
          descripcion={
            soloMisMaterias
              ? 'Los movimientos de asistencias, notas y material de las materias que dictás'
              : 'Qué hizo cada uno, cuándo y qué cambió. El registro no se edita ni se borra.'
          }
        />
      )}

      {/* ---------- Los números ---------- */}
      {resumen && (
        <div className="auditoria-resumen">
          {TARJETAS.map((t) => (
            <div
              key={t.id}
              className={
                t.alerta && resumen[t.id] > 0 ? 'auditoria-tarjeta alerta' : 'auditoria-tarjeta'
              }
            >
              <strong>{resumen[t.id] ?? 0}</strong>
              <span>{t.nombre}</span>
            </div>
          ))}
        </div>
      )}

      {/* ---------- Filtros ---------- */}
      <div className="filtros-plan">
        <label className="barra-busqueda">
          <IconoBuscar />
          <input
            type="search"
            value={escrito}
            placeholder="Buscar por palabra: nombre, elemento, detalle…"
            onChange={(e) => setEscrito(e.target.value)}
          />
        </label>

        {!soloMisMaterias && (
          <>
            <Desplegable
              valor={filtros.modulo}
              opciones={[
                { valor: '', nombre: 'Todos los módulos' },
                ...(opciones?.modulos ?? []).map((m) => ({ valor: m.id, nombre: m.nombre })),
              ]}
              onCambiar={(v) => cambiarFiltro('modulo', v)}
              etiqueta="Módulo"
            />
            <Desplegable
              valor={filtros.accion}
              opciones={[
                { valor: '', nombre: 'Toda acción' },
                ...(opciones?.acciones ?? []).map((a) => ({ valor: a.id, nombre: a.nombre })),
              ]}
              onCambiar={(v) => cambiarFiltro('accion', v)}
              etiqueta="Acción"
            />
            <Desplegable
              valor={filtros.usuarioId}
              opciones={[
                { valor: '', nombre: 'Cualquier usuario' },
                ...(opciones?.usuarios ?? []).map((u) => ({
                  valor: String(u.id),
                  nombre: u.nombre,
                })),
              ]}
              onCambiar={(v) => cambiarFiltro('usuarioId', v)}
              etiqueta="Usuario"
            />

            <button
              type="button"
              className={masFiltros ? 'boton-suave activo' : 'boton-suave'}
              onClick={() => setMasFiltros((m) => !m)}
              aria-expanded={masFiltros}
            >
              {masFiltros ? 'Menos filtros' : 'Más filtros'}
            </button>
          </>
        )}

        {hayFiltros && (
          <button type="button" className="boton-suave" onClick={limpiar}>
            Limpiar filtros
          </button>
        )}

        {/* Exporta lo filtrado, no todo: lo que se ve es lo que baja */}
        <div className="auditoria-exportar">
          <a className="boton-suave" href={enlaceExportarAuditoria(filtros, 'csv')}>
            <IconoDescargar width={16} height={16} />
            CSV
          </a>
          <a className="boton-suave" href={enlaceExportarAuditoria(filtros, 'xlsx')}>
            <IconoDescargar width={16} height={16} />
            Excel
          </a>
          <button type="button" className="boton-suave" onClick={() => window.print()}>
            <IconoDescargar width={16} height={16} />
            PDF
          </button>
        </div>
      </div>

      {/* El resto de los filtros, plegados: son muchos y casi nunca se usan
          todos juntos. Los cuatro de arriba son los de todos los días. */}
      {masFiltros && !soloMisMaterias && (
        <div className="filtros-plan segunda-fila">
          <Desplegable
            valor={filtros.rol}
            opciones={[
              { valor: '', nombre: 'Cualquier rol' },
              ...(opciones?.roles ?? []).map((r) => ({ valor: r, nombre: r })),
            ]}
            onCambiar={(v) => cambiarFiltro('rol', v)}
            etiqueta="Rol"
          />
          <Desplegable
            valor={filtros.resultado}
            opciones={[
              { valor: '', nombre: 'Cualquier resultado' },
              ...(opciones?.resultados ?? []).map((r) => ({ valor: r.id, nombre: r.nombre })),
            ]}
            onCambiar={(v) => cambiarFiltro('resultado', v)}
            etiqueta="Resultado"
          />
          <Desplegable
            valor={filtros.carreraId}
            opciones={[
              { valor: '', nombre: 'Todas las carreras' },
              ...(opciones?.carreras ?? []).map((c) => ({
                valor: String(c.id),
                nombre: c.nombre,
              })),
            ]}
            onCambiar={(v) => cambiarFiltro('carreraId', v)}
            etiqueta="Carrera"
          />
          <Desplegable
            valor={filtros.sedeId}
            opciones={[
              { valor: '', nombre: 'Todas las sedes' },
              ...(opciones?.sedes ?? []).map((s) => ({ valor: String(s.id), nombre: s.nombre })),
            ]}
            onCambiar={(v) => cambiarFiltro('sedeId', v)}
            etiqueta="Sede"
          />
          <Desplegable
            valor={filtros.comisionId}
            opciones={[
              { valor: '', nombre: 'Todas las comisiones' },
              ...comisiones.map((c) => ({ valor: String(c.id), nombre: c.nombre })),
            ]}
            onCambiar={(v) => cambiarFiltro('comisionId', v)}
            etiqueta="Comisión"
          />

          <label className="filtro-fecha">
            <span>Desde</span>
            <input
              type="date"
              value={filtros.desde}
              onChange={(e) => cambiarFiltro('desde', e.target.value)}
            />
          </label>
          <label className="filtro-fecha">
            <span>Hasta</span>
            <input
              type="date"
              value={filtros.hasta}
              onChange={(e) => cambiarFiltro('hasta', e.target.value)}
            />
          </label>
        </div>
      )}

      {error && <p className="aviso-error">{error}</p>}

      {/* ---------- La tabla ---------- */}
      {!cargando && eventos.length === 0 ? (
        <div className="biblioteca-vacio">
          <IconoActividad width={34} height={34} />
          <h3>No hay actividad que coincida</h3>
          <p className="texto-suave">
            {hayFiltros
              ? 'Probá con otros filtros o un período más amplio.'
              : 'Todavía no se registró ningún movimiento.'}
          </p>
        </div>
      ) : (
        <div className="tabla-auditoria-caja">
          <table className="tabla-auditoria">
            <thead>
              <tr>
                <th>Fecha y hora</th>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Acción</th>
                <th>Módulo</th>
                <th>Elemento afectado</th>
                <th>Resultado</th>
                <th><span className="solo-lectores">Detalles</span></th>
              </tr>
            </thead>
            <tbody>
              {eventos.map((e) => (
                <tr key={e.id} className={e.resultado === 'fallo' ? 'fallida' : undefined}>
                  <td>
                    <span className="auditoria-fecha">{fechaYHora(e.cuando)}</span>
                    <small className="texto-suave">{hace(e.cuando)}</small>
                  </td>
                  <td>{e.quien}</td>
                  <td>
                    {e.rol && <span className="etiqueta-rol">{e.rol}</span>}
                  </td>
                  <td>{e.nombreAccion}</td>
                  <td>{e.nombreModulo}</td>
                  <td>
                    {e.elemento ?? '—'}
                    {e.afectada && <small className="texto-suave"> · {e.afectada}</small>}
                  </td>
                  <td>
                    <span className={`resultado ${e.resultado}`}>{e.nombreResultado}</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="boton-suave"
                      onClick={() => setAbierto(e.id)}
                    >
                      Ver
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {datos?.paginas > 1 && (
        <div className="biblioteca-paginas">
          <button
            type="button"
            className="boton-suave"
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
            disabled={pagina <= 1}
          >
            Anterior
          </button>
          <span className="texto-suave">
            Página {datos.pagina} de {datos.paginas} · {datos.total} movimientos
          </span>
          <button
            type="button"
            className="boton-suave"
            onClick={() => setPagina((p) => Math.min(datos.paginas, p + 1))}
            disabled={pagina >= datos.paginas}
          >
            Siguiente
          </button>
        </div>
      )}

      {abierto && <Movimiento id={abierto} onCerrar={() => setAbierto(null)} />}
    </div>
  );
}
