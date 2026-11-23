import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  obtenerConversaciones,
  obtenerConversacion,
  obtenerContactos,
  enviarMensaje,
  abrirConversacionCon,
  editarMensaje,
  eliminarMensaje,
  fijarMensaje,
} from '../services/api.js';
import { hace } from '../services/fechas.js';
import { avisar } from '../services/avisos.js';
import Encabezado from '../components/Encabezado.jsx';
import {
  IconoUsuario,
  IconoEstudiante,
  IconoEnviar,
  IconoBuscar,
  IconoAdjuntar,
  IconoCerrar,
  IconoArchivo,
  IconoCampanaLlena,
  IconoLapiz,
  IconoPapelera,
  IconoSubir,
} from '../components/Iconos.jsx';
import Cara from '../components/Avatar.jsx';
import Confirmacion from '../components/Confirmacion.jsx';

import useTitulo from '../hooks/useTitulo';
// Lo mismo que exige el servidor (`IMAGENES_MAX_MB` en servicios/archivos.py).
const MAXIMO_ADJUNTO_MB = 10;

// Lo que el servidor acepta (`FORMATOS` en servicios/archivos.py). Se escribe
// acá además de allá para poder decirlo **antes** de elegir el archivo: que
// el campus rechace un `.zip` después de subirlo es tarde y no explica nada.
// Quien manda sigue siendo el servidor, que además mira los bytes.
const DOCUMENTOS = ['PDF', 'Word', 'EPUB'];
const IMAGENES = ['PNG', 'JPG'];
const EXTENSIONES = ['pdf', 'docx', 'epub', 'png', 'jpg', 'jpeg'];
const ACEPTA = EXTENSIONES.map((e) => `.${e}`).join(',');
const MAXIMO_ARCHIVOS = 5;

/** El cartel para adjuntar: dice qué entra **antes** de abrir el explorador.
 *
 * El clip abría el selector del sistema de una, y ahí el campus no tiene
 * forma de decir nada: el navegador muestra «Todos los archivos» y recién al
 * mandar aparece el error. Es el mismo cartel que el de la foto de perfil,
 * por el mismo motivo: lo que se acepta se dice antes, no después.
 */
function PanelAdjuntar({ yaElegidos, onAgregar, onCerrar }) {
  const [arrastrando, setArrastrando] = useState(false);
  const lugares = MAXIMO_ARCHIVOS - yaElegidos;

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape') onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    return () => window.removeEventListener('keydown', alTeclado);
  }, [onCerrar]);

  function tomar(archivos) {
    const elegidos = [...(archivos || [])].slice(0, lugares);
    if (elegidos.length) onAgregar(elegidos);
    onCerrar();
  }

  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && onCerrar()}
      role="presentation"
    >
      <div className="correccion foto-panel" role="dialog" aria-modal="true">
        <button
          type="button"
          className="correccion-cerrar"
          onClick={onCerrar}
          aria-label="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        <h3>Adjuntar al mensaje</h3>

        <label
          className={arrastrando ? 'foto-zona arrastrando' : 'foto-zona'}
          onDragOver={(e) => {
            e.preventDefault();
            setArrastrando(true);
          }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArrastrando(false);
            tomar(e.dataTransfer.files);
          }}
        >
          <input
            type="file"
            multiple
            accept={ACEPTA}
            onChange={(e) => {
              tomar(e.target.files);
              e.target.value = ''; // para poder volver a elegir el mismo
            }}
          />
          <IconoSubir width={22} height={22} />
          <strong>Elegí los archivos o arrastralos acá</strong>
          <small>
            Documentos: {DOCUMENTOS.join(', ')}. Imágenes: {IMAGENES.join(' y ')}.
            <br />
            Hasta {MAXIMO_ADJUNTO_MB} MB cada uno y {MAXIMO_ARCHIVOS} archivos por mensaje.
          </small>
        </label>

        {yaElegidos > 0 && (
          <p className="texto-suave adjuntar-nota">
            Ya elegiste {yaElegidos}: te{' '}
            {lugares === 1 ? 'queda 1 lugar' : `quedan ${lugares} lugares`}.
          </p>
        )}

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

/** El archivo en base64, sin la cabecera `data:` que agrega el navegador. */
function enBase64(archivo) {
  return new Promise((resolver, rechazar) => {
    const lector = new FileReader();
    lector.onerror = () => rechazar(new Error('No se pudo leer'));
    lector.onload = () => resolver(String(lector.result).split(',')[1] ?? '');
    lector.readAsDataURL(archivo);
  });
}

// Tamaño de archivo en algo legible
function pesoDe(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function Avatar({ persona }) {
  return (
    <span className={`docente-avatar avatar-estado ${persona.estado}`}>
      <Cara persona={persona} tamano={26} />
    </span>
  );
}

/** Las acciones de un mensaje: fijar, editar y eliminar.
 *
 * Aparecen al pasar por encima de la burbuja. Un menú siempre visible en
 * cada una convierte el hilo en una lista de botones y no se lee más.
 *
 * **Editar y eliminar, solo lo propio.** En una conversación de a dos, poder
 * cambiar lo que dijo el otro convierte el chat en algo que no sirve como
 * constancia de nada. Fijar sí lo puede cualquiera: lo que conviene tener a
 * la vista normalmente lo dijo el otro.
 */
function AccionesDelMensaje({ mensaje, mio, fijado, onEditar, onFijar, onEliminar }) {
  return (
    <div className="burbuja-acciones">
      <button
        type="button"
        onClick={onFijar}
        title={fijado ? 'Soltar el mensaje' : 'Fijar el mensaje'}
        aria-label={fijado ? 'Soltar el mensaje' : 'Fijar el mensaje'}
        className={fijado ? 'activo' : undefined}
      >
        <IconoCampanaLlena width={14} height={14} />
      </button>

      {mio && mensaje.texto && (
        <button type="button" onClick={onEditar} title="Editar" aria-label="Editar el mensaje">
          <IconoLapiz width={14} height={14} />
        </button>
      )}

      {mio && (
        <button
          type="button"
          onClick={onEliminar}
          title="Eliminar"
          aria-label="Eliminar el mensaje"
          className="peligro"
        >
          <IconoPapelera width={14} height={14} />
        </button>
      )}
    </div>
  );
}

/** Editar sin salir del hilo: el mensaje se edita donde está. */
function EdicionEnLinea({ valor, onCambiar, onGuardar, onCancelar }) {
  return (
    <div className="burbuja-editar">
      <textarea
        value={valor}
        rows={2}
        autoFocus
        onChange={(e) => onCambiar(e.target.value)}
        onKeyDown={(e) => {
          // Enter guarda, Shift+Enter hace un salto de línea: es como se
          // escribe en un chat.
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onGuardar();
          }
          if (e.key === 'Escape') onCancelar();
        }}
      />
      <div className="burbuja-editar-botones">
        <button type="button" className="boton-suave" onClick={onCancelar}>
          Cancelar
        </button>
        <button type="button" className="boton-principal" onClick={onGuardar}>
          Guardar
        </button>
      </div>
    </div>
  );
}

function horaDe(iso) {
  return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}

export default function Mensajes() {
  useTitulo('Mensajes');
  // ?con=N llega desde la lista de participantes de un módulo
  const [parametros, setParametros] = useSearchParams();
  const conPersona = parametros.get('con');

  const [lista, setLista] = useState(null);
  const [contactos, setContactos] = useState([]);
  const [abierta, setAbierta] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [texto, setTexto] = useState('');
  const [adjuntos, setAdjuntos] = useState([]);
  const [error, setError] = useState(null);

  const finDelHilo = useRef(null);
  // La imagen que se está mirando en grande, si hay alguna
  const [mirando, setMirando] = useState(null);
  // El mensaje que se está editando, y el que se va a eliminar
  const [editando, setEditando] = useState(null);
  const [aEliminar, setAEliminar] = useState(null);
  // El cartel de adjuntar, que dice qué se puede subir antes de abrir el
  // explorador del sistema.
  const [adjuntando, setAdjuntando] = useState(false);

  function recargarLista() {
    return obtenerConversaciones()
      .then((d) => setLista(d.conversaciones))
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    recargarLista();
    obtenerContactos().then(setContactos).catch(() => setContactos([]));
  }, []);

  // Si se vino desde "escribirle a alguien", se abre (o se crea) esa charla
  useEffect(() => {
    if (!conPersona) return;
    abrirConversacionCon(Number(conPersona))
      .then((c) => {
        setAbierta(c);
        setParametros({}, { replace: true });
        return recargarLista();
      })
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conPersona]);

  // Al llegar mensajes nuevos, bajar del todo
  useEffect(() => {
    finDelHilo.current?.scrollIntoView({ block: 'end' });
  }, [abierta]);

  const textoBuscado = busqueda.trim().toLowerCase();

  const charlasVisibles = useMemo(() => {
    if (!lista) return [];
    if (!textoBuscado) return lista;
    return lista.filter((c) => c.con.nombre.toLowerCase().includes(textoBuscado));
  }, [lista, textoBuscado]);

  // Al buscar también aparece gente de tus módulos con la que todavía
  // no hablaste, para poder empezar la charla.
  const nuevosContactos = useMemo(() => {
    if (!textoBuscado || !lista) return [];
    const yaHablados = new Set(lista.map((c) => c.con.id));
    return contactos.filter(
      (p) => !yaHablados.has(p.id) && p.nombre.toLowerCase().includes(textoBuscado)
    );
  }, [contactos, lista, textoBuscado]);

  function cerrarCharla() {
    setAbierta(null);
    setTexto('');
    setAdjuntos([]);
  }

  // El archivo se lee acá y viaja con el mensaje. Antes solo se mandaba el
  // nombre y el tamaño: el chat mostraba "foto.jpg · 41 KB" y no había foto.
  //
  // Se comprueban el formato y el peso **antes** de leerlo: que el servidor
  // lo rechace después de subir diez megas es tarde. La comprobación de
  // verdad sigue siendo la del servidor, que además mira los bytes.
  async function elegirArchivos(archivos) {
    const leidos = [];
    for (const f of archivos) {
      const extension = (f.name.split('.').pop() || '').toLowerCase();
      if (!EXTENSIONES.includes(extension)) {
        avisar(`«${f.name}» no es un formato que el campus acepte.`, 'error');
        continue;
      }
      if (f.size > MAXIMO_ADJUNTO_MB * 1024 * 1024) {
        avisar(`«${f.name}» pesa ${pesoDe(f.size)} y el máximo es ${MAXIMO_ADJUNTO_MB} MB.`, 'error');
        continue;
      }
      try {
        leidos.push({
          nombre: f.name,
          tamano: f.size,
          tipo: f.type,
          extension,
          contenido: await enBase64(f),
          // Para verla antes de mandarla, sin pasar por el servidor
          vistaPrevia: f.type.startsWith('image/') ? URL.createObjectURL(f) : null,
        });
      } catch {
        avisar(`No se pudo leer «${f.name}».`, 'error');
      }
    }
    setAdjuntos((previos) => [...previos, ...leidos].slice(0, MAXIMO_ARCHIVOS));
  }

  function sacarAdjunto(nombre) {
    setAdjuntos((previos) => previos.filter((a) => a.nombre !== nombre));
  }

  function abrir(id) {
    obtenerConversacion(id)
      .then((c) => {
        setAbierta(c);
        setTexto('');
        setAdjuntos([]);
        return recargarLista();
      })
      .catch((e) => setError(e.message));
  }

  function empezarCon(personaId) {
    abrirConversacionCon(personaId)
      .then((c) => {
        setAbierta(c);
        setBusqueda('');
        return recargarLista();
      })
      .catch((e) => setError(e.message));
  }

  function mandar(e) {
    e.preventDefault();
    const limpio = texto.trim();
    if ((!limpio && adjuntos.length === 0) || !abierta) return;

    const vanAdjuntos = adjuntos;
    setTexto('');
    setAdjuntos([]);
    enviarMensaje(abierta.id, limpio, vanAdjuntos)
      .then((mensaje) => {
        setAbierta((c) => ({ ...c, mensajes: [...c.mensajes, mensaje] }));
        return recargarLista();
      })
      .catch((e) => setError(e.message));
  }

  async function guardarEdicion(idMensaje) {
    const texto = editando?.texto?.trim() ?? '';
    if (!texto) {
      avisar('El mensaje no puede quedar vacío.', 'error');
      return;
    }
    try {
      const actualizado = await editarMensaje(abierta.id, idMensaje, texto);
      setAbierta((c) => ({
        ...c,
        mensajes: c.mensajes.map((m) => (m.id === idMensaje ? actualizado : m)),
      }));
      setEditando(null);
      recargarLista();
    } catch (e) {
      avisar(e.message, 'error');
    }
  }

  async function eliminar(mensaje) {
    try {
      await eliminarMensaje(abierta.id, mensaje.id);
      setAbierta((c) => ({
        ...c,
        mensajes: c.mensajes.filter((m) => m.id !== mensaje.id),
        fijado: c.fijado === mensaje.id ? null : c.fijado,
      }));
      setAEliminar(null);
      avisar('Mensaje eliminado.');
      recargarLista();
    } catch (e) {
      avisar(e.message, 'error');
    }
  }

  async function alternarFijado(idMensaje) {
    try {
      const { fijado } = await fijarMensaje(abierta.id, idMensaje);
      setAbierta((c) => ({ ...c, fijado }));
    } catch (e) {
      avisar(e.message, 'error');
    }
  }

  // El mensaje fijado, para mostrarlo arriba del hilo
  const fijado = abierta?.mensajes.find((m) => m.id === abierta.fijado) ?? null;

  return (
    <div className="pagina">
      <Encabezado
        titulo="Mensajes"
        descripcion="Escribile a tus compañeros y docentes sin salir del campus"
      />

      {error && <p className="error">No se pudieron cargar los mensajes. ¿Está corriendo el backend?</p>}

      <div className="mensajeria">
        <aside className="charlas">
          <label className="barra-busqueda">
            <IconoBuscar />
            <input
              type="search"
              placeholder="Buscar en tus módulos"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
          </label>

          <div className="charlas-lista">
            {!lista && <p className="texto-suave">Cargando…</p>}

            {lista?.length === 0 && !textoBuscado && (
              <p className="texto-suave">
                Todavía no tenés conversaciones. Buscá a alguien de tus módulos acá arriba.
              </p>
            )}

            {charlasVisibles.map((c) => (
              <button
                key={c.id}
                type="button"
                className={abierta?.id === c.id ? 'charla activa' : 'charla'}
                onClick={() => abrir(c.id)}
              >
                <Avatar persona={c.con} />
                <span className="charla-texto">
                  <strong>{c.con.nombre}</strong>
                  <small>{c.ultimo ? c.ultimo.texto : 'Sin mensajes todavía'}</small>
                </span>
                <span className="charla-lado">
                  {c.ultimo && <small>{hace(c.ultimo.fecha)}</small>}
                  {c.sinLeer > 0 && <span className="charla-sin-leer">{c.sinLeer}</span>}
                </span>
              </button>
            ))}

            {nuevosContactos.length > 0 && (
              <>
                <h3 className="charlas-titulo">De tus módulos</h3>
                {nuevosContactos.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="charla"
                    onClick={() => empezarCon(p.id)}
                  >
                    <Avatar persona={p} />
                    <span className="charla-texto">
                      <strong>{p.nombre}</strong>
                      <small>
                        {p.rol} · {p.modulos.join(', ')}
                      </small>
                    </span>
                  </button>
                ))}
              </>
            )}

            {textoBuscado && charlasVisibles.length === 0 && nuevosContactos.length === 0 && (
              <p className="texto-suave">Nadie de tus módulos coincide con la búsqueda.</p>
            )}
          </div>
        </aside>

        <section className="hilo">
          {!abierta ? (
            <p className="texto-suave hilo-vacio">Elegí una conversación para leerla.</p>
          ) : (
            <>
              <header className="hilo-cabecera">
                <Avatar persona={abierta.con} />
                <div className="hilo-quien">
                  <strong>{abierta.con.nombre}</strong>
                  <small>
                    {abierta.con.rol} · {hace(abierta.con.ultimoAcceso)}
                  </small>
                </div>
                <button
                  type="button"
                  className="hilo-cerrar"
                  onClick={cerrarCharla}
                  title="Cerrar la conversación"
                  aria-label="Cerrar la conversación"
                >
                  <IconoCerrar width={18} height={18} />
                </button>
              </header>

              {fijado && (
                <div className="hilo-fijado">
                  <IconoCampanaLlena width={15} height={15} />
                  <p>{fijado.texto || 'Un archivo'}</p>
                  <button
                    type="button"
                    onClick={() => alternarFijado(fijado.id)}
                    title="Soltar el mensaje"
                    aria-label="Soltar el mensaje fijado"
                  >
                    <IconoCerrar width={14} height={14} />
                  </button>
                </div>
              )}

              <div className="hilo-mensajes">
                {abierta.mensajes.length === 0 && (
                  <p className="texto-suave">Escribile el primer mensaje.</p>
                )}
                {abierta.mensajes.map((m) => (
                  <div
                    key={m.id}
                    className={[
                      'burbuja',
                      m.deId === abierta.con.id ? '' : 'mia',
                      abierta.fijado === m.id ? 'fijada' : '',
                    ].filter(Boolean).join(' ')}
                  >
                    {/* Las acciones aparecen al pasar por encima del mensaje:
                        un menú siempre visible en cada burbuja convierte el
                        hilo en una lista de botones. */}
                    <AccionesDelMensaje
                      mensaje={m}
                      mio={m.deId !== abierta.con.id}
                      fijado={abierta.fijado === m.id}
                      onEditar={() => setEditando({ id: m.id, texto: m.texto ?? '' })}
                      onFijar={() => alternarFijado(m.id)}
                      onEliminar={() => setAEliminar(m)}
                    />

                    {editando?.id === m.id ? (
                      <EdicionEnLinea
                        valor={editando.texto}
                        onCambiar={(texto) => setEditando({ id: m.id, texto })}
                        onGuardar={() => guardarEdicion(m.id)}
                        onCancelar={() => setEditando(null)}
                      />
                    ) : (
                      m.texto && <p>{m.texto}</p>
                    )}
                    {m.adjuntos?.map((a) =>
                      a.esImagen && a.url ? (
                        <button
                          key={a.url}
                          type="button"
                          className="adjunto-imagen"
                          onClick={() => setMirando(a)}
                          title={`Ver ${a.nombre}`}
                        >
                          <img src={a.url} alt={a.nombre} loading="lazy" />
                        </button>
                      ) : a.url ? (
                        <a key={a.url} className="adjunto" href={a.url} download={a.nombre}>
                          <IconoArchivo width={16} height={16} />
                          {a.nombre}
                          <small>{pesoDe(a.tamano)}</small>
                        </a>
                      ) : (
                        <span
                          key={a.nombre}
                          className="adjunto sin-archivo"
                          title="Se envió antes de que el campus guardara los archivos"
                        >
                          <IconoArchivo width={16} height={16} />
                          {a.nombre}
                          <small>ya no disponible</small>
                        </span>
                      )
                    )}
                    <small>
                      {horaDe(m.fecha)}
                      {/* Que se editó se dice: el otro leyó una cosa y
                          después ve otra. Ocultarlo es peor que no poder
                          editar. */}
                      {m.editado && <span className="editado"> · editado</span>}
                    </small>
                  </div>
                ))}
                <div ref={finDelHilo} />
              </div>

              <form className="hilo-escribir" onSubmit={mandar}>
                {adjuntos.length > 0 && (
                  <ul className="adjuntos-elegidos">
                    {adjuntos.map((a) => (
                      <li key={a.nombre}>
                        {a.vistaPrevia ? (
                          <img className="adjunto-miniatura" src={a.vistaPrevia} alt="" />
                        ) : (
                          <IconoArchivo width={15} height={15} />
                        )}
                        {a.nombre}
                        <button
                          type="button"
                          onClick={() => sacarAdjunto(a.nombre)}
                          aria-label={`Quitar ${a.nombre}`}
                        >
                          <IconoCerrar width={13} height={13} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                <div className="hilo-escribir-fila">
                  <button
                    type="button"
                    className="hilo-adjuntar"
                    onClick={() => setAdjuntando(true)}
                    disabled={adjuntos.length >= MAXIMO_ARCHIVOS}
                    title={
                      adjuntos.length >= MAXIMO_ARCHIVOS
                        ? `Son hasta ${MAXIMO_ARCHIVOS} archivos por mensaje`
                        : 'Adjuntar imágenes o archivos'
                    }
                    aria-label="Adjuntar imágenes o archivos"
                  >
                    <IconoAdjuntar />
                  </button>

                  <input
                    type="text"
                    placeholder={`Escribile a ${abierta.con.nombre.split(' ')[0]}…`}
                    value={texto}
                    onChange={(e) => setTexto(e.target.value)}
                    aria-label="Mensaje"
                  />

                  <button
                    type="submit"
                    disabled={!texto.trim() && adjuntos.length === 0}
                    aria-label="Enviar"
                  >
                    <IconoEnviar />
                  </button>
                </div>
              </form>
            </>
          )}
        </section>
      </div>

      {/* La imagen en grande. Se cierra con la X, con Escape o tocando
          afuera, igual que el visor de Novedades. */}
      {mirando && <VisorDeImagen adjunto={mirando} onCerrar={() => setMirando(null)} />}

      {adjuntando && (
        <PanelAdjuntar
          yaElegidos={adjuntos.length}
          onAgregar={elegirArchivos}
          onCerrar={() => setAdjuntando(false)}
        />
      )}

      {/* Eliminar un mensaje no se deshace, así que se reconfirma. */}
      {aEliminar && (
        <Confirmacion
          titulo="¿Eliminar el mensaje?"
          mensaje={
            aEliminar.adjuntos?.length
              ? 'Se borra también el archivo que mandaste. No se puede deshacer.'
              : 'No se puede deshacer.'
          }
          textoConfirmar="Sí, eliminar"
          peligro
          onConfirmar={() => eliminar(aEliminar)}
          onCancelar={() => setAEliminar(null)}
        />
      )}
    </div>
  );
}

function VisorDeImagen({ adjunto, onCerrar }) {
  useEffect(() => {
    const alTeclear = (e) => e.key === 'Escape' && onCerrar();
    window.addEventListener('keydown', alTeclear);
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', alTeclear);
      document.body.style.overflow = antes;
    };
  }, [onCerrar]);

  return (
    <div
      className="visor-imagen"
      onClick={(e) => e.target === e.currentTarget && onCerrar()}
      role="presentation"
    >
      <figure>
        <img src={adjunto.url} alt={adjunto.nombre} />
        <figcaption>
          <span>{adjunto.nombre}</span>
          {/* Bajarla es lo otro que se quiere hacer con una imagen que se
              está mirando, así que va acá y no escondido en el hilo. */}
          <a href={adjunto.url} download={adjunto.nombre} className="boton-suave">
            Descargar
          </a>
        </figcaption>
      </figure>

      <button type="button" className="visor-imagen-cerrar" onClick={onCerrar} aria-label="Cerrar">
        <IconoCerrar width={22} height={22} />
      </button>
    </div>
  );
}
