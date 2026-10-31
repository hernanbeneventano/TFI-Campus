import { useEffect, useMemo, useState } from 'react';
import { obtenerCursos, obtenerTareasPendientes } from '../services/api.js';
import { leerAgruparPorPeriodo } from '../services/preferencias.js';
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
  // Se cambia desde Ajustes, cuando esa pantalla exista
  const [agrupar] = useState(leerAgruparPorPeriodo);

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

  // Los módulos van separados por cuatrimestre, cada uno en su propio recuadro.
  // Los más nuevos arriba. Si la preferencia está apagada, va todo junto.
  const grupos = useMemo(() => {
    if (!agrupar) return [{ periodo: null, modulos: visibles }];

    const porPeriodo = new Map();
    for (const modulo of visibles) {
      if (!porPeriodo.has(modulo.periodo)) porPeriodo.set(modulo.periodo, []);
      porPeriodo.get(modulo.periodo).push(modulo);
    }

    return [...porPeriodo.entries()]
      .sort(([a], [b]) => b.localeCompare(a, 'es'))
      .map(([periodo, modulos]) => ({ periodo, modulos }));
  }, [visibles, agrupar]);

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

          {error && <p className="error">No se pudieron cargar los datos. ¿Está corriendo el backend?</p>}
          {!error && !modulos && <p className="texto-suave">Cargando…</p>}
          {modulos && visibles.length === 0 && (
            <p className="texto-suave">No hay módulos que coincidan con la búsqueda.</p>
          )}

          {grupos.map(({ periodo: cuatrimestre, modulos: delGrupo }) => (
            <div key={cuatrimestre ?? 'todos'} className="grupo-modulos">
              {cuatrimestre && <h2 className="periodo-titulo">{cuatrimestre}</h2>}
              <div className="modulos-contenedor">
                <div className={vista === 'grilla' ? 'modulos-grilla' : 'modulos-lista'}>
                  {delGrupo.map((m) => (
                    <TarjetaModulo
                      key={m.id}
                      modulo={m}
                      vista={vista}
                      onFavorito={alternarFavorito}
                      // Con los cuatrimestres separados, repetirlo en cada
                      // tarjeta sobra: ya está en el título del grupo.
                      mostrarPeriodo={!agrupar}
                    />
                  ))}
                </div>
              </div>
            </div>
          ))}
        </section>

        <PanelTareas pendientes={pendientes} />
      </div>
    </div>
  );
}
