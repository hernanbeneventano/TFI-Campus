// Mis datos y mis carreras.
//
// Lo que uno edita de sí mismo son los datos de contacto. Los roles y el
// estado de la cuenta se muestran, pero no se tocan: si cada uno pudiera
// darse el rol que quiera, los permisos del campus no significarían nada.
// Eso no es una decisión de esta pantalla —el servidor rechaza el intento—,
// pero conviene que se vea por qué están en gris.

import { useState } from 'react';
import { guardarMiPerfil } from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import { hace, fechaLarga } from '../../services/fechas.js';
import {
  IconoEstudiante,
  IconoUsuario,
  IconoCandado,
  IconoCheckCirculo,
} from '../Iconos.jsx';

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
        <div>
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

  const Avatar = perfil.roles?.includes('Estudiante') ? IconoEstudiante : IconoUsuario;
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
        <span className="perfil-avatar">
          <Avatar />
        </span>

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
          <p>
            {perfil.correo}
            {perfil.creada && <> · cuenta creada el {fechaLarga(perfil.creada)}</>}
            {perfil.ultimoAcceso && <> · último acceso {hace(perfil.ultimoAcceso)}</>}
          </p>
        </div>
      </section>

      <form className="editor-seccion" onSubmit={enviar}>
        <h3>Datos personales</h3>

        <div className="editor-fila">
          <label>
            <span>Nombre y apellido</span>
            <input
              type="text"
              value={campos.nombre}
              maxLength={120}
              onChange={(e) => cambio({ nombre: e.target.value })}
            />
          </label>
          {/* El correo no se edita: es con el que se entra al campus. Si se
              cambiara acá, la cuenta de Firebase seguiría con el viejo y el
              campus dejaría de reconocer a la persona. Lo cambia la
              secretaría, y el servidor rechaza el intento igual. */}
          <label>
            <span>Correo electrónico</span>
            <input type="email" value={campos.correo} readOnly disabled />
            <small className="texto-suave">
              Es con el que iniciás sesión. Si está mal, avisale a la secretaría.
            </small>
          </label>
        </div>

        <div className="editor-fila">
          <label>
            <span>
              DNI <small>sin puntos</small>
            </span>
            <input
              type="text"
              value={campos.dni}
              maxLength={10}
              placeholder="40123456"
              onChange={(e) => cambio({ dni: e.target.value })}
            />
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

      <section className="bloque-ajustes">
        <h3>Acceso</h3>
        <ul className="pendientes">
          {Object.entries(pendientes).map(([clave, texto]) => (
            <li key={clave}>
              <IconoCandado width={15} height={15} />
              <div>
                <strong>
                  {clave === 'contrasena'
                    ? 'Cambiar la contraseña'
                    : clave === 'sesiones'
                      ? 'Sesiones activas'
                      : 'Foto de perfil'}
                </strong>
                <small>{texto}</small>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
