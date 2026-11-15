// La grilla de notas del módulo: alumnos en las filas, trabajos en las
// columnas.
//
// Es la forma en que un docente mira una cursada: de un vistazo ve quién
// debe qué. Una lista de entregas sueltas obligaría a reconstruir eso de
// memoria.
//
// Al tocar una celda se abre la corrección de esa entrega —nota, condición y
// devolución—, porque corregir es escribir tres cosas, no solo un número, y
// una tabla con tres campos por celda no se lee.

import { useState } from 'react';
import { IconoNotas } from '../Iconos.jsx';
import Correccion from './Correccion.jsx';
import CerrarCursada from './CerrarCursada.jsx';

function claseDeNota(nota) {
  if (nota === null || nota === undefined) return 'vacia';
  return nota >= 6 ? 'aprobada' : 'desaprobada';
}

// Cómo se toma cada trabajo, para la cabecera de su columna
const MODALIDAD = {
  entrega: { texto: 'Entrega', clase: 'entrega' },
  cuestionario: { texto: 'Cuestionario', clase: 'cuestionario' },
  presencial: { texto: 'Presencial', clase: 'presencial' },
};

export default function PanelNotas({ datos, onGuardar, onFijarCierre, trabajando }) {
  const [corrigiendo, setCorrigiendo] = useState(null);
  const [cerrando, setCerrando] = useState(null);

  if (!datos) return <p className="texto-suave">Cargando las notas…</p>;

  const { alumnos, trabajos, notas, estados, resumen } = datos;

  if (trabajos.length === 0) {
    return (
      <p className="vacio">
        Todavía no hay trabajos en este módulo. Agregá uno desde Contenido y acá vas a poder
        corregirlo.
      </p>
    );
  }

  const buscar = (alumnoId, trabajoId) =>
    notas.find((n) => n.personaId === alumnoId && n.tareaId === trabajoId) ?? null;

  async function guardar(datosNota) {
    await onGuardar(datosNota);
    setCorrigiendo(null);
  }

  return (
    <>
      <div className="resumen-notas">
        <div>
          <strong>{alumnos.length}</strong>
          <small>alumnos</small>
        </div>
        <div>
          <strong>{trabajos.length}</strong>
          <small>trabajos</small>
        </div>
        <div>
          <strong>
            {resumen.cargadas} de {resumen.esperadas}
          </strong>
          <small>corregidas</small>
        </div>
        <div className="bien">
          <strong>{resumen.aprueban}</strong>
          <small>aprueban</small>
        </div>
        <div>
          <strong>{resumen.vanAFinal}</strong>
          <small>van a final</small>
        </div>
        <div className="destacado">
          <strong>{resumen.promedio ?? '—'}</strong>
          <small>promedio</small>
        </div>
      </div>

      <div className="tabla-envoltorio">
        <table className="tabla-notas grilla">
          <caption className="oculto">Notas de la cursada</caption>
          <thead>
            <tr>
              <th scope="col">Alumno</th>
              {trabajos.map((t) => {
                const m = MODALIDAD[t.formato] ?? MODALIDAD.entrega;
                return (
                  <th key={t.id} scope="col" title={`${t.titulo} · ${m.texto}`}>
                    <span className="columna-trabajo">
                      {t.titulo}
                      <small className={`modalidad ${m.clase}`}>{m.texto}</small>
                    </span>
                  </th>
                );
              })}
              <th scope="col" className="columna-cierre">
                Nota final
              </th>
            </tr>
          </thead>
          <tbody>
            {alumnos.map((a) => (
              <tr key={a.id}>
                <th scope="row">{a.nombre}</th>
                {trabajos.map((t) => {
                  const nota = buscar(a.id, t.id);
                  return (
                    <td key={t.id} className="celda-nota">
                      <button
                        type="button"
                        className={`nota-celda ${claseDeNota(nota?.nota)}`}
                        onClick={() => setCorrigiendo({ alumno: a, trabajo: t, nota })}
                        title={
                          nota
                            ? `${nota.estado}${nota.comentario ? ` · ${nota.comentario}` : ''}`
                            : 'Sin corregir'
                        }
                      >
                        {nota?.nota ?? <IconoNotas width={15} height={15} />}
                      </button>
                    </td>
                  );
                })}

                <td className="celda-cierre">
                  <button
                    type="button"
                    className={`cierre ${a.cierre.vaAFinal ? 'final' : ''} ${
                      a.cierre.promedio === null ? 'vacio' : ''
                    } ${a.cierre.automatico ? '' : 'a-mano'}`}
                    onClick={() => setCerrando(a)}
                    title={
                      a.cierre.automatico
                        ? `Promedio de ${a.cierre.corregidas} notas. Tocá para fijarla a mano.`
                        : `Fijada a mano${
                            a.cierre.observacion ? `: ${a.cierre.observacion}` : ''
                          }`
                    }
                  >
                    <strong>{a.cierre.promedio ?? '—'}</strong>
                    <small>{a.cierre.condicion}</small>
                    {!a.cierre.automatico && <span className="marca-mano">a mano</span>}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {cerrando && (
        <CerrarCursada
          alumno={cerrando}
          trabajando={trabajando}
          onGuardar={async (valores) => {
            await onFijarCierre(valores);
            setCerrando(null);
          }}
          onCerrar={() => setCerrando(null)}
        />
      )}

      {corrigiendo && (
        <Correccion
          alumno={corrigiendo.alumno}
          trabajo={corrigiendo.trabajo}
          nota={corrigiendo.nota}
          estados={estados}
          trabajando={trabajando}
          onGuardar={guardar}
          onCerrar={() => setCorrigiendo(null)}
        />
      )}
    </>
  );
}
