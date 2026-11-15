// Lo que ve el alumno en la pestaña Notas: **las suyas y nada más**.
//
// La grilla con todo el curso es del docente. Acá no hay forma de ver las de
// un compañero, y tampoco la hay en el servidor: de quién son las notas que
// se piden sale de la sesión, no de la pantalla.
//
// Arriba va la nota final, que es lo que se viene a mirar; abajo, de dónde
// sale. Si falta corregir algo, se dice: un promedio sobre la mitad de los
// trabajos no es la nota final todavía.

import { fechaLarga } from '../../services/fechas.js';
import { IconoCheckCirculo, IconoAdvertencia, IconoReloj, IconoNotas } from '../Iconos.jsx';

const MODALIDAD = {
  entrega: 'Entrega',
  cuestionario: 'Cuestionario',
  presencial: 'Presencial',
};

export default function MisNotas({ datos }) {
  if (!datos) return <p className="texto-suave">Cargando tus notas…</p>;

  const { trabajos, cierre, notaParaAprobar } = datos;

  if (trabajos.length === 0) {
    return <p className="vacio">Todavía no hay trabajos en este módulo.</p>;
  }

  const sinCorregir = trabajos.filter((t) => t.entregado && t.nota === null).length;

  return (
    <>
      <section className={`mi-cierre ${cierre.vaAFinal ? 'final' : ''}`}>
        <div className="mi-cierre-nota">
          <strong>{cierre.promedio ?? '—'}</strong>
          <small>nota final</small>
        </div>

        <div className="mi-cierre-texto">
          <h3>
            {cierre.condicion === 'Sin notas' ? (
              <>Todavía no tenés notas</>
            ) : cierre.vaAFinal ? (
              <>
                <IconoAdvertencia width={18} height={18} />
                Vas a final
              </>
            ) : (
              <>
                <IconoCheckCirculo width={18} height={18} />
                Cursada aprobada
              </>
            )}
          </h3>
          <p>
            {cierre.condicion === 'Sin notas'
              ? 'Cuando el docente corrija tu primer trabajo vas a ver acá tu promedio.'
              : `Promedio de ${cierre.corregidas} ${
                  cierre.corregidas === 1 ? 'nota corregida' : 'notas corregidas'
                }.`}
          </p>
          {!cierre.automatico && cierre.observacion && (
            <p className="mi-cierre-nota-docente">
              El docente fijó esta condición: «{cierre.observacion}»
            </p>
          )}
          {sinCorregir > 0 && (
            <p className="mi-cierre-pendiente">
              Te falta que corrijan {sinCorregir}{' '}
              {sinCorregir === 1 ? 'entrega' : 'entregas'}: la nota final puede cambiar.
            </p>
          )}
        </div>
      </section>

      <ul className="mis-trabajos">
        {trabajos.map((t) => (
          <li key={t.tareaId} className="mi-trabajo">
            <div className="mi-trabajo-texto">
              <strong>{t.titulo}</strong>
              <small>
                {MODALIDAD[t.formato] ?? 'Entrega'} · vence el {fechaLarga(t.fechaLimite)}
              </small>
              {t.entregado ? (
                <small className="entregado">Entregado el {fechaLarga(t.fecha)}</small>
              ) : (
                <small className="sin-entregar">
                  <IconoReloj width={13} height={13} />
                  Sin entregar
                </small>
              )}
              {t.devolucion && <p className="mi-trabajo-devolucion">«{t.devolucion}»</p>}
            </div>

            <div className="mi-trabajo-nota">
              {t.nota !== null && t.nota !== undefined ? (
                <span className={`nota-celda ${t.nota >= notaParaAprobar ? 'aprobada' : 'desaprobada'}`}>
                  {t.nota}
                </span>
              ) : (
                <span className="nota-celda vacia" title="Sin corregir">
                  <IconoNotas width={15} height={15} />
                </span>
              )}
              {t.estado && <small>{t.estado}</small>}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
