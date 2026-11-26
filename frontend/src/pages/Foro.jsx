import { useEffect, useMemo, useState } from 'react';
import {
  obtenerForo,
  obtenerTema,
  crearTema,
  responderTema,
  obtenerCursos,
  votarMensaje,
  seguirTema,
  retirarTemaForo,
  retirarRespuestaForo,
} from '../services/api.js';
import { avisar } from '../services/avisos.js';
import MotivoDeRetiro from '../components/MotivoDeRetiro.jsx';
import { hace } from '../services/fechas.js';
import Encabezado from '../components/Encabezado.jsx';
import Desplegable from '../components/Desplegable.jsx';
import {
  IconoUsuario,
  IconoEstudiante,
  IconoForo,
  IconoVolver,
  IconoEnviar,
  IconoPulgar,
  IconoCampana,
  IconoBuscar,
  IconoPapelera,
} from '../components/Iconos.jsx';
import Avatar from '../components/Avatar.jsx';

import useTitulo from '../hooks/useTitulo';
/** La cara de quien escribió, con su foto si la tiene. */
function Cara({ persona, grande }) {
  return (
    <span className={grande ? 'docente-avatar grande' : 'docente-avatar'}>
      <Avatar persona={persona} tamano={grande ? 40 : 26} />
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
      <Desplegable
        etiqueta="Asignatura"
        valor={cursoId}
        onCambiar={setCursoId}
        opciones={cursos.map((c) => ({ valor: c.id, nombre: `${c.codigo} · ${c.nombre}` }))}
      />
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
        <button type="submit" className="boton-principal" disabled={!titulo.trim() || !texto.trim()}>
          Abrir el tema
        </button>
      </div>
    </form>
  );
}

// "Me resultó útil", con su cuenta. Los votos son anónimos: se ve cuántos,
// nunca quiénes.
function Util({ mensaje, onVotar }) {
  return (
    <button
      type="button"
      className={mensaje.loVote ? 'voto puesto' : 'voto'}
      onClick={() => onVotar(mensaje.id)}
      aria-pressed={mensaje.loVote}
      title={`${mensaje.utiles} ${mensaje.utiles === 1 ? 'persona lo marcó' : 'personas lo marcaron'} como útil`}
    >
      <IconoPulgar width={15} height={15} />
      {mensaje.utiles > 0 ? `${mensaje.utiles} útil${mensaje.utiles === 1 ? '' : 'es'}` : 'Útil'}
    </button>
  );
}

// Un tema abierto: la consulta arriba y las respuestas en su propia tarjeta
function Tema({ id, onVolver, onCambio }) {
  const [tema, setTema] = useState(null);
  const [texto, setTexto] = useState('');
  const [error, setError] = useState(null);
  // Lo que se está por retirar: el tema entero o una respuesta suelta
  const [retirando, setRetirando] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  function retirar(motivo) {
    setTrabajando(true);
    const esElTema = retirando.que === 'tema';
    const hacer = esElTema
      ? retirarTemaForo(id, motivo)
      : retirarRespuestaForo(id, retirando.mensaje.id, motivo);

    hacer
      .then((actualizado) => {
        avisar(esElTema ? 'Tema retirado del foro.' : 'Respuesta retirada.');
        setRetirando(null);
        onCambio();
        // Si se fue el tema entero no hay a dónde volver dentro de él
        if (esElTema) onVolver();
        else setTema(actualizado);
      })
      .catch((e) => avisar(e.message, 'error'))
      .finally(() => setTrabajando(false));
  }

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

  function votar(mensajeId) {
    votarMensaje(id, mensajeId)
      .then((actualizado) => {
        setTema((t) => ({
          ...t,
          mensajes: t.mensajes.map((m) => (m.id === mensajeId ? actualizado : m)),
        }));
      })
      .catch((e) => setError(e.message));
  }

  function alternarSeguir() {
    seguirTema(id).then(setTema).catch((e) => setError(e.message));
  }

  if (error) return <p className="error">No se pudo cargar el tema.</p>;
  if (!tema) return <p className="texto-suave">Cargando…</p>;

  const [consulta, ...respuestas] = tema.mensajes;

  return (
    <div className="tema">
      {/* La consulta que abre el tema */}
      <article className="tema-consulta">
        <header className="tema-barra">
          <button type="button" className="tema-atras" onClick={onVolver} aria-label="Volver a los temas">
            <IconoVolver width={18} height={18} />
          </button>
          <span className="tema-asignatura" style={{ background: tema.curso?.color }}>
            {tema.curso?.codigo}
          </span>
          <span className="texto-suave">{tema.curso?.nombre}</span>
        </header>

        <div className="tema-autor">
          <Cara persona={tema.autor} grande />
          <div>
            <strong>{tema.autor?.nombre}</strong>
            <small className="texto-suave">
              {hace(tema.fecha)} · {tema.autor?.rol}
            </small>
          </div>
        </div>

        <h2>{tema.titulo}</h2>
        <p className="tema-texto">{consulta?.texto}</p>

        <div className="tema-cuentas">
          <span>
            {respuestas.length} {respuestas.length === 1 ? 'respuesta' : 'respuestas'}
          </span>
          {tema.seguidores > 0 && <span>{tema.seguidores} siguiendo</span>}
        </div>

        <div className="tema-acciones">
          {consulta && <Util mensaje={consulta} onVotar={votar} />}
          {tema.puedeRetirar && (
            <button
              type="button"
              className="voto peligro"
              onClick={() => setRetirando({ que: 'tema' })}
              title="Retirar el tema del foro"
            >
              <IconoPapelera width={15} height={15} />
              Retirar
            </button>
          )}
          <button
            type="button"
            className={tema.siguiendo ? 'voto puesto' : 'voto'}
            onClick={alternarSeguir}
            aria-pressed={tema.siguiendo}
          >
            <IconoCampana width={15} height={15} />
            {tema.siguiendo ? 'Siguiendo' : 'Seguir'}
          </button>
        </div>
      </article>

      {/* Las respuestas, en su propia tarjeta */}
      <section className="tema-respuestas">
        <h3>
          {respuestas.length} {respuestas.length === 1 ? 'respuesta' : 'respuestas'}
        </h3>

        {/* La caja para responder va arriba de las respuestas: así no hay que
            bajar hasta el final de un hilo largo para contestar. */}
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

        {respuestas.length === 0 && (
          <p className="texto-suave">Todavía nadie respondió. Podés ser la primera persona.</p>
        )}

        <ul>
          {respuestas.map((m) => (
            <li key={m.id} className="tema-respuesta">
              <Cara persona={m.autor} />
              <div>
                <div className="tema-mensaje-quien">
                  <strong>{m.autor?.nombre}</strong>
                  <small className="texto-suave">
                    {m.autor?.rol} · {hace(m.fecha)}
                  </small>
                </div>
                <p>{m.texto}</p>
                <div className="tema-acciones">
                  <Util mensaje={m} onVotar={votar} />
                  {m.puedeRetirar && (
                    <button
                      type="button"
                      className="voto peligro"
                      onClick={() => setRetirando({ que: 'respuesta', mensaje: m })}
                      title="Retirar la respuesta"
                      aria-label="Retirar la respuesta"
                    >
                      <IconoPapelera width={14} height={14} />
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {retirando && (
        <MotivoDeRetiro
          titulo={
            retirando.que === 'tema' ? '¿Retirar el tema entero?' : '¿Retirar esta respuesta?'
          }
          queSeRetira={
            retirando.que === 'tema'
              ? `${tema.titulo} · se lleva las ${respuestas.length} respuestas`
              : retirando.mensaje.texto.slice(0, 120)
          }
          autor={
            (retirando.que === 'tema' ? tema.autor : retirando.mensaje.autor)?.nombre ??
            'Quien lo escribió'
          }
          exigeMotivo={
            retirando.que === 'tema'
              ? tema.retiroExigeMotivo
              : retirando.mensaje.retiroExigeMotivo
          }
          trabajando={trabajando}
          onCerrar={() => setRetirando(null)}
          onRetirar={retirar}
        />
      )}
    </div>
  );
}

export default function Foro() {
  useTitulo('Foro');
  const [datos, setDatos] = useState(null);
  const [cursos, setCursos] = useState([]);
  const [asignatura, setAsignatura] = useState('todas');
  const [busqueda, setBusqueda] = useState('');
  const [abierto, setAbierto] = useState(null);
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState(null);
  // El tema que se está por retirar desde la lista
  const [retirandoDeLaLista, setRetirandoDeLaLista] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  function retirarDeLaLista(motivo) {
    setTrabajando(true);
    retirarTemaForo(retirandoDeLaLista.id, motivo)
      .then(() => {
        avisar('Tema retirado del foro.');
        setRetirandoDeLaLista(null);
        recargar();
      })
      .catch((e) => avisar(e.message, 'error'))
      .finally(() => setTrabajando(false));
  }

  function recargar() {
    return obtenerForo().then(setDatos).catch((e) => setError(e.message));
  }

  useEffect(() => {
    recargar();
    obtenerCursos().then(setCursos).catch(() => setCursos([]));
  }, []);

  // Filtra por asignatura y, si se escribió algo, por título, por quién lo
  // abrió o por la materia.
  const visibles = useMemo(() => {
    if (!datos) return [];
    const texto = busqueda.trim().toLowerCase();

    return datos.temas
      .filter((t) => asignatura === 'todas' || String(t.curso?.id) === asignatura)
      .filter((t) => {
        if (!texto) return true;
        const donde = [t.titulo, t.autor?.nombre, t.curso?.nombre, t.curso?.codigo];
        return donde.some((d) => (d ?? '').toLowerCase().includes(texto));
      });
  }, [datos, asignatura, busqueda]);

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

        <label className="barra-busqueda foro-buscador">
          <IconoBuscar />
          <input
            type="search"
            placeholder="Buscar una discusión"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </label>

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
          <li key={t.id} className="tema-fila-caja">
            <button type="button" className="tema-fila" onClick={() => setAbierto(t.id)}>
              <Cara persona={t.autor} />

              <span className="tema-fila-texto">
                <span className="tema-fila-titulo">
                  <span className="tema-asignatura chica" style={{ background: t.curso?.color }}>
                    {t.curso?.codigo}
                  </span>
                  <strong>{t.titulo}</strong>
                </span>
                <small>
                  {t.autor?.nombre} · {hace(t.fecha)}
                </small>
              </span>

              <span className="tema-respuestas-cuenta" title={`${t.respuestas} respuestas`}>
                <IconoForo width={16} height={16} />
                {t.respuestas}
              </span>

              <small className="tema-ultima">
                {t.ultimoAutor ? `Última: ${t.ultimoAutor.nombre} · ` : ''}
                {hace(t.ultimaActividad)}
              </small>
            </button>

            {t.puedeRetirar && (
              <button
                type="button"
                className="tema-retirar"
                onClick={() => setRetirandoDeLaLista(t)}
                title="Retirar el tema del foro"
                aria-label={`Retirar «${t.titulo}»`}
              >
                <IconoPapelera width={15} height={15} />
              </button>
            )}
          </li>
        ))}
      </ul>

      {retirandoDeLaLista && (
        <MotivoDeRetiro
          titulo="¿Retirar el tema entero?"
          queSeRetira={`${retirandoDeLaLista.titulo} · se lleva las ${retirandoDeLaLista.respuestas} respuestas`}
          autor={retirandoDeLaLista.autor?.nombre ?? 'Quien lo abrió'}
          exigeMotivo={retirandoDeLaLista.retiroExigeMotivo}
          trabajando={trabajando}
          onCerrar={() => setRetirandoDeLaLista(null)}
          onRetirar={retirarDeLaLista}
        />
      )}

      {datos && visibles.length === 0 && (
        <p className="texto-suave">
          {busqueda.trim()
            ? 'Ningún tema coincide con la búsqueda.'
            : 'Todavía no hay temas en esta asignatura.'}
        </p>
      )}
    </div>
  );
}
