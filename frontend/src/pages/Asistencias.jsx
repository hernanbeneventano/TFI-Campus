// El apartado Asistencias: todas las materias de una sola vez.
//
// Es el complemento de la pestaña que hay dentro de cada módulo. Ahí se
// trabaja sobre una materia —tomar lista, ver el detalle—; acá se mira el
// conjunto: cómo viene el alumno en todo lo que cursa, o qué justificaciones
// tiene pendientes el docente en todas sus cátedras.
//
// Cuál de las dos caras se muestra lo decide el rol, no la ruta, igual que
// en Finales.

import { useCallback, useEffect, useState } from 'react';
import { NavLink, useParams, Navigate, Link } from 'react-router-dom';
import {
  obtenerUsuarioActual,
  obtenerMiSituacion,
  obtenerJustificaciones,
  resolverJustificacion,
} from '../services/api.js';
import { avisar } from '../services/avisos.js';
import { fechaLarga, hace } from '../services/fechas.js';
import Encabezado from '../components/Encabezado.jsx';
import { Situacion, BarraAsistencia, Dato } from '../components/asistencias/comun.jsx';
import {
  IconoPresente,
  IconoNotas,
  IconoCheckCirculo,
  IconoCerrar,
  IconoArchivo,
} from '../components/Iconos.jsx';

const VISTAS = [
  { id: 'panel', nombre: 'Panel', Icono: IconoPresente },
  { id: 'justificaciones', nombre: 'Justificaciones', Icono: IconoNotas },
];

// ===================== Panel =====================
function PanelAlumno() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerMiSituacion().then(setDatos).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  const conClases = datos.materias.filter((m) => m.registradas > 0);

  return (
    <>
      <div className="datos-asistencia">
        <Dato valor={datos.resumen.materias} etiqueta="materias" />
        <Dato valor={`${datos.resumen.promedio ?? '—'}%`} etiqueta="promedio" variante="destacado" />
        <Dato
          valor={datos.resumen.enRiesgo}
          etiqueta="en riesgo"
          variante={datos.resumen.enRiesgo > 0 ? 'ambar' : ''}
        />
        <Dato
          valor={datos.resumen.porDebajo}
          etiqueta="por debajo"
          variante={datos.resumen.porDebajo > 0 ? 'rojo' : ''}
        />
      </div>

      {conClases.length === 0 && (
        <p className="vacio">Todavía no se registraron clases en tus materias.</p>
      )}

      <ul className="materias-asistencia">
        {datos.materias.map((m) => (
          <li key={m.cursoId}>
            <span className="materia-banda" style={{ background: m.color }} aria-hidden="true" />

            <div className="materia-texto">
              <Link to={`/modulos/${m.cursoId}`}>
                <strong>{m.nombre}</strong>
              </Link>
              <small>
                {m.codigo} · {m.clasesDictadas} clases dictadas
                {m.clasesPlanificadas && ` de ${m.clasesPlanificadas} previstas`}
              </small>
            </div>

            <div className="materia-barra">
              <BarraAsistencia
                porcentaje={m.porcentaje}
                minimo={m.minimoAsistencia}
                estado={m.estado}
              />
              <small>
                {m.porcentaje ?? '—'}% · {m.presentes} presentes, {m.ausentes} ausentes
              </small>
            </div>

            <div className="materia-faltas">
              <strong>{m.inasistenciasDisponibles ?? '—'}</strong>
              <small>faltas disponibles</small>
            </div>

            <Situacion estado={m.estado} chica />
          </li>
        ))}
      </ul>
    </>
  );
}

function PanelDocente({ justificaciones }) {
  const pendientes = justificaciones?.pendientes ?? 0;

  return (
    <>
      <p className="nota-bloque">
        El detalle de cada materia está en su módulo, en la pestaña Asistencias: ahí se toma
        lista y se ve cómo viene cada alumno.
      </p>

      <div className="datos-asistencia">
        <Dato
          valor={pendientes}
          etiqueta="justificaciones por resolver"
          variante={pendientes > 0 ? 'ambar' : ''}
        />
      </div>
    </>
  );
}

// ===================== Justificaciones =====================
function Justificaciones({ datos, onResolver, trabajando }) {
  const [resolviendo, setResolviendo] = useState(null);
  const [observacion, setObservacion] = useState('');

  if (!datos) return <p className="texto-suave">Cargando…</p>;
  if (datos.justificaciones.length === 0) {
    return (
      <p className="vacio">
        {datos.puedeResolver
          ? 'No hay justificaciones en tus materias.'
          : 'No pediste ninguna justificación.'}
      </p>
    );
  }

  function abrir(j, estado) {
    setResolviendo({ ...j, nuevoEstado: estado });
    setObservacion('');
  }

  return (
    <>
      <ul className="justificaciones">
        {datos.justificaciones.map((j) => (
          <li key={j.id} className={`justificacion ${j.estado.toLowerCase()}`}>
            <div className="justificacion-texto">
              <strong>{datos.puedeResolver ? j.alumno : j.curso}</strong>
              <small>
                {datos.puedeResolver && `${j.curso} · `}
                {j.fechaClase ? fechaLarga(j.fechaClase) : 'Clase sin fecha'}
                {j.tema && ` · ${j.tema}`}
              </small>
              <p>«{j.motivo}»</p>
              {j.archivo && (
                <small className="justificacion-archivo">
                  <IconoArchivo width={13} height={13} />
                  {j.archivo}
                </small>
              )}
              {j.observacion && (
                <small className="justificacion-respuesta">
                  {j.revisor}: «{j.observacion}»
                </small>
              )}
            </div>

            <div className="justificacion-estado">
              <span className={`estado-justificacion ${j.estado.toLowerCase()}`}>{j.estado}</span>
              <small>{hace(j.fecha)}</small>
            </div>

            {datos.puedeResolver && j.estado === 'Pendiente' && (
              <div className="justificacion-acciones">
                <button
                  type="button"
                  className="boton-principal"
                  onClick={() => abrir(j, 'Aprobada')}
                  disabled={trabajando}
                >
                  Aprobar
                </button>
                <button
                  type="button"
                  className="boton-suave peligro"
                  onClick={() => abrir(j, 'Rechazada')}
                  disabled={trabajando}
                >
                  Rechazar
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>

      {resolviendo && (
        <div
          className="correccion-fondo"
          onClick={(e) => e.target === e.currentTarget && !trabajando && setResolviendo(null)}
          role="presentation"
        >
          <form
            className="correccion"
            role="dialog"
            aria-modal="true"
            onSubmit={(e) => {
              e.preventDefault();
              onResolver(resolviendo.id, {
                estado: resolviendo.nuevoEstado,
                observacion: observacion.trim() || null,
              }).then(() => setResolviendo(null));
            }}
          >
            <button
              type="button"
              className="correccion-cerrar"
              onClick={() => setResolviendo(null)}
              disabled={trabajando}
              aria-label="Cerrar"
            >
              <IconoCerrar width={18} height={18} />
            </button>

            <h3>
              {resolviendo.nuevoEstado === 'Aprobada'
                ? '¿Aprobás la justificación?'
                : '¿Rechazás la justificación?'}
            </h3>
            <p className="correccion-trabajo">
              {resolviendo.alumno} · {resolviendo.curso}
              <br />«{resolviendo.motivo}»
            </p>

            {resolviendo.nuevoEstado === 'Aprobada' && (
              <p className="editor-nota">
                La falta queda como justificada. El porcentaje de asistencia no cambia.
              </p>
            )}

            <label>
              <span>
                {resolviendo.nuevoEstado === 'Rechazada' ? 'Por qué' : 'Observación'}
                {resolviendo.nuevoEstado === 'Aprobada' && <small> opcional</small>}
              </span>
              <textarea
                rows={3}
                value={observacion}
                maxLength={500}
                autoFocus
                placeholder={
                  resolviendo.nuevoEstado === 'Rechazada'
                    ? 'El alumno necesita saber qué le faltó'
                    : 'Certificado en regla'
                }
                onChange={(e) => setObservacion(e.target.value)}
              />
            </label>

            <div className="editor-botones">
              <button
                type="button"
                className="boton-suave"
                onClick={() => setResolviendo(null)}
                disabled={trabajando}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className={
                  resolviendo.nuevoEstado === 'Rechazada'
                    ? 'boton-principal peligroso'
                    : 'boton-principal'
                }
                disabled={
                  trabajando ||
                  (resolviendo.nuevoEstado === 'Rechazada' && !observacion.trim())
                }
              >
                {resolviendo.nuevoEstado === 'Aprobada' ? 'Sí, aprobar' : 'Sí, rechazar'}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}

// ===================== La pantalla =====================
const DESCRIPCIONES = {
  panel: 'Cómo venís con la asistencia en cada materia.',
  justificaciones: 'Los pedidos de justificación y en qué quedaron.',
};

const DESCRIPCIONES_DOCENTE = {
  panel: 'El resumen de tus materias.',
  justificaciones: 'Los pedidos de tus alumnos, los pendientes primero.',
};

export default function Asistencias() {
  const { vista } = useParams();
  const [usuario, setUsuario] = useState(null);
  const [justificaciones, setJustificaciones] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  const valida = VISTAS.some((v) => v.id === vista);

  useEffect(() => {
    obtenerUsuarioActual().then(setUsuario).catch(() => setUsuario(null));
  }, []);

  const traer = useCallback(() => {
    obtenerJustificaciones().then(setJustificaciones).catch(() => setJustificaciones(null));
  }, []);

  useEffect(traer, [traer]);

  async function resolver(id, datos) {
    setTrabajando(true);
    try {
      setJustificaciones(await resolverJustificacion(id, datos));
      avisar(`Justificación ${datos.estado.toLowerCase()}.`);
    } catch (e) {
      avisar(e.message, 'error');
      throw e;
    } finally {
      setTrabajando(false);
    }
  }

  if (!valida) return <Navigate to="/asistencias/panel" replace />;

  const esDocente = usuario?.rol === 'Docente';
  const descripciones = esDocente ? DESCRIPCIONES_DOCENTE : DESCRIPCIONES;

  return (
    <div className="pagina">
      <Encabezado titulo="Asistencias" descripcion={descripciones[vista]} />

      <nav className="pestanas" aria-label="Secciones de Asistencias">
        {VISTAS.map(({ id, nombre, Icono }) => (
          <NavLink
            key={id}
            to={`/asistencias/${id}`}
            className={({ isActive }) => (isActive ? 'pestana activa' : 'pestana')}
          >
            <Icono width={16} height={16} />
            {nombre}
            {id === 'justificaciones' && justificaciones?.pendientes > 0 && (
              <small className="pestana-cantidad alerta">{justificaciones.pendientes}</small>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="cuerpo-finales">
        {vista === 'panel' &&
          (usuario === null ? (
            <p className="texto-suave">Cargando…</p>
          ) : esDocente ? (
            <PanelDocente justificaciones={justificaciones} />
          ) : (
            <PanelAlumno />
          ))}

        {vista === 'justificaciones' && (
          <Justificaciones
            datos={justificaciones}
            onResolver={resolver}
            trabajando={trabajando}
          />
        )}
      </div>
    </div>
  );
}
