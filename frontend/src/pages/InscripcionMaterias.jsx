// Inscripción a materias: el plan de estudios del alumno y su avance.
//
// Se muestra el plan entero, no solo lo que puede cursar: ver la carrera
// completa —lo aprobado, lo que está cursando y lo que falta, con el motivo—
// es lo que hace entendible el sistema de correlatividades. Una lista con
// solo tres materias habilitadas no explica nada.
//
// Las materias van agrupadas por año y, adentro, por cuatrimestre, que es
// como está escrito el plan de estudios en papel.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  obtenerPlanDeEstudios,
  inscribirseAMateria,
  darDeBajaMateria,
} from '../services/api.js';
import { fechaLarga } from '../services/fechas.js';
import Encabezado from '../components/Encabezado.jsx';
import Confirmacion from '../components/Confirmacion.jsx';
import { avisar } from '../services/avisos.js';
import {
  IconoCheckCirculo,
  IconoCandado,
  IconoReloj,
  IconoAdvertencia,
  IconoPersonas,
  IconoModulos,
  IconoVolver,
  IconoInscribirse,
} from '../components/Iconos.jsx';

// Cada estado con su color y su ícono. Son los mismos tres niveles que usan
// las barras de avance: verde lo terminado, ámbar lo que está en marcha,
// gris lo que no se puede todavía.
// `corto` es lo que entra en la etiqueta; el estado entero queda en el
// atributo `title` y, sobre todo, en el motivo de abajo, que es el que
// explica qué hacer. Una etiqueta de tres palabras no entra en la tarjeta y
// tampoco agrega nada que el motivo no diga mejor.
const ESTADOS = {
  Aprobada: { clase: 'aprobada', Icono: IconoCheckCirculo },
  Regular: { clase: 'regular', Icono: IconoReloj },
  'En curso': { clase: 'cursando', Icono: IconoModulos },
  Inscripto: { clase: 'inscripto', Icono: IconoCheckCirculo },
  Habilitada: { clase: 'habilitada', Icono: IconoInscribirse },
  'Bloqueada por correlatividad': {
    clase: 'bloqueada',
    Icono: IconoCandado,
    corto: 'Bloqueada',
  },
  'Sin cupos disponibles': {
    clase: 'sin-cupo',
    Icono: IconoAdvertencia,
    corto: 'Sin cupos',
  },
};

const ORDINAL = { 1: '1.er', 2: '2.º', 3: '3.er', 4: '4.º', 5: '5.º' };

function Materia({ materia, onInscribirse, onBaja, trabajando }) {
  const { clase, Icono, corto } = ESTADOS[materia.estado] ?? ESTADOS.Habilitada;

  return (
    <article className={`materia ${clase}`}>
      <header className="materia-cabecera">
        <div className="materia-titulo">
          <h3>{materia.nombre}</h3>
          <p>
            {materia.codigo} · {ORDINAL[materia.cuatrimestre] ?? materia.cuatrimestre}{' '}
            cuatrimestre
          </p>
        </div>
        <span className={`estado-materia ${clase}`} title={materia.estado}>
          <Icono width={14} height={14} />
          {corto ?? materia.estado}
        </span>
      </header>

      <dl className="materia-datos">
        {materia.docente && (
          <div>
            <dt>Profesor</dt>
            <dd>{materia.docente}</dd>
          </div>
        )}
        {materia.comision && (
          <div>
            <dt>Comisión</dt>
            <dd>{materia.comision}</dd>
          </div>
        )}
        {materia.horario && (
          <div>
            <dt>Horario</dt>
            <dd>{materia.horario}</dd>
          </div>
        )}
        <div>
          <dt>Lugares</dt>
          <dd>
            <IconoPersonas width={14} height={14} /> {materia.inscriptos} de {materia.cupo}
          </dd>
        </div>
      </dl>

      {materia.correlativas.length > 0 && (
        <p className="materia-correlativas">
          <strong>Correlativas:</strong>{' '}
          {materia.correlativas.map((c) => c.nombre).join(', ')}
        </p>
      )}

      {materia.motivo && (
        <p className={`materia-motivo ${clase}`}>
          {materia.estado === 'Bloqueada por correlatividad' && (
            <IconoCandado width={14} height={14} />
          )}
          {materia.motivo}
        </p>
      )}

      <footer className="materia-pie">
        {materia.cursoId && (
          <Link className="boton-suave" to={`/modulos/${materia.cursoId}`}>
            Ir al módulo
          </Link>
        )}

        {materia.puedeInscribirse && (
          <button
            type="button"
            className="boton-principal"
            onClick={() => onInscribirse(materia)}
            disabled={trabajando}
          >
            Inscribirme
          </button>
        )}

        {materia.estado === 'Inscripto' && (
          <button
            type="button"
            className="boton-suave peligro"
            onClick={() => onBaja(materia)}
            disabled={trabajando}
          >
            Dar de baja
          </button>
        )}
      </footer>
    </article>
  );
}

export default function InscripcionMaterias() {
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [fallo, setFallo] = useState(null);
  const [trabajando, setTrabajando] = useState(false);
  const [soloHabilitadas, setSoloHabilitadas] = useState(false);
  // Lo que se está por confirmar, o null si no hay cartel abierto
  const [aConfirmar, setAConfirmar] = useState(null);

  const traer = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setDatos(await obtenerPlanDeEstudios());
    } catch (e) {
      setError(e.message);
      setDatos(null);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    traer();
  }, [traer]);

  async function accionar(accion, id, exito) {
    setTrabajando(true);
    setFallo(null);
    try {
      await accion(id);
      await traer();
      avisar(exito);
    } catch (e) {
      // El error va en los dos lados: el aviso se va solo y el texto de la
      // pantalla queda, por si llegó mientras mirabas para otro lado.
      setFallo(e.message);
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
      setAConfirmar(null);
    }
  }

  // Los datos de la materia van en el cartel: confirmar "una materia" sin ver
  // cuál es lo mismo que no confirmar nada.
  function detallesDe(materia) {
    const datos = [
      { etiqueta: 'Materia', valor: `${materia.nombre} (${materia.codigo})` },
      {
        etiqueta: 'Cursado',
        valor: `${ORDINAL[materia.anio] ?? materia.anio} año · ${
          ORDINAL[materia.cuatrimestre] ?? materia.cuatrimestre
        } cuatrimestre`,
      },
    ];
    if (materia.horario) datos.push({ etiqueta: 'Horario', valor: materia.horario });
    if (materia.docente) datos.push({ etiqueta: 'Profesor', valor: materia.docente });
    datos.push({ etiqueta: 'Lugares', valor: `${materia.inscriptos} de ${materia.cupo}` });
    return datos;
  }

  function pedirInscripcion(materia) {
    setAConfirmar({
      titulo: '¿Te inscribís a esta materia?',
      mensaje:
        'Vas a ocupar un lugar y la materia va a aparecer entre tus módulos. Podés darte de baja mientras el período de inscripción siga abierto.',
      detalles: detallesDe(materia),
      textoConfirmar: 'Sí, inscribirme',
      peligro: false,
      ejecutar: () =>
        accionar(inscribirseAMateria, materia.id, `Te inscribiste a ${materia.nombre}.`),
    });
  }

  function pedirBaja(materia) {
    setAConfirmar({
      titulo: '¿Das de baja la inscripción?',
      mensaje:
        'La materia sale de tus módulos y dejás tu lugar libre. Podés volver a anotarte mientras el período siga abierto; una vez que cierre, no.',
      detalles: detallesDe(materia),
      textoConfirmar: 'Sí, darme de baja',
      peligro: true,
      ejecutar: () =>
        accionar(darDeBajaMateria, materia.id, `Te diste de baja de ${materia.nombre}.`),
    });
  }

  // Agrupadas por año; el backend ya las manda ordenadas
  const porAnio = useMemo(() => {
    const mapa = new Map();
    for (const materia of datos?.materias ?? []) {
      if (soloHabilitadas && materia.estado !== 'Habilitada') continue;
      if (!mapa.has(materia.anio)) mapa.set(materia.anio, []);
      mapa.get(materia.anio).push(materia);
    }
    return [...mapa.entries()];
  }, [datos, soloHabilitadas]);

  const resumen = datos?.resumen;
  const avance = resumen ? Math.round((resumen.aprobadas / resumen.total) * 100) : 0;

  return (
    <div className="pagina">
      <Link className="volver" to="/modulos">
        <IconoVolver width={16} height={16} />
        Módulos
      </Link>

      <Encabezado
        titulo="Inscripciones a materias"
        descripcion="Las materias de tu carrera, con lo que ya aprobaste y lo que te falta para cada una."
      />

      {cargando && <p className="vacio">Cargando…</p>}

      {error && (
        <p className="aviso-error">
          {error}{' '}
          <button type="button" className="boton-suave" onClick={traer}>
            Reintentar
          </button>
        </p>
      )}

      {!cargando && !error && datos && (
        <>
          <section className="ficha-carrera">
            <div>
              <h2>{datos.carrera.carrera}</h2>
              <p>
                Plan {datos.carrera.plan} · Legajo {datos.carrera.legajo} · Ingreso{' '}
                {datos.carrera.ingreso}
              </p>
            </div>

            <div className="avance-carrera">
              <div className="barra-avance">
                <span style={{ width: `${avance}%` }} />
              </div>
              <small>
                {resumen.aprobadas} de {resumen.total} materias aprobadas ({avance}%)
              </small>
            </div>
          </section>

          <section
            className={datos.periodo.abierto ? 'periodo abierto' : 'periodo cerrado'}
            role="status"
          >
            {datos.periodo.abierto ? (
              <>
                <IconoCheckCirculo width={16} height={16} />
                <span>
                  La inscripción está abierta hasta el{' '}
                  <strong>{fechaLarga(datos.periodo.hasta)}</strong>.
                </span>
              </>
            ) : (
              <>
                <IconoReloj width={16} height={16} />
                <span>
                  La inscripción está cerrada. El período fue del{' '}
                  {fechaLarga(datos.periodo.desde)} al {fechaLarga(datos.periodo.hasta)}.
                </span>
              </>
            )}
          </section>

          <div className="filtros-plan">
            <div className="cuentas-plan">
              <span className="chip-estado aprobada">{resumen.aprobadas} aprobadas</span>
              <span className="chip-estado regular">{resumen.regulares} regulares</span>
              <span className="chip-estado cursando">{resumen.enCurso} en curso</span>
              <span className="chip-estado inscripto">{resumen.inscripto} inscripto</span>
              <span className="chip-estado habilitada">{resumen.habilitadas} habilitadas</span>
              <span className="chip-estado bloqueada">{resumen.bloqueadas} bloqueadas</span>
            </div>

            <label className="filtro-habilitadas">
              <input
                type="checkbox"
                className="interruptor"
                checked={soloHabilitadas}
                onChange={(e) => setSoloHabilitadas(e.target.checked)}
              />
              <span>Ver solo las que puedo cursar</span>
            </label>
          </div>

          {fallo && <p className="aviso-error">{fallo}</p>}

          {porAnio.length === 0 && (
            <p className="vacio">
              No hay materias habilitadas para inscribirte en este momento.
            </p>
          )}

          {porAnio.map(([anio, materias]) => (
            <section key={anio} className="bloque-anio">
              <h2 className="titulo-bloque">
                {ORDINAL[anio] ?? anio} año
                <small>{materias.length}</small>
              </h2>
              <div className="grilla-materias">
                {materias.map((materia) => (
                  <Materia
                    key={materia.id}
                    materia={materia}
                    trabajando={trabajando}
                    onInscribirse={pedirInscripcion}
                    onBaja={pedirBaja}
                  />
                ))}
              </div>
            </section>
          ))}
        </>
      )}

      {aConfirmar && (
        <Confirmacion
          titulo={aConfirmar.titulo}
          mensaje={aConfirmar.mensaje}
          detalles={aConfirmar.detalles}
          textoConfirmar={aConfirmar.textoConfirmar}
          peligro={aConfirmar.peligro}
          trabajando={trabajando}
          onConfirmar={aConfirmar.ejecutar}
          onCancelar={() => setAConfirmar(null)}
        />
      )}
    </div>
  );
}
