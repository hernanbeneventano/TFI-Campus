import { IconoBuscar, IconoGrilla, IconoLista } from './Iconos.jsx';

// Barra sobre los módulos: tipo de vista, búsqueda, filtro por fecha y apartados especiales
export default function BarraHerramientas({
  vista,
  onVista,
  busqueda,
  onBusqueda,
  periodos,
  periodo,
  onPeriodo,
  apartado,
  onApartado,
}) {
  return (
    <div className="barra">
      <div className="barra-vista" role="group" aria-label="Cómo ver los módulos">
        <button
          type="button"
          className={vista === 'grilla' ? 'activo' : ''}
          onClick={() => onVista('grilla')}
          aria-label="Ver en tarjetas"
          title="Ver en tarjetas"
        >
          <IconoGrilla />
        </button>
        <button
          type="button"
          className={vista === 'lista' ? 'activo' : ''}
          onClick={() => onVista('lista')}
          aria-label="Ver en lista"
          title="Ver en lista"
        >
          <IconoLista />
        </button>
      </div>

      <label className="barra-busqueda">
        <IconoBuscar />
        <input
          type="search"
          placeholder="Buscar módulo o docente"
          value={busqueda}
          onChange={(e) => onBusqueda(e.target.value)}
        />
      </label>

      <select
        className="barra-select"
        value={periodo}
        onChange={(e) => onPeriodo(e.target.value)}
        aria-label="Filtrar por fecha"
      >
        <option value="">Todas las fechas</option>
        {periodos.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>

      <select
        className="barra-select"
        value={apartado}
        onChange={(e) => onApartado(e.target.value)}
        aria-label="Apartados especiales"
      >
        <option value="todos">Todos los módulos</option>
        <option value="favoritos">Favoritos</option>
      </select>
    </div>
  );
}
