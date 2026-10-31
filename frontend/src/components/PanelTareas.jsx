import { useState } from 'react';
import { Link } from 'react-router-dom';
import { leerCompletados, avanceDeApartado, nivel } from '../services/progreso.js';
import { IconoCampana, IconoReloj } from './Iconos.jsx';

// Panel derecho: tareas pendientes próximas y atrasadas.
// Cada tarea abre la entrega dentro de su módulo (no Actividad, que es
// solamente el buzón de novedades).

const DIA = 24 * 60 * 60 * 1000;

function textoPlazo(fechaIso) {
  const dias = Math.round((new Date(fechaIso) - new Date()) / DIA);
  if (dias < 0) return dias === -1 ? 'Venció ayer' : `Venció hace ${-dias} días`;
  if (dias === 0) return 'Vence hoy';
  if (dias === 1) return 'Vence mañana';
  return `Vence en ${dias} días`;
}

function ListaTareas({ tareas, atrasadas, completados }) {
  if (tareas.length === 0) {
    return <p className="panel-vacio">{atrasadas ? 'No tenés tareas atrasadas.' : 'No tenés tareas próximas.'}</p>;
  }

  return (
    <ul className="panel-lista">
      {tareas.map((t) => {
        // Cuánto lleva hecho de la carpeta donde está la tarea
        const avance = avanceDeApartado(t.apartado, completados);

        return (
          <li key={t.id}>
            <Link
              to={`/modulos/${t.cursoId}?tarea=${t.id}`}
              className="panel-tarea"
              title={`Ir a la entrega en ${t.curso}`}
            >
              {/* Las próximas avisan con una campanita del color del módulo;
                  las atrasadas, con un reloj rojo: ya se pasó el tiempo. */}
              {atrasadas ? (
                <span className="panel-campana vencida">
                  <IconoReloj width={18} height={18} />
                </span>
              ) : (
                <span className="panel-campana" style={{ color: t.color }}>
                  <IconoCampana />
                </span>
              )}

              <div className="panel-tarea-texto">
                <small className="panel-tarea-curso">{t.curso}</small>
                <strong>{t.titulo}</strong>
                <small className={atrasadas ? 'plazo atrasado' : 'plazo'}>{textoPlazo(t.fechaLimite)}</small>
              </div>

              {avance && (
                <span
                  className={`contador ${nivel(avance.porcentaje)}`}
                  title={`Llevás ${avance.hechos} de ${avance.total} en «${t.apartado.titulo}»`}
                >
                  {avance.hechos}/{avance.total}
                </span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export default function PanelTareas({ pendientes }) {
  // Lo marcado no cambia desde esta pantalla, alcanza con leerlo al entrar
  const [completados] = useState(leerCompletados);

  return (
    <aside className="panel">
      <section>
        <h2 className="panel-titulo">Tareas pendientes recientes</h2>
        {pendientes ? (
          <ListaTareas tareas={pendientes.recientes} completados={completados} />
        ) : (
          <p className="panel-vacio">Cargando…</p>
        )}
      </section>

      <section>
        <h2 className="panel-titulo atrasado">Tareas pendientes atrasadas</h2>
        {pendientes ? (
          <ListaTareas tareas={pendientes.atrasadas} completados={completados} atrasadas />
        ) : (
          <p className="panel-vacio">Cargando…</p>
        )}
      </section>
    </aside>
  );
}
