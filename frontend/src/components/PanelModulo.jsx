import BarraProgreso from './BarraProgreso.jsx';
import { hace } from '../services/fechas.js';
import { IconoUsuario, IconoPersonas, IconoAnuncio, IconoNotas, IconoAvance } from './Iconos.jsx';

// Panel derecho de un módulo: quién lo dicta, accesos a las otras pestañas
// y cuánto del material lleva marcado el alumno.
export default function PanelModulo({ curso, participantes, anuncios, avance, onIrA }) {
  const docente = participantes.find((p) => p.rol === 'Docente');
  const estudiantes = participantes.filter((p) => p.rol === 'Estudiante').length;

  const acciones = [
    {
      clave: 'participantes',
      Icono: IconoPersonas,
      titulo: 'Participantes',
      detalle: `Ver a los ${participantes.length} del módulo`,
    },
    {
      clave: 'anuncios',
      Icono: IconoAnuncio,
      titulo: 'Anuncios',
      detalle: anuncios.length === 1 ? 'Ver el único anuncio' : `Ver los ${anuncios.length} anuncios`,
    },
    {
      clave: 'notas',
      Icono: IconoNotas,
      titulo: 'Notas',
      detalle: 'Ver tus calificaciones',
    },
  ];

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

      <section>
        <h2 className="panel-titulo">Detalles y acciones</h2>
        <ul className="acciones">
          {acciones.map(({ clave, Icono, titulo, detalle }) => (
            <li key={clave}>
              <button type="button" className="accion" onClick={() => onIrA(clave)}>
                <span className="accion-icono">
                  <Icono />
                </span>
                <span>
                  <strong>{titulo}</strong>
                  <small>{detalle}</small>
                </span>
              </button>
            </li>
          ))}
        </ul>
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
