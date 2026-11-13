import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import BarraProgreso from '../BarraProgreso.jsx';
import Confirmacion from '../Confirmacion.jsx';
import {
  IconoAdvertencia,
  IconoCandado,
  IconoCheckCirculo,
  IconoEstudiante,
  IconoNotas,
} from '../Iconos.jsx';
import { cerrarActa, guardarResultados, obtenerMesaGestion } from '../../services/api.js';
import { fechaConDia } from '../../services/fechas.js';
import { avisar } from '../../services/avisos.js';
import {
  Condicion,
  EstadoMesa,
  NombreMateria,
  Resultado,
  fechaNumerica,
  horario,
} from './comun.jsx';

function avance(hechos, total) {
  return { hechos, total, porcentaje: total ? Math.round((hechos / total) * 100) : 0 };
}

// Lo que hay escrito en una fila, comparado con lo que dicen las reglas.
// Las mismas que aplica el servidor; esto es para avisar antes de mandar.
function problemaDe(fila, notaAprobacion, notaMaxima) {
  if (!fila.resultado) return null;
  if (fila.resultado === 'Ausente') return null;
  if (fila.nota === '') return 'Falta la nota';
  const nota = Number(fila.nota);
  if (!Number.isInteger(nota) || nota < 1 || nota > notaMaxima) return `Entre 1 y ${notaMaxima}`;
  if (fila.resultado === 'Aprobado' && nota < notaAprobacion) return `Aprueba con ${notaAprobacion} o más`;
  if (fila.resultado === 'Desaprobado' && nota >= notaAprobacion) return `Con ${nota} aprueba`;
  return null;
}

export default function Resultados({ opciones, mesas, onCambio }) {
  const [parametros, setParametros] = useSearchParams();

  // Se califica lo que ya se tomó y no se canceló
  const calificables = mesas.filter((m) => m.tomada && m.estado !== 'cancelada');
  const abiertas = calificables.filter((m) => !m.actaCerrada);
  const cerradas = calificables.filter((m) => m.actaCerrada);
  const proximas = mesas.filter((m) => !m.tomada && m.estado !== 'cancelada').length;

  // ?mesa=ID llega desde Fechas; si no, la primera con el acta abierta
  const pedida = Number(parametros.get('mesa'));
  const elegidaId = calificables.some((m) => m.id === pedida) ? pedida : (abiertas[0] ?? cerradas[0])?.id;

  function elegir(id) {
    const siguiente = new URLSearchParams(parametros);
    siguiente.set('mesa', id);
    setParametros(siguiente, { replace: true });
  }

  if (calificables.length === 0) {
    return (
      <div className="vacio">
        <IconoNotas width={34} height={34} />
        <h3>Todavía no hay mesas para calificar</h3>
        <p className="texto-suave">
          Las notas se cargan después del examen.
          {proximas > 0 && ` Tenés ${proximas} ${proximas === 1 ? 'mesa próxima' : 'mesas próximas'}.`}
        </p>
      </div>
    );
  }

  return (
    <section className="finales-resultados">
      <aside className="finales-actas" aria-label="Mesas para calificar">
        {[
          ['Por cerrar', abiertas],
          ['Actas cerradas', cerradas],
        ].map(
          ([titulo, lista]) =>
            lista.length > 0 && (
              <div key={titulo}>
                <h3 className="finales-actas-titulo">
                  {titulo} <small>{lista.length}</small>
                </h3>
                <ul>
                  {lista.map((m) => (
                    <li key={m.id}>
                      <button
                        type="button"
                        className={m.id === elegidaId ? 'finales-acta activa' : 'finales-acta'}
                        onClick={() => elegir(m.id)}
                        aria-current={m.id === elegidaId}
                        style={{ '--color-materia': m.materia.color || 'var(--oscuro)' }}
                      >
                        <NombreMateria materia={m.materia} />
                        <small>
                          {fechaNumerica(m.fecha)} · {m.llamado}
                        </small>
                        {m.actaCerrada ? (
                          <span className="finales-acta-cerrada">
                            <IconoCandado width={13} height={13} /> {m.inscriptos} resultados
                          </span>
                        ) : (
                          <BarraProgreso avance={avance(m.conResultado, m.inscriptos)} />
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )
        )}
      </aside>

      {elegidaId && (
        <Planilla key={elegidaId} mesaId={elegidaId} opciones={opciones} onCambio={onCambio} />
      )}
    </section>
  );
}

function Planilla({ mesaId, opciones, onCambio }) {
  const { notaAprobacion, notaMaxima, resultados: condiciones } = opciones;
  const [mesa, setMesa] = useState(null);
  const [filas, setFilas] = useState([]);
  const [original, setOriginal] = useState('');
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);

  function cargar(respuesta) {
    setMesa(respuesta.mesa);
    const activas = respuesta.inscriptos
      .filter((i) => i.estado === 'Inscripto')
      .map((i) => ({
        id: i.id,
        alumno: i.alumno,
        comision: i.comision,
        condicion: i.condicion,
        resultado: i.resultado ?? '',
        nota: i.nota ?? '',
      }));
    setFilas(activas);
    setOriginal(JSON.stringify(activas.map(({ id, resultado, nota }) => ({ id, resultado, nota }))));
  }

  useEffect(() => {
    obtenerMesaGestion(mesaId)
      .then(cargar)
      .catch((e) => setError(e.message));
  }, [mesaId]);

  const sinGuardar =
    JSON.stringify(filas.map(({ id, resultado, nota }) => ({ id, resultado, nota }))) !== original;

  // Avisar antes de cerrar la pestaña con notas sin guardar
  useEffect(() => {
    if (!sinGuardar) return;
    const alSalir = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', alSalir);
    return () => window.removeEventListener('beforeunload', alSalir);
  }, [sinGuardar]);

  const cuenta = useMemo(() => {
    const c = { Aprobado: 0, Desaprobado: 0, Ausente: 0, falta: 0 };
    for (const f of filas) {
      if (f.resultado) c[f.resultado] += 1;
      else c.falta += 1;
    }
    return c;
  }, [filas]);

  const problemas = filas.map((f) => problemaDe(f, notaAprobacion, notaMaxima));
  const hayProblemas = problemas.some(Boolean);

  if (error && !mesa) return <p className="aviso-error">{error}</p>;
  if (!mesa) return <div className="finales-planilla finales-planilla-cargando" aria-busy="true" />;

  const editable = mesa.puedeCalificar;

  // Escribir la nota ya sugiere la condición; Ausente borra la nota
  function cambiarNota(id, valor) {
    setFilas((todas) =>
      todas.map((f) => {
        if (f.id !== id) return f;
        const nota = valor === '' ? '' : Number(valor);
        let resultado = f.resultado;
        if (valor === '') resultado = f.resultado === 'Ausente' ? 'Ausente' : '';
        else if (Number.isFinite(nota)) resultado = nota >= notaAprobacion ? 'Aprobado' : 'Desaprobado';
        return { ...f, nota: valor === '' ? '' : valor, resultado };
      })
    );
  }

  function cambiarCondicion(id, resultado) {
    setFilas((todas) =>
      todas.map((f) =>
        f.id !== id
          ? f
          : {
              ...f,
              // Tocar la elegida la saca
              resultado: f.resultado === resultado ? '' : resultado,
              nota: resultado === 'Ausente' ? '' : f.nota,
            }
      )
    );
  }

  const cuerpo = () =>
    filas.map((f) => ({
      inscripcionId: f.id,
      resultado: f.resultado || null,
      nota: f.resultado && f.resultado !== 'Ausente' ? Number(f.nota) : null,
    }));

  async function guardar() {
    if (hayProblemas) {
      setError('Hay notas que no coinciden con la condición. Revisá las marcadas en rojo.');
      return false;
    }
    setGuardando(true);
    setError(null);
    try {
      cargar(await guardarResultados(mesa.id, cuerpo()));
      onCambio();
      return true;
    } catch (e) {
      setError(e.message);
      avisar(e.message, 'error');
      return false;
    } finally {
      setGuardando(false);
    }
  }

  async function cerrar() {
    // Se guarda primero: el acta se cierra con lo que está en pantalla
    if (sinGuardar && !(await guardar())) {
      setConfirmando(false);
      return;
    }
    setGuardando(true);
    try {
      cargar(await cerrarActa(mesa.id));
      setConfirmando(false);
      onCambio();
      avisar('Acta cerrada. Los resultados ya están en el historial de cada alumno.');
    } catch (e) {
      setError(e.message);
      setConfirmando(false);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div
      className="finales-planilla"
      style={{ '--color-materia': mesa.materia.color || 'var(--oscuro)' }}
    >
      <header className="finales-planilla-cabecera">
        <div>
          <NombreMateria materia={mesa.materia} />
          <h2>{mesa.llamado}</h2>
          <p className="texto-suave">
            {fechaConDia(mesa.fecha)}, {horario(mesa)} · Tribunal: {mesa.tribunal.map((t) => t.nombre).join(', ')}
          </p>
        </div>
        <EstadoMesa mesa={mesa} />
      </header>

      <div className="finales-conteo" aria-label="Resumen del acta">
        <span className="aprobado">
          <strong>{cuenta.Aprobado}</strong> aprobados
        </span>
        <span className="desaprobado">
          <strong>{cuenta.Desaprobado}</strong> desaprobados
        </span>
        <span className="ausente">
          <strong>{cuenta.Ausente}</strong> ausentes
        </span>
        {cuenta.falta > 0 && (
          <span className="falta">
            <strong>{cuenta.falta}</strong> sin cargar
          </span>
        )}
        <span className="texto-suave finales-regla">Se aprueba con {notaAprobacion}</span>
      </div>

      {filas.length === 0 ? (
        <p className="texto-suave finales-sin-gente">No hubo inscriptos en esta mesa.</p>
      ) : (
        <table className="finales-tabla planilla">
          <thead>
            <tr>
              <th scope="col">Alumno</th>
              <th scope="col">Legajo</th>
              <th scope="col">Condición</th>
              <th scope="col">Nota</th>
              <th scope="col">Resultado</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f, i) => (
              <tr key={f.id} className={problemas[i] ? 'con-problema' : undefined}>
                <td data-etiqueta="Alumno">
                  <span className="finales-alumno">
                    <span className="finales-avatar">
                      <IconoEstudiante width={18} height={18} />
                    </span>
                    <span>
                      <strong>{f.alumno.nombre}</strong>
                      <small>Comisión {f.comision}</small>
                    </span>
                  </span>
                </td>
                <td data-etiqueta="Legajo">{f.alumno.legajo ?? '—'}</td>
                <td data-etiqueta="Condición">
                  <Condicion condicion={f.condicion} />
                </td>
                <td data-etiqueta="Nota">
                  {editable ? (
                    <span className="finales-nota">
                      <input
                        type="number"
                        min={1}
                        max={notaMaxima}
                        step={1}
                        inputMode="numeric"
                        value={f.nota}
                        disabled={f.resultado === 'Ausente'}
                        onChange={(e) => cambiarNota(f.id, e.target.value)}
                        aria-label={`Nota de ${f.alumno.nombre}`}
                        aria-invalid={Boolean(problemas[i])}
                      />
                      {problemas[i] && <small className="finales-problema">{problemas[i]}</small>}
                    </span>
                  ) : (
                    <strong>{f.nota === '' ? '—' : f.nota}</strong>
                  )}
                </td>
                <td data-etiqueta="Resultado">
                  {editable ? (
                    <div className="finales-segmentos" role="group" aria-label={`Resultado de ${f.alumno.nombre}`}>
                      {condiciones.map((c) => (
                        <button
                          key={c}
                          type="button"
                          className={f.resultado === c ? `elegido ${c.toLowerCase()}` : ''}
                          onClick={() => cambiarCondicion(f.id, c)}
                          aria-pressed={f.resultado === c}
                        >
                          {c}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <Resultado resultado={f.resultado} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {error && (
        <p className="error aporte-error" role="alert">
          <IconoAdvertencia width={16} height={16} />
          {error}
        </p>
      )}

      {editable ? (
        <div className="finales-planilla-pie">
          <span className="texto-suave">
            {sinGuardar ? 'Hay cambios sin guardar.' : 'Todo guardado. El acta sigue abierta.'}
          </span>
          <button type="button" className="boton-suave" onClick={guardar} disabled={!sinGuardar || guardando}>
            {guardando ? 'Guardando…' : 'Guardar borrador'}
          </button>
          <button
            type="button"
            className="boton-principal"
            onClick={() => setConfirmando(true)}
            disabled={guardando || cuenta.falta > 0 || hayProblemas || filas.length === 0}
            title={cuenta.falta > 0 ? 'Falta cargar a alguien' : undefined}
          >
            <IconoCandado width={16} height={16} />
            Cerrar acta
          </button>
        </div>
      ) : (
        <p className="finales-cerrada">
          {mesa.actaCerrada ? (
            <>
              <IconoCheckCirculo width={18} height={18} />
              Acta cerrada: los resultados están en el historial académico de cada alumno.
            </>
          ) : (
            <>
              <IconoCandado width={16} height={16} />
              Solo el tribunal de la mesa carga las notas.
            </>
          )}
        </p>
      )}

      {confirmando && (
        <Confirmacion
          titulo="¿Cerrás el acta?"
          mensaje="Después de cerrarla las notas no se pueden cambiar. Pasan al historial académico de cada alumno, que se entera por mensaje."
          detalles={[
            { etiqueta: 'Materia', valor: `${mesa.materia.nombre} (${mesa.materia.codigo})` },
            { etiqueta: 'Mesa', valor: `${mesa.llamado} · ${fechaConDia(mesa.fecha)}` },
            {
              etiqueta: 'Resultados',
              valor: `${cuenta.Aprobado} aprobados · ${cuenta.Desaprobado} desaprobados · ${cuenta.Ausente} ausentes`,
            },
          ]}
          textoConfirmar="Sí, cerrar el acta"
          peligro
          trabajando={guardando}
          onConfirmar={cerrar}
          onCancelar={() => setConfirmando(false)}
        />
      )}
    </div>
  );
}
