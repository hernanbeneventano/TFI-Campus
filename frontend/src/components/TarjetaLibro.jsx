import { IconoLibro, IconoEstrella, IconoEnlaceExterno, IconoDescargar } from './Iconos.jsx';

// Cómo se llama cada tipo en pantalla. El valor que viaja es el de la lista
// TIPOS_MATERIAL del backend.
export const nombreTipo = {
  libro: 'Libro',
  apunte: 'Apunte',
  resumen: 'Resumen',
  manual: 'Manual',
  guia: 'Guía',
  ejercicio: 'Ejercicios',
  otro: 'Material',
};

export const nombreEstado = {
  pendiente: 'En revisión',
  aprobado: 'Publicado',
  rechazado: 'Rechazado',
};

// Un resultado del catálogo, venga de la biblioteca del campus o de Google
// Books / Open Library. La diferencia se marca con la etiqueta de la fuente:
// de un libro externo nunca tenemos el archivo, solo adónde ir a buscarlo.
export default function TarjetaLibro({ libro, indice = 0, onAbrir, onFavorito }) {
  const externo = Boolean(libro.externo);

  // Qué se puede hacer de verdad con este libro. Si la fuente no ofrece nada,
  // no se inventa un botón: queda solo "Ver detalles".
  const sePuedeLeer = externo && libro.enlaceLectura;
  const sePuedeDescargar = externo ? Boolean(libro.enlaceDescarga) : Boolean(libro.tieneArchivo);

  // Las tarjetas entran escalonadas, igual que los módulos
  const entrada = { '--retraso': `${Math.min(indice, 12) * 35}ms` };

  function alFavorito(e) {
    e.stopPropagation();
    onFavorito?.(libro);
  }

  return (
    <article className="libro-tarjeta" style={entrada}>
      <button
        type="button"
        className="libro-portada"
        onClick={() => onAbrir?.(libro)}
        aria-label={`Ver los detalles de ${libro.titulo}`}
      >
        {libro.portada ? (
          <img src={libro.portada} alt="" loading="lazy" />
        ) : (
          <span className="libro-portada-vacia" aria-hidden="true">
            <IconoLibro width={30} height={30} />
          </span>
        )}
      </button>

      <div className="libro-cuerpo">
        <div className="libro-etiquetas">
          <span className={externo ? 'libro-fuente externa' : 'libro-fuente'}>
            {externo ? libro.nombreFuente : 'En el campus'}
          </span>
          {!externo && <span className="libro-tipo">{nombreTipo[libro.tipo] ?? 'Material'}</span>}
          {!externo && libro.estado !== 'aprobado' && (
            <span className={`libro-estado ${libro.estado}`}>{nombreEstado[libro.estado]}</span>
          )}
          {externo && libro.dominioPublico && <span className="libro-libre">Dominio público</span>}
        </div>

        <h3>
          <button type="button" className="libro-titulo" onClick={() => onAbrir?.(libro)}>
            {libro.titulo}
          </button>
        </h3>

        {libro.autor && <p className="libro-autor">{libro.autor}</p>}

        <p className="libro-datos">
          {[
            externo ? libro.editorial : libro.nombreCategoria,
            externo ? libro.anioPublicacion : libro.materia,
          ]
            .filter(Boolean)
            .join(' · ')}
        </p>

        <div className="libro-acciones">
          <button type="button" className="boton-suave" onClick={() => onAbrir?.(libro)}>
            Ver detalles
          </button>

          {sePuedeLeer && (
            <a
              className="libro-accion"
              href={libro.enlaceLectura}
              target="_blank"
              rel="noreferrer noopener"
              onClick={(e) => e.stopPropagation()}
            >
              <IconoEnlaceExterno width={16} height={16} />
              Leer
            </a>
          )}
          {sePuedeDescargar && (
            <span className="libro-accion-nota" title="Tiene archivo para descargar">
              <IconoDescargar width={16} height={16} />
              Descargable
            </span>
          )}

          <button
            type="button"
            className={libro.favorito ? 'libro-favorito activo' : 'libro-favorito'}
            onClick={alFavorito}
            aria-pressed={Boolean(libro.favorito)}
            aria-label={libro.favorito ? 'Quitar de favoritos' : 'Guardar en favoritos'}
            title={libro.favorito ? 'Quitar de favoritos' : 'Guardar en favoritos'}
          >
            <IconoEstrella llena={libro.favorito} width={18} height={18} />
          </button>
        </div>
      </div>
    </article>
  );
}
