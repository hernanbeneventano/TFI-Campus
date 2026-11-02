import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  obtenerPublicaciones,
  publicarNovedad,
  editarNovedad,
  reaccionar,
} from '../services/api.js';
import { hace } from '../services/fechas.js';
import Desplegable from '../components/Desplegable.jsx';
import {
  IconoUsuario,
  IconoAjustes,
  IconoAnuncio,
  IconoCalendario,
  IconoInformacion,
  IconoEstrella,
  IconoFlecha,
  IconoCerrar,
  IconoCheckChico,
  IconoPulgar,
  IconoDuda,
} from '../components/Iconos.jsx';

const DIAS_NUEVO = 7;
// A partir de acá la tarjeta recorta y ofrece abrir la novedad entera
const LARGO_RECORTE = 170;
const EN_EL_CARRUSEL = 3;

function esNueva(iso) {
  return Date.now() - new Date(iso) < DIAS_NUEVO * 24 * 60 * 60 * 1000;
}

// Las reacciones son anonimas: el backend manda los totales y cual puso uno
// mismo, nunca la lista de quienes reaccionaron.
const REACCIONES = [
  { tipo: 'leido', nombre: 'Lo leí', Icono: IconoCheckChico },
  { tipo: 'util', nombre: 'Me sirve', Icono: IconoPulgar },
  { tipo: 'dudas', nombre: 'Me genera dudas', Icono: IconoDuda },
];

function Reacciones({ publicacion, onReaccionar }) {
  return (
    <div className="reacciones" title="Nadie ve quién reaccionó">
      {REACCIONES.map(({ tipo, nombre, Icono }) => {
        const mia = publicacion.miReaccion === tipo;
        const cuantas = publicacion.cuenta?.[tipo] ?? 0;

        return (
          <button
            key={tipo}
            type="button"
            className={mia ? `reaccion ${tipo} puesta` : `reaccion ${tipo}`}
            onClick={() => onReaccionar(publicacion.id, tipo)}
            aria-pressed={mia}
            title={`${nombre} · ${cuantas} ${cuantas === 1 ? 'persona' : 'personas'}`}
          >
            <Icono width={15} height={15} />
            <span className="reaccion-nombre">{nombre}</span>
            {cuantas > 0 && <small>{cuantas}</small>}
          </button>
        );
      })}
    </div>
  );
}

// Quién la publicó, al estilo de una red social
function Autor({ publicacion, onEditar }) {
  return (
    <header className="publicacion-cabecera">
      <span className="docente-avatar">
        <IconoUsuario />
      </span>
      <div className="publicacion-quien">
        <strong>{publicacion.autor?.nombre}</strong>
        <small>
          {publicacion.autor?.rol} · {hace(publicacion.fecha)}
          {publicacion.editada && ' · editada'}
        </small>
      </div>
      {publicacion.puedeEditar && (
        <button
          type="button"
          className="publicacion-editar"
          onClick={onEditar}
          title="Editar la novedad"
          aria-label="Editar la novedad"
        >
          <IconoAjustes width={16} height={16} />
        </button>
      )}
    </header>
  );
}

function Etiquetas({ publicacion }) {
  return (
    <div className="publicacion-etiquetas">
      <span className="aviso-categoria">{publicacion.ambito}</span>
      <span className="publicacion-categoria">{publicacion.categoria}</span>
      {esNueva(publicacion.fecha) && <span className="aviso-nuevo">Nuevo</span>}
    </div>
  );
}

// Formulario para publicar o para editar. Solo lo ven los docentes.
function Editor({ inicial, onGuardar, onCancelar }) {
  const [titulo, setTitulo] = useState(inicial?.titulo ?? '');
  const [cuerpo, setCuerpo] = useState(inicial?.cuerpo ?? '');
  const [categoria, setCategoria] = useState(inicial?.categoria ?? 'Académico');
  const [ambito, setAmbito] = useState(inicial?.ambito ?? 'Institucional');
  const [anclada, setAnclada] = useState(inicial?.anclada ?? false);
  const [imagen, setImagen] = useState(inicial?.imagen ?? '');

  function enviar(e) {
    e.preventDefault();
    if (!titulo.trim() || !cuerpo.trim()) return;
    onGuardar({ titulo, cuerpo, categoria, ambito, anclada, imagen });
  }

  return (
    <form className="editor-novedad" onSubmit={enviar}>
      <input
        type="text"
        placeholder="Título de la novedad"
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        aria-label="Título"
      />
      <textarea
        rows={4}
        placeholder="Contá de qué se trata…"
        value={cuerpo}
        onChange={(e) => setCuerpo(e.target.value)}
        aria-label="Texto de la novedad"
      />

      {/* Mientras no haya subida de archivos, la imagen es una direccion */}
      <input
        type="text"
        placeholder="Imagen (opcional): dirección del archivo"
        value={imagen}
        onChange={(e) => setImagen(e.target.value)}
        aria-label="Imagen de la novedad"
      />

      <div className="editor-pie">
        {/* En una publicación ya hecha no se cambian el ámbito ni la categoría */}
        {!inicial && (
          <>
            <Desplegable
              etiqueta="Ámbito"
              valor={ambito}
              onCambiar={setAmbito}
              opciones={[
                { valor: 'Institucional', nombre: 'Institucional' },
                { valor: 'Académico', nombre: 'Académico' },
              ]}
            />
            <Desplegable
              etiqueta="Categoría"
              valor={categoria}
              onCambiar={setCategoria}
              opciones={[
                { valor: 'Académico', nombre: 'Académico' },
                { valor: 'Inscripciones', nombre: 'Inscripciones' },
                { valor: 'Biblioteca', nombre: 'Biblioteca' },
                { valor: 'Becas', nombre: 'Becas' },
                { valor: 'Campus', nombre: 'Campus' },
              ]}
            />
          </>
        )}

        <label className="editor-anclar">
          <input type="checkbox" checked={anclada} onChange={(e) => setAnclada(e.target.checked)} />
          Destacar arriba de todo
        </label>

        {onCancelar && (
          <button type="button" className="boton-suave" onClick={onCancelar}>
            Cancelar
          </button>
        )}
        <button type="submit" className="boton-principal" disabled={!titulo.trim() || !cuerpo.trim()}>
          {inicial ? 'Guardar cambios' : 'Publicar'}
        </button>
      </div>
    </form>
  );
}

// El panel de arriba: título de la sección y las novedades importantes, de a
// una, con flechas y puntos para pasarlas.
function Portada({ destacadas, onEditar, onVerTodas, onAbrir, onReaccionar }) {
  const [slide, setSlide] = useState(0);
  const [editando, setEditando] = useState(false);

  // Si cambia la lista (se publicó o se editó algo), no quedarse pasado de índice
  const actual = destacadas[Math.min(slide, destacadas.length - 1)];

  function mover(pasos) {
    setSlide((i) => (i + pasos + destacadas.length) % destacadas.length);
  }

  return (
    <section className="portada">
      <header className="portada-cabecera">
        <div>
          <h1>Novedades</h1>
          <p>Anuncios de la facultad y de tus materias, lo más reciente primero.</p>
        </div>
        <button type="button" className="portada-ver-todas" onClick={onVerTodas}>
          Ver todas
          <IconoFlecha width={15} height={15} />
        </button>
      </header>

      {actual &&
        (editando ? (
          <div className="portada-slide editando">
            <Editor
              inicial={actual}
              onCancelar={() => setEditando(false)}
              onGuardar={(datos) => {
                onEditar(actual.id, datos);
                setEditando(false);
              }}
            />
          </div>
        ) : (
          <div className="portada-carrusel">
            {destacadas.length > 1 && (
              <button
                type="button"
                className="portada-flecha atras"
                onClick={() => mover(-1)}
                aria-label="Novedad anterior"
              >
                <IconoFlecha width={18} height={18} />
              </button>
            )}

            {/* Las novedades van una al lado de la otra y la pista se corre:
                así el cambio se desliza en vez de saltar. */}
            <div className="portada-ventana">
              <div
                className="portada-pista"
                style={{ transform: `translateX(-${slide * 100}%)` }}
              >
                {destacadas.map((p, i) => (
                  <article
                    className="portada-slide"
                    key={p.id}
                    // Las que no se ven no deberían alcanzarse con el teclado
                    aria-hidden={i !== slide}
                    inert={i === slide ? undefined : ''}
                  >
                    {p.imagen ? (
                      <div className="portada-ilustracion con-imagen">
                        <img src={p.imagen} alt="" />
                      </div>
                    ) : (
                      <div className="portada-ilustracion" aria-hidden="true">
                        <IconoAnuncio width={120} height={120} />
                      </div>
                    )}

                    <div className="portada-texto">
                      {p.anclada && (
                        <span className="destacada-marca">
                          <IconoEstrella llena width={13} height={13} />
                          Destacada
                        </span>
                      )}

                      <h2>{p.titulo}</h2>

                      <div className="portada-datos">
                        <span>
                          <IconoCalendario width={16} height={16} />
                          {hace(p.fecha)}
                        </span>
                        <span className="portada-separador" />
                        <span>
                          <IconoInformacion width={16} height={16} />
                          {p.ambito}
                        </span>
                        {p.puedeEditar && (
                          <button
                            type="button"
                            className="publicacion-editar"
                            onClick={() => setEditando(true)}
                            title="Editar la novedad"
                            aria-label="Editar la novedad"
                          >
                            <IconoAjustes width={16} height={16} />
                          </button>
                        )}
                      </div>

                      <p>{p.cuerpo.split('\n\n')[0]}</p>

                      <Reacciones publicacion={p} onReaccionar={onReaccionar} />

                      <button
                        type="button"
                        className="publicacion-mas"
                        onClick={(e) => onAbrir(p, e.currentTarget.closest('.portada-slide'))}
                      >
                        Leer la novedad completa
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            {destacadas.length > 1 && (
              <button
                type="button"
                className="portada-flecha adelante"
                onClick={() => mover(1)}
                aria-label="Novedad siguiente"
              >
                <IconoFlecha width={18} height={18} />
              </button>
            )}
          </div>
        ))}

      {destacadas.length > 1 && !editando && (
        <div className="portada-puntos" role="tablist" aria-label="Novedades destacadas">
          {destacadas.map((p, i) => (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={i === slide}
              aria-label={p.titulo}
              className={i === slide ? 'portada-punto activo' : 'portada-punto'}
              onClick={() => setSlide(i)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

const APERTURA = 400;
const CIERRE = 300;

// Lleva el visor desde donde está la tarjeta hasta su lugar final, o al
// revés. Es la técnica FLIP: el visor ya está en su posición definitiva y se
// lo transforma para que *parezca* que todavía está en la tarjeta; después se
// saca la transformación y el navegador anima la diferencia.
function volarDesde(visor, tarjeta, hastaLaTarjeta) {
  if (!visor || !tarjeta) return null;

  // Medir el visor sin transformación. Si ya se está animando (en modo
  // estricto React corre el efecto dos veces), su rectángulo vendría
  // deformado y la cuenta daría casi cero: no se movería nada.
  visor.style.transition = 'none';
  visor.style.transform = 'none';

  const hasta = visor.getBoundingClientRect();
  const desde = tarjeta.getBoundingClientRect();
  if (!desde.width || !hasta.width) return null;

  // Una sola escala para los dos ejes: con dos distintas el texto se estira
  const escala = desde.width / hasta.width;
  const dx = desde.left + desde.width / 2 - (hasta.left + hasta.width / 2);
  const dy = desde.top + desde.height / 2 - (hasta.top + hasta.height / 2);
  const enLaTarjeta = `translate(${dx}px, ${dy}px) scale(${escala})`;

  if (hastaLaTarjeta) {
    visor.style.transition = `transform ${CIERRE}ms cubic-bezier(0.4, 0, 1, 1), opacity ${CIERRE}ms ease`;
    visor.style.transform = enLaTarjeta;
    visor.style.opacity = '0';
    return CIERRE;
  }

  visor.style.transform = enLaTarjeta;
  visor.style.opacity = '0.35';
  // Forzar el recálculo: si no, el navegador junta los dos estados y no anima
  void visor.offsetWidth;
  visor.style.transition = `transform ${APERTURA}ms cubic-bezier(0.16, 1, 0.3, 1), opacity ${
    APERTURA / 2
  }ms ease`;
  visor.style.transform = 'none';
  visor.style.opacity = '1';
  return APERTURA;
}

// La novedad entera, superpuesta y con el fondo oscurecido
function Lector({ publicacion, origen, onCerrar, onReaccionar }) {
  const visor = useRef(null);
  const [cerrando, setCerrando] = useState(false);

  // Crece desde la tarjeta al abrirse
  useLayoutEffect(() => {
    volarDesde(visor.current, origen, false);
  }, [origen]);

  // Y vuelve a ella al cerrarse, antes de desaparecer
  function cerrar() {
    if (cerrando) return;
    setCerrando(true);
    const duracion = volarDesde(visor.current, origen, true);
    if (duracion === null) return onCerrar();
    setTimeout(onCerrar, duracion);
  }

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape') cerrar();
    }
    window.addEventListener('keydown', alTeclado);
    // Mientras está abierta, la página de atrás no se mueve
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className={cerrando ? 'lector-fondo saliendo' : 'lector-fondo'}
      // Clic afuera para cerrar; adentro no, de ahí la comparación
      onClick={(e) => e.target === e.currentTarget && cerrar()}
      role="presentation"
    >
      <article
        ref={visor}
        className="lector"
        role="dialog"
        aria-modal="true"
        aria-label={publicacion.titulo}
      >
        <button type="button" className="lector-cerrar" onClick={cerrar} aria-label="Cerrar">
          <IconoCerrar width={20} height={20} />
        </button>

        {publicacion.imagen && (
          <div className="lector-imagen">
            <img src={publicacion.imagen} alt="" />
          </div>
        )}

        <div className="lector-cuerpo">
          <Autor publicacion={publicacion} />
          <Etiquetas publicacion={publicacion} />
          <h2>{publicacion.titulo}</h2>
          {publicacion.cuerpo.split('\n\n').map((parrafo, i) => (
            <p key={i}>{parrafo}</p>
          ))}

          <Reacciones publicacion={publicacion} onReaccionar={onReaccionar} />
        </div>
      </article>
    </div>
  );
}

// Las demás, en la grilla de abajo
function Publicacion({ publicacion, onEditar, onAbrir, onReaccionar }) {
  const [editando, setEditando] = useState(false);

  const largo = publicacion.cuerpo.length > LARGO_RECORTE;
  const texto = largo
    ? `${publicacion.cuerpo.slice(0, LARGO_RECORTE).trimEnd()}…`
    : publicacion.cuerpo;

  if (editando) {
    return (
      <article className="publicacion">
        <Editor
          inicial={publicacion}
          onCancelar={() => setEditando(false)}
          onGuardar={(datos) => {
            onEditar(publicacion.id, datos);
            setEditando(false);
          }}
        />
      </article>
    );
  }

  return (
    <article className="publicacion">
      <Autor publicacion={publicacion} onEditar={() => setEditando(true)} />

      {publicacion.imagen && (
        <button
          type="button"
          className="publicacion-imagen"
          onClick={(e) => onAbrir(publicacion, e.currentTarget.closest('.publicacion'))}
          aria-label={`Abrir «${publicacion.titulo}»`}
        >
          <img src={publicacion.imagen} alt="" loading="lazy" />
        </button>
      )}

      <Etiquetas publicacion={publicacion} />
      <h3>{publicacion.titulo}</h3>
      {texto.split('\n\n').map((parrafo, i) => (
        <p key={i}>{parrafo}</p>
      ))}

      <Reacciones publicacion={publicacion} onReaccionar={onReaccionar} />

      {/* Las largas se abren enteras arriba de todo, no acá adentro */}
      {largo && (
        <button
          type="button"
          className="publicacion-mas"
          onClick={(e) => onAbrir(publicacion, e.currentTarget.closest('.publicacion'))}
        >
          Leer la novedad completa
        </button>
      )}
    </article>
  );
}

export default function Novedades() {
  const [datos, setDatos] = useState(null);
  const [escribiendo, setEscribiendo] = useState(false);
  // La novedad que se está leyendo entera, superpuesta
  const [leyendo, setLeyendo] = useState(null);
  const [error, setError] = useState(null);

  const listaCompleta = useRef(null);

  function recargar() {
    return obtenerPublicaciones().then(setDatos).catch((e) => setError(e.message));
  }

  useEffect(() => {
    recargar();
  }, []);

  function publicar(nueva) {
    publicarNovedad(nueva)
      .then(() => {
        setEscribiendo(false);
        return recargar();
      })
      .catch((e) => setError(e.message));
  }

  // Al reaccionar el backend devuelve la publicación con los totales nuevos:
  // se reemplaza esa sola, sin volver a pedir toda la lista.
  function cambiarReaccion(id, tipo) {
    reaccionar(id, tipo)
      .then((actualizada) => {
        setDatos((d) => ({
          ...d,
          publicaciones: d.publicaciones.map((p) => (p.id === id ? actualizada : p)),
        }));
        setLeyendo((l) => (l && l.publicacion.id === id ? { ...l, publicacion: actualizada } : l));
      })
      .catch((e) => setError(e.message));
  }

  function guardarEdicion(id, cambios) {
    editarNovedad(id, cambios)
      .then(recargar)
      .catch((e) => setError(e.message));
  }

  // El backend ya manda la anclada primera y el resto por fecha
  const todas = datos?.publicaciones ?? [];
  const destacadas = todas.slice(0, EN_EL_CARRUSEL);

  return (
    <div className="pagina">
      {error && <p className="error">No se pudieron cargar las novedades. ¿Está corriendo el backend?</p>}
      {!error && !datos && <p className="texto-suave">Cargando…</p>}

      {datos && (
        <Portada
          destacadas={destacadas}
          onEditar={guardarEdicion}
          onVerTodas={() => listaCompleta.current?.scrollIntoView({ behavior: 'smooth' })}
          onAbrir={(p, desde) => setLeyendo({ publicacion: p, desde })}
          onReaccionar={cambiarReaccion}
        />
      )}

      {/* Publicar es cosa de los docentes; los estudiantes solo leen */}
      {datos?.puedePublicar &&
        (escribiendo ? (
          <div className="publicacion">
            <Editor onGuardar={publicar} onCancelar={() => setEscribiendo(false)} />
          </div>
        ) : (
          <button type="button" className="muro-publicar" onClick={() => setEscribiendo(true)}>
            Publicar una novedad…
          </button>
        ))}

      <div className="muro" ref={listaCompleta}>
        {todas.map((p) => (
          <Publicacion
            key={p.id}
            publicacion={p}
            onEditar={guardarEdicion}
            onAbrir={(p, desde) => setLeyendo({ publicacion: p, desde })}
            onReaccionar={cambiarReaccion}
          />
        ))}
      </div>

      {datos && todas.length === 0 && (
        <p className="texto-suave">Todavía no hay novedades publicadas.</p>
      )}

      {leyendo && (
        <Lector
          publicacion={leyendo.publicacion}
          origen={leyendo.desde}
          onCerrar={() => setLeyendo(null)}
          onReaccionar={cambiarReaccion}
        />
      )}
    </div>
  );
}
