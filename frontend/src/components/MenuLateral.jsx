import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { leerMenuCerrado, guardarMenuCerrado } from '../services/preferencias.js';
import usePresencia from '../hooks/usePresencia.js';
import {
  Logo,
  IconoInformacion,
  IconoActividad,
  IconoModulos,
  IconoMensajes,
  IconoUsuario,
  IconoEstudiante,
  IconoPanel,
  IconoAjustes,
  IconoSalir,
  IconoCampana,
} from './Iconos.jsx';

const textoEstado = {
  conectado: 'Conectado',
  ausente: 'Ausente',
  desconectado: 'Desconectado',
};

// `aviso` es la clave del contador de novedades que le corresponde a cada
// apartado; Actividad no lleva porque ya es el buzón de todo lo que pasa.
const secciones = [
  { ruta: '/informacion', nombre: 'Información', Icono: IconoInformacion, aviso: 'informacion' },
  { ruta: '/actividad', nombre: 'Actividad', Icono: IconoActividad },
  { ruta: '/modulos', nombre: 'Módulos', Icono: IconoModulos, aviso: 'modulos' },
  { ruta: '/mensajes', nombre: 'Mensajes', Icono: IconoMensajes, aviso: 'mensajes' },
];

const textoAviso = {
  informacion: (n) => `${n} ${n === 1 ? 'aviso nuevo' : 'avisos nuevos'}`,
  modulos: (n) => `${n} ${n === 1 ? 'módulo con novedades' : 'módulos con novedades'}`,
  mensajes: (n) => `${n} ${n === 1 ? 'mensaje sin leer' : 'mensajes sin leer'}`,
};

// Adentro de un módulo (/modulos/algo) conviene más lugar para el contenido
function esPantallaDeModulo(ruta) {
  return /^\/modulos\/.+/.test(ruta);
}

export default function MenuLateral({ usuario, novedades }) {
  // Plegado: quedan solo los íconos. Se recuerda para la próxima visita.
  const [cerrado, setCerrado] = useState(leerMenuCerrado);

  const enModulo = esPantallaDeModulo(useLocation().pathname);
  const estado = usePresencia();

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
          {secciones.map(({ ruta, nombre, Icono, aviso }) => {
            const cuantas = aviso ? (novedades?.[aviso] ?? 0) : 0;
            const ayuda = cuantas > 0 ? `${nombre} · ${textoAviso[aviso](cuantas)}` : nombre;

            return (
              <li key={ruta}>
                <NavLink
                  to={ruta}
                  title={ayuda}
                  className={({ isActive }) => (isActive ? 'menu-item activo' : 'menu-item')}
                >
                  <Icono />
                  <span className="menu-etiqueta">{nombre}</span>
                  {cuantas > 0 && (
                    <span className="menu-aviso" aria-label={textoAviso[aviso](cuantas)}>
                      <IconoCampana width={14} height={14} />
                      {cuantas}
                    </span>
                  )}
                </NavLink>
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
            <button type="button" title="Ajustes" aria-label="Ajustes">
              <IconoAjustes />
            </button>
            <button type="button" title="Cerrar sesión" aria-label="Cerrar sesión">
              <IconoSalir />
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
