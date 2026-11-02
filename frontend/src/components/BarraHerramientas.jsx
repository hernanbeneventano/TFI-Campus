import { IconoBuscar, IconoGrilla, IconoLista } from './Iconos.jsx';
import Desplegable from './Desplegable.jsx';

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

      <Desplegable
        className="barra-select"
        etiqueta="Filtrar por fecha"
        valor={periodo}
        onCambiar={onPeriodo}
        opciones={[
          { valor: '', nombre: 'Todas las fechas' },
          ...periodos.map((p) => ({ valor: p, nombre: p })),
        ]}
      />

      <Desplegable
        className="barra-select"
        etiqueta="Apartados especiales"
        valor={apartado}
        onCambiar={onApartado}
        opciones={[
          { valor: 'todos', nombre: 'Todos los módulos' },
          { valor: 'favoritos', nombre: 'Favoritos' },
        ]}
      />
    </div>
  );
}
