import { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  leerMenuCerrado,
  guardarMenuCerrado,
  leerModulosDesplegados,
  guardarModulosDesplegados,
  leerPeriodosCerrados,
  guardarPeriodosCerrados,
  leerFinalesDesplegados,
  guardarFinalesDesplegados,
} from '../services/preferencias.js';
import { obtenerCursos } from '../services/api.js';
import { salir } from '../services/sesion.js';
import { avisar } from '../services/avisos.js';
import usePresencia from '../hooks/usePresencia.js';
import usePreferencia from '../hooks/usePreferencia.js';
import {
  Logo,
  IconoAnuncio,
  IconoModulos,
  IconoCalendario,
  IconoForo,
  IconoMensajes,
  IconoPanel,
  IconoAjustes,
  IconoSalir,
  IconoCampanaLlena,
  IconoFlecha,
  IconoEstrella,
  IconoBiblioteca,
  IconoActividad,
  IconoFinales,
  IconoInscribirse,
  IconoPresente,
} from './Iconos.jsx';
import Avatar from './Avatar.jsx';

const textoEstado = {
  conectado: 'Conectado',
  ausente: 'Ausente',
  desconectado: 'Desconectado',
};

// `aviso` es la clave del contador de novedades que le corresponde a cada
// apartado; Calendario y Foro no llevan porque no acumulan pendientes.
// El grupo "Materias" de la sublista de Módulos se pliega con el mismo
// mecanismo que los cuatrimestres, así que comparte su preferencia: se
// guarda entre los grupos cerrados. Lleva prefijo para no confundirse nunca
// con el nombre de un cuatrimestre real.
const GRUPO_MATERIAS = '__materias';

// Finales cuelga tres pantallas fijas, igual que Módulos cuelga las materias.
// Son tres para el estudiante y tres para el docente: las mismas mesas de
// examen vistas de los dos lados del mostrador (ver `pages/Finales.jsx`).
const SUBMENU_FINALES = [
  { ruta: '/finales/inscripciones', nombre: 'Inscripciones' },
  { ruta: '/finales/fechas', nombre: 'Fechas próximas' },
  { ruta: '/finales/resultados', nombre: 'Resultados' },
];

const SUBMENU_FINALES_DOCENTE = [
  { ruta: '/finales/inscriptos', nombre: 'Inscriptos' },
  { ruta: '/finales/fechas', nombre: 'Fechas' },
  { ruta: '/finales/resultados', nombre: 'Resultados' },
];

const secciones = [
  { ruta: '/novedades', nombre: 'Novedades', Icono: IconoAnuncio, aviso: 'novedades' },
  { ruta: '/modulos', nombre: 'Módulos', Icono: IconoModulos, aviso: 'modulos', conHijos: true },
  { ruta: '/finales', nombre: 'Finales', Icono: IconoFinales, conFinales: true },
  { ruta: '/asistencias', nombre: 'Asistencias', Icono: IconoPresente },
  { ruta: '/calendario', nombre: 'Calendario', Icono: IconoCalendario },
  { ruta: '/foro', nombre: 'Foro', Icono: IconoForo },
  { ruta: '/mensajes', nombre: 'Mensajes', Icono: IconoMensajes, aviso: 'mensajes' },
  { ruta: '/biblioteca', nombre: 'Biblioteca', Icono: IconoBiblioteca },
  // Lo de la institución va junto: estructura, estudiantes, cuentas y el
  // registro de actividad. Esconder la opción no es el control de acceso:
  // el servidor responde 403 igual.
  {
    ruta: '/administracion',
    nombre: 'Administración',
    Icono: IconoAjustes,
    roles: ['Administrador', 'Supervisor'],
  },
  // El docente no administra nada, pero sí mira la actividad de sus
  // materias. Si además supervisa, la encuentra dentro de Administración y
  // esta opción sobra.
  {
    ruta: '/auditoria',
    nombre: 'Actividad',
    Icono: IconoActividad,
    roles: ['Docente'],
    salvoRoles: ['Administrador', 'Supervisor'],
  },
];

const textoAviso = {
  novedades: (n) => `${n} ${n === 1 ? 'novedad nueva' : 'novedades nuevas'}`,
  modulos: (n) => `${n} ${n === 1 ? 'módulo con novedades' : 'módulos con novedades'}`,
  mensajes: (n) => `${n} ${n === 1 ? 'mensaje sin leer' : 'mensajes sin leer'}`,
};

// Adentro de un módulo (/modulos/algo) conviene más lugar para el contenido.
// La inscripción a materias vive bajo /modulos pero no es un módulo: es una
// pantalla ancha y no tiene por qué plegar el menú.
function esPantallaDeModulo(ruta) {
  return /^\/modulos\/.+/.test(ruta) && ruta !== '/modulos/inscripciones';
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

  const ruta = useLocation().pathname;
  const enModulo = esPantallaDeModulo(ruta);
  const enFinales = ruta.startsWith('/finales');

  // El menú es el mismo para todos salvo en dos lugares: qué cuelga de
  // Finales y que inscribirse a materias es cosa del estudiante.
  const esDocente = usuario?.rol === 'Docente';
  // Solo el estudiante se inscribe a materias; el resto no tiene carrera.
  const esAlumno = (usuario?.roles ?? [usuario?.rol]).includes('Estudiante');

  // Una opción con `roles` solo se muestra a quien tenga alguno de ellos. El
  // servidor comprueba lo mismo: esto es para no ofrecer una puerta cerrada.
  const mios = usuario?.roles ?? (usuario?.rol ? [usuario.rol] : []);
  const visibles = secciones.filter(
    (s) =>
      (!s.roles || s.roles.some((r) => mios.includes(r))) &&
      (!s.salvoRoles || !s.salvoRoles.some((r) => mios.includes(r)))
  );
  const submenuFinales = esDocente ? SUBMENU_FINALES_DOCENTE : SUBMENU_FINALES;
  const estado = usePresencia();
  const navegar = useNavigate();
  const [saliendo, setSaliendo] = useState(false);

  async function cerrarSesion() {
    setSaliendo(true);
    try {
      await salir();
      // Al cerrar la sesión de Firebase, `alCambiarSesion` de App.jsx se
      // entera y vuelve a preguntar quién es: el menú se rearma solo.
      navegar('/login', { replace: true });
    } catch (e) {
      avisar(e.message, 'error');
      setSaliendo(false);
    }
  }

  // Los módulos se listan colgando de su opción, para saltar de uno a otro
  // sin pasar por la grilla.
  const [modulos, setModulos] = useState([]);
  const [desplegados, setDesplegados] = usePreferencia(leerModulosDesplegados);
  const [periodosCerrados, setPeriodosCerrados] = useState(leerPeriodosCerrados);

  // Finales cuelga sus tres pantallas; se recuerda si queda abierto
  const [finalesAbierto, setFinalesAbierto] = usePreferencia(leerFinalesDesplegados);

  function alternarFinales() {
    setFinalesAbierto((valor) => {
      guardarFinalesDesplegados(!valor);
      return !valor;
    });
  }

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

  const materiasCerrado = periodosCerrados.includes(GRUPO_MATERIAS);

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

  // Finales **no** se despliega solo al entrar: lo abre y lo cierra la
  // flecha, y nada más.
  //
  // Antes se abría al navegar a /finales, pero ese `setFinalesAbierto(true)`
  // cambiaba el estado sin guardar la preferencia. Como `usePreferencia`
  // vuelve a leer de localStorage cada vez que se guarda cualquier otra
  // (plegar el menú, cerrar un cuatrimestre, un filtro del calendario), el
  // panel saltaba solo al valor guardado y parecía cerrarse de la nada.

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
          {visibles.map(({ ruta: destino, nombre, Icono, aviso, conHijos, conFinales }) => {
            const cuantas = aviso ? (contadores?.[aviso] ?? 0) : 0;
            const ayuda = cuantas > 0 ? `${nombre} · ${textoAviso[aviso](cuantas)}` : nombre;
            const hijos = conFinales || (conHijos && modulos.length > 0);

            // Las dos opciones desplegables comparten el mismo mecanismo y
            // solo se diferencian en qué estado miran y qué cuelgan.
            const abierto = conFinales ? finalesAbierto : desplegados;
            const alternarHijos = conFinales ? alternarFinales : alternarModulos;
            const ayudaHijos = conFinales
              ? abierto
                ? 'Ocultar los finales'
                : 'Ver los finales'
              : abierto
                ? 'Ocultar tus módulos'
                : 'Ver tus módulos';

            return (
              <li key={destino}>
                <div className={hijos ? 'menu-fila con-hijos' : 'menu-fila'}>
                  <NavLink
                    to={conFinales ? submenuFinales[0].ruta : destino}
                    // Plegado, el nombre sale al costado en un globo propio
                    // (ver `.menu.cerrado .menu-item::after`). El `title` del
                    // navegador se saca ahí para que no salgan los dos.
                    title={cerrado ? undefined : ayuda}
                    data-nombre={nombre}
                    // "end" para que la opción no quede marcada estando dentro
                    // de un módulo: ahí se marca el módulo en la sublista
                    end={conHijos}
                    className={({ isActive }) =>
                      // Finales no tiene pantalla propia: la opción se marca
                      // cuando alguna de sus tres pantallas está abierta
                      (conFinales ? enFinales : isActive) ? 'menu-item activo' : 'menu-item'
                    }
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
                      className={abierto ? 'menu-desplegar abierto' : 'menu-desplegar'}
                      onClick={alternarHijos}
                      aria-expanded={abierto}
                      aria-label={ayudaHijos}
                      title={ayudaHijos}
                    >
                      <IconoFlecha width={15} height={15} />
                    </button>
                  )}
                </div>

                {/* Siempre montada: la altura se anima desde el CSS */}
                {hijos && conFinales && (
                  <div className={abierto ? 'menu-panel abierto' : 'menu-panel'}>
                    <div className="menu-panel-interior">
                      <ul className="menu-modulos">
                        {submenuFinales.map((pantalla) => (
                          <li key={pantalla.ruta}>
                            <NavLink
                              to={pantalla.ruta}
                              tabIndex={abierto ? 0 : -1}
                              title={`Finales · ${pantalla.nombre}`}
                              className={({ isActive }) =>
                                isActive ? 'menu-subitem activo' : 'menu-subitem'
                              }
                            >
                              <span className="menu-hueco" aria-hidden="true" />
                              <span className="menu-etiqueta">{pantalla.nombre}</span>
                            </NavLink>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {hijos && !conFinales && (
                  <div className={abierto ? 'menu-panel abierto' : 'menu-panel'}>
                    <div className="menu-panel-interior">
                      <ul className="menu-sublista">
                        {/* "Materias" es un grupo más, como un cuatrimestre:
                            se pliega igual y recuerda su estado igual. Adentro
                            va la inscripción, que es lo que se hace con las
                            materias que todavía no cursás.

                            Al docente no se le muestra: no se inscribe a
                            materias, y el servidor le contesta que no está
                            inscripto a ninguna carrera. */}
                        {esAlumno && (
                          <li>
                            <button
                              type="button"
                              className={
                                materiasCerrado ? 'menu-periodo' : 'menu-periodo abierto'
                              }
                              onClick={() => alternarPeriodo(GRUPO_MATERIAS)}
                              aria-expanded={!materiasCerrado}
                              tabIndex={desplegados ? 0 : -1}
                              title="Materias de tu carrera"
                            >
                              <IconoFlecha width={13} height={13} />
                              <span>Materias</span>
                            </button>

                            <div
                              className={materiasCerrado ? 'menu-panel' : 'menu-panel abierto'}
                            >
                              <div className="menu-panel-interior">
                                <ul className="menu-modulos">
                                  <li>
                                    <NavLink
                                      to="/modulos/inscripciones"
                                      tabIndex={desplegados && !materiasCerrado ? 0 : -1}
                                      title="Inscribirte a materias de tu carrera"
                                      className={({ isActive }) =>
                                        isActive ? 'menu-subitem activo' : 'menu-subitem'
                                      }
                                    >
                                      <span className="menu-hueco" aria-hidden="true">
                                        <IconoInscribirse width={13} height={13} />
                                      </span>
                                      <span className="menu-etiqueta">Inscribirme</span>
                                    </NavLink>
                                  </li>
                                </ul>
                              </div>
                            </div>
                          </li>
                        )}

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
          desvanecen y en su lugar aparecen Ajustes y Cerrar sesión. */}
      <div className="menu-usuario-caja">
        <div className="menu-usuario" title={`${nombreCompleto} · ${textoEstado[estado]}`}>
          <span className={`menu-avatar avatar-estado ${estado}`}>
            <Avatar persona={usuario} tamano={22} />
          </span>

          <div className="menu-datos menu-etiqueta">
            <strong>{nombreCompleto}</strong>
            <small>{usuario?.rol}</small>
          </div>

          <div className="menu-acciones">
            <Link to="/ajustes" title="Ajustes" aria-label="Ajustes">
              <IconoAjustes />
            </Link>
            <button
              type="button"
              onClick={cerrarSesion}
              disabled={saliendo}
              title="Cerrar sesión"
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
