import { IconoEstrella } from './Iconos.jsx';

// Un módulo (materia). Se muestra como tarjeta o como fila según la vista elegida.
export default function TarjetaModulo({ modulo, vista, onFavorito }) {
  const botonFavorito = (
    <button
      type="button"
      className={modulo.favorito ? 'favorito activo' : 'favorito'}
      onClick={() => onFavorito(modulo.id)}
      aria-label={modulo.favorito ? 'Quitar de favoritos' : 'Marcar como favorito'}
      title={modulo.favorito ? 'Quitar de favoritos' : 'Marcar como favorito'}
    >
      <IconoEstrella llena={modulo.favorito} />
    </button>
  );

  if (vista === 'lista') {
    return (
      <article className="modulo-fila">
        <span className="modulo-color" style={{ background: modulo.color }} />
        <div className="modulo-fila-texto">
          <strong>{modulo.nombre}</strong>
          <small>
            {modulo.codigo} · {modulo.docente}
          </small>
        </div>
        <small className="modulo-fila-periodo">{modulo.periodo}</small>
        {botonFavorito}
      </article>
    );
  }

  return (
    <article className="modulo-tarjeta">
      <div className="modulo-banda" style={{ background: modulo.color }}>
        <span>{modulo.codigo}</span>
        {botonFavorito}
      </div>
      <div className="modulo-cuerpo">
        <h3>{modulo.nombre}</h3>
        <p>{modulo.docente}</p>
        <small>{modulo.periodo}</small>
      </div>
    </article>
  );
}
