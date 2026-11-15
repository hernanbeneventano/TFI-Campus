// La distribución de estudiantes dentro de la estructura.
//
// Es lo del supervisor: toma la estructura que armó el administrador y
// ubica a cada estudiante —carrera, sede, comisión y plan—. No crea nada
// nuevo: solo elige entre lo que ya existe.
//
// Arriba van los que están en una carrera pero **sin comisión**: son los que
// hay que ubicar, y si no se destacan se pierden entre los demás.

import { useCallback, useEffect, useState } from 'react';
import {
  obtenerAsignaciones,
  crearAsignacion,
  editarAsignacion,
  obtenerUsuarios,
} from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import { TarjetaAsociacion } from './MiPerfil.jsx';
import Desplegable from '../Desplegable.jsx';
import { IconoMas, IconoLapiz, IconoCerrar, IconoBuscar } from '../Iconos.jsx';

function Formulario({ catalogo, estudiantes, asignacion, onGuardar, onCerrar, trabajando }) {
  const editando = Boolean(asignacion);
  const [v, setV] = useState({
    personaId: asignacion?.personaId ?? '',
    carreraId: asignacion?.carreraId ?? '',
    sedeId: asignacion?.sedeId ?? '',
    comisionId: asignacion?.comisionId ?? '',
    planId: asignacion?.planId ?? '',
    legajo: asignacion?.legajo ?? '',
  });

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !trabajando) onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    return () => window.removeEventListener('keydown', alTeclado);
  }, [onCerrar, trabajando]);

  const cambio = (c) => setV((x) => ({ ...x, ...c }));

  // Los planes y las comisiones dependen de la carrera elegida: mostrar
  // todos obligaría al supervisor a saber de memoria cuál va con cuál.
  const planes = catalogo.planes.filter(
    (p) => p.activo && String(p.carreraId) === String(v.carreraId)
  );
  const comisiones = catalogo.comisiones.filter(
    (c) =>
      c.activa &&
      String(c.carreraId) === String(v.carreraId) &&
      (!v.sedeId || String(c.sedeId) === String(v.sedeId))
  );

  const falta = !v.personaId || !v.carreraId || !v.sedeId || !v.planId;

  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && !trabajando && onCerrar()}
      role="presentation"
    >
      <form
        className="correccion ancha"
        role="dialog"
        aria-modal="true"
        onSubmit={(e) => {
          e.preventDefault();
          onGuardar({
            ...v,
            personaId: Number(v.personaId),
            carreraId: Number(v.carreraId),
            sedeId: Number(v.sedeId),
            planId: Number(v.planId),
            comisionId: v.comisionId ? Number(v.comisionId) : null,
            legajo: v.legajo || null,
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

        <h3>{editando ? 'Cambiar la asignación' : 'Inscribir a un estudiante'}</h3>
        {editando && (
          <p className="correccion-trabajo">
            {asignacion.nombre} · {asignacion.carrera}
          </p>
        )}

        {!editando && (
          <label>
            <span>Estudiante</span>
            <select
              value={v.personaId}
              autoFocus
              onChange={(e) => cambio({ personaId: e.target.value })}
            >
              <option value="">Elegí un estudiante</option>
              {estudiantes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
          </label>
        )}

        {!editando && (
          <div className="editor-fila">
            <label>
              <span>Carrera</span>
              <select
                value={v.carreraId}
                onChange={(e) =>
                  cambio({ carreraId: e.target.value, planId: '', comisionId: '' })
                }
              >
                <option value="">Elegí una carrera</option>
                {catalogo.carreras
                  .filter((c) => c.activa)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              <span>Sede</span>
              <select
                value={v.sedeId}
                onChange={(e) => cambio({ sedeId: e.target.value, comisionId: '' })}
              >
                <option value="">Elegí una sede</option>
                {catalogo.sedes
                  .filter((s) => s.activa)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.nombre}
                    </option>
                  ))}
              </select>
            </label>
          </div>
        )}

        <div className="editor-fila">
          <label>
            <span>
              Comisión <small>se puede asignar después</small>
            </span>
            <select
              value={v.comisionId ?? ''}
              onChange={(e) => cambio({ comisionId: e.target.value })}
            >
              <option value="">Sin asignar</option>
              {comisiones.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre} · {c.sede}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Plan de estudio</span>
            <select value={v.planId} onChange={(e) => cambio({ planId: e.target.value })}>
              <option value="">Elegí un plan</option>
              {planes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label>
          <span>
            Legajo <small>opcional</small>
          </span>
          <input
            type="text"
            value={v.legajo}
            maxLength={40}
            placeholder="SIS-2026-0042"
            onChange={(e) => cambio({ legajo: e.target.value })}
          />
        </label>

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={trabajando}>
            Cancelar
          </button>
          <button type="submit" className="boton-principal" disabled={trabajando || falta}>
            {editando ? 'Guardar' : 'Inscribir'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Estudiantes({ catalogo }) {
  const [datos, setDatos] = useState(null);
  const [estudiantes, setEstudiantes] = useState([]);
  const [formulario, setFormulario] = useState(null);
  const [filtros, setFiltros] = useState({ carreraId: '', sedeId: '', comisionId: '' });
  // Lo que se escribe se separa de lo que se busca, como en la Biblioteca:
  // la consulta sale recién cuando dejás de teclear.
  const [escrito, setEscrito] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const reloj = setTimeout(() => setBusqueda(escrito.trim()), 350);
    return () => clearTimeout(reloj);
  }, [escrito]);

  const traer = useCallback(() => {
    const pedido = {};
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor) pedido[clave] = Number(valor);
    }
    if (busqueda) pedido.q = busqueda;

    obtenerAsignaciones(pedido)
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, [filtros, busqueda]);

  useEffect(traer, [traer]);

  // Elegir una carrera o una sede borra lo que ya no corresponde: una
  // comisión de otra carrera dejaría la lista vacía sin motivo aparente.
  function cambiarFiltro(cambio) {
    setFiltros((f) => {
      const nuevo = { ...f, ...cambio };
      if ('carreraId' in cambio) nuevo.comisionId = '';
      if ('sedeId' in cambio) nuevo.comisionId = '';
      return nuevo;
    });
  }

  useEffect(() => {
    obtenerUsuarios({ rol: 'Estudiante' })
      .then((r) => setEstudiantes(r.usuarios))
      .catch(() => setEstudiantes([]));
  }, []);

  async function guardar(valores) {
    setTrabajando(true);
    try {
      if (formulario.asignacion) {
        await editarAsignacion(formulario.asignacion.id, valores);
        avisar('Asignación actualizada.');
      } else {
        await crearAsignacion(valores);
        avisar('Estudiante inscripto.');
      }
      setFormulario(null);
      traer();
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  const sinComision = datos.asignaciones.filter((a) => !a.comisionId);
  const conComision = datos.asignaciones.filter((a) => a.comisionId);

  // Solo las comisiones que pueden tener gente con los otros filtros puestos
  const comisionesPosibles = catalogo.comisiones.filter(
    (c) =>
      c.activa &&
      (!filtros.carreraId || String(c.carreraId) === filtros.carreraId) &&
      (!filtros.sedeId || String(c.sedeId) === filtros.sedeId)
  );

  const hayFiltros = Boolean(
    filtros.carreraId || filtros.sedeId || filtros.comisionId || escrito
  );

  return (
    <>
      <div className="filtros-plan">
        <label className="barra-busqueda">
          <IconoBuscar />
          <input
            type="search"
            value={escrito}
            placeholder="Buscar por nombre, correo o legajo"
            onChange={(e) => setEscrito(e.target.value)}
          />
        </label>

        <Desplegable
          valor={filtros.carreraId}
          opciones={[
            { valor: '', nombre: 'Todas las carreras' },
            ...catalogo.carreras
              .filter((c) => c.activa)
              .map((c) => ({ valor: String(c.id), nombre: c.nombre })),
          ]}
          onCambiar={(v) => cambiarFiltro({ carreraId: v })}
          etiqueta="Carrera"
        />

        <Desplegable
          valor={filtros.sedeId}
          opciones={[
            { valor: '', nombre: 'Todas las sedes' },
            ...catalogo.sedes
              .filter((s) => s.activa)
              .map((s) => ({ valor: String(s.id), nombre: s.nombre })),
          ]}
          onCambiar={(v) => cambiarFiltro({ sedeId: v })}
          etiqueta="Sede"
        />

        <Desplegable
          valor={filtros.comisionId}
          opciones={[
            { valor: '', nombre: 'Todas las comisiones' },
            ...comisionesPosibles.map((c) => ({ valor: String(c.id), nombre: c.nombre })),
          ]}
          onCambiar={(v) => cambiarFiltro({ comisionId: v })}
          etiqueta="Comisión"
        />

        {hayFiltros && (
          <button
            type="button"
            className="boton-suave"
            onClick={() => {
              setFiltros({ carreraId: '', sedeId: '', comisionId: '' });
              setEscrito('');
            }}
          >
            Limpiar filtros
          </button>
        )}

        <button
          type="button"
          className="boton-principal"
          onClick={() => setFormulario({ asignacion: null })}
        >
          <IconoMas width={16} height={16} />
          Inscribir a un estudiante
        </button>
      </div>

      {sinComision.length > 0 && (
        <section className="bloque-ajustes">
          <h3>
            Sin comisión <small>{sinComision.length}</small>
          </h3>
          <div className="asociaciones">
            {sinComision.map((a) => (
              <TarjetaAsociacion
                key={a.id}
                asociacion={{ ...a, carrera: `${a.nombre} · ${a.carrera}` }}
                acciones={
                  <button
                    type="button"
                    className="boton-principal"
                    onClick={() => setFormulario({ asignacion: a })}
                  >
                    Asignar comisión
                  </button>
                }
              />
            ))}
          </div>
        </section>
      )}

      <section className="bloque-ajustes">
        <h3>
          Estudiantes <small>{conComision.length}</small>
        </h3>
        {conComision.length === 0 ? (
          <p className="vacio">No hay estudiantes asignados con ese filtro.</p>
        ) : (
          <ul className="catalogo">
            {conComision.map((a) => (
              <li key={a.id} className="fila-catalogo">
                <div className="fila-texto">
                  <strong>{a.nombre}</strong>
                  <small>
                    {a.carrera} · {a.comision} · {a.sede} · {a.plan}
                  </small>
                  {a.legajo && <small className="fila-baja">Legajo {a.legajo}</small>}
                </div>
                <span className="acciones-editor">
                  <button
                    type="button"
                    onClick={() => setFormulario({ asignacion: a })}
                    title="Cambiar de comisión o de plan"
                    aria-label={`Cambiar la asignación de ${a.nombre}`}
                  >
                    <IconoLapiz width={14} height={14} />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {formulario && (
        <Formulario
          catalogo={catalogo}
          estudiantes={estudiantes}
          asignacion={formulario.asignacion}
          trabajando={trabajando}
          onGuardar={guardar}
          onCerrar={() => setFormulario(null)}
        />
      )}
    </>
  );
}
