// La pestaña Asistencias dentro de un módulo.
//
// Dos caras según quién mire, como el resto del campus:
//
// - **Docente**: la planificación, las clases dictadas y cómo viene cada
//   alumno. Es donde toma lista, que es lo que hace dos veces por semana.
// - **Alumno**: su situación en esa materia, clase por clase, y el botón
//   para pedir que le justifiquen una falta.
//
// El panel de todas las materias juntas está en `/asistencias`; acá se mira
// una sola, que es el contexto en el que uno ya está parado.

import { useCallback, useEffect, useState } from 'react';
import {
  obtenerPlanificacion,
  guardarPlanificacion,
  obtenerClases,
  crearClase,
  obtenerListaDeClase,
  guardarLista,
  obtenerAsistenciaDeAlumnos,
  obtenerMiAsistencia,
  pedirJustificacion,
} from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import { fechaConDia, fechaLarga } from '../../services/fechas.js';
import Confirmacion from '../Confirmacion.jsx';
import TomarLista from './TomarLista.jsx';
import { ESTADOS, Situacion, EstadoAsistencia, BarraAsistencia, Dato } from './comun.jsx';
import { IconoMas, IconoLapiz, IconoPersonas, IconoCerrar } from '../Iconos.jsx';

// El <input type="datetime-local"> quiere la hora local, no ISO
function ahoraParaElCampo() {
  const f = new Date();
  const dos = (n) => String(n).padStart(2, '0');
  return `${f.getFullYear()}-${dos(f.getMonth() + 1)}-${dos(f.getDate())}T${dos(
    f.getHours()
  )}:${dos(f.getMinutes())}`;
}

// ===================== Planificación =====================
function Planificacion({ datos, onGuardar, trabajando }) {
  const [editando, setEditando] = useState(false);
  const [total, setTotal] = useState(datos.clasesPlanificadas ?? '');

  if (editando) {
    return (
      <form
        className="editor-seccion"
        onSubmit={(e) => {
          e.preventDefault();
          onGuardar(Number(total)).then(() => setEditando(false));
        }}
      >
        <label>
          <span>Clases previstas para el período</span>
          <input
            type="number"
            min="1"
            max="300"
            value={total}
            autoFocus
            onChange={(e) => setTotal(e.target.value)}
          />
        </label>
        <div className="editor-botones">
          <button
            type="button"
            className="boton-suave"
            onClick={() => setEditando(false)}
            disabled={trabajando}
          >
            Cancelar
          </button>
          <button type="submit" className="boton-principal" disabled={trabajando || !total}>
            Guardar
          </button>
        </div>
      </form>
    );
  }

  return (
    <section className="planificacion">
      <div className="datos-asistencia">
        <Dato valor={datos.clasesPlanificadas ?? '—'} etiqueta="clases previstas" />
        <Dato valor={datos.clasesDictadas} etiqueta="dictadas" />
        <Dato valor={datos.clasesPendientes ?? '—'} etiqueta="pendientes" />
        <Dato valor={`${datos.minimoAsistencia}%`} etiqueta="mínimo exigido" />
        <Dato
          valor={datos.maximoInasistencias ?? '—'}
          etiqueta="faltas permitidas"
          variante="destacado"
        />
      </div>

      {datos.puedeEditar && (
        <button type="button" className="boton-suave" onClick={() => setEditando(true)}>
          <IconoLapiz width={15} height={15} />
          {datos.clasesPlanificadas ? 'Cambiar las clases previstas' : 'Planificar las clases'}
        </button>
      )}
    </section>
  );
}

// ===================== La cara del docente =====================
function VistaDocente({ cursoId }) {
  const [plan, setPlan] = useState(null);
  const [clases, setClases] = useState(null);
  const [alumnos, setAlumnos] = useState(null);
  const [vista, setVista] = useState('clases');
  const [tomando, setTomando] = useState(null);
  const [nueva, setNueva] = useState(null);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);

  const traer = useCallback(() => {
    setError(null);
    obtenerPlanificacion(cursoId).then(setPlan).catch((e) => setError(e.message));
    obtenerClases(cursoId).then(setClases).catch((e) => setError(e.message));
    obtenerAsistenciaDeAlumnos(cursoId).then(setAlumnos).catch((e) => setError(e.message));
  }, [cursoId]);

  useEffect(traer, [traer]);

  async function accionar(accion, exito) {
    setTrabajando(true);
    try {
      const r = await accion();
      traer();
      if (exito) avisar(exito);
      return r;
    } catch (e) {
      avisar(e.message, 'error');
      throw e;
    } finally {
      setTrabajando(false);
    }
  }

  async function abrirLista(clase) {
    try {
      setTomando(await obtenerListaDeClase(cursoId, clase.id));
    } catch (e) {
      avisar(e.message, 'error');
    }
  }

  if (error) return <p className="aviso-error">{error}</p>;
  if (!plan || !clases || !alumnos) return <p className="texto-suave">Cargando…</p>;

  return (
    <div className="asistencias">
      <Planificacion
        datos={plan}
        trabajando={trabajando}
        onGuardar={(total) =>
          accionar(() => guardarPlanificacion(cursoId, total), 'Planificación guardada.')
        }
      />

      <nav className="pestanas" aria-label="Vistas de asistencia">
        <button
          type="button"
          className={vista === 'clases' ? 'pestana activa' : 'pestana'}
          onClick={() => setVista('clases')}
        >
          Clases
          <small className="pestana-cantidad">{clases.clases.length}</small>
        </button>
        <button
          type="button"
          className={vista === 'alumnos' ? 'pestana activa' : 'pestana'}
          onClick={() => setVista('alumnos')}
        >
          Alumnos
          {alumnos.resumen.porDebajo + alumnos.resumen.enRiesgo > 0 && (
            <small className="pestana-cantidad alerta">
              {alumnos.resumen.porDebajo + alumnos.resumen.enRiesgo}
            </small>
          )}
        </button>
      </nav>

      {vista === 'clases' && (
        <>
          <div className="barra-asistencias">
            {!nueva && (
              <button
                type="button"
                className="boton-principal"
                onClick={() => setNueva({ fecha: ahoraParaElCampo(), tema: '', estado: 'dictada', motivo: '' })}
              >
                <IconoMas width={16} height={16} />
                Registrar una clase
              </button>
            )}
          </div>

          {nueva && (
            <form
              className="editor-seccion"
              onSubmit={(e) => {
                e.preventDefault();
                accionar(
                  () =>
                    crearClase(cursoId, {
                      fecha: new Date(nueva.fecha).toISOString(),
                      tema: nueva.tema || null,
                      estado: nueva.estado,
                      motivo: nueva.motivo || null,
                    }),
                  nueva.estado === 'suspendida' ? 'Clase suspendida registrada.' : 'Clase registrada.'
                ).then(() => setNueva(null));
              }}
            >
              <div className="editor-fila">
                <label>
                  <span>Fecha y hora</span>
                  <input
                    type="datetime-local"
                    value={nueva.fecha}
                    onChange={(e) => setNueva({ ...nueva, fecha: e.target.value })}
                  />
                </label>
                <label>
                  <span>¿Se dictó?</span>
                  <select
                    value={nueva.estado}
                    onChange={(e) => setNueva({ ...nueva, estado: e.target.value })}
                  >
                    <option value="dictada">Sí, se dictó</option>
                    <option value="suspendida">No, se suspendió</option>
                  </select>
                </label>
              </div>

              {nueva.estado === 'dictada' ? (
                <label>
                  <span>
                    Tema <small>opcional</small>
                  </span>
                  <input
                    type="text"
                    value={nueva.tema}
                    maxLength={200}
                    placeholder="Recorridos en árboles"
                    onChange={(e) => setNueva({ ...nueva, tema: e.target.value })}
                  />
                </label>
              ) : (
                <label>
                  <span>Motivo de la suspensión</span>
                  <input
                    type="text"
                    value={nueva.motivo}
                    maxLength={500}
                    placeholder="Paro de transporte"
                    onChange={(e) => setNueva({ ...nueva, motivo: e.target.value })}
                  />
                </label>
              )}

              <div className="editor-botones">
                <button type="button" className="boton-suave" onClick={() => setNueva(null)}>
                  Cancelar
                </button>
                <button type="submit" className="boton-principal" disabled={trabajando}>
                  Registrar
                </button>
              </div>
            </form>
          )}

          <ul className="clases">
            {clases.clases.map((clase) => (
              <li
                key={clase.id}
                className={`clase ${clase.estado === 'suspendida' ? 'suspendida' : ''}`}
              >
                <div className="clase-dia" aria-hidden="true">
                  <strong>{new Date(clase.fecha).getDate()}</strong>
                  <small>
                    {new Intl.DateTimeFormat('es-AR', { month: 'short' }).format(
                      new Date(clase.fecha)
                    )}
                  </small>
                </div>

                <div className="clase-texto">
                  <strong>{clase.tema || (clase.estado === 'suspendida' ? 'Clase suspendida' : 'Sin tema')}</strong>
                  <small>{fechaConDia(clase.fecha)}</small>
                  {clase.estado === 'suspendida' && clase.motivo && (
                    <small className="clase-motivo">{clase.motivo}</small>
                  )}
                </div>

                {clase.estado === 'suspendida' ? (
                  <span className="estado-asistencia vacio">No cuenta</span>
                ) : (
                  <>
                    <div className="clase-resumen">
                      {clase.resumen.tomada ? (
                        <>
                          <span className="cuenta presente">
                            <strong>{clase.resumen.presente}</strong> presentes
                          </span>
                          {clase.resumen.ausente > 0 && (
                            <span className="cuenta ausente">
                              <strong>{clase.resumen.ausente}</strong> ausentes
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="estado-asistencia vacio">Sin tomar</span>
                      )}
                    </div>

                    <button
                      type="button"
                      className={clase.resumen.tomada ? 'boton-suave' : 'boton-principal'}
                      onClick={() => abrirLista(clase)}
                    >
                      {clase.resumen.tomada ? 'Ver o corregir' : 'Tomar lista'}
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {vista === 'alumnos' && (
        <>
          <div className="datos-asistencia">
            <Dato valor={alumnos.resumen.alumnos} etiqueta="alumnos" />
            <Dato valor={`${alumnos.resumen.promedio ?? '—'}%`} etiqueta="promedio" />
            <Dato
              valor={alumnos.resumen.enRiesgo}
              etiqueta="en riesgo"
              variante={alumnos.resumen.enRiesgo > 0 ? 'ambar' : ''}
            />
            <Dato
              valor={alumnos.resumen.porDebajo}
              etiqueta="por debajo"
              variante={alumnos.resumen.porDebajo > 0 ? 'rojo' : ''}
            />
          </div>

          <ul className="alumnos-asistencia">
            {alumnos.alumnos.map((a) => (
              <li key={a.id}>
                <div className="alumno-nombre">
                  <strong>{a.nombre}</strong>
                  <Situacion estado={a.estado} chica />
                </div>

                <div className="alumno-barra">
                  <BarraAsistencia
                    porcentaje={a.porcentaje}
                    minimo={a.minimoAsistencia}
                    estado={a.estado}
                  />
                  <small>
                    {a.porcentaje ?? '—'}% · {a.presentes} presentes, {a.ausentes} ausentes
                    {a.justificadas > 0 && `, ${a.justificadas} justificadas`}
                  </small>
                </div>

                <div className="alumno-faltas">
                  <strong>{a.inasistenciasDisponibles ?? '—'}</strong>
                  <small>faltas disponibles</small>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {tomando && (
        <TomarLista
          datos={tomando}
          trabajando={trabajando}
          onCerrar={() => setTomando(null)}
          onGuardar={(valores) =>
            accionar(
              () => guardarLista(cursoId, tomando.clase.id, valores),
              'Lista guardada.'
            ).then(() => setTomando(null))
          }
        />
      )}
    </div>
  );
}

// ===================== La cara del alumno =====================
function VistaAlumno({ cursoId }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [pidiendo, setPidiendo] = useState(null);
  const [motivo, setMotivo] = useState('');
  const [archivo, setArchivo] = useState('');
  const [trabajando, setTrabajando] = useState(false);

  const traer = useCallback(() => {
    obtenerMiAsistencia(cursoId).then(setDatos).catch((e) => setError(e.message));
  }, [cursoId]);

  useEffect(traer, [traer]);

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  const s = datos.situacion;

  async function enviarPedido() {
    setTrabajando(true);
    try {
      await pedirJustificacion({
        claseId: pidiendo.claseId,
        motivo: motivo.trim(),
        archivo: archivo.trim() || null,
      });
      avisar('Pedido enviado. Te avisamos cuando lo revisen.');
      setPidiendo(null);
      setMotivo('');
      setArchivo('');
      traer();
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

  return (
    <div className="asistencias">
      <section className={`mi-asistencia ${(s.estado || '').replace(/ /g, '-')}`}>
        <div className="mi-asistencia-nota">
          <strong>{s.porcentaje ?? '—'}%</strong>
          <small>de asistencia</small>
        </div>

        <div className="mi-asistencia-texto">
          <Situacion estado={s.estado} />
          <BarraAsistencia
            porcentaje={s.porcentaje}
            minimo={s.minimoAsistencia}
            estado={s.estado}
          />
          <p>
            {s.inasistenciasDisponibles === null
              ? `Mínimo exigido: ${s.minimoAsistencia}%.`
              : s.inasistenciasDisponibles > 0
                ? `Podés faltar ${s.inasistenciasDisponibles} ${
                    s.inasistenciasDisponibles === 1 ? 'clase más' : 'clases más'
                  } sobre las ${s.clasesPlanificadas} previstas.`
                : 'Ya usaste todas las faltas permitidas.'}
          </p>
        </div>
      </section>

      <div className="datos-asistencia">
        <Dato valor={s.clasesDictadas} etiqueta="clases dictadas" />
        <Dato valor={s.presentes} etiqueta="asistencias" variante="verde" />
        <Dato valor={s.ausentes} etiqueta="inasistencias" variante={s.ausentes ? 'rojo' : ''} />
        <Dato valor={s.justificadas} etiqueta="justificadas" />
      </div>

      <ul className="mis-clases">
        {datos.clases.map((c) => (
          <li key={c.claseId} className={c.suspendida ? 'suspendida' : ''}>
            <div className="mi-clase-texto">
              <strong>{c.tema || (c.suspendida ? 'Clase suspendida' : 'Sin tema')}</strong>
              <small>{fechaLarga(c.fecha)}</small>
              {c.observacion && <small className="mi-clase-obs">«{c.observacion}»</small>}
              {c.justificacion && (
                <small className={`lista-justificacion ${c.justificacion.estado.toLowerCase()}`}>
                  Justificación {c.justificacion.estado.toLowerCase()}
                  {c.justificacion.observacion && `: ${c.justificacion.observacion}`}
                </small>
              )}
            </div>

            {c.suspendida ? (
              <span className="estado-asistencia vacio">No cuenta</span>
            ) : (
              <EstadoAsistencia estado={c.estado} />
            )}

            {c.puedeJustificar && (
              <button
                type="button"
                className="boton-suave"
                onClick={() => setPidiendo(c)}
              >
                Justificar
              </button>
            )}
          </li>
        ))}
      </ul>

      {pidiendo && (
        <div
          className="correccion-fondo"
          onClick={(e) => e.target === e.currentTarget && !trabajando && setPidiendo(null)}
          role="presentation"
        >
          <form
            className="correccion"
            onSubmit={(e) => {
              e.preventDefault();
              enviarPedido();
            }}
            role="dialog"
            aria-modal="true"
            aria-label="Pedir una justificación"
          >
            <button
              type="button"
              className="correccion-cerrar"
              onClick={() => setPidiendo(null)}
              disabled={trabajando}
              aria-label="Cerrar"
            >
              <IconoCerrar width={18} height={18} />
            </button>

            <h3>Justificar la falta</h3>
            <p className="correccion-trabajo">
              {fechaLarga(pidiendo.fecha)} · {pidiendo.tema || 'Sin tema'}
            </p>

            <label>
              <span>Motivo</span>
              <textarea
                rows={3}
                value={motivo}
                maxLength={1000}
                autoFocus
                placeholder="Por qué faltaste"
                onChange={(e) => setMotivo(e.target.value)}
              />
            </label>

            <label>
              <span>
                Certificado <small>opcional</small>
              </span>
              <input
                type="text"
                value={archivo}
                maxLength={200}
                placeholder="certificado-medico.pdf"
                onChange={(e) => setArchivo(e.target.value)}
              />
            </label>

            <div className="editor-botones">
              <button
                type="button"
                className="boton-suave"
                onClick={() => setPidiendo(null)}
                disabled={trabajando}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="boton-principal"
                disabled={trabajando || !motivo.trim()}
              >
                Enviar el pedido
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default function AsistenciasDelModulo({ cursoId, puedeGestionar }) {
  return puedeGestionar ? <VistaDocente cursoId={cursoId} /> : <VistaAlumno cursoId={cursoId} />;
}
