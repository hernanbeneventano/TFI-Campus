import { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import {
  leerMenuCerrado,
  guardarMenuCerrado,
  leerModulosDesplegados,
  guardarModulosDesplegados,
  leerPeriodosCerrados,
  guardarPeriodosCerrados,
} from '../services/preferencias.js';
import { obtenerCursos } from '../services/api.js';
import usePresencia from '../hooks/usePresencia.js';
import usePreferencia from '../hooks/usePreferencia.js';
import {
  Logo,
  IconoAnuncio,
  IconoModulos,
  IconoCalendario,
  IconoForo,
  IconoMensajes,
  IconoUsuario,
  IconoEstudiante,
  IconoPanel,
  IconoAjustes,
  IconoSalir,
  IconoCampanaLlena,
  IconoFlecha,
  IconoEstrella,
} from './Iconos.jsx';

const textoEstado = {
  conectado: 'Conectado',
  ausente: 'Ausente',
  desconectado: 'Desconectado',
};

// `aviso` es la clave del contador de novedades que le corresponde a cada
// apartado; Calendario y Foro no llevan porque no acumulan pendientes.
const secciones = [
  { ruta: '/novedades', nombre: 'Novedades', Icono: IconoAnuncio, aviso: 'novedades' },
  { ruta: '/modulos', nombre: 'Módulos', Icono: IconoModulos, aviso: 'modulos', conHijos: true },
  { ruta: '/calendario', nombre: 'Calendario', Icono: IconoCalendario },
  { ruta: '/foro', nombre: 'Foro', Icono: IconoForo },
  { ruta: '/mensajes', nombre: 'Mensajes', Icono: IconoMensajes, aviso: 'mensajes' },
];

const textoAviso = {
  novedades: (n) => `${n} ${n === 1 ? 'novedad nueva' : 'novedades nuevas'}`,
  modulos: (n) => `${n} ${n === 1 ? 'módulo con novedades' : 'módulos con novedades'}`,
  mensajes: (n) => `${n} ${n === 1 ? 'mensaje sin leer' : 'mensajes sin leer'}`,
};

// Adentro de un módulo (/modulos/algo) conviene más lugar para el contenido
function esPantallaDeModulo(ruta) {
  return /^\/modulos\/.+/.test(ruta);
}

// "2026 – 2.º cuatrimestre" → "2.º cuatrimestre": en el menú no hay ancho
// para el año, y además se repite en todos los grupos.
function periodoCorto(periodo) {
  const partes = periodo.split('–');
  return (partes[1] ?? partes[0]).trim();
}

export default function MenuLateral({ usuario, contadores }) {
  // Plegado: quedan solo los íconos. Se recuerda para la próxima visita.
  const [cerrado, setCerrado] = usePreferencia(leerMenuCerrado);

  const enModulo = esPantallaDeModulo(useLocation().pathname);
  const estado = usePresencia();

  // Los módulos se listan colgando de su opción, para saltar de uno a otro
  // sin pasar por la grilla.
  const [modulos, setModulos] = useState([]);
  const [desplegados, setDesplegados] = usePreferencia(leerModulosDesplegados);
  const [periodosCerrados, setPeriodosCerrados] = useState(leerPeriodosCerrados);

  useEffect(() => {
    function traerModulos() {
      obtenerCursos().then(setModulos).catch(() => setModulos([]));
    }
    traerModulos();
    // Al marcar un favorito desde Módulos hay que volver a pedirlos
    window.addEventListener('campustfi:cursos', traerModulos);
    return () => window.removeEventListener('campustfi:cursos', traerModulos);
  }, []);

  // Los módulos van separados por cuatrimestre, los más nuevos arriba
  const porPeriodo = useMemo(() => {
    const mapa = new Map();
    for (const modulo of modulos) {
      if (!mapa.has(modulo.periodo)) mapa.set(modulo.periodo, []);
      mapa.get(modulo.periodo).push(modulo);
    }
    return [...mapa.entries()]
      .sort(([a], [b]) => b.localeCompare(a, 'es'))
      .map(([periodo, suyos]) => ({
        periodo,
        // Los favoritos van arriba de su cuatrimestre
        modulos: [...suyos].sort((a, b) => Number(b.favorito) - Number(a.favorito)),
      }));
  }, [modulos]);

  function alternarPeriodo(periodo) {
    setPeriodosCerrados((cerrados) => {
      const siguiente = cerrados.includes(periodo)
        ? cerrados.filter((p) => p !== periodo)
        : [...cerrados, periodo];
      guardarPeriodosCerrados(siguiente);
      return siguiente;
    });
  }

  // Al entrar a un módulo la lista se abre sola, para ver dónde estás parado
  useEffect(() => {
    if (enModulo) setDesplegados(true);
  }, [enModulo]);

  function alternarModulos() {
    setDesplegados((valor) => {
      guardarModulosDesplegados(!valor);
      return !valor;
    });
  }

  // Al entrar a un módulo se pliega solo; al salir vuelve a lo que haya
  // elegido el usuario. Adentro se puede desplegar a mano igual, y eso sí
  // se guarda: solo el plegado automático no pisa la preferencia.
  useEffect(() => {
    setCerrado(enModulo ? true : leerMenuCerrado());
  }, [enModulo]);

  // Los alumnos llevan la silueta con birrete; los docentes, la genérica
  const Avatar = usuario?.rol === 'Estudiante' ? IconoEstudiante : IconoUsuario;
  const nombreCompleto = usuario ? `${usuario.nombre} ${usuario.apellido}` : '…';

  function alternar() {
    setCerrado((valor) => {
      guardarMenuCerrado(!valor);
      return !valor;
    });
  }

  return (
    <aside className={cerrado ? 'menu cerrado' : 'menu'}>
      <button
        type="button"
        className="menu-alternar"
        onClick={alternar}
        aria-expanded={!cerrado}
        aria-label={cerrado ? 'Desplegar el menú' : 'Plegar el menú'}
        title={cerrado ? 'Desplegar el menú' : 'Plegar el menú'}
      >
        <IconoPanel />
      </button>

      <div className="menu-logo">
        <Logo />
        <span className="menu-etiqueta">CampusTFI</span>
      </div>

      <nav>
        <ul className="menu-lista">
          {secciones.map(({ ruta, nombre, Icono, aviso, conHijos }) => {
            const cuantas = aviso ? (contadores?.[aviso] ?? 0) : 0;
            const ayuda = cuantas > 0 ? `${nombre} · ${textoAviso[aviso](cuantas)}` : nombre;
            const hijos = conHijos && modulos.length > 0;

            return (
              <li key={ruta}>
                <div className={hijos ? 'menu-fila con-hijos' : 'menu-fila'}>
                  <NavLink
                    to={ruta}
                    title={ayuda}
                    // "end" para que la opción no quede marcada estando dentro
                    // de un módulo: ahí se marca el módulo en la sublista
                    end={conHijos}
                    className={({ isActive }) => (isActive ? 'menu-item activo' : 'menu-item')}
                  >
                    <Icono />
                    <span className="menu-etiqueta">{nombre}</span>
                    {cuantas > 0 && (
                      <span className="menu-aviso" aria-label={textoAviso[aviso](cuantas)}>
                        <IconoCampanaLlena width={17} height={17} />
                        <span className="menu-aviso-numero">{cuantas}</span>
                      </span>
                    )}
                  </NavLink>

                  {hijos && (
                    <button
                      type="button"
                      className={desplegados ? 'menu-desplegar abierto' : 'menu-desplegar'}
                      onClick={alternarModulos}
                      aria-expanded={desplegados}
                      aria-label={desplegados ? 'Ocultar tus módulos' : 'Ver tus módulos'}
                      title={desplegados ? 'Ocultar tus módulos' : 'Ver tus módulos'}
                    >
                      <IconoFlecha width={15} height={15} />
                    </button>
                  )}
                </div>

                {/* Siempre montada: la altura se anima desde el CSS */}
                {hijos && (
                  <div className={desplegados ? 'menu-panel abierto' : 'menu-panel'}>
                    <div className="menu-panel-interior">
                      <ul className="menu-sublista">
                        {porPeriodo.map(({ periodo, modulos: delPeriodo }) => {
                          const periodoCerrado = periodosCerrados.includes(periodo);
                          const alcanzables = desplegados && !periodoCerrado;

                          return (
                            <li key={periodo}>
                              <button
                                type="button"
                                className={periodoCerrado ? 'menu-periodo' : 'menu-periodo abierto'}
                                onClick={() => alternarPeriodo(periodo)}
                                aria-expanded={!periodoCerrado}
                                tabIndex={desplegados ? 0 : -1}
                                title={periodo}
                              >
                                <IconoFlecha width={13} height={13} />
                                <span>{periodoCorto(periodo)}</span>
                                <small>{delPeriodo.length}</small>
                              </button>

                              <div className={periodoCerrado ? 'menu-panel' : 'menu-panel abierto'}>
                                <div className="menu-panel-interior">
                                  <ul className="menu-modulos">
                                    {delPeriodo.map((modulo) => (
                                      <li key={modulo.id}>
                                        <NavLink
                                          to={`/modulos/${modulo.id}`}
                                          tabIndex={alcanzables ? 0 : -1}
                                          title={`${modulo.codigo} · ${modulo.nombre}`}
                                          className={({ isActive }) =>
                                            isActive ? 'menu-subitem activo' : 'menu-subitem'
                                          }
                                        >
                                          {/* Solo los favoritos llevan marca */}
                                          {modulo.favorito ? (
                                            <span className="menu-estrella" aria-label="Favorito">
                                              <IconoEstrella llena width={13} height={13} />
                                            </span>
                                          ) : (
                                            <span className="menu-hueco" aria-hidden="true" />
                                          )}
                                          <span className="menu-etiqueta">{modulo.nombre}</span>
                                          {modulo.novedades?.total > 0 && (
                                            <span
                                              className="menu-campanita"
                                              title={`${modulo.novedades.total} novedades`}
                                              aria-label={`${modulo.novedades.total} novedades`}
                                            >
                                              <IconoCampanaLlena width={13} height={13} />
                                            </span>
                                          )}
                                        </NavLink>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Al pasar el mouse (o al llegar con el teclado) el nombre y el rol se
          desvanecen y en su lugar aparecen Ajustes y Cerrar sesión. Todavía
          no hacen nada: faltan esas pantallas y el login. */}
      <div className="menu-usuario-caja">
        <div className="menu-usuario" title={`${nombreCompleto} · ${textoEstado[estado]}`}>
          <span className={`menu-avatar avatar-estado ${estado}`}>
            <Avatar />
          </span>

          <div className="menu-datos menu-etiqueta">
            <strong>{nombreCompleto}</strong>
            <small>{usuario?.rol}</small>
          </div>

          <div className="menu-acciones">
            <Link to="/ajustes" title="Ajustes" aria-label="Ajustes">
              <IconoAjustes />
            </Link>
            {/* Todavía no hace nada: llega con el login */}
            <button
              type="button"
              title="Cerrar sesión (disponible cuando esté el login)"
              aria-label="Cerrar sesión"
            >
              <IconoSalir />
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
