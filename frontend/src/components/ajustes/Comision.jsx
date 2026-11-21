// El cuadro de materias de una comisión: qué se dicta y quién lo dicta.
//
// Se listan **todas las materias del plan**, no solo las que ya tienen
// docente. Una lista con solo lo configurado esconde justamente lo que falta
// configurar, que es lo que el administrador viene a ver.
//
// Los docentes son una lista: una cátedra compartida tiene titular y
// adjunto, y la misma persona puede dictar en varias comisiones.
//
// **Lo que ya se dicta va arriba de todo**, y el resto del plan abajo,
// separado por año y cuatrimestre. Con veinte materias seguidas en una sola
// lista no se encontraba lo que se acababa de asignar ni lo que faltaba: hay
// que poder mirar el cuadro de la comisión y, aparte, buscar qué agregar.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { obtenerComision, configurarDictado, quitarDictado } from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import { IconoCerrar, IconoCheckCirculo } from '../Iconos.jsx';

const ORDINAL = { 1: '1.er', 2: '2.º', 3: '3.er', 4: '4.º', 5: '5.º', 6: '6.º', 7: '7.º' };

/** "2.º año · 1.º cuatrimestre". El 3 es anual, no un tercer cuatrimestre. */
function tituloDePeriodo(materia) {
  const anio = `${ORDINAL[materia.anio] ?? materia.anio} año`;
  if (materia.cuatrimestre === 3) return `${anio} · anual`;
  return `${anio} · ${materia.cuatrimestre === 2 ? '2.º' : '1.º'} cuatrimestre`;
}

function Materia({ materia, docentes, onGuardar, onQuitar, trabajando }) {
  const [editando, setEditando] = useState(false);
  const [elegidos, setElegidos] = useState(materia.docentes.map((x) => x.id));
  const [horario, setHorario] = useState(materia.horario ?? '');

  function alternar(id) {
    setElegidos((x) => (x.includes(id) ? x.filter((y) => y !== id) : [...x, id]));
  }

  if (!editando) {
    return (
      <li className={materia.seDicta ? 'fila-catalogo' : 'fila-catalogo inactiva'}>
        <div className="fila-texto">
          <strong>{materia.nombre}</strong>
          <small>
            {materia.codigo} · {materia.anio}.º año · {materia.cuatrimestre}.º cuatrimestre
          </small>
          {materia.seDicta ? (
            <small className="fila-docentes">
              {materia.docentes.length > 0
                ? materia.docentes.map((x) => x.nombre).join(' · ')
                : 'Sin docente asignado'}
              {materia.horario && ` · ${materia.horario}`}
            </small>
          ) : (
            <small className="fila-baja">No se dicta en esta comisión</small>
          )}
        </div>

        <div className="fila-acciones">
          <button
            type="button"
            className={materia.seDicta ? 'boton-suave' : 'boton-principal'}
            onClick={() => setEditando(true)}
          >
            {materia.seDicta ? 'Cambiar docentes' : 'Dictar acá'}
          </button>
          {materia.seDicta && (
            <button
              type="button"
              className="boton-suave peligro"
              onClick={() => onQuitar(materia)}
              disabled={trabajando}
            >
              Quitar
            </button>
          )}
        </div>
      </li>
    );
  }

  return (
    <li className="fila-catalogo editando">
      <form
        className="editor-dictado"
        onSubmit={(e) => {
          e.preventDefault();
          onGuardar(materia, { docentes: elegidos, horario: horario.trim() || null }).then(() =>
            setEditando(false)
          );
        }}
      >
        <strong>{materia.nombre}</strong>

        <fieldset className="editor-tipos compacto">
          <legend>Docentes responsables</legend>
          <div>
            {docentes.map((p) => (
              <label key={p.id} className={elegidos.includes(p.id) ? 'tipo elegido' : 'tipo'}>
                <input
                  type="checkbox"
                  checked={elegidos.includes(p.id)}
                  onChange={() => alternar(p.id)}
                />
                <strong>{p.nombre}</strong>
              </label>
            ))}
          </div>
        </fieldset>

        <label>
          <span>
            Horario <small>opcional</small>
          </span>
          <input
            type="text"
            value={horario}
            maxLength={120}
            placeholder="Lunes y miércoles de 18:00 a 21:00"
            onChange={(e) => setHorario(e.target.value)}
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
          <button type="submit" className="boton-principal" disabled={trabajando}>
            Guardar
          </button>
        </div>
      </form>
    </li>
  );
}

export default function Comision({ comisionId, onCerrar }) {
  const [datos, setDatos] = useState(null);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);

  const traer = useCallback(() => {
    obtenerComision(comisionId).then(setDatos).catch((e) => setError(e.message));
  }, [comisionId]);

  useEffect(traer, [traer]);

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !trabajando) onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
  }, [onCerrar, trabajando]);

  async function accionar(accion, exito) {
    setTrabajando(true);
    try {
      setDatos(await accion());
      avisar(exito);
    } catch (e) {
      avisar(e.message, 'error');
      throw e;
    } finally {
      setTrabajando(false);
    }
  }

  const guardar = (materia, valores) =>
    accionar(() => configurarDictado(comisionId, materia.id, valores), 'Docentes asignados.');

  const quitar = (materia) =>
    accionar(() => quitarDictado(comisionId, materia.id), 'La materia deja de dictarse acá.');

  // Lo que ya se dicta, para el bloque de arriba.
  const dictadas = useMemo(
    () => (datos?.materias ?? []).filter((m) => m.seDicta),
    [datos]
  );

  // Y el resto, agrupado por año y cuatrimestre. El servidor ya las manda
  // ordenadas por (año, cuatrimestre, código), así que alcanza con cortar la
  // lista cada vez que cambia el período: no hace falta volver a ordenar.
  const porPeriodo = useMemo(() => {
    const grupos = [];
    for (const m of datos?.materias ?? []) {
      if (m.seDicta) continue;
      const clave = `${m.anio}-${m.cuatrimestre}`;
      if (grupos.at(-1)?.clave !== clave) {
        grupos.push({ clave, titulo: tituloDePeriodo(m), materias: [] });
      }
      grupos.at(-1).materias.push(m);
    }
    return grupos;
  }, [datos]);

  return (
    <div
      className="lista-fondo"
      onClick={(e) => e.target === e.currentTarget && !trabajando && onCerrar()}
      role="presentation"
    >
      <section className="lista-asistencia" role="dialog" aria-modal="true">
        <button
          type="button"
          className="lista-cerrar"
          onClick={onCerrar}
          aria-label="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        {error && <p className="aviso-error">{error}</p>}
        {!datos && !error && <p className="texto-suave">Cargando…</p>}

        {datos && (
          <>
            <header className="lista-encabezado">
              <div>
                <h2>{datos.comision.nombre}</h2>
                <p>
                  {datos.comision.carrera} · {datos.comision.sede}
                  {datos.comision.plan && ` · ${datos.comision.plan}`}
                  {datos.comision.turno && ` · turno ${datos.comision.turno}`}
                </p>
              </div>
              <span className="situacion al-dia chica">
                <IconoCheckCirculo width={13} height={13} />
                {datos.estudiantes} estudiantes
              </span>
            </header>

            <p className="nota-bloque">
              {dictadas.length} de {datos.materias.length} materias del plan se dictan en esta
              comisión.
            </p>
            {datos.materias.length === 0 ? (
              <p className="vacio">
                El plan de esta carrera todavía no tiene materias cargadas, así que no hay nada
                para dictar acá. Cargalas primero en la pestaña <strong>Materias</strong>.
              </p>
            ) : (
              <>

            {/* Lo que ya está configurado, arriba de todo: es el cuadro de la
                comisión, y es a lo que se vuelve después de asignar algo. */}
            <h4 className="comision-titulo">Se dictan en esta comisión</h4>
            {dictadas.length === 0 ? (
              <p className="vacio">
                Todavía no se dicta ninguna materia acá. Agregá la primera desde el plan de
                abajo.
              </p>
            ) : (
              <ul className="catalogo">
                {dictadas.map((m) => (
                  <Materia key={m.id} materia={m} docentes={datos.docentesDisponibles}
                    trabajando={trabajando} onGuardar={guardar} onQuitar={quitar} />
                ))}
              </ul>
            )}

            {/* Y el resto del plan, por año y cuatrimestre: así se busca qué
                agregar sin leer veinte nombres seguidos. */}
            <h4 className="comision-titulo">Resto del plan</h4>
            {porPeriodo.length === 0 ? (
              <p className="vacio">Todo el plan se dicta en esta comisión.</p>
            ) : (
              porPeriodo.map((grupo) => (
                <section key={grupo.clave} className="comision-periodo">
                  <h5>{grupo.titulo}</h5>
                  <ul className="catalogo">
                    {grupo.materias.map((m) => (
                      <Materia key={m.id} materia={m} docentes={datos.docentesDisponibles}
                        trabajando={trabajando} onGuardar={guardar} onQuitar={quitar} />
                    ))}
                  </ul>
                </section>
              ))
            )}
              </>
            )}
          </>
        )}
      </section>
    </div>
  );
}
