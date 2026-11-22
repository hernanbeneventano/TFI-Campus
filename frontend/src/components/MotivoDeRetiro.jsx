// Retirar una publicación de otra persona: el cartel que pide el motivo.
//
// Lo usan Novedades y el Foro, que son los dos lugares donde la
// administración saca algo que escribió otro. Sin motivo, a quien publicó le
// desaparece el texto y no tiene forma de saber por qué ni con quién
// hablarlo, así que el motivo es obligatorio y se le manda por Mensajes.
//
// Cuando uno retira **lo suyo** no hace falta motivo: ahí el cartel solo
// reconfirma, porque la baja no se deshace.

import { useEffect, useState } from 'react';
import { IconoCerrar } from './Iconos.jsx';

export default function MotivoDeRetiro({
  titulo,
  queSeRetira,
  autor,
  exigeMotivo,
  trabajando,
  onCerrar,
  onRetirar,
}) {
  const [motivo, setMotivo] = useState('');

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !trabajando) onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    return () => window.removeEventListener('keydown', alTeclado);
  }, [onCerrar, trabajando]);

  const falta = exigeMotivo && !motivo.trim();

  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && !trabajando && onCerrar()}
      role="presentation"
    >
      <form
        className="correccion"
        role="dialog"
        aria-modal="true"
        onSubmit={(e) => {
          e.preventDefault();
          onRetirar(motivo.trim());
        }}
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

        <h3>{titulo}</h3>
        <p className="correccion-trabajo">{queSeRetira}</p>

        {exigeMotivo ? (
          <label>
            <span>Motivo *</span>
            <textarea
              rows={4}
              value={motivo}
              maxLength={500}
              autoFocus
              placeholder="Por qué se retira: fuera de lugar, repetido, datos personales…"
              onChange={(e) => setMotivo(e.target.value)}
            />
            <small className="texto-suave">
              {autor} va a recibir este motivo en Mensajes.
            </small>
          </label>
        ) : (
          <p className="texto-suave">Se retira del campus y no se puede deshacer.</p>
        )}

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={trabajando}>
            Cancelar
          </button>
          <button
            type="submit"
            className="boton-principal peligro"
            disabled={trabajando || falta}
          >
            {trabajando ? 'Retirando…' : 'Retirar'}
          </button>
        </div>
      </form>
    </div>
  );
}
