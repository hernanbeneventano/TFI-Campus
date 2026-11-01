import { useEffect, useMemo, useState } from 'react';
import { obtenerForo, obtenerTema, crearTema, responderTema, obtenerCursos } from '../services/api.js';
import { hace } from '../services/fechas.js';
import Encabezado from '../components/Encabezado.jsx';
import {
  IconoUsuario,
  IconoEstudiante,
  IconoForo,
  IconoVolver,
  IconoEnviar,
} from '../components/Iconos.jsx';

function Avatar({ persona }) {
  const Icono = persona?.rol === 'Estudiante' ? IconoEstudiante : IconoUsuario;
  return (
    <span className="docente-avatar">
      <Icono />
    </span>
  );
}

// Formulario para abrir un tema nuevo
function NuevoTema({ cursos, onCrear, onCancelar }) {
  const [cursoId, setCursoId] = useState(cursos[0]?.id ?? '');
  const [titulo, setTitulo] = useState('');
  const [texto, setTexto] = useState('');

  function enviar(e) {
    e.preventDefault();
    if (!titulo.trim() || !texto.trim() || !cursoId) return;
    onCrear({ cursoId: Number(cursoId), titulo, texto });
  }

  return (
    <form className="editor-novedad" onSubmit={enviar}>
      <select value={cursoId} onChange={(e) => setCursoId(e.target.value)} aria-label="Asignatura">
        {cursos.map((c) => (
          <option key={c.id} value={c.id}>
            {c.codigo} · {c.nombre}
          </option>
        ))}
      </select>
      <input
        type="text"
        placeholder="¿Sobre qué es tu consulta?"
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        aria-label="Título del tema"
      />
      <textarea
        rows={4}
        placeholder="Contá tu duda con el mayor detalle posible…"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        aria-label="Consulta"
      />
      <div className="editor-pie">
        <button type="button" className="boton-suave" onClick={onCancelar}>
          Cancelar
        </button>
        <button
          type="submit"
          className="boton-principal"
          disabled={!titulo.trim() || !texto.trim()}
        >
          Abrir el tema
        </button>
      </div>
    </form>
  );
}

// Un tema abierto: la consulta y sus respuestas
function Tema({ id, onVolver, onCambio }) {
  const [tema, setTema] = useState(null);
  const [texto, setTexto] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerTema(id).then(setTema).catch((e) => setError(e.message));
  }, [id]);

  function responder(e) {
    e.preventDefault();
    const limpio = texto.trim();
    if (!limpio) return;

    setTexto('');
    responderTema(id, limpio)
      .then((mensaje) => {
        setTema((t) => ({ ...t, mensajes: [...t.mensajes, mensaje] }));
        onCambio();
      })
      .catch((e) => setError(e.message));
  }

  if (error) return <p className="error">No se pudo cargar el tema.</p>;
  if (!tema) return <p className="texto-suave">Cargando…</p>;

  return (
    <div className="tema">
      <button type="button" className="volver" onClick={onVolver}>
        <IconoVolver />
        Todos los temas
      </button>

      <header className="tema-cabecera">
        <span className="tema-asignatura" style={{ background: tema.curso?.color }}>
          {tema.curso?.codigo}
        </span>
        <h2>{tema.titulo}</h2>
        <small className="texto-suave">
          Abierto por {tema.autor?.nombre} · {hace(tema.fecha)}
        </small>
      </header>

      <ul className="tema-mensajes">
        {tema.mensajes.map((m, i) => (
          <li key={m.id} className={i === 0 ? 'tema-mensaje consulta' : 'tema-mensaje'}>
            <Avatar persona={m.autor} />
            <div>
              <div className="tema-mensaje-quien">
                <strong>{m.autor?.nombre}</strong>
                <small className="texto-suave">
                  {m.autor?.rol} · {hace(m.fecha)}
                </small>
              </div>
              <p>{m.texto}</p>
            </div>
          </li>
        ))}
      </ul>

      <form className="hilo-escribir" onSubmit={responder}>
        <div className="hilo-escribir-fila">
          <input
            type="text"
            placeholder="Escribí tu respuesta…"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            aria-label="Respuesta"
          />
          <button type="submit" disabled={!texto.trim()} aria-label="Responder">
            <IconoEnviar />
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Foro() {
  const [datos, setDatos] = useState(null);
  const [cursos, setCursos] = useState([]);
  const [asignatura, setAsignatura] = useState('todas');
  const [abierto, setAbierto] = useState(null);
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState(null);

  function recargar() {
    return obtenerForo().then(setDatos).catch((e) => setError(e.message));
  }

  useEffect(() => {
    recargar();
    obtenerCursos().then(setCursos).catch(() => setCursos([]));
  }, []);

  const visibles = useMemo(() => {
    if (!datos) return [];
    if (asignatura === 'todas') return datos.temas;
    return datos.temas.filter((t) => String(t.curso?.id) === asignatura);
  }, [datos, asignatura]);

  if (abierto) {
    return (
      <div className="pagina">
        <Encabezado titulo="Foro" descripcion="Consultas y respuestas, organizadas por asignatura" />
        <Tema
          id={abierto}
          onVolver={() => {
            setAbierto(null);
            recargar();
          }}
          onCambio={recargar}
        />
      </div>
    );
  }

  return (
    <div className="pagina">
      <Encabezado titulo="Foro" descripcion="Consultas y respuestas, organizadas por asignatura" />

      {error && <p className="error">No se pudo cargar el foro. ¿Está corriendo el backend?</p>}
      {!error && !datos && <p className="texto-suave">Cargando…</p>}

      <div className="foro-barra">
        <div className="foro-asignaturas">
          <button
            type="button"
            className={asignatura === 'todas' ? 'asignatura activa' : 'asignatura'}
            onClick={() => setAsignatura('todas')}
          >
            Todas
            <small>{datos?.temas.length ?? 0}</small>
          </button>
          {datos?.asignaturas.map((a) => (
            <button
              key={a.id}
              type="button"
              className={asignatura === String(a.id) ? 'asignatura activa' : 'asignatura'}
              onClick={() => setAsignatura(String(a.id))}
            >
              <span className="asignatura-color" style={{ background: a.color }} />
              {a.codigo}
              <small>{a.temas}</small>
            </button>
          ))}
        </div>

        {!creando && (
          <button type="button" className="boton-principal" onClick={() => setCreando(true)}>
            Nuevo tema
          </button>
        )}
      </div>

      {creando && cursos.length > 0 && (
        <div className="publicacion">
          <NuevoTema
            cursos={cursos}
            onCancelar={() => setCreando(false)}
            onCrear={(datosTema) => {
              crearTema(datosTema)
                .then((tema) => {
                  setCreando(false);
                  setAbierto(tema.id);
                  return recargar();
                })
                .catch((e) => setError(e.message));
            }}
          />
        </div>
      )}

      <ul className="temas">
        {visibles.map((t) => (
          <li key={t.id}>
            <button type="button" className="tema-fila" onClick={() => setAbierto(t.id)}>
              <span className="tema-asignatura" style={{ background: t.curso?.color }}>
                {t.curso?.codigo}
              </span>
              <span className="tema-fila-texto">
                <strong>{t.titulo}</strong>
                <small>
                  {t.autor?.nombre} · {hace(t.fecha)}
                </small>
              </span>
              <span className="tema-respuestas" title={`${t.respuestas} respuestas`}>
                <IconoForo width={16} height={16} />
                {t.respuestas}
              </span>
              <small className="tema-ultima">
                {t.ultimoAutor ? `${t.ultimoAutor.nombre} · ` : ''}
                {hace(t.ultimaActividad)}
              </small>
            </button>
          </li>
        ))}
      </ul>

      {datos && visibles.length === 0 && (
        <p className="texto-suave">Todavía no hay temas en esta asignatura.</p>
      )}
    </div>
  );
}
