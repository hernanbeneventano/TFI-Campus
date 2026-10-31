// Panel derecho: tareas pendientes próximas y atrasadas

const DIA = 24 * 60 * 60 * 1000;

function textoPlazo(fechaIso) {
  const dias = Math.round((new Date(fechaIso) - new Date()) / DIA);
  if (dias < 0) return dias === -1 ? 'Venció ayer' : `Venció hace ${-dias} días`;
  if (dias === 0) return 'Vence hoy';
  if (dias === 1) return 'Vence mañana';
  return `Vence en ${dias} días`;
}

function ListaTareas({ tareas, atrasadas }) {
  if (tareas.length === 0) {
    return <p className="panel-vacio">{atrasadas ? 'No tenés tareas atrasadas.' : 'No tenés tareas próximas.'}</p>;
  }
  return (
    <ul className="panel-lista">
      {tareas.map((t) => (
        <li key={t.id} className="panel-tarea">
          <span className="panel-punto" style={{ background: t.color }} />
          <div>
            <strong>{t.titulo}</strong>
            <small>{t.curso}</small>
            <small className={atrasadas ? 'plazo atrasado' : 'plazo'}>{textoPlazo(t.fechaLimite)}</small>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function PanelTareas({ pendientes }) {
  return (
    <aside className="panel">
      <section>
        <h2 className="panel-titulo">Tareas pendientes recientes</h2>
        {pendientes ? <ListaTareas tareas={pendientes.recientes} /> : <p className="panel-vacio">Cargando…</p>}
      </section>

      <section>
        <h2 className="panel-titulo atrasado">Tareas pendientes atrasadas</h2>
        {pendientes ? (
          <ListaTareas tareas={pendientes.atrasadas} atrasadas />
        ) : (
          <p className="panel-vacio">Cargando…</p>
        )}
      </section>
    </aside>
  );
}
