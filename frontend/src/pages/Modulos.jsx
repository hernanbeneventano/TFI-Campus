import { useEffect, useMemo, useState } from 'react';
import { obtenerCursos, obtenerTareasPendientes } from '../services/api.js';
import Encabezado from '../components/Encabezado.jsx';
import BarraHerramientas from '../components/BarraHerramientas.jsx';
import TarjetaModulo from '../components/TarjetaModulo.jsx';
import PanelTareas from '../components/PanelTareas.jsx';

export default function Modulos() {
  const [modulos, setModulos] = useState(null);
  const [pendientes, setPendientes] = useState(null);
  const [error, setError] = useState(null);

  // Filtros de la barra
  const [vista, setVista] = useState('grilla');
  const [busqueda, setBusqueda] = useState('');
  const [periodo, setPeriodo] = useState('');
  const [apartado, setApartado] = useState('todos');

  useEffect(() => {
    obtenerCursos().then(setModulos).catch((e) => setError(e.message));
    obtenerTareasPendientes().then(setPendientes).catch((e) => setError(e.message));
  }, []);

  const periodos = useMemo(
    () => (modulos ? [...new Set(modulos.map((m) => m.periodo))] : []),
    [modulos]
  );

  const visibles = useMemo(() => {
    if (!modulos) return [];
    const texto = busqueda.trim().toLowerCase();
    return modulos
      .filter((m) => !periodo || m.periodo === periodo)
      .filter((m) => apartado !== 'favoritos' || m.favorito)
      .filter(
        (m) =>
          !texto ||
          m.nombre.toLowerCase().includes(texto) ||
          m.codigo.toLowerCase().includes(texto) ||
          m.docente.toLowerCase().includes(texto)
      )
      // Los favoritos van primero
      .sort((a, b) => Number(b.favorito) - Number(a.favorito));
  }, [modulos, busqueda, periodo, apartado]);

  // Por ahora el favorito se guarda solo en pantalla. Más adelante se guardará en el backend.
  function alternarFavorito(id) {
    setModulos((lista) => lista.map((m) => (m.id === id ? { ...m, favorito: !m.favorito } : m)));
  }

  const descripcion = modulos
    ? `${modulos.length} módulos · ${modulos.filter((m) => m.favorito).length} favoritos`
    : 'Cargando…';

  return (
    <div className="pagina">
      <Encabezado titulo="Módulos" descripcion={descripcion} />

      <div className="pagina-cuerpo">
        <section className="pagina-principal">
          <BarraHerramientas
            vista={vista}
            onVista={setVista}
            busqueda={busqueda}
            onBusqueda={setBusqueda}
            periodos={periodos}
            periodo={periodo}
            onPeriodo={setPeriodo}
            apartado={apartado}
            onApartado={setApartado}
          />

          <div className="modulos-contenedor">
            {error && <p className="error">No se pudieron cargar los datos. ¿Está corriendo el backend?</p>}
            {!error && !modulos && <p className="texto-suave">Cargando…</p>}
            {modulos && visibles.length === 0 && (
              <p className="texto-suave">No hay módulos que coincidan con la búsqueda.</p>
            )}
            <div className={vista === 'grilla' ? 'modulos-grilla' : 'modulos-lista'}>
              {visibles.map((m) => (
                <TarjetaModulo key={m.id} modulo={m} vista={vista} onFavorito={alternarFavorito} />
              ))}
            </div>
          </div>
        </section>

        <PanelTareas pendientes={pendientes} />
      </div>
    </div>
  );
}
