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

const ORDINAL = { 1: '1.er', 2: '2.º', 3: '3.er', 4: '4.º', 5: '5.º', 6: '6.º', 7: '7.º' };

/** "2.º año". El 0 es el módulo que no está en ningún plan. */
function nombreDeAnio(anio) {
  if (!anio) return 'Sin año asignado';
  return `${ORDINAL[anio] ?? `${anio}.º`} año`;
}

/** El 3 es anual, no un tercer cuatrimestre: así lo guarda el plan. */
function nombreDeCuatrimestre(cuatrimestre) {
  if (cuatrimestre === 3) return 'Anual';
  if (cuatrimestre === 2) return '2.º cuatrimestre';
  if (cuatrimestre === 1) return '1.er cuatrimestre';
  return 'Sin período';
}

export default function Modulos() {
  const [modulos, setModulos] = useState(null);
  const [pendientes, setPendientes] = useState(null);
  const [error, setError] = useState(null);

  // Filtros de la barra
  const [vista, setVista] = useState('grilla');
  const [busqueda, setBusqueda] = useState('');
  const [periodo, setPeriodo] = useState('');
  const [anio, setAnio] = useState('');
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

  // Los años que hay de verdad, no del 1 al 7: ofrecer un año vacío es
  // ofrecer un filtro que deja la pantalla sin nada.
  const anios = useMemo(
    () =>
      modulos
        ? [...new Set(modulos.map((m) => m.anio ?? 0))].sort((a, b) =>
            a === 0 ? 1 : b === 0 ? -1 : a - b
          )
        : [],
    [modulos]
  );

  const visibles = useMemo(() => {
    if (!modulos) return [];
    const texto = busqueda.trim().toLowerCase();
    return modulos
      .filter((m) => !periodo || m.periodo === periodo)
      .filter((m) => !anio || String(m.anio ?? 0) === anio)
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
  }, [modulos, busqueda, periodo, anio, apartado]);

  // Los módulos van en tres niveles: **carrera → año → cuatrimestre**.
  //
  // La carrera importa desde que el administrador y el supervisor ven todo el
  // campus: sin ella, "2.º cuatrimestre" mezcla materias de carreras
  // distintas y deja de querer decir nada.
  //
  // El año importa por lo mismo, un nivel más abajo. Agrupando solo por
  // cuatrimestre, el segundo de primer año caía junto al de segundo y al de
  // tercero: catorce módulos en dos montones donde no se distingue qué se
  // cursa cuándo. Para un estudiante de un solo año queda un grupo y no
  // estorba; para quien administra, es lo que hace legible la pantalla.
  const carreras = useMemo(() => {
    // Agrupa manteniendo el orden de aparición, y manda al final a los que no
    // tienen el dato: un módulo sin materia en el plan no tiene año.
    const agrupar = (lista, dato) => {
      const mapa = new Map();
      for (const modulo of lista) {
        const clave = modulo[dato] ?? 0;
        if (!mapa.has(clave)) mapa.set(clave, []);
        mapa.get(clave).push(modulo);
      }
      return [...mapa.entries()].sort(([a], [b]) =>
        a === 0 ? 1 : b === 0 ? -1 : a - b
      );
    };

    const porCarrera = new Map();
    for (const modulo of visibles) {
      const clave = modulo.carrera ?? '';
      if (!porCarrera.has(clave)) porCarrera.set(clave, []);
      porCarrera.get(clave).push(modulo);
    }

    return [...porCarrera.entries()]
      .sort(([a], [b]) => {
        if (!a) return 1;  // los sin carrera, últimos
        if (!b) return -1;
        return a.localeCompare(b, 'es');
      })
      .map(([carrera, lista]) => ({
        carrera,
        anios: agrupar(lista, 'anio').map(([anio, suyos]) => ({
          anio,
          // Primero el 1.º, después el 2.º y al final las anuales: es el
          // orden en que se cursan, no el alfabético.
          cuatrimestres: agrupar(suyos, 'cuatrimestre').map(([cuatrimestre, modulos]) => ({
            cuatrimestre,
            modulos,
          })),
        })),
      }));
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
            anios={anios}
            anio={anio}
            onAnio={setAnio}
            apartado={apartado}
            onApartado={setApartado}
            esAlumno={esAlumno}
          />

          {error && <p className="error">No se pudieron cargar los datos. ¿Está corriendo el backend?</p>}
          {!error && !modulos && <p className="texto-suave">Cargando…</p>}
          {modulos && visibles.length === 0 && (
            <p className="texto-suave">No hay módulos que coincidan con la búsqueda.</p>
          )}

          {carreras.map(({ carrera, anios }) => (
            <section key={carrera || 'sin-carrera'} className="grupo-carrera">
              {/* La carrera va siempre, aunque haya una sola: es el nivel
                  que ordena todo lo de abajo y conviene que se vea. */}
              <h2 className="carrera-titulo">
                {carrera || 'Sin carrera asignada'}
                <small>
                  {(() => {
                    const n = anios.reduce(
                      (suma, a) => suma + a.cuatrimestres.reduce((s, c) => s + c.modulos.length, 0),
                      0
                    );
                    return `${n} ${n === 1 ? 'módulo' : 'módulos'}`;
                  })()}
                </small>
              </h2>

              {anios.map(({ anio, cuatrimestres }) => (
                <section key={anio} className="grupo-anio">
                  <h3 className="anio-titulo">{nombreDeAnio(anio)}</h3>

                  {cuatrimestres.map(({ cuatrimestre, modulos: delGrupo }) => (
                    <div key={cuatrimestre} className="grupo-modulos">
                      <h4 className="periodo-titulo">{nombreDeCuatrimestre(cuatrimestre)}</h4>
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
