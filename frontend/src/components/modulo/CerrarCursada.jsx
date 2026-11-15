// Fijar a mano la condición de un alumno.
//
// Normalmente la condición sale del promedio y no hay que tocar nada. Pero
// hay motivos que el sistema no conoce —una recuperación, una falta
// justificada, un acta ya firmada— y entonces decide el docente. Lo que fija
// pesa más que el cálculo, y queda marcado como puesto a mano para que no se
// confunda con lo automático.

import { useEffect, useRef, useState } from 'react';
import { IconoCerrar } from '../Iconos.jsx';

export default function CerrarCursada({ alumno, onGuardar, onCerrar, trabajando }) {
  const { cierre } = alumno;
  const [condicion, setCondicion] = useState(cierre.condicion);
  const [observacion, setObservacion] = useState(cierre.observacion ?? '');
  const primero = useRef(null);

  useEffect(() => {
    primero.current?.focus();
    function alTeclado(e) {
      if (e.key === 'Escape' && !trabajando) onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    return () => window.removeEventListener('keydown', alTeclado);
  }, [onCerrar, trabajando]);

  function enviar(e) {
    e.preventDefault();
    onGuardar({
      personaId: alumno.id,
      condicion,
      observacion: observacion.trim() || null,
    });
  }

  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && !trabajando && onCerrar()}
      role="presentation"
    >
      <form
        className="correccion"
        onSubmit={enviar}
        role="dialog"
        aria-modal="true"
        aria-label={`Cerrar la cursada de ${alumno.nombre}`}
      >
        <button
          type="button"
          className="correccion-cerrar"
          onClick={onCerrar}
          disabled={trabajando}
          aria-label="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        <h3>{alumno.nombre}</h3>
        <p className="correccion-trabajo">
          Promedio {cierre.promedio ?? '—'} sobre {cierre.corregidas}{' '}
          {cierre.corregidas === 1 ? 'nota corregida' : 'notas corregidas'}
          {cierre.automatico
            ? ` · por promedio le corresponde «${cierre.condicionCalculada}»`
            : ` · el cálculo daba «${cierre.condicionCalculada}»`}
        </p>

        <fieldset className="editor-tipos compacto">
          <legend>Condición</legend>
          <div>
            <label className={condicion === 'Aprobada' ? 'tipo elegido' : 'tipo'}>
              <input
                ref={primero}
                type="radio"
                name="condicion"
                checked={condicion === 'Aprobada'}
                onChange={() => setCondicion('Aprobada')}
              />
              <strong>Aprobada</strong>
              <small>Cierra la cursada</small>
            </label>
            <label className={condicion === 'Va a final' ? 'tipo elegido' : 'tipo'}>
              <input
                type="radio"
                name="condicion"
                checked={condicion === 'Va a final'}
                onChange={() => setCondicion('Va a final')}
              />
              <strong>Va a final</strong>
              <small>Tiene que rendir</small>
            </label>
          </div>
        </fieldset>

        <label>
          <span>
            Por qué <small>queda registrado con tu nombre</small>
          </span>
          <textarea
            rows={3}
            value={observacion}
            maxLength={1000}
            onChange={(e) => setObservacion(e.target.value)}
            placeholder="Recuperó el parcial en la fecha extraordinaria."
          />
        </label>

        <div className="editor-botones">
          {!cierre.automatico && (
            <button
              type="button"
              className="boton-suave"
              disabled={trabajando}
              onClick={() => onGuardar({ personaId: alumno.id, condicion: null })}
              title="Vuelve a mandar el promedio"
            >
              Volver al cálculo
            </button>
          )}
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={trabajando}>
            Cancelar
          </button>
          <button type="submit" className="boton-principal" disabled={trabajando}>
            Fijar la condición
          </button>
        </div>
      </form>
    </div>
  );
}
