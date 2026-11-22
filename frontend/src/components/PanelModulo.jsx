import { useState } from 'react';
import { Link } from 'react-router-dom';
import BarraProgreso from './BarraProgreso.jsx';
import Desplegable from './Desplegable.jsx';
import { hace } from '../services/fechas.js';
import {
  IconoUsuario,
  IconoCalendario,
  IconoTarea,
  IconoNotas,
  IconoAvance,
  IconoPersonas,
  IconoMas,
  IconoCerrar,
} from './Iconos.jsx';
import Avatar from './Avatar.jsx';

const DIA = 24 * 60 * 60 * 1000;

function cuandoEs(iso) {
  const dias = Math.round((new Date(iso) - new Date()) / DIA);
  if (dias === 0) return 'hoy';
  if (dias === 1) return 'mañana';
  return `en ${dias} días`;
}

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' });
}

// Panel derecho de un módulo. A propósito no repite lo que ya está en las
// pestañas de arriba (participantes, anuncios, notas): muestra el horario de
// cursada y lo que se viene, que de otro modo habría que ir a buscar.
const DIAS = [
  { valor: 1, nombre: 'Lunes' },
  { valor: 2, nombre: 'Martes' },
  { valor: 3, nombre: 'Miércoles' },
  { valor: 4, nombre: 'Jueves' },
  { valor: 5, nombre: 'Viernes' },
  { valor: 6, nombre: 'Sábado' },
];

// Las horas se eligen de una lista y no se escriben: el `<input type="time">`
// del navegador trae su propio reloj, que no se puede estilar y desentona con
// el resto del campus. Además, una clase arranca y termina en hora o media,
// así que una lista cada 30 minutos cubre todos los casos reales y evita
// tener que validar lo que alguien tipee.
const HORAS = Array.from({ length: (23 - 7) * 2 + 1 }, (_, i) => {
  const minutos = 7 * 60 + i * 30;
  const texto = `${String(Math.floor(minutos / 60)).padStart(2, '0')}:${
    minutos % 60 === 0 ? '00' : '30'
  }`;
  return { valor: texto, nombre: texto };
});

/** Las horas que pueden ir en "hasta": siempre después de la de inicio. */
function horasDespuesDe(desde) {
  if (!desde) return HORAS;
  return HORAS.filter((h) => h.valor > desde);
}

/** "Martes de 12 a 14, Aula 7": un día del horario semanal. */
function AgregarDiaDeClase({ onAgregar }) {
  const [abierto, setAbierto] = useState(false);
  const [dia, setDia] = useState(1);
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [aula, setAula] = useState('');

  if (!abierto) {
    return (
      <button type="button" className="boton-suave" onClick={() => setAbierto(true)}>
        <IconoMas width={15} height={15} />
        Agregar un día
      </button>
    );
  }

  return (
    <form
      className="cursada-form"
      onSubmit={(e) => {
        e.preventDefault();
        onAgregar({ dia: Number(dia), desde, hasta, aula: aula.trim() || null });
        setAbierto(false);
        setDesde('');
        setHasta('');
        setAula('');
      }}
    >
      <label>
        <span>Día</span>
        <Desplegable
          valor={dia}
          opciones={DIAS}
          onCambiar={(v) => setDia(Number(v))}
          etiqueta="Día de la semana"
        />
      </label>

      <div className="cursada-horas">
        <label>
          <span>Desde</span>
          <Desplegable
            valor={desde}
            opciones={[{ valor: '', nombre: 'Elegí' }, ...HORAS]}
            onCambiar={(v) => {
              setDesde(v);
              // Si la de fin quedó antes de la de inicio, se borra: dejarla
              // puesta haría que el servidor rechace el formulario sin que se
              // entienda por qué.
              if (hasta && v && hasta <= v) setHasta('');
            }}
            etiqueta="Hora de inicio"
          />
        </label>
        <label>
          <span>Hasta</span>
          <Desplegable
            valor={hasta}
            opciones={[{ valor: '', nombre: 'Elegí' }, ...horasDespuesDe(desde)]}
            onCambiar={setHasta}
            etiqueta="Hora de fin"
          />
        </label>
      </div>

      <label>
        <span>
          Aula <small>opcional</small>
        </span>
        <input
          type="text"
          value={aula}
          maxLength={60}
          placeholder="Aula 7, Lab. 3…"
          onChange={(e) => setAula(e.target.value)}
        />
      </label>

      <div className="editor-botones">
        <button type="button" className="boton-suave" onClick={() => setAbierto(false)}>
          Cancelar
        </button>
        <button type="submit" className="boton-principal" disabled={!desde || !hasta}>
          Agregar
        </button>
      </div>
    </form>
  );
}


export default function PanelModulo({
  curso,
  participantes,
  cursada = [],
  // La cátedra arma el horario semanal desde acá: es parte de cómo se dicta
  // la materia, y además llena el calendario de todos los que cursan.
  puedeGestionar = false,
  onAgregarClase,
  onQuitarClase,
  proximas = [],
  avance,
  // Al docente no le sirve su propio avance: el material lo subió él. En su
  // lugar va cómo viene el curso con ese material.
  seguimiento = null,
}) {
  const docente = participantes.find((p) => p.rol === 'Docente');
  const estudiantes = participantes.filter((p) => p.rol === 'Estudiante').length;

  return (
    <aside className="panel">
      <section>
        <h2 className="panel-titulo">Equipo del módulo</h2>
        <div className="docente">
          <span className={`docente-avatar avatar-estado ${docente?.estado ?? 'desconectado'}`}>
            <Avatar persona={docente} tamano={26} />
          </span>
          <div>
            <strong>{docente ? docente.nombre : curso.docente}</strong>
            <small>Docente a cargo</small>
            {docente?.ultimoAcceso && <small>Último acceso {hace(docente.ultimoAcceso)}</small>}
          </div>
        </div>
        <p className="panel-vacio">{estudiantes} estudiantes inscriptos</p>
      </section>

      {(cursada.length > 0 || puedeGestionar) && (
        <section>
          <h2 className="panel-titulo">Días de clase</h2>

          {cursada.length === 0 ? (
            <p className="panel-vacio">
              {puedeGestionar
                ? 'Todavía no cargaste los días de cursada.'
                : 'La cátedra todavía no cargó los días de cursada.'}
            </p>
          ) : (
            <ul className="cursada">
              {cursada.map((c) => (
                <li key={`${c.diaNumero}-${c.desde}`}>
                  <span className="accion-icono">
                    <IconoCalendario width={18} height={18} />
                  </span>
                  <span>
                    <strong>{c.dia}</strong>
                    <small>
                      {c.desde} a {c.hasta}
                      {c.aula ? ` · ${c.aula}` : ''}
                    </small>
                  </span>
                  {puedeGestionar && (
                    <button
                      type="button"
                      className="cursada-quitar"
                      onClick={() => onQuitarClase(c)}
                      title="Quitar este día"
                      aria-label={`Quitar ${c.dia} de ${c.desde}`}
                    >
                      <IconoCerrar width={13} height={13} />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          {puedeGestionar && <AgregarDiaDeClase onAgregar={onAgregarClase} />}
        </section>
      )}

      <section>
        <h2 className="panel-titulo">Lo que se viene</h2>
        {proximas.length === 0 ? (
          <p className="panel-vacio">No hay nada agendado por ahora.</p>
        ) : (
          <ul className="proximas">
            {proximas.map((p) => {
              const contenido = (
                <>
                  <span className={`accion-icono ${p.tipo}`}>
                    {p.tipo === 'examen' ? (
                      <IconoNotas width={18} height={18} />
                    ) : (
                      <IconoTarea width={18} height={18} />
                    )}
                  </span>
                  <span>
                    <strong>{p.titulo}</strong>
                    <small>
                      {fechaCorta(p.fecha)} · {cuandoEs(p.fecha)}
                      {p.lugar ? ` · ${p.lugar}` : ''}
                    </small>
                  </span>
                </>
              );

              // Las entregas llevan a su pantalla; los exámenes no tienen una
              return (
                <li key={`${p.tipo}-${p.titulo}`}>
                  {p.tipo === 'entrega' ? (
                    <Link to={`/modulos/${curso.id}?tarea=${p.tareaId}`} className="proxima">
                      {contenido}
                    </Link>
                  ) : (
                    <span className="proxima">{contenido}</span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {seguimiento && (
        <section>
          <h2 className="panel-titulo">Avance del curso</h2>
          <div className="avance">
            <span className="accion-icono">
              <IconoPersonas />
            </span>
            <div className="avance-curso">
              <strong>{seguimiento.resumen.porcentaje}%</strong>
              <div className="barra-avance">
                <span style={{ width: `${seguimiento.resumen.porcentaje}%` }} />
              </div>
            </div>
          </div>
          <p className="panel-vacio">
            {seguimiento.resumen.completaronTodo} de {seguimiento.resumen.alumnos} alumnos
            completaron todo el material.
          </p>
          {seguimiento.resumen.sinCorregir > 0 && (
            <p className="panel-vacio destacado">
              Tenés {seguimiento.resumen.sinCorregir}{' '}
              {seguimiento.resumen.sinCorregir === 1 ? 'entrega' : 'entregas'} sin corregir.
            </p>
          )}
        </section>
      )}

      {!seguimiento && avance.total > 0 && (
        <section>
          <h2 className="panel-titulo">Tu avance</h2>
          <div className="avance">
            <span className="accion-icono">
              <IconoAvance />
            </span>
            <BarraProgreso avance={avance} />
          </div>
          <p className="panel-vacio">
            {avance.hechos === avance.total
              ? '¡Completaste todo el material!'
              : `Te faltan ${avance.total - avance.hechos} de ${avance.total} recursos.`}
          </p>
        </section>
      )}
    </aside>
  );
}
