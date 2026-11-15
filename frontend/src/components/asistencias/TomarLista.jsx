// Tomar lista de una clase.
//
// Arranca con **todos presentes**: en una clase normal falta uno o dos, así
// que marcar las excepciones es mucho menos trabajo que marcar uno por uno.
// Eso también evita el error de guardar media lista creyendo que está
// completa.
//
// Una clase ya cerrada se puede corregir, pero pidiendo el motivo: es lo que
// convierte una corrección en algo que después se puede revisar.

import { useEffect, useState } from 'react';
import { fechaConDia } from '../../services/fechas.js';
import { ESTADOS, Situacion } from './comun.jsx';
import { IconoCerrar, IconoCheckCirculo } from '../Iconos.jsx';

const ORDEN = ['presente', 'ausente', 'justificada'];

export default function TomarLista({ datos, onGuardar, onCerrar, trabajando }) {
  const { clase, alumnos, curso } = datos;
  const cerrada = Boolean(clase.cerrada);

  // Lo que no tiene registro arranca en presente
  const [estados, setEstados] = useState(() =>
    Object.fromEntries(alumnos.map((a) => [a.id, a.estado ?? 'presente']))
  );
  const [observaciones, setObservaciones] = useState(() =>
    Object.fromEntries(alumnos.map((a) => [a.id, a.observacion ?? '']))
  );
  const [motivo, setMotivo] = useState('');
  const [cerrar, setCerrar] = useState(false);

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !trabajando) onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
  }, [onCerrar, trabajando]);

  const cuenta = ORDEN.reduce(
    (acc, e) => ({ ...acc, [e]: Object.values(estados).filter((x) => x === e).length }),
    {}
  );

  function enviar(e) {
    e.preventDefault();
    onGuardar({
      asistencias: alumnos.map((a) => ({
        personaId: a.id,
        estado: estados[a.id],
        observacion: observaciones[a.id]?.trim() || null,
      })),
      motivo: motivo.trim() || null,
      cerrar,
    });
  }

  return (
    <div
      className="lista-fondo"
      onClick={(e) => e.target === e.currentTarget && !trabajando && onCerrar()}
      role="presentation"
    >
      <form
        className="lista-asistencia"
        onSubmit={enviar}
        role="dialog"
        aria-modal="true"
        aria-label={`Lista del ${fechaConDia(clase.fecha)}`}
      >
        <button
          type="button"
          className="lista-cerrar"
          onClick={onCerrar}
          disabled={trabajando}
          aria-label="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        <header className="lista-encabezado">
          <div>
            <h2>{fechaConDia(clase.fecha)}</h2>
            <p>
              {curso.codigo} · {clase.tema || 'Sin tema cargado'}
              {cerrada && <> · registro cerrado</>}
            </p>
          </div>

          <button
            type="button"
            className="boton-suave"
            onClick={() =>
              setEstados(Object.fromEntries(alumnos.map((a) => [a.id, 'presente'])))
            }
            disabled={trabajando}
          >
            <IconoCheckCirculo width={15} height={15} />
            Todos presentes
          </button>
        </header>

        <div className="lista-cuenta">
          {ORDEN.map((e) => (
            <span key={e} className={`cuenta ${ESTADOS[e].clase}`}>
              <strong>{cuenta[e]}</strong> {ESTADOS[e].texto.toLowerCase()}
            </span>
          ))}
        </div>

        <ul className="lista-alumnos">
          {alumnos.map((a) => (
            <li key={a.id}>
              <div className="lista-alumno">
                <strong>{a.nombre}</strong>
                <span className="lista-alumno-datos">
                  {a.porcentaje !== null && <small>{a.porcentaje}% de asistencia</small>}
                  <Situacion estado={a.situacion} chica />
                </span>
                {a.justificacion && (
                  <small className={`lista-justificacion ${a.justificacion.estado.toLowerCase()}`}>
                    Justificación {a.justificacion.estado.toLowerCase()}: {a.justificacion.motivo}
                  </small>
                )}
              </div>

              <div className="lista-estados" role="group" aria-label={`Asistencia de ${a.nombre}`}>
                {ORDEN.map((e) => (
                  <label
                    key={e}
                    className={estados[a.id] === e ? `opcion-estado ${ESTADOS[e].clase} elegida` : 'opcion-estado'}
                    title={ESTADOS[e].texto}
                  >
                    <input
                      type="radio"
                      name={`alumno-${a.id}`}
                      checked={estados[a.id] === e}
                      onChange={() => setEstados((x) => ({ ...x, [a.id]: e }))}
                    />
                    <span aria-hidden="true">{ESTADOS[e].corto}</span>
                    <span className="oculto">{ESTADOS[e].texto}</span>
                  </label>
                ))}
              </div>

              {/* El campo se abre solo al marcar la falta como justificada:
                  es ahí donde hay algo que escribir, y lo que se escribe es
                  el motivo. En los otros estados no hace falta y solo
                  agregaría una caja vacía por alumno. */}
              {estados[a.id] === 'justificada' && (
                <input
                  type="text"
                  className="lista-observacion"
                  value={observaciones[a.id]}
                  maxLength={500}
                  autoFocus
                  placeholder="Por qué se justifica"
                  onChange={(e) =>
                    setObservaciones((x) => ({ ...x, [a.id]: e.target.value }))
                  }
                />
              )}
            </li>
          ))}
        </ul>

        {cerrada && (
          <label className="lista-motivo">
            <span>Motivo de la corrección</span>
            <input
              type="text"
              value={motivo}
              maxLength={500}
              placeholder="Por qué se modifica un registro ya cerrado"
              onChange={(e) => setMotivo(e.target.value)}
            />
          </label>
        )}

        <footer className="lista-pie">
          {!cerrada && (
            <label className="lista-cerrar-registro">
              <input
                type="checkbox"
                className="interruptor"
                checked={cerrar}
                onChange={(e) => setCerrar(e.target.checked)}
              />
              <span>Cerrar el registro</span>
            </label>
          )}

          <div className="editor-botones">
            <button
              type="button"
              className="boton-suave"
              onClick={onCerrar}
              disabled={trabajando}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="boton-principal"
              disabled={trabajando || (cerrada && !motivo.trim())}
            >
              {trabajando ? 'Guardando…' : 'Guardar la lista'}
            </button>
          </div>
        </footer>
      </form>
    </div>
  );
}
