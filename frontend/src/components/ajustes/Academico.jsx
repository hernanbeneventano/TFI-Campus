/**
 * La configuración académica de la facultad.
 *
 * Dos decisiones que se toman cada cuatrimestre y que hasta ahora solo se
 * podían cambiar editando un archivo del servidor: **cuándo se puede uno
 * inscribir a materias** y **cuánta asistencia se exige**.
 *
 * Que no se pudieran tocar no era un detalle: sin lo primero la secretaría no
 * podía abrir ni cerrar el cuatrimestre, que es su trabajo.
 *
 * La ve quien supervisa y la cambia quien administra. Separadas a propósito:
 * el supervisor necesita saber si la inscripción está abierta para explicarle
 * a un alumno por qué no puede anotarse, pero abrir el cuatrimestre es una
 * decisión de la institución.
 */
import { useEffect, useState } from 'react';
import {
  obtenerConfiguracionAcademica,
  guardarPeriodoInscripcion,
  guardarConfiguracionAsistencia,
} from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import Eventos from './Eventos.jsx';
import { fechaLarga } from '../../services/fechas.js';
import {
  IconoCalendario,
  IconoPresente,
  IconoCheckCirculo,
  IconoAdvertencia,
} from '../Iconos.jsx';

/** De una fecha ISO al valor de un `<input type="date">`. */
function paraElCampo(iso) {
  if (!iso) return '';
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return '';
  const mes = String(f.getMonth() + 1).padStart(2, '0');
  const dia = String(f.getDate()).padStart(2, '0');
  return `${f.getFullYear()}-${mes}-${dia}`;
}

export default function Academico() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerConfiguracionAcademica()
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  return (
    <div className="academico">
      <PeriodoDeInscripcion datos={datos} onCambio={setDatos} />
      <Asistencia datos={datos} onCambio={setDatos} />
      {/* Los eventos del calendario viven acá porque son del mismo orden:
          cuándo pasan las cosas en la facultad. */}
      <Eventos />
    </div>
  );
}

function PeriodoDeInscripcion({ datos, onCambio }) {
  const { periodoInscripcion: periodo, puedeEditar } = datos;
  const [desde, setDesde] = useState(paraElCampo(periodo.desde));
  const [hasta, setHasta] = useState(paraElCampo(periodo.hasta));
  const [guardando, setGuardando] = useState(false);

  const sinCambios =
    desde === paraElCampo(periodo.desde) && hasta === paraElCampo(periodo.hasta);

  async function guardar(e) {
    e.preventDefault();
    setGuardando(true);
    try {
      onCambio(await guardarPeriodoInscripcion({ desde, hasta }));
      avisar('Período de inscripción actualizado.');
    } catch (err) {
      avisar(err.message, 'error');
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className="bloque-ajustes">
      <h3>
        <IconoCalendario width={17} height={17} />
        Inscripción a materias
      </h3>

      {/* Lo primero es si está abierta ahora: es la pregunta que trae a
          cualquiera a esta pantalla. */}
      <p className={periodo.abierto ? 'estado-periodo abierto' : 'estado-periodo cerrado'}>
        {periodo.abierto ? (
          <IconoCheckCirculo width={17} height={17} />
        ) : (
          <IconoAdvertencia width={17} height={17} />
        )}
        <span>
          {periodo.abierto ? (
            <>
              <strong>La inscripción está abierta.</strong> Cierra el{' '}
              {fechaLarga(periodo.hasta)}.
            </>
          ) : (
            <>
              <strong>La inscripción está cerrada.</strong> Nadie puede anotarse a materias
              hasta que el período incluya el día de hoy.
            </>
          )}
        </span>
      </p>

      <form onSubmit={guardar}>
        <div className="editor-fila">
          <label>
            <span>Abre el</span>
            <input
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              disabled={!puedeEditar || guardando}
            />
          </label>
          <label>
            <span>Cierra el</span>
            <input
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              disabled={!puedeEditar || guardando}
            />
          </label>
        </div>

        {puedeEditar ? (
          <div className="editor-botones">
            <button type="submit" className="boton-principal" disabled={guardando || sinCambios}>
              {guardando ? 'Guardando…' : 'Guardar el período'}
            </button>
          </div>
        ) : (
          <p className="aviso-institucional">
            <IconoAdvertencia width={16} height={16} />
            <span>El período lo cambia la administración de la facultad.</span>
          </p>
        )}
      </form>
    </section>
  );
}

function Asistencia({ datos, onCambio }) {
  const { asistencia, puedeEditar } = datos;
  const [minimo, setMinimo] = useState(String(asistencia.minimoPorDefecto ?? 75));
  const [descuenta, setDescuenta] = useState(Boolean(asistencia.justificadaDescuenta));
  const [guardando, setGuardando] = useState(false);

  const sinCambios =
    Number(minimo) === asistencia.minimoPorDefecto &&
    descuenta === Boolean(asistencia.justificadaDescuenta);

  async function guardar(e) {
    e.preventDefault();
    setGuardando(true);
    try {
      onCambio(
        await guardarConfiguracionAsistencia({
          minimoPorDefecto: Number(minimo),
          justificadaDescuenta: descuenta,
        })
      );
      avisar('Configuración de asistencia actualizada.');
    } catch (err) {
      avisar(err.message, 'error');
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className="bloque-ajustes">
      <h3>
        <IconoPresente width={17} height={17} />
        Asistencia
      </h3>

      <form onSubmit={guardar}>
        <div className="editor-fila">
          <label>
            <span>Mínimo para regularizar</span>
            <div className="campo-con-sufijo">
              <input
                type="number"
                min={0}
                max={100}
                value={minimo}
                onChange={(e) => setMinimo(e.target.value)}
                disabled={!puedeEditar || guardando}
              />
              <span>%</span>
            </div>
          </label>

          {/* El texto dice **qué le pasa al alumno**, no si la regla está
              encendida. «Descuentan» / «No descuentan», a secas, se lee al
              revés de lo que hace: cualquiera entiende que una falta que «no
              descuenta» no lo perjudica, y es justo al revés. Acá decide si
              alguien regulariza, así que no puede quedar a interpretación. */}
          <label className="campo-interruptor">
            <span>Faltas justificadas</span>
            <span className="interruptor-fila">
              <input
                type="checkbox"
                className="interruptor"
                checked={descuenta}
                onChange={(e) => setDescuenta(e.target.checked)}
                disabled={!puedeEditar || guardando}
              />
              <span className="interruptor-texto">
                {descuenta ? 'No restan asistencia' : 'Cuentan como inasistencia'}
              </span>
            </span>
            <small className="texto-suave">
              {descuenta
                ? 'Al aprobarle la justificación, esa clase deja de restarle asistencia.'
                : 'Aprobar la justificación deja constancia de por qué faltó, pero la clase le sigue contando como falta.'}
            </small>
          </label>
        </div>

        {/* Cambiar el mínimo no recalcula nada hacia atrás: la condición se
            mira cuando se consulta. Subirlo a mitad de cuatrimestre deja
            gente por debajo de un día para el otro, y eso hay que decirlo. */}
        <p className="aviso-institucional">
          <IconoAdvertencia width={16} height={16} />
          <span>
            El mínimo se aplica <strong>a todo el campus y en el acto</strong>. Subirlo a mitad
            de cuatrimestre puede dejar por debajo a quienes hoy están en condiciones.
          </span>
        </p>

        {puedeEditar && (
          <div className="editor-botones">
            <button type="submit" className="boton-principal" disabled={guardando || sinCambios}>
              {guardando ? 'Guardando…' : 'Guardar la asistencia'}
            </button>
          </div>
        )}
      </form>
    </section>
  );
}
