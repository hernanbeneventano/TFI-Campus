// El panel de control de la institución.
//
// Tres bloques, en este orden, que es el de la pregunta que se hace quien
// entra: **qué hay que hacer hoy** (las alertas), **cómo viene la
// institución** (los números y las distribuciones) y **qué pasó recién** (la
// actividad).
//
// Las alertas van primero a propósito. Un tablero que arranca con gráficos se
// mira una vez por semana; uno que arranca con "seis materias sin docente" se
// mira todos los días. Y cada alerta lleva a la pantalla donde se resuelve:
// una que no lleva a ninguna parte obliga a buscarla a mano, que es
// justamente lo que el panel tendría que evitar.
//
// Nada de lo que se ve acá está inventado: todo sale de los registros. Si la
// facultad no cargó nada, el número es cero y lo dice.

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { obtenerPanel, obtenerAlertas } from '../../services/api.js';
import { hace, fechaConDia } from '../../services/fechas.js';
import {
  IconoAdvertencia,
  IconoCheckCirculo,
  IconoActividad,
  IconoFlecha,
} from '../Iconos.jsx';

/** Un número grande con su etiqueta. Cuando lleva ruta, es un atajo. */
function Indicador({ nombre, valor, detalle, ruta, alerta }) {
  const cuerpo = (
    <>
      <strong>{valor}</strong>
      <span>{nombre}</span>
      {detalle && <small>{detalle}</small>}
    </>
  );

  const clase = alerta ? 'indicador con-pendientes' : 'indicador';
  return ruta ? (
    <Link className={`${clase} enlace`} to={ruta}>
      {cuerpo}
    </Link>
  ) : (
    <div className={clase}>{cuerpo}</div>
  );
}

/**
 * Barras horizontales para comparar una misma medida entre categorías.
 *
 * Van horizontales porque los nombres son largos —"Licenciatura en Sistemas
 * de Información" no entra bajo una barra vertical— y de un solo color
 * porque es **una** medida: el color acá no distingue nada, y pintarlas de
 * colores distintos haría creer que sí.
 */
function Barras({ titulo, datos, vacio, formato = (n) => n }) {
  const maximo = Math.max(1, ...datos.map((d) => d.cantidad));

  return (
    <section className="grafico">
      <h3>{titulo}</h3>
      {datos.length === 0 ? (
        <p className="texto-suave">{vacio}</p>
      ) : (
        <ul className="barras">
          {datos.map((d) => (
            <li key={d.id ?? d.nombre} title={`${d.nombre}: ${formato(d.cantidad)}`}>
              <span className="barra-nombre">{d.nombre}</span>
              <span className="barra-pista">
                <span
                  className="barra-relleno"
                  style={{ width: `${(d.cantidad / maximo) * 100}%` }}
                />
              </span>
              <span className="barra-valor">{formato(d.cantidad)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** El porcentaje general de asistencia, con el mínimo marcado. */
function Asistencia({ datos }) {
  if (datos.porcentaje == null) {
    return (
      <section className="grafico">
        <h3>Asistencia general</h3>
        <p className="texto-suave">Todavía no se tomó lista en ninguna clase.</p>
      </section>
    );
  }

  // Rojo por debajo del mínimo, amarillo en los cinco puntos justo encima
  // —ahí todavía se puede caer— y verde más arriba. Pintar de advertencia algo
  // que ya está aprobado enseña a no hacerle caso al color.
  const nivel =
    datos.porcentaje < datos.minimo
      ? 'bajo'
      : datos.porcentaje < datos.minimo + 5
        ? 'medio'
        : 'alto';

  return (
    <section className="grafico">
      <h3>Asistencia general</h3>
      <p className={`numero-grande ${nivel}`}>
        {datos.porcentaje}
        <small>%</small>
      </p>
      <div className="medidor" role="img" aria-label={`${datos.porcentaje} por ciento de asistencia`}>
        <span className={`medidor-relleno ${nivel}`} style={{ width: `${datos.porcentaje}%` }} />
        {/* La marca del mínimo exigido: sin ella el porcentaje no dice si
            está bien o mal. */}
        <span className="medidor-minimo" style={{ left: `${datos.minimo}%` }} />
      </div>
      <p className="texto-suave">
        Mínimo exigido {datos.minimo} % · {datos.registros} registros de clases dictadas
      </p>
    </section>
  );
}

export default function Panel() {
  const [datos, setDatos] = useState(null);
  const [alertas, setAlertas] = useState(null);
  const [error, setError] = useState(null);
  const [abierta, setAbierta] = useState(null);

  useEffect(() => {
    obtenerPanel().then(setDatos).catch((e) => setError(e.message));
    obtenerAlertas().then(setAlertas).catch(() => setAlertas(null));
  }, []);

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  const { indicadores: i, distribuciones: dis } = datos;

  return (
    <div className="panel-control">
      {/* ---------- Lo que hay que atender ---------- */}
      {alertas && (
        <section className="panel-alertas">
          <h3>
            {alertas.cuantas === 0 ? 'No hay nada pendiente' : 'Lo que hay que atender'}
            {alertas.urgentes > 0 && (
              <span className="cuenta-urgente">{alertas.urgentes} urgentes</span>
            )}
          </h3>

          {alertas.alertas.length === 0 ? (
            <p className="texto-suave">
              <IconoCheckCirculo width={15} height={15} /> Todo al día: no hay estudiantes sin
              comisión, materias sin docente ni aportes esperando revisión.
            </p>
          ) : (
            <ul className="panel-alerta-lista">
              {alertas.alertas.map((a) => (
                <li key={a.id} className={`panel-alerta nivel-${a.nivel}`}>
                  <button
                    type="button"
                    className="panel-alerta-cabecera"
                    onClick={() => setAbierta(abierta === a.id ? null : a.id)}
                    aria-expanded={abierta === a.id}
                  >
                    <span className="panel-alerta-cantidad">{a.cantidad}</span>
                    <span className="panel-alerta-texto">
                      <strong>{a.titulo}</strong>
                      <small>{a.explicacion}</small>
                    </span>
                    {a.items.length > 0 && (
                      <IconoFlecha
                        width={14}
                        height={14}
                        className={abierta === a.id ? 'girada' : undefined}
                      />
                    )}
                  </button>

                  {/* El detalle se despliega acá: cada línea lleva a su
                      pantalla, que es donde se arregla. */}
                  {abierta === a.id && a.items.length > 0 && (
                    <ul className="panel-alerta-items">
                      {a.items.map((item) => (
                        <li key={item.id}>
                          <Link to={item.ruta}>{item.texto}</Link>
                        </li>
                      ))}
                      {a.cantidad > a.items.length && (
                        <li className="texto-suave">
                          y {a.cantidad - a.items.length} más
                        </li>
                      )}
                    </ul>
                  )}

                  <Link className="panel-alerta-accion" to={a.ruta}>
                    {a.accion}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* ---------- Cómo viene la institución ---------- */}
      <div className="indicadores">
        <Indicador nombre="Estudiantes" valor={i.estudiantes} detalle="con carrera asignada" />
        <Indicador nombre="Docentes" valor={i.docentes} />
        <Indicador nombre="Carreras" valor={i.carreras} ruta="/administracion/estructura" />
        <Indicador nombre="Sedes" valor={i.sedes} ruta="/administracion/estructura" />
        <Indicador nombre="Comisiones" valor={i.comisiones} ruta="/administracion/estructura" />
        <Indicador nombre="Materias del plan" valor={i.materias} />
        <Indicador
          nombre="Sin comisión"
          valor={i.sinComision}
          alerta={i.sinComision > 0}
          ruta="/administracion/estudiantes"
        />
        <Indicador
          nombre="Aportes sin revisar"
          valor={i.aportesPendientes}
          alerta={i.aportesPendientes > 0}
          ruta="/biblioteca"
        />
        <Indicador
          nombre="Cuentas pendientes"
          valor={i.cuentasPendientes}
          alerta={i.cuentasPendientes > 0}
          ruta="/administracion/cuentas"
        />
        <Indicador nombre="Exámenes próximos" valor={i.proximosExamenes} ruta="/calendario" />
      </div>

      <div className="panel-graficos">
        <Barras
          titulo="Estudiantes por carrera"
          datos={dis.porCarrera}
          vacio="Todavía no hay carreras cargadas."
        />
        <Barras
          titulo="Estudiantes por sede"
          datos={dis.porSede}
          vacio="Todavía no hay sedes cargadas."
        />
        <Barras
          titulo="Estudiantes por comisión"
          datos={dis.porComision}
          vacio="Ninguna comisión tiene estudiantes asignados todavía."
        />
        <Barras
          titulo="Ingresantes por año"
          datos={dis.matricula.map((m) => ({ id: m.anio, nombre: String(m.anio), cantidad: m.cantidad }))}
          vacio="Todavía no hay inscripciones a carreras."
        />
        <Asistencia datos={dis.asistencia} />

        <section className="grafico">
          <h3>Rendimiento académico</h3>
          <dl className="datos-sueltos">
            <div>
              <dt>Materias aprobadas</dt>
              <dd>{dis.rendimiento.materiasAprobadas}</dd>
            </div>
            <div>
              <dt>Trabajos corregidos</dt>
              <dd>{dis.rendimiento.trabajosCorregidos}</dd>
            </div>
            <div>
              <dt>Aprobados</dt>
              <dd>{dis.rendimiento.trabajosAprobados}</dd>
            </div>
            <div>
              <dt>Promedio general</dt>
              <dd>{dis.rendimiento.promedio ?? '—'}</dd>
            </div>
          </dl>
          {dis.rendimiento.trabajosCorregidos === 0 && (
            <p className="texto-suave">Todavía no hay notas cargadas.</p>
          )}
        </section>
      </div>

      {/* ---------- Qué pasó recién ---------- */}
      <section className="grafico">
        <h3>
          <IconoActividad width={16} height={16} /> Actividad reciente
        </h3>
        {datos.actividad.length === 0 ? (
          <p className="texto-suave">
            Todavía no se registró ningún movimiento desde que arrancó el servidor.
          </p>
        ) : (
          <>
            <ul className="actividad-reciente">
              {datos.actividad.map((e) => (
                <li key={e.id}>
                  <span className="actividad-que">
                    <strong>{e.quien}</strong> · {e.nombreAccion.toLowerCase()} en{' '}
                    {e.nombreModulo.toLowerCase()}
                  </span>
                  <span className="actividad-elemento">{e.elemento}</span>
                  <small className="texto-suave">{hace(e.cuando)}</small>
                </li>
              ))}
            </ul>
            <Link className="boton-suave" to="/administracion/actividad">
              Ver el registro completo
            </Link>
          </>
        )}
      </section>

      {/* ---------- Lo que se viene ---------- */}
      {datos.proximos.length > 0 && (
        <section className="grafico">
          <h3>Próximos exámenes y mesas</h3>
          <ul className="actividad-reciente">
            {datos.proximos.map((e, n) => (
              <li key={n}>
                <span className="actividad-que">
                  <strong>{e.titulo}</strong>
                  {e.detalle ? ` · ${e.detalle}` : ''}
                </span>
                <span className="actividad-elemento">{fechaConDia(e.fecha)}</span>
                <Link className="boton-suave" to={e.ruta}>
                  Ver
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="nota-bloque">
        <IconoAdvertencia width={15} height={15} />
        Todos los números salen de los registros del campus. Los datos viven en memoria mientras
        el servidor esté levantado, así que se reinician con él.
      </p>
    </div>
  );
}
