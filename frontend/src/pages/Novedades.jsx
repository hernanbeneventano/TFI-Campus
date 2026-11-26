import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  obtenerPublicaciones,
  publicarNovedad,
  editarNovedad,
  reaccionar,
  retirarNovedad,
  subirImagenDeNovedad,
} from '../services/api.js';
import { avisar } from '../services/avisos.js';
import { urlDeRecurso } from '../services/destino.js';
import MotivoDeRetiro from '../components/MotivoDeRetiro.jsx';
import { hace } from '../services/fechas.js';
import Desplegable from '../components/Desplegable.jsx';
import {
  IconoUsuario,
  IconoAjustes,
  IconoPapelera,
  IconoAnuncio,
  IconoCalendario,
  IconoInformacion,
  IconoEstrella,
  IconoFlecha,
  IconoCerrar,
  IconoCheckChico,
  IconoPulgar,
  IconoDuda,
  IconoSubir,
} from '../components/Iconos.jsx';
import Avatar from '../components/Avatar.jsx';

import useTitulo from '../hooks/useTitulo';
// Lo mismo que exige el servidor (`IMAGENES_MAX_MB` en servicios/archivos.py).
const MAXIMO_IMAGEN_MB = 10;

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
function Autor({ publicacion, onEditar, onRetirar }) {
  return (
    <header className="publicacion-cabecera">
      <span className="docente-avatar">
        <Avatar persona={publicacion.autor} tamano={26} />
      </span>
      <div className="publicacion-quien">
        <strong>{publicacion.autor?.nombre}</strong>
        <small>
          {publicacion.autor?.rol} · {hace(publicacion.fecha)}
          {publicacion.editada && ' · editada'}
        </small>
      </div>
      <span className="publicacion-acciones">
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
        {publicacion.puedeRetirar && (
          <button
            type="button"
            className="publicacion-editar peligro"
            onClick={onRetirar}
            title="Retirar del muro"
            aria-label="Retirar del muro"
          >
            <IconoPapelera width={16} height={16} />
          </button>
        )}
      </span>
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
  // La imagen elegida, todavía sin subir: se manda después de guardar la
  // novedad, porque hasta entonces no hay id al que colgarla.
  const [imagen, setImagen] = useState(null);
  const [vistaPrevia, setVistaPrevia] = useState(urlDeRecurso(inicial?.imagen) ?? null);
  const [errorImagen, setErrorImagen] = useState(null);

  function enviar(e) {
    e.preventDefault();
    if (!titulo.trim() || !cuerpo.trim()) return;
    onGuardar({ titulo, cuerpo, categoria, ambito, anclada }, imagen);
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

      {/* La imagen se elige acá y se sube después de guardar: hasta
          entonces no hay novedad a la que colgarla. */}
      <div className="novedad-imagen">
        {vistaPrevia ? (
          <div className="novedad-imagen-elegida">
            <img src={vistaPrevia} alt="" />
            <button
              type="button"
              className="boton-suave peligro"
              onClick={() => {
                if (imagen) URL.revokeObjectURL(vistaPrevia);
                setImagen(null);
                setVistaPrevia(null);
              }}
            >
              Quitar la imagen
            </button>
          </div>
        ) : (
          <label className="foto-zona">
            <input
              type="file"
              accept="image/png,image/jpeg"
              onChange={(e) => {
                const archivo = e.target.files?.[0];
                e.target.value = '';
                if (!archivo) return;
                if (!/^image\/(png|jpe?g)$/.test(archivo.type)) {
                  setErrorImagen('Solo se aceptan imágenes PNG o JPG.');
                  return;
                }
                if (archivo.size > MAXIMO_IMAGEN_MB * 1024 * 1024) {
                  setErrorImagen(`La imagen supera los ${MAXIMO_IMAGEN_MB} MB.`);
                  return;
                }
                setErrorImagen(null);
                setImagen(archivo);
                setVistaPrevia(URL.createObjectURL(archivo));
              }}
            />
            <IconoSubir width={20} height={20} />
            <strong>Agregar una imagen</strong>
            <small>PNG o JPG, hasta {MAXIMO_IMAGEN_MB} MB. Opcional.</small>
          </label>
        )}
        {errorImagen && <p className="aviso-error">{errorImagen}</p>}
      </div>

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
              onGuardar={(datos, imagen) => {
                onEditar(actual.id, datos, imagen);
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
                        <img src={urlDeRecurso(p.imagen)} alt="" />
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
            <img src={urlDeRecurso(publicacion.imagen)} alt="" />
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
function Publicacion({ publicacion, onEditar, onRetirar, onAbrir, onReaccionar }) {
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
          onGuardar={(datos, imagen) => {
            onEditar(publicacion.id, datos, imagen);
            setEditando(false);
          }}
        />
      </article>
    );
  }

  return (
    <article className="publicacion">
      <Autor
        publicacion={publicacion}
        onEditar={() => setEditando(true)}
        onRetirar={() => onRetirar(publicacion)}
      />

      {publicacion.imagen && (
        <button
          type="button"
          className="publicacion-imagen"
          onClick={(e) => onAbrir(publicacion, e.currentTarget.closest('.publicacion'))}
          aria-label={`Abrir «${publicacion.titulo}»`}
        >
          <img src={urlDeRecurso(publicacion.imagen)} alt="" loading="lazy" />
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
  useTitulo('Novedades');
  const [datos, setDatos] = useState(null);
  const [escribiendo, setEscribiendo] = useState(false);
  // La novedad que se está leyendo entera, superpuesta
  const [leyendo, setLeyendo] = useState(null);
  const [error, setError] = useState(null);
  // La publicación que se está por retirar, mientras se escribe el motivo
  const [retirando, setRetirando] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  const listaCompleta = useRef(null);

  function retirar(motivo) {
    setTrabajando(true);
    retirarNovedad(retirando.id, motivo)
      .then(() => {
        avisar('Novedad retirada del muro.');
        setRetirando(null);
        recargar();
      })
      .catch((e) => avisar(e.message, 'error'))
      .finally(() => setTrabajando(false));
  }

  function recargar() {
    return obtenerPublicaciones().then(setDatos).catch((e) => setError(e.message));
  }

  useEffect(() => {
    recargar();
  }, []);

  // La imagen se sube **después** de crear la novedad: hasta que no existe
  // no hay id al que colgarla. Si la imagen falla, la novedad igual quedó
  // publicada y se avisa; perderla entera por una foto sería peor.
  async function publicar(nueva, imagen) {
    try {
      const creada = await publicarNovedad(nueva);
      if (imagen) {
        try {
          await subirImagenDeNovedad(creada.id, imagen);
        } catch (e) {
          avisar(`La novedad se publicó, pero la imagen no: ${e.message}`, 'error');
        }
      }
      setEscribiendo(false);
      await recargar();
    } catch (e) {
      setError(e.message);
    }
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

  async function guardarEdicion(id, cambios, imagen) {
    try {
      await editarNovedad(id, cambios);
      // La imagen va aparte, con su propia ruta: al editar el texto no hace
      // falta volver a subir la foto que ya estaba.
      if (imagen) await subirImagenDeNovedad(id, imagen);
      await recargar();
    } catch (e) {
      setError(e.message);
    }
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
            onRetirar={setRetirando}
            onAbrir={(p, desde) => setLeyendo({ publicacion: p, desde })}
            onReaccionar={cambiarReaccion}
          />
        ))}
      </div>

      {datos && todas.length === 0 && (
        <p className="texto-suave">Todavía no hay novedades publicadas.</p>
      )}

      {retirando && (
        <MotivoDeRetiro
          titulo="¿Retirar esta novedad?"
          queSeRetira={retirando.titulo}
          autor={retirando.autor?.nombre ?? 'Quien la publicó'}
          exigeMotivo={retirando.retiroExigeMotivo}
          trabajando={trabajando}
          onCerrar={() => setRetirando(null)}
          onRetirar={retirar}
        />
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
