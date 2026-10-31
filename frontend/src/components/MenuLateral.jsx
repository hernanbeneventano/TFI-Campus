import { NavLink } from 'react-router-dom';
import {
  Logo,
  IconoInformacion,
  IconoActividad,
  IconoModulos,
  IconoMensajes,
  IconoUsuario,
} from './Iconos.jsx';

const secciones = [
  { ruta: '/informacion', nombre: 'Información', Icono: IconoInformacion },
  { ruta: '/actividad', nombre: 'Actividad', Icono: IconoActividad },
  { ruta: '/modulos', nombre: 'Módulos', Icono: IconoModulos },
  { ruta: '/mensajes', nombre: 'Mensajes', Icono: IconoMensajes },
];

export default function MenuLateral({ usuario }) {
  return (
    <aside className="menu">
      <div className="menu-logo">
        <Logo />
        <span>CampusTFI</span>
      </div>

      <nav>
        <ul className="menu-lista">
          {secciones.map(({ ruta, nombre, Icono }) => (
            <li key={ruta}>
              <NavLink
                to={ruta}
                className={({ isActive }) => (isActive ? 'menu-item activo' : 'menu-item')}
              >
                <Icono />
                <span>{nombre}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="menu-usuario">
        <span className="menu-avatar">
          <IconoUsuario />
        </span>
        <div>
          <strong>{usuario ? `${usuario.nombre} ${usuario.apellido}` : '…'}</strong>
          <small>{usuario?.rol}</small>
        </div>
      </div>
    </aside>
  );
}
