import { Link } from 'react-router-dom';
import BarraProgreso from './BarraProgreso.jsx';
import { hace } from '../services/fechas.js';
import { IconoUsuario, IconoCalendario, IconoTarea, IconoNotas, IconoAvance } from './Iconos.jsx';

const DIA = 24 * 60 * 60 * 1000;

function cuandoEs(iso) {
  const dias = Math.round((new Date(iso) - new Date()) / DIA);
  if (dias === 0) return 'hoy';
  if (dias === 1) return 'mañana';
  return `en ${dias} días`;
}

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' });
}

// Panel derecho de un módulo. A propósito no repite lo que ya está en las
// pestañas de arriba (participantes, anuncios, notas): muestra el horario de
// cursada y lo que se viene, que de otro modo habría que ir a buscar.
export default function PanelModulo({ curso, participantes, cursada = [], proximas = [], avance }) {
  const docente = participantes.find((p) => p.rol === 'Docente');
  const estudiantes = participantes.filter((p) => p.rol === 'Estudiante').length;

  return (
    <aside className="panel">
      <section>
        <h2 className="panel-titulo">Equipo del módulo</h2>
        <div className="docente">
          <span className={`docente-avatar avatar-estado ${docente?.estado ?? 'desconectado'}`}>
            <IconoUsuario />
          </span>
          <div>
            <strong>{docente ? docente.nombre : curso.docente}</strong>
            <small>Docente a cargo</small>
            {docente?.ultimoAcceso && <small>Último acceso {hace(docente.ultimoAcceso)}</small>}
          </div>
        </div>
        <p className="panel-vacio">{estudiantes} estudiantes inscriptos</p>
      </section>

      {cursada.length > 0 && (
        <section>
          <h2 className="panel-titulo">Cursada</h2>
          <ul className="cursada">
            {cursada.map((c) => (
              <li key={`${c.dia}-${c.desde}`}>
                <span className="accion-icono">
                  <IconoCalendario width={18} height={18} />
                </span>
                <span>
                  <strong>{c.dia}</strong>
                  <small>
                    {c.desde} a {c.hasta} · {c.aula}
                  </small>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2 className="panel-titulo">Lo que se viene</h2>
        {proximas.length === 0 ? (
          <p className="panel-vacio">No hay nada agendado por ahora.</p>
        ) : (
          <ul className="proximas">
            {proximas.map((p) => {
              const contenido = (
                <>
                  <span className={`accion-icono ${p.tipo}`}>
                    {p.tipo === 'examen' ? (
                      <IconoNotas width={18} height={18} />
                    ) : (
                      <IconoTarea width={18} height={18} />
                    )}
                  </span>
                  <span>
                    <strong>{p.titulo}</strong>
                    <small>
                      {fechaCorta(p.fecha)} · {cuandoEs(p.fecha)}
                      {p.lugar ? ` · ${p.lugar}` : ''}
                    </small>
                  </span>
                </>
              );

              // Las entregas llevan a su pantalla; los exámenes no tienen una
              return (
                <li key={`${p.tipo}-${p.titulo}`}>
                  {p.tipo === 'entrega' ? (
                    <Link to={`/modulos/${curso.id}?tarea=${p.tareaId}`} className="proxima">
                      {contenido}
                    </Link>
                  ) : (
                    <span className="proxima">{contenido}</span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {avance.total > 0 && (
        <section>
          <h2 className="panel-titulo">Tu avance</h2>
          <div className="avance">
            <span className="accion-icono">
              <IconoAvance />
            </span>
            <BarraProgreso avance={avance} />
          </div>
          <p className="panel-vacio">
            {avance.hechos === avance.total
              ? '¡Completaste todo el material!'
              : `Te faltan ${avance.total - avance.hechos} de ${avance.total} recursos.`}
          </p>
        </section>
      )}
    </aside>
  );
}
