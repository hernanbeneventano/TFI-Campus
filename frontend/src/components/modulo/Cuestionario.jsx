// Un cuestionario de opción múltiple, del lado del alumno.
//
// Se responde una sola vez y se corrige en el acto. Una sola vez porque,
// pudiendo repetir, el cuestionario deja de medir nada: se prueba hasta
// acertar. Por eso se avisa antes de mandar.
//
// Las respuestas correctas no están en la pantalla hasta que se responde:
// el servidor no las manda. Esconderlas en el navegador sería regalárselas a
// cualquiera que abra las herramientas de desarrollo.

import { useEffect, useState } from 'react';
import { abrirCuestionario, responderCuestionario } from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import { fechaLarga } from '../../services/fechas.js';
import { IconoCheckCirculo, IconoCerrar, IconoReloj } from '../Iconos.jsx';

export default function Cuestionario({ tareaId }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [elegidas, setElegidas] = useState({});
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let vigente = true;
    abrirCuestionario(tareaId)
      .then((d) => vigente && setDatos(d))
      .catch((e) => vigente && setError(e.message));
    return () => {
      vigente = false;
    };
  }, [tareaId]);

  async function enviar() {
    setEnviando(true);
    try {
      const r = await responderCuestionario(tareaId, elegidas);
      setDatos((previo) => ({ ...previo, respondido: true, resultado: r.resultado }));
      setConfirmando(false);
      avisar(`Cuestionario entregado. Tu nota es ${r.resultado.nota}.`);
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setEnviando(false);
    }
  }

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando el cuestionario…</p>;

  const { trabajo, preguntas, abierto, respondido, resultado } = datos;
  const faltan = preguntas.length - Object.keys(elegidas).length;

  // Ya respondido: se muestra qué estuvo bien, que es de lo que se aprende
  if (respondido && resultado) {
    const porPregunta = new Map(resultado.detalle.map((d) => [d.preguntaId, d]));
    return (
      <div className="cuestionario">
        <header className="cuestionario-resultado">
          <span className={`nota-celda ${resultado.nota >= 6 ? 'aprobada' : 'desaprobada'}`}>
            {resultado.nota}
          </span>
          <div>
            <h3>Ya lo respondiste</h3>
            <p>
              {resultado.puntos} de {resultado.total} puntos · {fechaLarga(resultado.fecha)}
            </p>
          </div>
        </header>

        <ol className="preguntas-resueltas">
          {preguntas.map((p) => {
            const d = porPregunta.get(p.id);
            return (
              <li key={p.id} className={d?.acerto ? 'bien' : 'mal'}>
                <h4>
                  {d?.acerto ? (
                    <IconoCheckCirculo width={16} height={16} />
                  ) : (
                    <IconoCerrar width={16} height={16} />
                  )}
                  {p.texto}
                </h4>
                <ul>
                  {p.opciones.map((o, i) => (
                    <li
                      key={i}
                      className={[
                        i === d?.correcta ? 'correcta' : '',
                        i === d?.elegida && i !== d?.correcta ? 'elegida-mal' : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                    >
                      {o}
                      {i === d?.correcta && <small>correcta</small>}
                      {i === d?.elegida && i !== d?.correcta && <small>tu respuesta</small>}
                    </li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  if (!abierto) {
    return (
      <p className="vacio">
        <IconoReloj width={16} height={16} /> El cuestionario está cerrado y no llegaste a
        responderlo.
      </p>
    );
  }

  return (
    <div className="cuestionario">
      {/* La consigna no se repite: ya la muestra el visor arriba */}
      <p className="nota-bloque">
        {preguntas.length} {preguntas.length === 1 ? 'pregunta' : 'preguntas'} · se responde una
        sola vez · hasta el {fechaLarga(trabajo.fechaLimite)}
      </p>

      <ol className="preguntas-resueltas respondiendo">
        {preguntas.map((p, n) => (
          <li key={p.id} className={elegidas[p.id] !== undefined ? 'contestada' : ''}>
            <h4>
              <span className="numero">{n + 1}</span>
              {p.texto}
            </h4>
            <ul>
              {p.opciones.map((o, i) => (
                <li key={i}>
                  <label className={elegidas[p.id] === i ? 'opcion elegida' : 'opcion'}>
                    <input
                      type="radio"
                      name={`pregunta-${p.id}`}
                      checked={elegidas[p.id] === i}
                      onChange={() => setElegidas((e) => ({ ...e, [p.id]: i }))}
                    />
                    <span className="marca" aria-hidden="true" />
                    {o}
                  </label>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>

      <div className="cuestionario-pie">
        {faltan > 0 && (
          <small>
            Te {faltan === 1 ? 'falta' : 'faltan'} {faltan}{' '}
            {faltan === 1 ? 'pregunta' : 'preguntas'}
          </small>
        )}
        <button
          type="button"
          className="boton-principal"
          disabled={faltan > 0 || enviando}
          onClick={() => setConfirmando(true)}
        >
          Entregar
        </button>
      </div>

      {confirmando && (
        <div
          className="correccion-fondo"
          onClick={(e) => e.target === e.currentTarget && setConfirmando(false)}
          role="presentation"
        >
          <div className="correccion" role="alertdialog" aria-modal="true">
            <h3>¿Entregás el cuestionario?</h3>
            <p className="correccion-trabajo">
              Se corrige al instante y no se puede volver a responder.
            </p>
            <div className="editor-botones">
              <button
                type="button"
                className="boton-suave"
                onClick={() => setConfirmando(false)}
                disabled={enviando}
              >
                Volver
              </button>
              <button
                type="button"
                className="boton-principal"
                onClick={enviar}
                disabled={enviando}
              >
                {enviando ? 'Un momento…' : 'Sí, entregar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
