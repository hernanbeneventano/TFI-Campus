// Las cuentas del campus: quién es quién y qué puede hacer.
//
// Solo el administrador cambia roles o suspende cuentas. Dos resguardos que
// el servidor impone y la pantalla explica: nadie se edita a sí mismo —para
// no quitarse el rol y quedar afuera, ni dárselo— y el campus no se queda
// sin ningún administrador.

import { useCallback, useEffect, useState } from 'react';
import { obtenerUsuarios, administrarUsuario, crearUsuario } from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import { hace } from '../../services/fechas.js';
import { IconoMas, IconoBuscar, IconoCerrar, IconoEstudiante, IconoUsuario } from '../Iconos.jsx';

const ESTADO = {
  activa: 'al-dia',
  suspendida: 'por-debajo',
  pendiente: 'en-riesgo',
};

// Lo que hay que pasarle a la persona para que entre la primera vez. Se
// muestra una sola vez, al crearla: la contraseña no queda guardada en ningún
// lado, así que si se cierra este cartel sin copiarla hay que cambiarla.
function DatosDeAcceso({ cuenta, onCerrar }) {
  const [copiado, setCopiado] = useState(false);

  async function copiar() {
    const texto = `Campus: ${location.origin}/login
Correo: ${cuenta.correo}
Contraseña: ${cuenta.contrasena}`;
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
    } catch {
      // Algunos navegadores lo niegan; el texto está a la vista para copiarlo a mano
      avisar('No se pudo copiar. Seleccionalo a mano.', 'error');
    }
  }

  return (
    <div className="correccion-fondo" role="presentation">
      <div className="correccion" role="dialog" aria-modal="true" aria-labelledby="acceso-titulo">
        <h3 id="acceso-titulo">Cuenta creada</h3>
        <p className="correccion-trabajo">
          Pasale estos datos a {cuenta.nombre}. Con eso entra la próxima vez, y después
          puede cambiar la contraseña desde «¿Olvidaste tu contraseña?».
        </p>

        <dl className="datos-acceso">
          <div>
            <dt>Correo</dt>
            <dd>{cuenta.correo}</dd>
          </div>
          <div>
            <dt>Contraseña</dt>
            <dd>
              <strong>{cuenta.contrasena}</strong>
            </dd>
          </div>
        </dl>

        <p className="texto-suave">
          No se guarda en ninguna parte: si cerrás esto sin copiarla, hay que ponerle
          una nueva.
        </p>

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={copiar}>
            {copiado ? 'Copiado' : 'Copiar los datos'}
          </button>
          <button type="button" className="boton-principal" onClick={onCerrar}>
            Listo
          </button>
        </div>
      </div>
    </div>
  );
}

function Editor({ usuario, roles, estados, yo, onGuardar, onCerrar, trabajando }) {
  const [elegidos, setElegidos] = useState(usuario.roles ?? []);
  const [estado, setEstado] = useState(usuario.estadoCuenta ?? 'activa');

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !trabajando) onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    return () => window.removeEventListener('keydown', alTeclado);
  }, [onCerrar, trabajando]);

  const esYo = usuario.id === yo?.id;

  function alternar(rol) {
    setElegidos((x) => (x.includes(rol) ? x.filter((r) => r !== rol) : [...x, rol]));
  }

  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && !trabajando && onCerrar()}
      role="presentation"
    >
      <form
        className="correccion"
        role="dialog"
        aria-modal="true"
        onSubmit={(e) => {
          e.preventDefault();
          onGuardar({ roles: elegidos, estado });
        }}
      >
        <button
          type="button"
          className="correccion-cerrar"
          onClick={onCerrar}
          disabled={trabajando}
          aria-label="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        <h3>{usuario.nombre}</h3>
        <p className="correccion-trabajo">{usuario.correo}</p>

        {esYo && (
          <p className="aviso-error">
            No podés cambiarte los roles a vos mismo. Pedíselo a otro administrador.
          </p>
        )}

        <fieldset className="editor-tipos compacto">
          <legend>Roles</legend>
          <div>
            {roles.map((rol) => (
              <label key={rol} className={elegidos.includes(rol) ? 'tipo elegido' : 'tipo'}>
                <input
                  type="checkbox"
                  checked={elegidos.includes(rol)}
                  disabled={esYo}
                  onChange={() => alternar(rol)}
                />
                <strong>{rol}</strong>
              </label>
            ))}
          </div>
        </fieldset>

        <label>
          <span>Estado de la cuenta</span>
          <select value={estado} disabled={esYo} onChange={(e) => setEstado(e.target.value)}>
            {estados.map((x) => (
              <option key={x} value={x}>
                {x}
              </option>
            ))}
          </select>
        </label>

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={trabajando}>
            Cancelar
          </button>
          <button
            type="submit"
            className="boton-principal"
            disabled={trabajando || esYo || elegidos.length === 0}
          >
            Guardar
          </button>
        </div>
      </form>
    </div>
  );
}

function Alta({ roles, onGuardar, onCerrar, trabajando }) {
  const [nombre, setNombre] = useState('');
  const [correo, setCorreo] = useState('');
  const [contrasena, setContrasena] = useState('');
  const [elegidos, setElegidos] = useState(['Estudiante']);

  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && !trabajando && onCerrar()}
      role="presentation"
    >
      <form
        className="correccion"
        role="dialog"
        aria-modal="true"
        onSubmit={(e) => {
          e.preventDefault();
          onGuardar({
            nombre: nombre.trim(),
            correo: correo.trim(),
            roles: elegidos,
            // Vacía, el servidor genera una al azar y la devuelve una vez
            contrasena: contrasena.trim() || undefined,
          });
        }}
      >
        <button
          type="button"
          className="correccion-cerrar"
          onClick={onCerrar}
          disabled={trabajando}
          aria-label="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        <h3>Dar de alta una cuenta</h3>
        <p className="correccion-trabajo">
          La cuenta queda lista para usar: con estos datos, la persona ya puede entrar
          la próxima vez que lo intente. Es el único modo de tener cuenta en el campus:
          nadie se registra por su cuenta.
        </p>

        <label>
          <span>Nombre y apellido</span>
          <input
            type="text"
            value={nombre}
            maxLength={120}
            autoFocus
            onChange={(e) => setNombre(e.target.value)}
          />
        </label>

        <label>
          <span>Correo electrónico</span>
          <input
            type="email"
            value={correo}
            maxLength={150}
            placeholder="nombre.apellido@campustfi.edu.ar"
            onChange={(e) => setCorreo(e.target.value)}
          />
        </label>

        <label>
          <span>Contraseña</span>
          <input
            type="text"
            value={contrasena}
            minLength={6}
            maxLength={72}
            placeholder="Al menos 6 caracteres. Vacía, se genera una."
            onChange={(e) => setContrasena(e.target.value)}
          />
          <small className="texto-suave">
            Es la que hay que darle a la persona para que entre la primera vez. Se
            muestra una sola vez al crear la cuenta y no queda guardada: después cada
            uno pone la suya desde «¿Olvidaste tu contraseña?».
          </small>
        </label>

        <fieldset className="editor-tipos compacto">
          <legend>Roles</legend>
          <div>
            {roles.map((rol) => (
              <label key={rol} className={elegidos.includes(rol) ? 'tipo elegido' : 'tipo'}>
                <input
                  type="checkbox"
                  checked={elegidos.includes(rol)}
                  onChange={() =>
                    setElegidos((x) =>
                      x.includes(rol) ? x.filter((r) => r !== rol) : [...x, rol]
                    )
                  }
                />
                <strong>{rol}</strong>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={trabajando}>
            Cancelar
          </button>
          <button
            type="submit"
            className="boton-principal"
            disabled={trabajando || !nombre.trim() || !correo.trim() || !elegidos.length}
          >
            Crear la cuenta
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Cuentas({ yo }) {
  const [datos, setDatos] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [rol, setRol] = useState('');
  const [editando, setEditando] = useState(null);
  const [creando, setCreando] = useState(false);
  // La cuenta que se acaba de crear, mientras se muestran sus datos de acceso
  const [recienCreada, setRecienCreada] = useState(null);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);

  const traer = useCallback(() => {
    obtenerUsuarios({ q: busqueda, rol })
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, [busqueda, rol]);

  // Se espera a que pare de teclear, como en la Biblioteca
  useEffect(() => {
    const reloj = setTimeout(traer, 300);
    return () => clearTimeout(reloj);
  }, [traer]);

  async function accionar(accion, exito) {
    setTrabajando(true);
    try {
      const resultado = await accion();
      setEditando(null);
      setCreando(false);
      traer();
      avisar(exito);

      // El campus hizo lo suyo, pero el acceso en Firebase puede haber
      // fallado: la cuenta queda sin poder entrar y hay que decirlo.
      if (resultado?.acceso && resultado.acceso.hecho === false) {
        avisar(resultado.acceso.motivo ?? 'El acceso quedó pendiente.', 'error');
      }
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  return (
    <>
      <div className="filtros-plan">
        <label className="barra-busqueda">
          <IconoBuscar />
          <input
            type="search"
            value={busqueda}
            placeholder="Buscar por nombre o correo"
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </label>

        <label className="filtro-habilitadas">
          <span>Rol</span>
          <select value={rol} onChange={(e) => setRol(e.target.value)}>
            <option value="">Todos</option>
            {datos.roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>

        {datos.puedeAdministrar && (
          <button type="button" className="boton-principal" onClick={() => setCreando(true)}>
            <IconoMas width={16} height={16} />
            Nueva cuenta
          </button>
        )}
      </div>

      {datos.usuarios.length === 0 ? (
        <p className="vacio">No hay cuentas que coincidan.</p>
      ) : (
        <ul className="catalogo">
          {datos.usuarios.map((u) => {
            const Avatar = u.roles?.includes('Estudiante') ? IconoEstudiante : IconoUsuario;
            return (
              <li key={u.id} className="fila-catalogo">
                <span className="perfil-avatar chica">
                  <Avatar />
                </span>

                <div className="fila-texto">
                  <strong>{u.nombre}</strong>
                  <small>{u.correo}</small>
                  {u.ultimoAcceso && (
                    <small className="fila-baja">Último acceso {hace(u.ultimoAcceso)}</small>
                  )}
                </div>

                <span className="fila-roles">
                  {(u.roles ?? []).map((r) => (
                    <span key={r} className="etiqueta-rol">
                      {r}
                    </span>
                  ))}
                  <span className={`situacion ${ESTADO[u.estadoCuenta] ?? 'al-dia'} chica`}>
                    {u.estadoCuenta}
                  </span>
                </span>

                {datos.puedeAdministrar && (
                  <button
                    type="button"
                    className="boton-suave"
                    onClick={() => setEditando(u)}
                    disabled={u.id === yo?.id}
                    title={
                      u.id === yo?.id
                        ? 'No podés cambiarte los roles a vos mismo'
                        : 'Cambiar roles o estado'
                    }
                  >
                    Roles
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {editando && (
        <Editor
          usuario={editando}
          roles={datos.roles}
          estados={datos.estadosCuenta}
          yo={yo}
          trabajando={trabajando}
          onCerrar={() => setEditando(null)}
          onGuardar={(valores) =>
            accionar(() => administrarUsuario(editando.id, valores), 'Cuenta actualizada.')
          }
        />
      )}

      {creando && (
        <Alta
          roles={datos.roles}
          trabajando={trabajando}
          onCerrar={() => setCreando(false)}
          onGuardar={(valores) =>
            accionar(async () => {
              const respuesta = await crearUsuario(valores);
              // La contraseña viene una sola vez, acá: se muestra enseguida
              if (respuesta?.acceso?.contrasena) {
                setRecienCreada({
                  nombre: valores.nombre,
                  correo: valores.correo,
                  contrasena: respuesta.acceso.contrasena,
                });
              }
              return respuesta;
            }, 'Cuenta creada.')
          }
        />
      )}

      {recienCreada && (
        <DatosDeAcceso cuenta={recienCreada} onCerrar={() => setRecienCreada(null)} />
      )}
    </>
  );
}
