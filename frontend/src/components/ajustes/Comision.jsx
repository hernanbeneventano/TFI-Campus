// El cuadro de materias de una comisión: qué se dicta y quién lo dicta.
//
// Se listan **todas las materias del plan**, no solo las que ya tienen
// docente. Una lista con solo lo configurado esconde justamente lo que falta
// configurar, que es lo que el administrador viene a ver.
//
// Los docentes son una lista: una cátedra compartida tiene titular y
// adjunto, y la misma persona puede dictar en varias comisiones.

import { useCallback, useEffect, useState } from 'react';
import { obtenerComision, configurarDictado, quitarDictado } from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import { IconoCerrar, IconoCheckCirculo } from '../Iconos.jsx';

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
              {datos.materias.filter((m) => m.seDicta).length} de {datos.materias.length}{' '}
              materias del plan se dictan en esta comisión.
            </p>

            <ul className="catalogo">
              {datos.materias.map((m) => (
                <Materia
                  key={m.id}
                  materia={m}
                  docentes={datos.docentesDisponibles}
                  trabajando={trabajando}
                  onGuardar={(materia, valores) =>
                    accionar(
                      () => configurarDictado(comisionId, materia.id, valores),
                      'Docentes asignados.'
                    )
                  }
                  onQuitar={(materia) =>
                    accionar(
                      () => quitarDictado(comisionId, materia.id),
                      'La materia deja de dictarse acá.'
                    )
                  }
                />
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
