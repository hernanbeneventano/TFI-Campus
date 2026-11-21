// Quién puede entrar a cada apartado.
//
// Esconder la opción del menú no alcanza: la dirección se puede escribir a
// mano, y entonces el apartado se abría igual y fallaba de mala manera, con
// pantallas a medio cargar y errores del servidor en la consola.
//
// Esto **no es el control de acceso**: el que manda es el servidor, que
// vuelve a comprobar el rol en cada ruta y responde 403. Esto es para que la
// pantalla diga que no, en vez de romperse.

import { Link } from 'react-router-dom';
import Encabezado from './Encabezado.jsx';
import { IconoCandado } from './Iconos.jsx';

/** Los roles de una persona, venga como venga del servidor. */
export function rolesDe(usuario) {
  if (!usuario) return [];
  return usuario.roles ?? (usuario.rol ? [usuario.rol] : []);
}

/** Si esa persona tiene alguno de los roles pedidos. */
export function tieneAlgunRol(usuario, roles) {
  if (!roles || roles.length === 0) return true;
  const suyos = rolesDe(usuario);
  return roles.some((r) => suyos.includes(r));
}

export default function Permitido({ usuario, roles, children }) {
  // Mientras no se sabe quién es, no se muestra ni el apartado ni el cartel:
  // los dos estarían adivinando. Con la sesión de Firebase la identidad llega
  // un instante después de montar, y sin esta espera el estudiante veía por
  // un momento el apartado del administrador.
  if (!usuario) return <p className="texto-suave">Cargando…</p>;

  if (tieneAlgunRol(usuario, roles)) return children;

  return (
    <div className="pagina">
      <Encabezado titulo="Este apartado no es para tu rol" />
      <div className="biblioteca-vacio">
        <IconoCandado width={34} height={34} />
        <h3>No tenés acceso a esta sección</h3>
        <p className="texto-suave">
          Tu cuenta es {rolesDe(usuario).join(' y ')}, y esta parte del campus es para{' '}
          {roles.join(' o ')}. Si creés que te corresponde, pedíselo a la secretaría.
        </p>
        <Link className="boton-principal" to="/novedades">
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}
