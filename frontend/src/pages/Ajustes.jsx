import { useEffect, useState } from 'react';
import { obtenerUsuarioActual, guardarPerfil } from '../services/api.js';
import { hace } from '../services/fechas.js';
import Encabezado from '../components/Encabezado.jsx';
import { IconoEstudiante, IconoUsuario, IconoAdjuntar } from '../components/Iconos.jsx';

export default function Ajustes() {
  const [usuario, setUsuario] = useState(null);
  const [perfil, setPerfil] = useState({ nombre: '', apellido: '', correo: '' });
  const [guardado, setGuardado] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerUsuarioActual()
      .then((u) => {
        setUsuario(u);
        setPerfil({ nombre: u.nombre, apellido: u.apellido, correo: u.correo ?? '' });
      })
      .catch((e) => setError(e.message));
  }, []);

  function enviar(e) {
    e.preventDefault();
    setError(null);
    guardarPerfil(perfil)
      .then((u) => {
        setUsuario(u);
        setGuardado(true);
        setTimeout(() => setGuardado(false), 2500);
      })
      .catch(() => setError('No se pudo guardar. Revisá los datos e intentá de nuevo.'));
  }

  const Avatar = usuario?.rol === 'Estudiante' ? IconoEstudiante : IconoUsuario;
  const sinCambios =
    usuario &&
    perfil.nombre === usuario.nombre &&
    perfil.apellido === usuario.apellido &&
    perfil.correo === (usuario.correo ?? '');

  return (
    <div className="pagina">
      <Encabezado titulo="Ajustes" descripcion="Tu perfil y los datos de tu cuenta" />

      {error && <p className="error">{error}</p>}
      {!usuario && !error && <p className="texto-suave">Cargando…</p>}

      {usuario && (
        <section className="ajustes-bloque">
          <header>
            <h2>Tu perfil</h2>
            <p>Así te ven el resto de los estudiantes y los docentes.</p>
          </header>

          <div className="ajustes-foto">
            <span className="docente-avatar enorme">
              <Avatar width={44} height={44} />
            </span>
            <div>
              <button type="button" className="boton-suave" disabled>
                <IconoAdjuntar width={16} height={16} />
                Subir una foto
              </button>
              <small className="texto-suave">
                Todavía no hay dónde guardar la imagen: se habilita con Firebase Storage.
              </small>
            </div>
          </div>

          <form className="ajustes-campos" onSubmit={enviar}>
            <label>
              <span>Nombre</span>
              <input
                type="text"
                value={perfil.nombre}
                onChange={(e) => setPerfil({ ...perfil, nombre: e.target.value })}
              />
            </label>

            <label>
              <span>Apellido</span>
              <input
                type="text"
                value={perfil.apellido}
                onChange={(e) => setPerfil({ ...perfil, apellido: e.target.value })}
              />
            </label>

            <label>
              <span>Correo</span>
              <input
                type="email"
                value={perfil.correo}
                onChange={(e) => setPerfil({ ...perfil, correo: e.target.value })}
                placeholder="tu.correo@comunidad.unne.edu.ar"
              />
            </label>

            {/* Lo define la facultad: se muestra, no se edita */}
            <div className="ajustes-fijos">
              <div>
                <span>Rol</span>
                <strong className="etiqueta-rol">{usuario.rol}</strong>
              </div>
              <div>
                <span>Último acceso</span>
                <strong>{hace(usuario.ultimoAcceso)}</strong>
              </div>
            </div>

            <div className="ajustes-pie">
              <small className="texto-suave">
                Cambiar la contraseña y cerrar sesión van a estar disponibles cuando esté el login
                con Firebase Authentication.
              </small>
              {guardado && <span className="ajustes-listo">Cambios guardados</span>}
              <button
                type="submit"
                className="boton-principal"
                disabled={sinCambios || !perfil.nombre.trim() || !perfil.apellido.trim()}
              >
                Guardar cambios
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  );
}
