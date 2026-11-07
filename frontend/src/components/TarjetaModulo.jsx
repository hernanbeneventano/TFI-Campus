import { Link } from 'react-router-dom';
import { IconoEstrella, IconoCampana } from './Iconos.jsx';

// Qué hay de nuevo en el módulo, para el globito de ayuda de la campanita
function textoNovedades({ anuncios, tareas }) {
  const partes = [];
  if (anuncios) partes.push(`${anuncios} ${anuncios === 1 ? 'anuncio nuevo' : 'anuncios nuevos'}`);
  if (tareas) partes.push(`${tareas} ${tareas === 1 ? 'tarea nueva' : 'tareas nuevas'}`);
  return partes.join(' y ');
}

// Un módulo (materia). Se muestra como tarjeta o como fila según la vista elegida.
// El enlace del nombre se estira sobre toda la tarjeta (clase "enlace-tarjeta"),
// así se puede hacer clic en cualquier parte sin anidar botones dentro del enlace.
// El período no se repite acá: lo dice el título del cuatrimestre al que
// pertenece el grupo.
export default function TarjetaModulo({ modulo, vista, indice = 0, onFavorito }) {
  const hayNovedades = modulo.novedades?.total > 0;

  // Las tarjetas entran escalonadas al cambiar de vista, pero sin que la
  // última de una lista larga tarde una eternidad.
  const entrada = { '--retraso': `${Math.min(indice, 12) * 35}ms` };
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

  // Campanita a la derecha del nombre cuando hay algo publicado esta semana
  const novedad = hayNovedades && (
    <span className="novedad" title={textoNovedades(modulo.novedades)}>
      <IconoCampana width={16} height={16} />
    </span>
  );

  const enlace = (
    <Link to={`/modulos/${modulo.id}`} className="enlace-tarjeta">
      {modulo.nombre}
    </Link>
  );

  if (vista === 'lista') {
    return (
      <article
        className={hayNovedades ? 'modulo-fila con-novedades' : 'modulo-fila'}
        style={entrada}
      >
        <span className="modulo-color" style={{ background: modulo.color }} />
        <div className="modulo-fila-texto">
          <strong>{enlace}</strong>
          <small>
            {modulo.codigo} · {modulo.docente}
          </small>
        </div>
        {novedad}
        {botonFavorito}
      </article>
    );
  }

  return (
    <article
      className={hayNovedades ? 'modulo-tarjeta con-novedades' : 'modulo-tarjeta'}
      style={entrada}
    >
      <div className="modulo-banda" style={{ background: modulo.color }}>
        <span>{modulo.codigo}</span>
        {botonFavorito}
      </div>
      <div className="modulo-cuerpo">
        <h3 className="modulo-nombre">
          {enlace}
          {novedad}
        </h3>
        <p>{modulo.docente}</p>
      </div>
    </article>
  );
}
