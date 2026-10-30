import { NavLink } from 'react-router-dom';

const secciones = [
  { ruta: '/actividad', nombre: 'Actividad' },
  { ruta: '/cursos', nombre: 'Cursos' },
  { ruta: '/notas', nombre: 'Notas' },
];

export default function MenuLateral() {
  return (
    <nav className="menu">
      <div className="menu-logo">CampusTFI</div>
      <ul>
        {secciones.map((s) => (
          <li key={s.ruta}>
            <NavLink
              to={s.ruta}
              className={({ isActive }) => (isActive ? 'menu-link activo' : 'menu-link')}
            >
              {s.nombre}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
