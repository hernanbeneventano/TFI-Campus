// El detalle que hay detrás del porcentaje de una sección.
//
// El número solo no alcanza para corregir: un 40% no distingue entre "a casi
// todos les falta una cosa" y "la mitad no abrió nada". Acá se ve, alumno por
// alumno, qué material vio, qué entregó, cuándo, si llegó tarde y qué nota
// tiene, con el botón para corregir ahí mismo.
//
// Los que necesitan atención van primero: el orden lo decide el servidor
// (primero lo que está sin corregir, después lo incompleto).

import { useEffect, useState } from 'react';
import { hace } from '../../services/fechas.js';
import {
  IconoCerrar,
  IconoCheckCirculo,
  IconoReloj,
  IconoAdvertencia,
  IconoArchivo,
  IconoNotas,
} from '../Iconos.jsx';

/** "320 KB", al lado del nombre del archivo. */
function pesoDe(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function Alumno({ alumno, onCorregir }) {
  const [abierto, setAbierto] = useState(alumno.sinCorregir > 0);

  return (
    <li className={alumno.completo ? 'entrega-alumno completo' : 'entrega-alumno'}>
      <button
        type="button"
        className="entrega-cabecera"
        onClick={() => setAbierto((x) => !x)}
        aria-expanded={abierto}
      >
        <span className="entrega-nombre">
          {alumno.completo ? (
            <IconoCheckCirculo width={16} height={16} />
          ) : (
            <IconoAdvertencia width={15} height={15} />
          )}
          <strong>{alumno.nombre}</strong>
        </span>

        <span className="entrega-cuentas">
          <small>
            material {alumno.vistos}/{alumno.material}
          </small>
          {alumno.trabajos > 0 && (
            <small>
              entregas {alumno.entregados}/{alumno.trabajos}
            </small>
          )}
          {alumno.sinCorregir > 0 && (
            <small className="pendiente">
              {alumno.sinCorregir} sin corregir
            </small>
          )}
        </span>
      </button>

      {abierto && alumno.detalle.length > 0 && (
        <ul className="entrega-trabajos">
          {alumno.detalle.map((t) => (
            <li key={t.tareaId}>
              <div className="entrega-trabajo">
                <strong>{t.titulo}</strong>
                {t.entregado ? (
                  <small className={t.atrasada ? 'atrasada' : ''}>
                    {t.archivo?.url ? (
                      <a
                        className="entrega-archivo"
                        href={t.archivo.url}
                        download={t.archivo.nombre}
                        title={`Bajar ${t.archivo.nombre}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <IconoArchivo width={13} height={13} />
                        {t.archivo.nombre}
                        {t.archivo.tamano ? ` · ${pesoDe(t.archivo.tamano)}` : ''}
                      </a>
                    ) : (
                      <>
                        <IconoArchivo width={13} height={13} />
                        {t.archivo?.nombre ?? 'entrega sin archivo'}
                      </>
                    )}
                    {' · '}
                    {hace(t.fecha)}
                    {t.atrasada && ' · fuera de término'}
                  </small>
                ) : (
                  <small className="sin-entregar">
                    <IconoReloj width={13} height={13} />
                    Sin entregar
                  </small>
                )}
                {t.comentario && <small className="entrega-comentario">«{t.comentario}»</small>}
              </div>

              <div className="entrega-nota">
                {t.nota !== null && t.nota !== undefined ? (
                  <span className={`nota-celda ${t.nota >= 6 ? 'aprobada' : 'desaprobada'}`}>
                    {t.nota}
                  </span>
                ) : (
                  <span className="nota-celda vacia">
                    <IconoNotas width={15} height={15} />
                  </span>
                )}
                <button
                  type="button"
                  className="boton-suave"
                  onClick={() => onCorregir(alumno, t)}
                  disabled={!t.entregado && t.nota === null}
                  title={
                    t.entregado
                      ? 'Corregir esta entrega'
                      : 'Todavía no entregó: se puede poner nota igual'
                  }
                >
                  {t.corregido ? 'Revisar' : 'Corregir'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {abierto && alumno.detalle.length === 0 && (
        <p className="entrega-vacia">Esta sección no tiene trabajos para entregar.</p>
      )}
    </li>
  );
}

export default function EntregasSeccion({ datos, onCorregir, onCerrar }) {
  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape') onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
  }, [onCerrar]);

  return (
    <div
      className="entregas-fondo"
      onClick={(e) => e.target === e.currentTarget && onCerrar()}
      role="presentation"
    >
      <section
        className="entregas"
        role="dialog"
        aria-modal="true"
        aria-label={datos ? `Entregas de ${datos.seccion.titulo}` : 'Entregas'}
      >
        <button
          type="button"
          className="entregas-cerrar"
          onClick={onCerrar}
          aria-label="Cerrar"
          title="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        {!datos ? (
          <p className="texto-suave">Cargando las entregas…</p>
        ) : (
          <>
            <header className="entregas-encabezado">
              <h2>{datos.seccion.titulo}</h2>
              <p>
                {datos.resumen.completaron} de {datos.resumen.alumnos} alumnos completaron la
                sección
                {datos.resumen.sinCorregir > 0 && (
                  <> · {datos.resumen.sinCorregir} entregas sin corregir</>
                )}
              </p>
            </header>

            <ul className="entregas-lista">
              {datos.alumnos.map((a) => (
                <Alumno key={a.id} alumno={a} onCorregir={onCorregir} />
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}
