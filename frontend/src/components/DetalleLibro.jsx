import { useEffect, useState } from 'react';
import { obtenerMaterial, enlaceDescarga, retirarMaterial } from '../services/api.js';
import { hace } from '../services/fechas.js';
import { nombreTipo, nombreEstado } from './TarjetaLibro.jsx';
import {
  IconoCerrar,
  IconoLibro,
  IconoDescargar,
  IconoEnlaceExterno,
  IconoEstrella,
  IconoAdvertencia,
} from './Iconos.jsx';

// Una fila de la ficha. Si el dato no vino, la fila no se dibuja: una ficha
// llena de "—" no dice nada.
function Dato({ nombre, children }) {
  if (!children) return null;
  return (
    <div className="ficha-dato">
      <span>{nombre}</span>
      <strong>{children}</strong>
    </div>
  );
}

const idiomas = { es: 'Español', en: 'Inglés', pt: 'Portugués', fr: 'Francés', it: 'Italiano' };

// La ficha completa, superpuesta sobre el catálogo. Se cierra con la X, con
// Escape o tocando afuera, igual que el lector de Novedades.
export default function DetalleLibro({ libro: inicial, onCerrar, onFavorito, onCambio, onAbrir }) {
  const [libro, setLibro] = useState(inicial);
  const [error, setError] = useState(null);
  const [retirando, setRetirando] = useState(false);

  // De la tarjeta llega lo justo; la ficha pide el resto (descripción,
  // relacionados, historial de moderación).
  useEffect(() => {
    let vigente = true;
    setLibro(inicial);
    setError(null);
    obtenerMaterial(inicial.id)
      .then((completo) => vigente && setLibro(completo))
      .catch((e) => vigente && setError(e.message));
    return () => {
      vigente = false;
    };
  }, [inicial]);

  // Escape cierra, y mientras está abierta la página de atrás no se mueve
  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape') onCerrar();
    }
    document.addEventListener('keydown', alTeclado);
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
  }, [onCerrar]);

  const externo = Boolean(libro.externo);

  function retirar() {
    if (!window.confirm(`¿Retirar "${libro.titulo}" de la biblioteca? No se puede deshacer.`)) {
      return;
    }
    setRetirando(true);
    retirarMaterial(libro.id)
      .then(() => {
        onCambio?.();
        onCerrar();
      })
      .catch((e) => {
        setError(e.message);
        setRetirando(false);
      });
  }

  return (
    <div className="lector-fondo" onClick={onCerrar} role="presentation">
      <div
        className="lector ficha"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={libro.titulo}
      >
        <button type="button" className="lector-cerrar" onClick={onCerrar} aria-label="Cerrar">
          <IconoCerrar />
        </button>

        <div className="ficha-cabecera">
          <div className="ficha-portada">
            {libro.portada ? (
              <img src={libro.portada} alt="" />
            ) : (
              <span className="libro-portada-vacia grande" aria-hidden="true">
                <IconoLibro width={46} height={46} />
              </span>
            )}
          </div>

          <div className="ficha-titulo">
            <div className="libro-etiquetas">
              <span className={externo ? 'libro-fuente externa' : 'libro-fuente'}>
                {externo ? libro.nombreFuente : 'En el campus'}
              </span>
              {!externo && <span className="libro-tipo">{nombreTipo[libro.tipo] ?? 'Material'}</span>}
              {!externo && libro.estado !== 'aprobado' && (
                <span className={`libro-estado ${libro.estado}`}>{nombreEstado[libro.estado]}</span>
              )}
              {externo && libro.dominioPublico && <span className="libro-libre">Dominio público</span>}
              {libro.tambienEn && <span className="libro-fuente externa">También en {libro.tambienEn}</span>}
            </div>

            <h2>{libro.titulo}</h2>
            {libro.subtitulo && <p className="ficha-subtitulo">{libro.subtitulo}</p>}
            {libro.autor && <p className="libro-autor">{libro.autor}</p>}

            <button
              type="button"
              className={libro.favorito ? 'boton-suave activo' : 'boton-suave'}
              onClick={() => onFavorito?.(libro)}
              aria-pressed={Boolean(libro.favorito)}
            >
              <IconoEstrella llena={libro.favorito} width={16} height={16} />
              {libro.favorito ? 'Guardado' : 'Guardar'}
            </button>
          </div>
        </div>

        {error && <p className="error">{error}</p>}

        {libro.descripcion && <p className="ficha-descripcion">{libro.descripcion}</p>}

        <div className="ficha-datos">
          <Dato nombre="Editorial">{libro.editorial}</Dato>
          <Dato nombre="Publicado">{libro.anioPublicacion}</Dato>
          <Dato nombre="ISBN">{libro.isbn}</Dato>
          <Dato nombre="Idioma">{idiomas[libro.idioma] ?? libro.idioma}</Dato>
          <Dato nombre="Categoría">{libro.nombreCategoria}</Dato>
          <Dato nombre="Materia">{libro.materia}</Dato>
          <Dato nombre="Carrera">{libro.carrera}</Dato>
          <Dato nombre="Año">{libro.anio}</Dato>
          <Dato nombre="Licencia">{libro.licencia}</Dato>
          <Dato nombre="Aportado por">{libro.subidoPorNombre}</Dato>
          <Dato nombre="Agregado">{libro.creado ? hace(libro.creado) : null}</Dato>
          {Boolean(libro.categorias?.length) && (
            <Dato nombre="Temas">{libro.categorias.slice(0, 4).join(' · ')}</Dato>
          )}
        </div>

        {/* Solo lo que la fuente ofrece de verdad. Si no hay nada, se dice. */}
        <div className="ficha-acciones">
          {libro.tieneArchivo && (
            <a className="boton-principal" href={enlaceDescarga(libro.id)} download>
              <IconoDescargar width={18} height={18} />
              Descargar {libro.archivo?.nombre?.split('.').pop()?.toUpperCase()}
            </a>
          )}
          {libro.enlaceLectura && (
            <a
              className="boton-principal"
              href={libro.enlaceLectura}
              target="_blank"
              rel="noreferrer noopener"
            >
              <IconoEnlaceExterno width={18} height={18} />
              Leer completo
            </a>
          )}
          {libro.enlaceDescarga && (
            <a
              className="boton-principal"
              href={libro.enlaceDescarga}
              target="_blank"
              rel="noreferrer noopener"
            >
              <IconoDescargar width={18} height={18} />
              Descargar PDF
            </a>
          )}
          {libro.enlacePrestamo && (
            <a
              className="boton-suave"
              href={libro.enlacePrestamo}
              target="_blank"
              rel="noreferrer noopener"
            >
              <IconoEnlaceExterno width={16} height={16} />
              Pedir prestado
            </a>
          )}
          {libro.enlaceVistaPrevia && (
            <a
              className="boton-suave"
              href={libro.enlaceVistaPrevia}
              target="_blank"
              rel="noreferrer noopener"
            >
              <IconoEnlaceExterno width={16} height={16} />
              Vista previa
            </a>
          )}
          {(libro.enlaceFicha || libro.enlace) && (
            <a
              className="boton-suave"
              href={libro.enlaceFicha ?? libro.enlace}
              target="_blank"
              rel="noreferrer noopener"
            >
              <IconoEnlaceExterno width={16} height={16} />
              Abrir en la fuente
            </a>
          )}

          {libro.puedeEditar && (
            <button type="button" className="boton-suave peligro" onClick={retirar} disabled={retirando}>
              {retirando ? 'Retirando…' : 'Retirar de la biblioteca'}
            </button>
          )}
        </div>

        {!libro.tieneArchivo &&
          !libro.enlaceLectura &&
          !libro.enlaceDescarga &&
          !libro.enlacePrestamo &&
          !libro.enlaceFicha &&
          !libro.enlace && (
            <p className="ficha-aviso">
              <IconoAdvertencia width={16} height={16} />
              Esta fuente no ofrece lectura ni descarga en línea. Se puede consultar en la
              biblioteca de la facultad.
            </p>
          )}

        {libro.motivo && libro.estado === 'rechazado' && (
          <p className="ficha-aviso rechazo">
            <IconoAdvertencia width={16} height={16} />
            Rechazado: {libro.motivo}
          </p>
        )}

        {Boolean(libro.relacionados?.length) && (
          <section className="ficha-relacionados">
            <h3>Material relacionado</h3>
            <ul>
              {libro.relacionados.map((otro) => (
                <li key={otro.id}>
                  <button type="button" onClick={() => onAbrir?.(otro)}>
                    <IconoLibro width={18} height={18} />
                    <span>
                      <strong>{otro.titulo}</strong>
                      <small>{[otro.autor, otro.nombreCategoria].filter(Boolean).join(' · ')}</small>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
