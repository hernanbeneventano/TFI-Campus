// Las cuentas del campus: quién es quién y qué puede hacer.
//
// Solo el administrador cambia roles o suspende cuentas. Dos resguardos que
// el servidor impone y la pantalla explica: nadie se edita a sí mismo —para
// no quitarse el rol y quedar afuera, ni dárselo— y el campus no se queda
// sin ningún administrador.

import { useCallback, useEffect, useState } from 'react';
import {
  obtenerUsuarios,
  administrarUsuario,
  crearUsuario,
  restablecerContrasena,
} from '../../services/api.js';
import Confirmacion from '../Confirmacion.jsx';
import { avisar } from '../../services/avisos.js';
import { hace } from '../../services/fechas.js';
import {
  IconoMas,
  IconoBuscar,
  IconoCerrar,
  IconoEstudiante,
  IconoUsuario,
  IconoAdvertencia,
  IconoCandado,
} from '../Iconos.jsx';
import Avatar from '../Avatar.jsx';

const ESTADO = {
  activa: 'al-dia',
  suspendida: 'por-debajo',
  pendiente: 'en-riesgo',
};

function Editor({
  usuario,
  roles,
  estados,
  carreras,
  sedes,
  yo,
  onGuardar,
  onCerrar,
  trabajando,
}) {
  const [elegidos, setElegidos] = useState(usuario.roles ?? []);
  const [estado, setEstado] = useState(usuario.estadoCuenta ?? 'activa');
  // Hasta dónde llega si supervisa. Vacío quiere decir todo el campus, que es
  // como venían todos antes de que esto existiera.
  const [susCarreras, setSusCarreras] = useState(
    (usuario.ambito?.carreras ?? []).map((c) => c.id)
  );
  const [susSedes, setSusSedes] = useState((usuario.ambito?.sedes ?? []).map((s) => s.id));

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
          onGuardar({
            roles: elegidos,
            estado,
            // El administrador alcanza todo el campus por definición: el
            // servidor rechaza ponerle ámbito, así que ni se manda.
            ...(elegidos.includes('Administrador')
              ? {}
              : { ambito: { carreras: susCarreras, sedes: susSedes } }),
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

        {/* El ámbito solo tiene sentido para quien supervisa: es lo que
            recorta hasta dónde llega. El administrador define qué es la
            facultad, así que la ve entera y no lleva ámbito. */}
        {elegidos.includes('Supervisor') && !elegidos.includes('Administrador') && (
          <fieldset className="editor-tipos compacto">
            <legend>
              Ámbito <small>vacío: todo el campus</small>
            </legend>
            <p className="texto-suave ambito-ayuda">
              Elegí las carreras y las sedes de las que responde. Sin nada marcado ve y modera
              todo el campus.
            </p>
            <div>
              {carreras.map((c) => (
                <label key={`c${c.id}`} className={susCarreras.includes(c.id) ? 'tipo elegido' : 'tipo'}>
                  <input
                    type="checkbox"
                    checked={susCarreras.includes(c.id)}
                    disabled={esYo}
                    onChange={() =>
                      setSusCarreras((x) =>
                        x.includes(c.id) ? x.filter((i) => i !== c.id) : [...x, c.id]
                      )
                    }
                  />
                  <strong>{c.nombre}</strong>
                </label>
              ))}
            </div>
            <div>
              {sedes.map((s) => (
                <label key={`s${s.id}`} className={susSedes.includes(s.id) ? 'tipo elegido' : 'tipo'}>
                  <input
                    type="checkbox"
                    checked={susSedes.includes(s.id)}
                    disabled={esYo}
                    onChange={() =>
                      setSusSedes((x) =>
                        x.includes(s.id) ? x.filter((i) => i !== s.id) : [...x, s.id]
                      )
                    }
                  />
                  <strong>{s.nombre}</strong>
                </label>
              ))}
            </div>
          </fieldset>
        )}

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
          onGuardar({ nombre: nombre.trim(), correo: correo.trim(), roles: elegidos });
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
          Se le crea el acceso en el acto y se te muestra una contraseña provisoria para
          que se la pases.
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

/**
 * La contraseña provisoria recién generada.
 *
 * Se muestra **una sola vez y nunca se guarda**: ni en el campus, ni en la
 * auditoría. Lo que queda registrado es que se restableció y quién lo hizo,
 * no cuál es. Por eso tampoco se puede "ver la contraseña anterior" de nadie:
 * el campus no la tiene —la guarda Firebase, cifrada—, solo puede reemplazarla.
 */
function ContrasenaProvisoria({ persona, contrasena, onCerrar }) {
  const [copiada, setCopiada] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(contrasena);
      setCopiada(true);
      setTimeout(() => setCopiada(false), 2500);
    } catch {
      avisar('No se pudo copiar. Seleccionala y copiala a mano.', 'error');
    }
  }

  return (
    <div className="correccion-fondo" role="presentation">
      <section className="correccion" role="dialog" aria-modal="true">
        <h3>Contraseña provisoria</h3>
        <p className="correccion-trabajo">{persona}</p>

        <p className="texto-suave">
          Pasásela por un medio seguro y pedile que la cambie desde Ajustes al entrar.
        </p>

        <div className="contrasena-provisoria">
          <code>{contrasena}</code>
          <button type="button" className="boton-suave" onClick={copiar}>
            {copiada ? 'Copiada' : 'Copiar'}
          </button>
        </div>

        <p className="nota-bloque">
          <IconoAdvertencia width={14} height={14} />
          Es la única vez que se muestra: no queda guardada en ningún lado. Si se pierde,
          hay que generar otra.
        </p>

        <div className="editor-botones">
          <button type="button" className="boton-principal" onClick={onCerrar}>
            Listo, ya la copié
          </button>
        </div>
      </section>
    </div>
  );
}


export default function Cuentas({ yo }) {
  const [datos, setDatos] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [rol, setRol] = useState('');
  const [editando, setEditando] = useState(null);
  const [creando, setCreando] = useState(false);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);
  // La provisoria recién generada, para mostrarla una sola vez
  const [provisoria, setProvisoria] = useState(null);
  // La cuenta a la que se le está por restablecer la contraseña
  const [aRestablecer, setARestablecer] = useState(null);

  async function restablecer() {
    setTrabajando(true);
    try {
      const r = await restablecerContrasena(aRestablecer.id);
      setProvisoria({ persona: aRestablecer.nombre, contrasena: r.contrasenaProvisoria });
      setARestablecer(null);
      traer();
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

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
      await accion();
      setEditando(null);
      setCreando(false);
      traer();
      avisar(exito);
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
            return (
              <li key={u.id} className="fila-catalogo">
                <span className="perfil-avatar chica">
                  <Avatar persona={u} tamano={30} />
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
                  <span className="fila-acciones">
                    <button
                      type="button"
                      className="boton-suave"
                      onClick={() => setARestablecer(u)}
                      title="Asignarle una contraseña provisoria"
                    >
                      <IconoCandado width={14} height={14} />
                      Contraseña
                    </button>
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
                  </span>
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
          carreras={datos.carreras ?? []}
          sedes={datos.sedes ?? []}
          yo={yo}
          trabajando={trabajando}
          onCerrar={() => setEditando(null)}
          onGuardar={(valores) =>
            accionar(() => administrarUsuario(editando.id, valores), 'Cuenta actualizada.')
          }
        />
      )}

      {aRestablecer && (
        <Confirmacion
          titulo="¿Le asignás una contraseña nueva?"
          mensaje={
            'La anterior deja de servir en el acto. Nadie puede ver cuál era —el campus no la ' +
            'guarda—, así que si la persona la recuerda después, igual va a tener que usar la nueva.'
          }
          detalles={[
            { etiqueta: 'Cuenta', valor: aRestablecer.nombre },
            { etiqueta: 'Correo', valor: aRestablecer.correo },
          ]}
          textoConfirmar="Generar la provisoria"
          trabajando={trabajando}
          onConfirmar={restablecer}
          onCancelar={() => setARestablecer(null)}
        />
      )}

      {provisoria && (
        <ContrasenaProvisoria
          persona={provisoria.persona}
          contrasena={provisoria.contrasena}
          onCerrar={() => setProvisoria(null)}
        />
      )}

      {creando && (
        <Alta
          roles={datos.roles}
          trabajando={trabajando}
          onCerrar={() => setCreando(false)}
          onGuardar={async (valores) => {
            setTrabajando(true);
            try {
              const r = await crearUsuario(valores);
              setCreando(false);
              traer();
              if (r.contrasenaProvisoria) {
                setProvisoria({
                  persona: valores.nombre,
                  contrasena: r.contrasenaProvisoria,
                });
              } else {
                avisar(
                  'Cuenta creada, pero sin acceso: hay que crearle la contraseña a mano.',
                  'error'
                );
              }
            } catch (e) {
              avisar(e.message, 'error');
            } finally {
              setTrabajando(false);
            }
          }}
        />
      )}
    </>
  );
}
