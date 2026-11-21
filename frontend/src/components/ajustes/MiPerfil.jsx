// Mis datos y mis carreras.
//
// Lo que uno edita de sí mismo son **los datos de contacto**: el teléfono y
// la fecha de nacimiento. El nombre, el correo y el DNI se muestran pero no
// se tocan, y los roles tampoco:
//
// - El nombre y el DNI son con lo que la facultad te identifica. Un legajo
//   vale porque alguien respondió por esos datos.
// - El correo es con lo que entrás: cambiarlo acá y no en Firebase te dejaría
//   afuera.
// - Si cada uno pudiera darse el rol que quiera, los permisos no
//   significarían nada.
//
// Eso no lo decide esta pantalla —el servidor rechaza el intento igual—, pero
// conviene que se vea por qué están en gris y a quién hay que pedírselo.

import { useEffect, useState } from 'react';
import {
  guardarMiPerfil,
  obtenerMiAcceso,
  cerrarMisSesiones,
  subirMiFoto,
  quitarMiFoto,
} from '../../services/api.js';
import { cambiarContrasena } from '../../services/sesion.js';
import { avisar } from '../../services/avisos.js';
import { hace } from '../../services/fechas.js';
import Confirmacion from '../Confirmacion.jsx';
import Avatar from '../Avatar.jsx';
import {
  IconoCandado,
  IconoSalir,
  IconoCheckCirculo,
  IconoLapiz,
  IconoCerrar,
  IconoPapelera,
  IconoSubir,
} from '../Iconos.jsx';

/** Una fecha que viene de Firebase en milisegundos. */
function cuando(ms) {
  if (!ms) return null;
  return new Date(ms).toISOString();
}

// Lo mismo que exige el servidor (`IMAGENES_MAX_MB` en servicios/archivos.py).
const MAXIMO_FOTO_MB = 10;

const ESTADO_CUENTA = {
  activa: { texto: 'Activa', clase: 'al-dia' },
  suspendida: { texto: 'Suspendida', clase: 'por-debajo' },
  pendiente: { texto: 'Pendiente', clase: 'en-riesgo' },
};

// El <input type="date"> quiere AAAA-MM-DD
function paraElCampo(iso) {
  if (!iso) return '';
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return '';
  const dos = (n) => String(n).padStart(2, '0');
  return `${f.getFullYear()}-${dos(f.getMonth() + 1)}-${dos(f.getDate())}`;
}

/** El acceso al campus: la contraseña y las sesiones abiertas. */

/** La foto de perfil: se cambia tocando la foto, no un botón al lado.
 *
 * La foto **es** el control. Al pasar el mouse por encima aparece el lápiz y
 * al tocarla se abre el panel: es como funciona en cualquier lado y ahorra un
 * botón suelto que compite con la foto por la atención.
 *
 * El panel existe en vez de abrir el selector de archivos directo porque hay
 * tres cosas que decir antes de elegir —qué formatos entran, cuánto puede
 * pesar y que se puede quitar la que está—, y un selector del sistema no dice
 * ninguna.
 *
 * **Solo PNG y JPG.** Nada de GIF ni WEBP: una foto de perfil no se anima, y
 * cada formato que se acepta es uno más que el servidor tiene que saber
 * reconocer por sus bytes. El SVG queda afuera por otra razón: es un
 * documento con scripts adentro, no una imagen.
 */
const FORMATOS_FOTO = [
  { extension: 'PNG', mime: 'image/png' },
  { extension: 'JPG', mime: 'image/jpeg' },
];

const ACEPTA = FORMATOS_FOTO.map((f) => f.mime).join(',');

function FotoDePerfil({ perfil, onGuardado }) {
  const [abierto, setAbierto] = useState(false);

  return (
    <>
      <button
        type="button"
        className="perfil-avatar editable"
        onClick={() => setAbierto(true)}
        aria-label={perfil.foto ? 'Cambiar la foto de perfil' : 'Subir una foto de perfil'}
        title={perfil.foto ? 'Cambiar la foto' : 'Subir una foto'}
      >
        <Avatar persona={perfil} tamano={72} />
        <span className="perfil-avatar-editar" aria-hidden="true">
          <IconoLapiz width={20} height={20} />
        </span>
      </button>

      {abierto && (
        <PanelDeFoto
          perfil={perfil}
          onGuardado={onGuardado}
          onCerrar={() => setAbierto(false)}
        />
      )}
    </>
  );
}

/** El panel donde se elige el archivo, se ve subir y se puede quitar. */
function PanelDeFoto({ perfil, onGuardado, onCerrar }) {
  const [subiendo, setSubiendo] = useState(false);
  const [avance, setAvance] = useState(0);
  const [error, setError] = useState(null);
  const [elegida, setElegida] = useState(null); // { archivo, url }
  const [quitando, setQuitando] = useState(false);
  const [arrastrando, setArrastrando] = useState(false);

  // La dirección temporal de la vista previa hay que soltarla, o el navegador
  // se queda con el archivo en memoria hasta que se recargue la página.
  useEffect(() => () => elegida && URL.revokeObjectURL(elegida.url), [elegida]);

  // Se cierra con Escape, como el resto de lo que se superpone. Mientras sube
  // no: cerrar a mitad de camino deja la subida sin a quién avisarle.
  useEffect(() => {
    const alTeclear = (e) => {
      if (e.key === 'Escape' && !subiendo) onCerrar();
    };
    window.addEventListener('keydown', alTeclear);
    return () => window.removeEventListener('keydown', alTeclear);
  }, [onCerrar, subiendo]);

  function tomar(archivo) {
    if (!archivo) return;
    // Lo mismo que comprueba el servidor mirando los bytes. Acá es para
    // avisar antes de mandar tres megas al pedo, no es el control.
    if (!FORMATOS_FOTO.some((f) => f.mime === archivo.type)) {
      setError('Solo se aceptan imágenes PNG o JPG.');
      return;
    }
    if (archivo.size > MAXIMO_FOTO_MB * 1024 * 1024) {
      setError(`La imagen pesa ${(archivo.size / 1024 / 1024).toFixed(1)} MB y el máximo es ${MAXIMO_FOTO_MB} MB.`);
      return;
    }
    setError(null);
    setElegida({ archivo, url: URL.createObjectURL(archivo) });
  }

  async function confirmar() {
    if (!elegida) return;
    setSubiendo(true);
    setAvance(0);
    setError(null);
    try {
      onGuardado(await subirMiFoto(elegida.archivo, setAvance));
      avisar('Foto actualizada.');
      onCerrar();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubiendo(false);
    }
  }

  async function quitar() {
    setQuitando(true);
    setError(null);
    try {
      onGuardado(await quitarMiFoto());
      avisar('Foto quitada.');
      onCerrar();
    } catch (err) {
      setError(err.message);
    } finally {
      setQuitando(false);
    }
  }

  const mostrada = elegida ? { ...perfil, foto: elegida.url } : perfil;

  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && !subiendo && onCerrar()}
      role="presentation"
    >
      <section className="correccion foto-panel" role="dialog" aria-modal="true" aria-label="Foto de perfil">
        <button
          type="button"
          className="correccion-cerrar"
          onClick={onCerrar}
          disabled={subiendo}
          aria-label="Cerrar"
        >
          <IconoCerrar width={18} height={18} />
        </button>

        <h3>{perfil.foto ? 'Cambiar la foto de perfil' : 'Subir una foto de perfil'}</h3>

        <div className="foto-panel-vista">
          <span className={subiendo ? 'perfil-avatar grande subiendo' : 'perfil-avatar grande'}>
            <Avatar persona={mostrada} tamano={120} />
            {subiendo && (
              <span className="perfil-foto-avance" style={{ '--avance': `${avance}%` }} />
            )}
          </span>
        </div>

        {/* La zona de arrastre es también la etiqueta del selector: el
            selector del navegador no se puede estilar, así que se esconde. */}
        <label
          className={arrastrando ? 'foto-zona arrastrando' : 'foto-zona'}
          onDragOver={(e) => {
            e.preventDefault();
            setArrastrando(true);
          }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArrastrando(false);
            tomar(e.dataTransfer.files?.[0]);
          }}
        >
          <input
            type="file"
            accept={ACEPTA}
            disabled={subiendo}
            onChange={(e) => {
              tomar(e.target.files?.[0]);
              e.target.value = ''; // para poder volver a elegir el mismo
            }}
          />
          <IconoSubir width={22} height={22} />
          <strong>{elegida ? elegida.archivo.name : 'Elegí una imagen o arrastrala acá'}</strong>
          <small>
            Se aceptan {FORMATOS_FOTO.map((f) => f.extension).join(' y ')}, hasta{' '}
            {MAXIMO_FOTO_MB} MB. No se aceptan GIF, WEBP ni SVG.
          </small>
        </label>

        {error && <p className="aviso-error">{error}</p>}

        <div className="editor-botones">
          {/* Eliminar la foto deja la silueta que da el campus. Va a la
              izquierda y separado de los otros dos: es lo único acá que
              deshace algo, y pegado a "Guardar" se toca sin querer. */}
          {perfil.foto && (
            <button
              type="button"
              className="boton-suave peligro"
              onClick={quitar}
              disabled={quitando || subiendo}
              title="Volver a la silueta que da el campus"
            >
              <IconoPapelera width={15} height={15} />
              {quitando ? 'Eliminando…' : 'Eliminar foto'}
            </button>
          )}

          {/* Con un archivo ya elegido, "Cancelar" cierra todo y se pierde la
              elección sin querer: primero se ofrece descartarla nomás. */}
          {elegida && (
            <button
              type="button"
              className="boton-suave"
              onClick={() => {
                URL.revokeObjectURL(elegida.url);
                setElegida(null);
                setError(null);
              }}
              disabled={subiendo}
            >
              Descartar
            </button>
          )}

          <button type="button" className="boton-suave" onClick={onCerrar} disabled={subiendo}>
            Cancelar
          </button>
          <button
            type="button"
            className="boton-principal"
            onClick={confirmar}
            disabled={!elegida || subiendo}
          >
            {subiendo ? `Subiendo… ${avance}%` : 'Guardar la foto'}
          </button>
        </div>
      </section>
    </div>
  );
}

function Acceso({ pendientes }) {
  const [acceso, setAcceso] = useState(null);
  const [cambiando, setCambiando] = useState(false);
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [trabajando, setTrabajando] = useState(false);
  const [aConfirmar, setAConfirmar] = useState(false);

  useEffect(() => {
    obtenerMiAcceso().then(setAcceso).catch(() => setAcceso(null));
  }, []);

  async function guardarContrasena(e) {
    e.preventDefault();
    if (nueva !== repetida) {
      avisar('Las dos contraseñas nuevas no coinciden.', 'error');
      return;
    }
    setTrabajando(true);
    try {
      await cambiarContrasena(actual, nueva);
      avisar('Contraseña cambiada.');
      setCambiando(false);
      setActual('');
      setNueva('');
      setRepetida('');
    } catch (error) {
      avisar(error.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

  async function cerrarTodo() {
    setTrabajando(true);
    try {
      await cerrarMisSesiones();
      avisar('Se cerraron todas las sesiones. Volvé a iniciar sesión.');
      setAConfirmar(false);
    } catch (error) {
      avisar(error.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

  // Sin Firebase configurado no hay nada que ofrecer
  if (acceso?.sinFirebase || acceso?.tieneAcceso === false) {
    return (
      <section className="bloque-ajustes">
        <h3>Acceso</h3>
        <p className="vacio">
          Tu cuenta todavía no tiene acceso con correo y contraseña. Lo crea la secretaría.
        </p>
      </section>
    );
  }

  return (
    <section className="bloque-ajustes">
      <h3>Acceso</h3>

      {/* ---------- La contraseña ---------- */}
      {!cambiando ? (
        <div className="fila-catalogo">
          <span className="fila-icono" aria-hidden="true">
            <IconoCandado width={18} height={18} />
          </span>
          <div className="fila-texto">
            <strong>Contraseña</strong>
            <small>Vas a necesitar tu contraseña actual para confirmar el cambio.</small>
          </div>
          <button type="button" className="boton-suave" onClick={() => setCambiando(true)}>
            Cambiar la contraseña
          </button>
        </div>
      ) : (
        <form className="editor-seccion" onSubmit={guardarContrasena}>
          <label>
            <span>Contraseña actual</span>
            <input
              type="password"
              value={actual}
              autoComplete="current-password"
              autoFocus
              onChange={(e) => setActual(e.target.value)}
            />
          </label>
          <div className="editor-fila">
            <label>
              <span>Contraseña nueva</span>
              <input
                type="password"
                value={nueva}
                autoComplete="new-password"
                onChange={(e) => setNueva(e.target.value)}
              />
            </label>
            <label>
              <span>Repetila</span>
              <input
                type="password"
                value={repetida}
                autoComplete="new-password"
                onChange={(e) => setRepetida(e.target.value)}
              />
            </label>
          </div>
          <small className="texto-suave">Al menos 6 caracteres.</small>
          <div className="editor-botones">
            <button
              type="button"
              className="boton-suave"
              onClick={() => setCambiando(false)}
              disabled={trabajando}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="boton-principal"
              disabled={trabajando || !actual || !nueva}
            >
              {trabajando ? 'Cambiando…' : 'Cambiar la contraseña'}
            </button>
          </div>
        </form>
      )}

      {/* ---------- Las sesiones ---------- */}
      <div className="fila-catalogo">
        <span className="fila-icono" aria-hidden="true">
          <IconoSalir width={18} height={18} />
        </span>
        <div className="fila-texto">
          <strong>Sesiones</strong>
          <small>
            {acceso?.ultimoIngreso
              ? `Último ingreso ${hace(cuando(acceso.ultimoIngreso))}`
              : 'Todavía no hay registro de ingresos.'}
            {acceso?.sesionesDesde
              ? ` · las sesiones abiertas valen desde ${hace(cuando(acceso.sesionesDesde))}`
              : ''}
          </small>
        </div>
        <button
          type="button"
          className="boton-suave peligro"
          onClick={() => setAConfirmar(true)}
          disabled={trabajando}
        >
          Cerrar sesión en todos los equipos
        </button>
      </div>


      {aConfirmar && (
        <Confirmacion
          titulo="¿Cerrar todas las sesiones?"
          mensaje={
            'Se cierran en todos los equipos, incluido este. Vas a tener que volver a ' +
            'iniciar sesión.'
          }
          textoConfirmar="Sí, cerrar todas"
          peligro
          trabajando={trabajando}
          onConfirmar={cerrarTodo}
          onCancelar={() => setAConfirmar(false)}
        />
      )}
    </section>
  );
}


/** Una asociación académica: carrera, sede, comisión y plan. */
export function TarjetaAsociacion({ asociacion, acciones }) {
  return (
    <article className={`asociacion ${asociacion.estado}`}>
      <header>
        <strong>{asociacion.carrera ?? 'Carrera sin asignar'}</strong>
        {asociacion.estado !== 'activa' && (
          <span className="estado-asociacion">{asociacion.estado}</span>
        )}
      </header>

      <dl>
        <div>
          <dt>Sede</dt>
          <dd>{asociacion.sede ?? '—'}</dd>
        </div>
        <div>
          <dt>Comisión</dt>
          <dd>{asociacion.comision ?? 'Sin asignar'}</dd>
        </div>
        <div>
          <dt>Plan</dt>
          <dd>{asociacion.plan ?? '—'}</dd>
        </div>
        {/* El legajo es el dato con el que la facultad te identifica: entre
            la comisión y el plan se perdía como uno más. Va destacado. */}
        <div className="dato-legajo">
          <dt>Legajo</dt>
          <dd>{asociacion.legajo ?? '—'}</dd>
        </div>
      </dl>

      {acciones}
    </article>
  );
}

export default function MiPerfil({ datos, onGuardado }) {
  const { perfil, pendientes } = datos;
  const [campos, setCampos] = useState({
    nombre: perfil.nombre ?? '',
    correo: perfil.correo ?? '',
    dni: perfil.dni ?? '',
    telefono: perfil.telefono ?? '',
    fechaNacimiento: paraElCampo(perfil.fechaNacimiento),
  });
  const [guardando, setGuardando] = useState(false);

  const estado = ESTADO_CUENTA[perfil.estadoCuenta] ?? ESTADO_CUENTA.activa;


  const cambio = (c) => setCampos((x) => ({ ...x, ...c }));
  const sinCambios =
    campos.nombre === (perfil.nombre ?? '') &&
    campos.correo === (perfil.correo ?? '') &&
    campos.dni === (perfil.dni ?? '') &&
    campos.telefono === (perfil.telefono ?? '') &&
    campos.fechaNacimiento === paraElCampo(perfil.fechaNacimiento);

  async function enviar(e) {
    e.preventDefault();
    setGuardando(true);
    try {
      const r = await guardarMiPerfil({
        ...campos,
        dni: campos.dni || null,
        telefono: campos.telefono || null,
        fechaNacimiento: campos.fechaNacimiento
          ? new Date(`${campos.fechaNacimiento}T12:00:00`).toISOString()
          : null,
      });
      onGuardado(r);
      avisar('Datos guardados.');
    } catch (err) {
      avisar(err.message, 'error');
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <section className="perfil-ficha">
        <FotoDePerfil perfil={perfil} onGuardado={onGuardado} />

        <div className="perfil-datos">
          <h2>{perfil.nombre}</h2>
          <div className="perfil-roles">
            {(perfil.roles ?? []).map((rol) => (
              <span key={rol} className="etiqueta-rol">
                {rol}
              </span>
            ))}
            <span className={`situacion ${estado.clase} chica`}>
              <IconoCheckCirculo width={13} height={13} />
              {estado.texto}
            </span>
          </div>
        </div>
      </section>

      <form className="editor-seccion" onSubmit={enviar}>
        <h3>Datos personales</h3>

        <div className="editor-fila">
          {/* Los tres de la identidad van bloqueados: los cambia la
              administración, no cada uno. */}
          <label className="campo-bloqueado">
            <span>
              Nombre y apellido <IconoCandado width={12} height={12} />
            </span>
            <input type="text" value={campos.nombre} readOnly disabled />
          </label>
          <label className="campo-bloqueado">
            <span>
              Correo electrónico <IconoCandado width={12} height={12} />
            </span>
            <input type="email" value={campos.correo} readOnly disabled />
          </label>
        </div>

        <div className="editor-fila">
          <label className="campo-bloqueado">
            <span>
              DNI <IconoCandado width={12} height={12} />
            </span>
            <input type="text" value={campos.dni || '—'} readOnly disabled />
          </label>
          <label>
            <span>Teléfono</span>
            <input
              type="tel"
              value={campos.telefono}
              maxLength={25}
              placeholder="3794 123456"
              onChange={(e) => cambio({ telefono: e.target.value })}
            />
          </label>
        </div>

        <label>
          <span>Fecha de nacimiento</span>
          <input
            type="date"
            value={campos.fechaNacimiento}
            onChange={(e) => cambio({ fechaNacimiento: e.target.value })}
          />
        </label>

        <p className="aviso-institucional">
          <IconoCandado width={16} height={16} />
          <span>
            <strong>Tus datos de identidad no son modificables.</strong> Si encontrás un error en
            tu nombre, correo electrónico o DNI, informalo a Secretaría Académica para su
            corrección. Desde este apartado solo podés actualizar tus datos de contacto.
          </span>
        </p>

        <div className="editor-botones">
          <button
            type="submit"
            className="boton-principal"
            disabled={guardando || sinCambios}
          >
            {guardando ? 'Guardando…' : 'Guardar cambios'}
          </button>
        </div>
      </form>

      <section className="bloque-ajustes">
        <h3>Mis carreras</h3>
        {perfil.asociaciones.length === 0 ? (
          <p className="vacio">
            Todavía no estás inscripto a ninguna carrera. La inscripción la hace la secretaría.
          </p>
        ) : (
          <div className="asociaciones">
            {perfil.asociaciones.map((a) => (
              <TarjetaAsociacion key={a.id} asociacion={a} />
            ))}
          </div>
        )}
      </section>

      <Acceso pendientes={pendientes} />
    </>
  );
}
