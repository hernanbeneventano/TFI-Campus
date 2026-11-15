// El diálogo para corregir una entrega: nota, condición y devolución.
//
// Vive aparte porque lo abren dos pantallas distintas: la grilla de notas
// (una celda) y el detalle de entregas de una sección (un alumno y su
// trabajo). Corregir es escribir tres cosas, no solo un número.

import { useEffect, useRef, useState } from 'react';
import { IconoCerrar } from '../Iconos.jsx';

export default function Correccion({ alumno, trabajo, nota, estados, onGuardar, onCerrar, trabajando }) {
  const [valor, setValor] = useState(nota?.nota ?? '');
  const [estado, setEstado] = useState(nota?.estado ?? 'Aprobado');
  const [comentario, setComentario] = useState(nota?.comentario ?? '');
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
      tareaId: trabajo.id,
      personaId: alumno.id,
      // Vacío borra la celda: es la forma de deshacer una carga equivocada
      nota: valor === '' ? null : Number(valor),
      estado,
      comentario: comentario.trim() || null,
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
        aria-label={`Corregir a ${alumno.nombre}`}
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
        <p className="correccion-trabajo">{trabajo.titulo}</p>

        <div className="editor-fila">
          <label>
            <span>
              Nota <small>de 1 a 10, vacío para borrar</small>
            </span>
            <input
              ref={primero}
              type="number"
              min="1"
              max="10"
              step="0.5"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
            />
          </label>
          <label>
            <span>Condición</span>
            <select value={estado} onChange={(e) => setEstado(e.target.value)}>
              {estados.map((x) => (
                <option key={x} value={x}>
                  {x}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label>
          <span>
            Devolución <small>la ve el alumno</small>
          </span>
          <textarea
            rows={4}
            value={comentario}
            maxLength={1000}
            onChange={(e) => setComentario(e.target.value)}
            placeholder="Qué estuvo bien y qué hay que corregir."
          />
        </label>

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={trabajando}>
            Cancelar
          </button>
          <button type="submit" className="boton-principal" disabled={trabajando}>
            Guardar
          </button>
        </div>
      </form>
    </div>
  );
}
