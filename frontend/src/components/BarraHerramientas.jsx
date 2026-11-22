import { Link } from 'react-router-dom';
import { IconoBuscar, IconoGrilla, IconoLista, IconoInscribirse } from './Iconos.jsx';
import Desplegable from './Desplegable.jsx';

const ORDINAL = { 1: '1.er', 2: '2.º', 3: '3.er', 4: '4.º', 5: '5.º', 6: '6.º', 7: '7.º' };

function nombreDeAnio(anio) {
  return anio ? `${ORDINAL[anio] ?? `${anio}.º`} año` : 'Sin año asignado';
}

// Barra sobre los módulos: tipo de vista, búsqueda, filtro por fecha, año y
// apartados especiales
export default function BarraHerramientas({
  vista,
  onVista,
  busqueda,
  onBusqueda,
  periodos,
  periodo,
  onPeriodo,
  anios,
  anio,
  onAnio,
  apartado,
  onApartado,
  // Un docente no se inscribe a materias: la acción no va en su barra
  esAlumno = true,
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

      {/* El año va al lado de la fecha porque filtran lo mismo —cuándo se
          cursa— y porque con un plan de cinco años la grilla entera no entra
          en la pantalla. Si hay un solo año no se muestra: un filtro con una
          sola opción no filtra nada. */}
      {anios.length > 1 && (
        <Desplegable
          className="barra-select"
          etiqueta="Filtrar por año"
          valor={anio}
          onCambiar={onAnio}
          opciones={[
            { valor: '', nombre: 'Todos los años' },
            ...anios.map((a) => ({ valor: String(a), nombre: nombreDeAnio(a) })),
          ]}
        />
      )}

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

      {/* La única acción de la barra, al final: lo de la izquierda filtra lo
          que ya tenés, esto te lleva a sumar una materia nueva. Solo para el
          alumno: el docente no se inscribe a materias, las dicta. */}
      {esAlumno && (
        <Link className="barra-accion" to="/modulos/inscripciones">
          <IconoInscribirse width={16} height={16} />
          Inscribirse a materias
        </Link>
      )}
    </div>
  );
}
