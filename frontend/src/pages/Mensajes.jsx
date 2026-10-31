import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  obtenerConversaciones,
  obtenerConversacion,
  obtenerContactos,
  enviarMensaje,
  abrirConversacionCon,
} from '../services/api.js';
import { hace } from '../services/fechas.js';
import Encabezado from '../components/Encabezado.jsx';
import {
  IconoUsuario,
  IconoEstudiante,
  IconoEnviar,
  IconoBuscar,
  IconoAdjuntar,
  IconoCerrar,
  IconoArchivo,
} from '../components/Iconos.jsx';

// Tamaño de archivo en algo legible
function pesoDe(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function Avatar({ persona }) {
  const Icono = persona.rol === 'Estudiante' ? IconoEstudiante : IconoUsuario;
  return (
    <span className={`docente-avatar avatar-estado ${persona.estado}`}>
      <Icono />
    </span>
  );
}

function horaDe(iso) {
  return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}

export default function Mensajes() {
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
  const selectorDeArchivos = useRef(null);

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

  function elegirArchivos(e) {
    const elegidos = [...e.target.files].map((f) => ({ nombre: f.name, tamano: f.size }));
    setAdjuntos((previos) => [...previos, ...elegidos].slice(0, 5));
    e.target.value = '';
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

              <div className="hilo-mensajes">
                {abierta.mensajes.length === 0 && (
                  <p className="texto-suave">Escribile el primer mensaje.</p>
                )}
                {abierta.mensajes.map((m) => (
                  <div key={m.id} className={m.deId === abierta.con.id ? 'burbuja' : 'burbuja mia'}>
                    {m.texto && <p>{m.texto}</p>}
                    {m.adjuntos?.map((a) => (
                      <span key={a.nombre} className="adjunto">
                        <IconoArchivo width={16} height={16} />
                        {a.nombre}
                        <small>{pesoDe(a.tamano)}</small>
                      </span>
                    ))}
                    <small>{horaDe(m.fecha)}</small>
                  </div>
                ))}
                <div ref={finDelHilo} />
              </div>

              <form className="hilo-escribir" onSubmit={mandar}>
                {adjuntos.length > 0 && (
                  <ul className="adjuntos-elegidos">
                    {adjuntos.map((a) => (
                      <li key={a.nombre}>
                        <IconoArchivo width={15} height={15} />
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
                  <input
                    type="file"
                    multiple
                    ref={selectorDeArchivos}
                    onChange={elegirArchivos}
                    hidden
                  />
                  <button
                    type="button"
                    className="hilo-adjuntar"
                    onClick={() => selectorDeArchivos.current?.click()}
                    title="Adjuntar imágenes o archivos"
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
    </div>
  );
}
