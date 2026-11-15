import { useCallback, useEffect, useState } from 'react';
import { IconoCerrar, IconoDescargar, IconoVideo, IconoArchivo, IconoReloj } from './Iconos.jsx';
import Cuestionario from './modulo/Cuestionario.jsx';

function formatearFecha(iso) {
  return new Date(iso).toLocaleString('es-AR', {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatearDia(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' });
}

// Texto largo: cada párrafo del arreglo es un <p>
function Pagina({ item }) {
  return (
    <article className="visor-texto">
      {item.cuerpo.map((parrafo, i) => (
        <p key={i}>{parrafo}</p>
      ))}
    </article>
  );
}

// Todavía no hay archivos reales: se muestra el recuadro y el botón de descarga.
function Archivo({ item }) {
  const esVideo = item.formato === 'Video';
  return (
    <div className="visor-archivo">
      <div className="visor-previo">
        {esVideo ? <IconoVideo width={56} height={56} /> : <IconoArchivo width={56} height={56} />}
        <p>
          {item.formato} · {item.tamano}
        </p>
        <small className="texto-suave">
          La vista previa va a estar disponible cuando se suban los archivos reales.
        </small>
      </div>
      <button type="button" className="boton-principal">
        <IconoDescargar />
        Descargar
      </button>
    </div>
  );
}

// Un trabajo. Cómo se resuelve depende de cómo lo tomó la cátedra:
//
// - **virtual · entrega**     se sube un archivo
// - **virtual · cuestionario** se responde acá mismo y se corrige solo
// - **presencial**            no hay nada que subir: se rinde en el aula
function Tarea({ item }) {
  const cerrada = item.cerrada === true;
  const reabierta = item.cerrada === false;
  const atrasada = !item.entregada && !reabierta && new Date(item.fechaLimite) < new Date();
  const presencial = item.modalidad === 'presencial';

  return (
    <div className="visor-tarea">
      <div className={atrasada || cerrada ? 'visor-plazo atrasado' : 'visor-plazo'}>
        <IconoReloj />
        <div>
          <strong>{presencial ? 'Fecha del examen' : 'Fecha de entrega'}</strong>
          <span>{formatearFecha(item.fechaLimite)}</span>
        </div>
        {item.entregada && <span className="etiqueta entregada">Entregada</span>}
        {/* El cierre a mano pesa más que la fecha, así que se dice primero */}
        {cerrada && <span className="etiqueta atrasada">Entrega cerrada</span>}
        {reabierta && <span className="etiqueta">Entrega reabierta</span>}
        {atrasada && !cerrada && <span className="etiqueta atrasada">Atrasada</span>}
      </div>

      {item.consigna && (
        <article className="visor-texto">
          <p>{item.consigna}</p>
        </article>
      )}

      {item.formato === 'cuestionario' ? (
        <Cuestionario tareaId={item.tareaId} />
      ) : presencial ? (
        <div className="visor-entrega">
          <p className="texto-suave">
            Este examen es presencial: no hay nada que subir. La nota la carga el docente y la vas
            a ver en la pestaña Notas.
          </p>
        </div>
      ) : (
        <>
          <article className="visor-texto">
            <p>
              Subí tu resolución en un único archivo. Se toma en cuenta la última entrega hecha
              antes de la fecha límite.
            </p>
          </article>

          <div className="visor-entrega">
            <p className="texto-suave">
              La entrega de archivos se va a habilitar en la próxima etapa.
            </p>
            <button type="button" className="boton-principal" disabled>
              Subir entrega
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// Tablero de consultas: una columna por tema, con las publicaciones del curso.
function Tablero({ item }) {
  return (
    <div className="tablero">
      {item.columnas.map((columna) => (
        <section key={columna.titulo} className="tablero-columna">
          <h3>{columna.titulo}</h3>
          {columna.publicaciones.map((pub) => (
            <article key={pub.id} className="tablero-publicacion">
              <header>
                <strong>{pub.autor}</strong>
                <small>{formatearDia(pub.fecha)}</small>
              </header>
              <p>{pub.texto}</p>
            </article>
          ))}
          <button type="button" className="tablero-agregar">
            + Publicar
          </button>
        </section>
      ))}
    </div>
  );
}

// Pantalla completa sobre el módulo, con la ruta arriba y la X para volver.
// Al cerrar se marca "saliendo" para que se desvanezca antes de desaparecer.
export default function VisorItem({ curso, carpeta, item, onCerrar }) {
  const [saliendo, setSaliendo] = useState(false);

  const cerrar = useCallback(() => setSaliendo(true), []);

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape') cerrar();
    }
    window.addEventListener('keydown', alTeclado);
    return () => window.removeEventListener('keydown', alTeclado);
  }, [cerrar]);

  // Avisa recién cuando termina la animación del visor (no la de lo de adentro)
  function alTerminarAnimacion(e) {
    if (saliendo && e.target === e.currentTarget) onCerrar();
  }

  return (
    <div
      className={saliendo ? 'visor saliendo' : 'visor'}
      onAnimationEnd={alTerminarAnimacion}
    >
      <div className="visor-ruta">
        <button type="button" onClick={cerrar} aria-label="Cerrar">
          <IconoCerrar />
        </button>
        <span>
          {curso.codigo} · {curso.nombre}
        </span>
        <span className="visor-ruta-sep">›</span>
        <span>{carpeta.titulo}</span>
        <span className="visor-ruta-sep">›</span>
        <strong>{item.titulo}</strong>
      </div>

      <div className="visor-cuerpo">
        <div className="visor-contenido">
          <small className="texto-suave">{curso.nombre}</small>
          <h1>{item.titulo}</h1>

          {item.tipo === 'pagina' && <Pagina item={item} />}
          {item.tipo === 'archivo' && <Archivo item={item} />}
          {item.tipo === 'tarea' && <Tarea item={item} />}
          {item.tipo === 'tablero' && <Tablero item={item} />}
        </div>
      </div>
    </div>
  );
}
