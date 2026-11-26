import { useCallback, useEffect, useState } from 'react';
import {
  IconoCerrar,
  IconoDescargar,
  IconoVideo,
  IconoArchivo,
  IconoReloj,
  IconoCheckCirculo,
  IconoSubir,
} from './Iconos.jsx';
import {
  descargarArchivoDeElemento,
  obtenerMiEntrega,
  obtenerEntregasDeTarea,
  publicarEnTablero,
  entregarTrabajo,
  retirarMiEntrega,
} from '../services/api.js';
import Avatar from './Avatar.jsx';
import VisorDocumento, { sePuedeVer } from './VisorDocumento.jsx';
import { avisar } from '../services/avisos.js';
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

// Un elemento de tipo archivo puede tener el archivo subido o ser solo una
// referencia —un video que vive en otro lado, un enlace—. Se muestra lo que
// hay: no se ofrece descargar algo que no está.
function Archivo({ curso, carpeta, item }) {
  const esVideo = item.formato === 'Video';
  const subido = item.archivo;
  const seVe = sePuedeVer(subido);

  function descargar() {
    if (!subido) return;
    descargarArchivoDeElemento(curso.id, carpeta.id, item.id, subido.nombre)
      .catch((error) => avisar(error.message, 'error'));
  }

  return (
    <div className="visor-archivo">
      {seVe ? (
        <VisorDocumento archivo={subido} descargar={descargar} />
      ) : (
        <div className="visor-previo">
          {esVideo ? <IconoVideo width={56} height={56} /> : <IconoArchivo width={56} height={56} />}
          <p>{[item.formato, item.tamano].filter(Boolean).join(' · ')}</p>
          {subido ? (
            <small className="texto-suave">{subido.nombre}</small>
          ) : (
            <small className="texto-suave">
              La cátedra todavía no subió el archivo de este elemento.
            </small>
          )}
        </div>
      )}

      {/* Cuando se puede mirar, el visor ya trae su propio Descargar, pegado
          al borde del documento. */}
      {subido && !seVe && (
        <button type="button" className="boton-principal" onClick={descargar}>
          <IconoDescargar />
          Descargar
        </button>
      )}
    </div>
  );
}

/** Subir el trabajo, verlo subir y poder cambiarlo.
 *
 * **Se puede volver a entregar y vale la última**: lo contrario del
 * cuestionario, que se responde una sola vez. Lo que se corrige acá es un
 * trabajo, y corregir una versión vieja porque alguien se equivocó de archivo
 * no le sirve a nadie.
 *
 * El estado lo manda el servidor (`abierta`), no la fecha: el docente puede
 * cortar antes o dar prórroga, y la pantalla tiene que decir lo mismo que va
 * a hacer el servidor cuando se toque el botón.
 */
function MiEntrega({ tareaId, onCambio }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [elegido, setElegido] = useState(null);
  const [subiendo, setSubiendo] = useState(false);
  const [avance, setAvance] = useState(0);
  const [retirando, setRetirando] = useState(false);

  useEffect(() => {
    obtenerMiEntrega(tareaId)
      .then((x) => {
        setDatos(x);
        // La etiqueta «Entregada» de arriba la dibuja el visor, con el dato
        // que trajo la pantalla del módulo al abrirse. Si no se le avisa,
        // sigue diciendo «Entregada» después de retirar.
        onCambio?.(Boolean(x.entrega));
      })
      .catch((e) => setError(e.message));
  }, [tareaId, onCambio]);

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  const { entrega, abierta, maximoMb, formatos } = datos;

  function tomar(e) {
    const archivo = e.target.files?.[0];
    e.target.value = '';
    if (!archivo) return;
    const extension = archivo.name.split('.').pop()?.toLowerCase();
    if (!formatos.includes(extension)) {
      setError(`Solo se aceptan archivos ${formatos.join(', ').toUpperCase()}.`);
      return;
    }
    if (archivo.size > maximoMb * 1024 * 1024) {
      setError(`El archivo pesa ${(archivo.size / 1024 / 1024).toFixed(1)} MB y el máximo es ${maximoMb} MB.`);
      return;
    }
    setError(null);
    setElegido(archivo);
  }

  async function entregar() {
    if (!elegido) return;
    setSubiendo(true);
    setAvance(0);
    setError(null);
    try {
      const hecho = await entregarTrabajo(tareaId, elegido, setAvance);
      setDatos((x) => ({ ...x, ...hecho }));
      onCambio?.(true);
      setElegido(null);
      setComentario('');
      avisar(entrega ? 'Entrega reemplazada.' : 'Trabajo entregado.');
    } catch (e) {
      setError(e.message);
    } finally {
      setSubiendo(false);
    }
  }

  async function retirar() {
    setRetirando(true);
    setError(null);
    try {
      const hecho = await retirarMiEntrega(tareaId);
      setDatos((x) => ({ ...x, ...hecho }));
      onCambio?.(false);
      avisar('Entrega retirada.');
    } catch (e) {
      setError(e.message);
    } finally {
      setRetirando(false);
    }
  }

  return (
    <>
      <article className="visor-texto">
        <p>
          Subí tu resolución en un único archivo. Se toma en cuenta la última entrega hecha antes
          de la fecha límite.
        </p>
      </article>

      {entrega && (
        <div className={entrega.tarde ? 'entrega-hecha tarde' : 'entrega-hecha'}>
          <span className="entrega-icono" aria-hidden="true">
            <IconoCheckCirculo width={20} height={20} />
          </span>
          <div>
            <strong>{entrega.tarde ? 'Entregado fuera de término' : 'Entregado'}</strong>
            <small>{formatearFecha(entrega.fecha)}</small>
            {entrega.comentario && <p className="entrega-comentario">{entrega.comentario}</p>}
          </div>
          {entrega.archivo?.url ? (
            <a className="boton-suave" href={entrega.archivo.url} download={entrega.archivo.nombre}>
              <IconoDescargar width={15} height={15} />
              {entrega.archivo.nombre}
            </a>
          ) : (
            <span className="texto-suave">{entrega.archivo?.nombre}</span>
          )}
        </div>
      )}

      {abierta ? (
        <div className="visor-entrega">
          <label className="foto-zona">
            <input type="file" onChange={tomar} disabled={subiendo} />
            <IconoSubir width={22} height={22} />
            <strong>{elegido ? elegido.name : 'Elegí tu archivo o arrastralo acá'}</strong>
            <small>
              Se aceptan {formatos.join(', ').toUpperCase()}, hasta {maximoMb} MB.
            </small>
          </label>

          {error && <p className="aviso-error">{error}</p>}

          <div className="editor-botones">
            {entrega && (
              <button
                type="button"
                className="boton-suave peligro"
                onClick={retirar}
                disabled={retirando || subiendo}
              >
                {retirando ? 'Retirando…' : 'Retirar la entrega'}
              </button>
            )}
            <button
              type="button"
              className="boton-principal"
              onClick={entregar}
              disabled={!elegido || subiendo}
            >
              {subiendo
                ? `Subiendo… ${avance}%`
                : entrega
                  ? 'Reemplazar la entrega'
                  : 'Entregar'}
            </button>
          </div>
        </div>
      ) : (
        <div className="visor-entrega">
          <p className="texto-suave">
            {entrega
              ? 'La entrega está cerrada. Lo que subiste quedó registrado.'
              : 'La entrega está cerrada y no llegaste a subir nada. Hablá con la cátedra.'}
          </p>
          {error && <p className="aviso-error">{error}</p>}
        </div>
      )}
    </>
  );
}

function pesoDe(bytes) {
  if (!bytes) return '';
  const mb = bytes / 1024 / 1024;
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// Lo que ve la cátedra al abrir un trabajo: quién entregó y qué subió.
//
// El docente **no entrega**, así que pedirle su propia entrega no tiene
// sentido: el servidor contesta 403 y el visor mostraba ese error como si
// algo hubiera fallado. Lo que quiere saber al abrir un trabajo es quién lo
// resolvió y poder bajar lo que subieron, que es justo lo que había que ir a
// buscar a la planilla de la sección.
function EntregasDelCurso({ cursoId, tareaId, onCorregir, version }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');

  // `version` cambia cada vez que se guarda una nota: la lista queda vieja
  // —la nota recién puesta es justo lo que se mira— y se vuelve a pedir.
  useEffect(() => {
    let vigente = true;
    obtenerEntregasDeTarea(cursoId, tareaId)
      .then((d) => vigente && setDatos(d))
      .catch((e) => vigente && setError(e.message));
    return () => {
      vigente = false;
    };
  }, [cursoId, tareaId, version]);

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Buscando las entregas…</p>;

  const { alumnos, resumen } = datos;

  return (
    <div className="visor-entregas">
      <header>
        <h2>Entregas</h2>
        <span className="texto-suave">
          {resumen.entregaron} de {resumen.total}
          {resumen.sinCorregir > 0 && ` · ${resumen.sinCorregir} sin corregir`}
        </span>
      </header>

      {alumnos.length === 0 ? (
        <p className="vacio">Todavía no hay estudiantes en este módulo.</p>
      ) : (
        <ul className="visor-entregas-lista">
          {alumnos.map((a) => (
            <li key={a.id} className={a.entregado ? '' : 'sin-entregar'}>
              {/* La foto va en un hueco redondo de medida fija: `.avatar-foto`
                  ocupa el 100% de lo que la contenga, así que suelta en una
                  fila flexible se estiraba hasta tapar la pantalla. */}
              <span className="visor-entrega-cara">
                <Avatar persona={a} tamano={34} />
              </span>

              <div className="visor-entrega-quien">
                <strong>{a.nombre}</strong>
                <small>
                  {a.entregado ? formatearFecha(a.fecha) : 'Sin entregar'}
                  {a.atrasada && <span className="etiqueta atrasada">Atrasada</span>}
                </small>
              </div>

              {/* La nota va en la fila, no debajo del nombre: ahí quedaba
                  colgada de la línea de la fecha y descolocada respecto del
                  botón que tiene al lado. */}
              {a.corregido && <span className="etiqueta entregada">Nota {a.nota}</span>}

              {a.archivo?.url ? (
                <a
                  className="boton-suave"
                  href={a.archivo.url}
                  download={a.archivo.nombre}
                  title={`${a.archivo.nombre}${a.archivo.tamano ? ` · ${pesoDe(a.archivo.tamano)}` : ''}`}
                >
                  <IconoDescargar width={15} height={15} />
                  Descargar
                </a>
              ) : (
                <span className="texto-suave visor-entrega-sin">—</span>
              )}

              {/* El mismo botón que la planilla de la sección: se baja el
                  trabajo y se lo corrige sin salir de acá, que es lo que se
                  viene a hacer. Sin entrega también se puede poner nota —un
                  «Sin entregar» con su devolución—, igual que allá. */}
              <button
                type="button"
                className="boton-suave"
                onClick={() => onCorregir(a, datos.tarea)}
                title={
                  a.entregado
                    ? 'Corregir esta entrega'
                    : 'Todavía no entregó: se puede poner nota igual'
                }
              >
                {a.corregido ? 'Revisar' : 'Corregir'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Un trabajo. Cómo se resuelve depende de cómo lo tomó la cátedra:
//
// - **virtual · entrega**     se sube un archivo
// - **virtual · cuestionario** se responde acá mismo y se corrige solo
// - **presencial**            no hay nada que subir: se rinde en el aula
function Tarea({ item, curso, gestionando, onCorregir, versionNotas }) {
  const cerrada = item.cerrada === true;
  const reabierta = item.cerrada === false;
  const presencial = item.modalidad === 'presencial';

  // `item.entregada` es lo que sabía la pantalla del módulo al abrirse. Si se
  // entrega o se retira acá adentro, eso queda viejo: manda lo que diga la
  // entrega mientras el visor siga abierto.
  const [entregada, setEntregada] = useState(item.entregada);
  const alCambiar = useCallback((hay) => setEntregada(hay), []);

  const atrasada = !entregada && !reabierta && new Date(item.fechaLimite) < new Date();

  return (
    <div className="visor-tarea">
      <div className={atrasada || cerrada ? 'visor-plazo atrasado' : 'visor-plazo'}>
        <IconoReloj />
        <div>
          <strong>{presencial ? 'Fecha del examen' : 'Fecha de entrega'}</strong>
          <span>{formatearFecha(item.fechaLimite)}</span>
        </div>
        {!gestionando && entregada && <span className="etiqueta entregada">Entregada</span>}
        {/* El cierre a mano pesa más que la fecha, así que se dice primero */}
        {cerrada && <span className="etiqueta atrasada">Entrega cerrada</span>}
        {reabierta && <span className="etiqueta">Entrega reabierta</span>}
        {!gestionando && atrasada && !cerrada && (
          <span className="etiqueta atrasada">Atrasada</span>
        )}
      </div>

      {item.consigna && (
        <article className="visor-texto">
          <p>{item.consigna}</p>
        </article>
      )}

      {/* Un presencial no se entrega: no hay lista que mostrar, ni al que lo
          rinde ni a la cátedra. */}
      {presencial ? (
        <div className="visor-entrega">
          <p className="texto-suave">
            {gestionando
              ? 'Este examen es presencial: no hay entregas que revisar. La nota se carga en la pestaña Notas.'
              : 'Este examen es presencial: no hay nada que subir. La nota la carga el docente y la vas a ver en la pestaña Notas.'}
          </p>
        </div>
      ) : gestionando ? (
        <EntregasDelCurso
          cursoId={curso.id}
          tareaId={item.tareaId}
          onCorregir={onCorregir}
          version={versionNotas}
        />
      ) : item.formato === 'cuestionario' ? (
        <Cuestionario tareaId={item.tareaId} />
      ) : (
        <MiEntrega tareaId={item.tareaId} onCambio={alCambiar} />
      )}
    </div>
  );
}

// Tablero de consultas: una columna por tema, con las publicaciones del curso.
//
// El botón «+ Publicar» estaba dibujado y no hacía nada: no había ruta, así
// que la única forma de agregarle algo era tocar la base. Un tablero al que
// no se puede escribir no es un tablero.
function Tablero({ item, curso }) {
  const [columnas, setColumnas] = useState(item.columnas);
  const [escribiendo, setEscribiendo] = useState(null); // el título de la columna
  const [texto, setTexto] = useState('');
  const [mandando, setMandando] = useState(false);

  async function publicar(e, titulo) {
    e.preventDefault();
    const limpio = texto.trim();
    if (!limpio || mandando) return;
    setMandando(true);
    try {
      const nueva = await publicarEnTablero(curso.id, item.id, titulo, limpio);
      setColumnas((previas) =>
        previas.map((c) =>
          c.titulo === titulo ? { ...c, publicaciones: [...c.publicaciones, nueva] } : c
        )
      );
      setTexto('');
      setEscribiendo(null);
    } catch (error) {
      avisar(error.message, 'error');
    } finally {
      setMandando(false);
    }
  }

  return (
    <div className="tablero">
      {columnas.map((columna) => (
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

          {escribiendo === columna.titulo ? (
            <form className="tablero-nueva" onSubmit={(e) => publicar(e, columna.titulo)}>
              <textarea
                rows={3}
                value={texto}
                maxLength={1000}
                autoFocus
                placeholder="Escribí tu consulta…"
                onChange={(e) => setTexto(e.target.value)}
                disabled={mandando}
              />
              <div className="editor-botones">
                <button
                  type="button"
                  className="boton-suave"
                  onClick={() => {
                    setEscribiendo(null);
                    setTexto('');
                  }}
                  disabled={mandando}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="boton-principal"
                  disabled={mandando || !texto.trim()}
                >
                  {mandando ? 'Publicando…' : 'Publicar'}
                </button>
              </div>
            </form>
          ) : (
            <button
              type="button"
              className="tablero-agregar"
              onClick={() => {
                setEscribiendo(columna.titulo);
                setTexto('');
              }}
            >
              + Publicar
            </button>
          )}
        </section>
      ))}
    </div>
  );
}

// Pantalla completa sobre el módulo, con la ruta arriba y la X para volver.
// Al cerrar se marca "saliendo" para que se desvanezca antes de desaparecer.
export default function VisorItem({
  curso,
  carpeta,
  item,
  gestionando,
  onCorregir,
  versionNotas,
  onCerrar,
}) {
  const [saliendo, setSaliendo] = useState(false);
  // Un documento que se mira acá adentro necesita toda la pantalla: el ancho
  // de lectura de un texto le deja una hoja A4 del tamaño de una estampilla.
  const documento = item.tipo === 'archivo' && sePuedeVer(item.archivo);

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

      <div className={documento ? 'visor-cuerpo con-documento' : 'visor-cuerpo'}>
        <div className={documento ? 'visor-contenido ancho' : 'visor-contenido'}>
          <small className="texto-suave">{curso.nombre}</small>
          <h1>{item.titulo}</h1>

          {item.tipo === 'pagina' && <Pagina item={item} />}
          {item.tipo === 'archivo' && (
            <Archivo curso={curso} carpeta={carpeta} item={item} />
          )}
          {item.tipo === 'tarea' && (
            <Tarea
              item={item}
              curso={curso}
              gestionando={gestionando}
              onCorregir={onCorregir}
              versionNotas={versionNotas}
            />
          )}
          {item.tipo === 'tablero' && <Tablero item={item} curso={curso} />}
        </div>
      </div>
    </div>
  );
}
