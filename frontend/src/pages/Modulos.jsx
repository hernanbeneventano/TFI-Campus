import { useEffect, useMemo, useState } from 'react';
import {
  obtenerCursos,
  obtenerTareasPendientes,
  marcarFavorito,
  obtenerUsuarioActual,
} from '../services/api.js';
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

  // Quién mira: al docente no se le muestra lo que hace el alumno
  const [usuario, setUsuario] = useState(null);
  // Inscribirse a materias y tener tareas pendientes es cosa del estudiante.
  // Antes se preguntaba "¿no es docente?", y con eso el administrador —que no
  // cursa nada— veía un botón que el servidor le iba a rechazar.
  const esAlumno = (usuario?.roles ?? [usuario?.rol]).includes('Estudiante');

  useEffect(() => {
    obtenerCursos().then(setModulos).catch((e) => setError(e.message));
    obtenerTareasPendientes().then(setPendientes).catch((e) => setError(e.message));
    obtenerUsuarioActual().then(setUsuario).catch(() => setUsuario(null));
    // Las pendientes se piden igual: hasta saber el rol no se sabe si hacen
    // falta, y es una consulta chica contra datos que ya están en memoria.
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

  // Los módulos van separados **por carrera** y, dentro de cada una, por
  // cuatrimestre, con los más nuevos arriba.
  //
  // El nivel de carrera importa desde que el administrador y el supervisor
  // ven todo el campus: sin él, "2.º cuatrimestre" mezcla materias de
  // carreras distintas y deja de querer decir nada. Para un estudiante, que
  // casi siempre está en una sola carrera, queda un único grupo y no estorba.
  const carreras = useMemo(() => {
    const porCarrera = new Map();
    for (const modulo of visibles) {
      // Un módulo sin materia en el plan no tiene carrera: va al final, junto
      const clave = modulo.carrera ?? '';
      if (!porCarrera.has(clave)) porCarrera.set(clave, []);
      porCarrera.get(clave).push(modulo);
    }

    const porPeriodo = (lista) => {
      const mapa = new Map();
      for (const modulo of lista) {
        if (!mapa.has(modulo.periodo)) mapa.set(modulo.periodo, []);
        mapa.get(modulo.periodo).push(modulo);
      }
      return [...mapa.entries()]
        .sort(([a], [b]) => b.localeCompare(a, 'es'))
        .map(([periodo, modulos]) => ({ periodo, modulos }));
    };

    return [...porCarrera.entries()]
      .sort(([a], [b]) => {
        // Los sin carrera, últimos
        if (!a) return 1;
        if (!b) return -1;
        return a.localeCompare(b, 'es');
      })
      .map(([carrera, lista]) => ({ carrera, grupos: porPeriodo(lista) }));
  }, [visibles]);



  function alternarFavorito(id) {
    marcarFavorito(id)
      .then((curso) => setModulos((lista) => lista.map((m) => (m.id === id ? curso : m))))
      .catch((e) => setError(e.message));
  }

  const descripcion = useMemo(() => {
    if (!modulos) return 'Cargando…';
    const favoritos = modulos.filter((m) => m.favorito).length;
    // Con un solo módulo decía "1 módulos · 1 favoritos"
    const enPlural = (n, singular, plural) => `${n} ${n === 1 ? singular : plural}`;
    return `${enPlural(modulos.length, 'módulo', 'módulos')} · ${enPlural(
      favoritos,
      'favorito',
      'favoritos'
    )}`;
  }, [modulos]);

  return (
    <div className="pagina">
      <Encabezado titulo="Módulos" descripcion={descripcion} />

      <div className={esAlumno ? 'pagina-cuerpo' : 'pagina-cuerpo sin-panel'}>
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
            esAlumno={esAlumno}
          />

          {error && <p className="error">No se pudieron cargar los datos. ¿Está corriendo el backend?</p>}
          {!error && !modulos && <p className="texto-suave">Cargando…</p>}
          {modulos && visibles.length === 0 && (
            <p className="texto-suave">No hay módulos que coincidan con la búsqueda.</p>
          )}

          {carreras.map(({ carrera, grupos }) => (
            <section key={carrera || 'sin-carrera'} className="grupo-carrera">
              {/* La carrera va siempre, aunque haya una sola: es el nivel
                  que ordena todo lo de abajo y conviene que se vea. */}
              <h2 className="carrera-titulo">
                {carrera || 'Sin carrera asignada'}
                <small>
                  {(() => {
                    const n = grupos.reduce((suma, g) => suma + g.modulos.length, 0);
                    return `${n} ${n === 1 ? 'módulo' : 'módulos'}`;
                  })()}
                </small>
              </h2>

              {grupos.map(({ periodo: cuatrimestre, modulos: delGrupo }) => (
                <div key={cuatrimestre ?? 'todos'} className="grupo-modulos">
                  {cuatrimestre && <h3 className="periodo-titulo">{cuatrimestre}</h3>}
                  <div className="modulos-contenedor">
                    {/* La `key` con la vista hace que al cambiar de tarjetas a
                        lista se vuelva a montar, y con eso se reproduce la
                        animación de entrada de cada módulo. */}
                    <div
                      key={vista}
                      className={vista === 'grilla' ? 'modulos-grilla' : 'modulos-lista'}
                    >
                      {delGrupo.map((m, i) => (
                        <TarjetaModulo
                          key={m.id}
                          modulo={m}
                          vista={vista}
                          indice={i}
                          onFavorito={alternarFavorito}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </section>
          ))}
        </section>

        {/* "Lo que tenés que entregar" es del alumno. Un docente no tiene
            pendientes propios en sus materias: las corrige, que se hace
            desde la pestaña Notas de cada módulo. */}
        {esAlumno && <PanelTareas pendientes={pendientes} />}
      </div>
    </div>
  );
}
