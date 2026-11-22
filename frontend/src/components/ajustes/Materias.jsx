// Las materias del plan de estudios, con sus correlatividades.
//
// Una materia es del **plan**, no de la comisión: el plan dice qué hay que
// cursar y en qué orden, y la comisión dice quién la dicta y cuándo. Por eso
// las correlatividades se administran acá.
//
// Lo que más importa de esta pantalla son las correlatividades, y por eso
// están separadas en dos: **para cursar** y **para rendir**. Un plan real
// pide cosas distintas para cada una —regular para cursar, aprobada para
// rendir el final— y con una sola lista no se podía expresar.

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  obtenerMaterias,
  crearMateria,
  editarMateria,
  borrarMateria,
} from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import Desplegable from '../Desplegable.jsx';
import Confirmacion from '../Confirmacion.jsx';
import {
  IconoMas,
  IconoBuscar,
  IconoLapiz,
  IconoPapelera,
  IconoCerrar,
  IconoAdvertencia,
} from '../Iconos.jsx';

const CUATRIMESTRES = [
  { valor: 1, nombre: '1.º cuatrimestre' },
  { valor: 2, nombre: '2.º cuatrimestre' },
  { valor: 3, nombre: 'Anual' },
];

const ORDENES = [
  { valor: '', nombre: 'Por año y cuatrimestre' },
  { valor: 'nombre', nombre: 'Por nombre' },
  { valor: 'codigo', nombre: 'Por código' },
  { valor: 'carrera', nombre: 'Por carrera' },
];

const POR_PAGINA = 15;

const nombreCuatrimestre = (n) =>
  CUATRIMESTRES.find((c) => c.valor === n)?.nombre ?? `${n}.º cuatrimestre`;

/** Un grupo de correlatividades: para cursar o para rendir. */
function Correlatividades({ titulo, ayuda, grupo, materias, condiciones, modos, onCambiar }) {
  const elegidas = grupo.requisitos.map((r) => r.materiaId);
  const disponibles = materias.filter((m) => !elegidas.includes(m.id));

  function agregar(id) {
    if (!id) return;
    onCambiar({
      ...grupo,
      requisitos: [...grupo.requisitos, { materiaId: Number(id), condicion: condiciones[0] }],
    });
  }

  function cambiarCondicion(materiaId, condicion) {
    onCambiar({
      ...grupo,
      requisitos: grupo.requisitos.map((r) =>
        r.materiaId === materiaId ? { ...r, condicion } : r
      ),
    });
  }

  function quitar(materiaId) {
    onCambiar({
      ...grupo,
      requisitos: grupo.requisitos.filter((r) => r.materiaId !== materiaId),
    });
  }

  return (
    <fieldset className="correlativas-grupo">
      <legend>{titulo}</legend>
      <p className="texto-suave">{ayuda}</p>

      {grupo.requisitos.length === 0 ? (
        <p className="vacio">Sin requisitos: se puede {titulo.toLowerCase()} sin nada previo.</p>
      ) : (
        <ul className="correlativas-lista">
          {grupo.requisitos.map((r) => {
            const m = materias.find((x) => x.id === r.materiaId);
            return (
              <li key={r.materiaId}>
                <span className="correlativa-nombre">
                  <strong>{m ? m.nombre : 'Materia desconocida'}</strong>
                  <small>{m?.codigo}</small>
                </span>
                <Desplegable
                  valor={r.condicion}
                  opciones={condiciones.map((x) => ({ valor: x, nombre: x }))}
                  onCambiar={(v) => cambiarCondicion(r.materiaId, v)}
                  etiqueta="Condición exigida"
                />
                <button
                  type="button"
                  className="correlativa-quitar"
                  onClick={() => quitar(r.materiaId)}
                  aria-label={`Quitar ${m?.nombre ?? 'la correlativa'}`}
                >
                  <IconoCerrar width={14} height={14} />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <div className="correlativas-pie">
        <Desplegable
          valor=""
          opciones={[
            { valor: '', nombre: 'Agregar una correlativa…' },
            ...disponibles.map((m) => ({ valor: m.id, nombre: `${m.codigo} · ${m.nombre}` })),
          ]}
          onCambiar={agregar}
          etiqueta="Agregar correlativa"
        />

        {/* El modo solo tiene sentido con más de una: con una sola, "todas" y
            "alguna" quieren decir lo mismo. */}
        {grupo.requisitos.length > 1 && (
          <Desplegable
            valor={grupo.modo}
            opciones={modos.map((m) => ({
              valor: m,
              nombre: m === 'todas' ? 'Hay que cumplirlas todas' : 'Alcanza con cumplir una',
            }))}
            onCambiar={(v) => onCambiar({ ...grupo, modo: v })}
            etiqueta="Cómo se cumplen"
          />
        )}
      </div>
    </fieldset>
  );
}

/** El formulario de alta y edición. */
function Formulario({ materia, catalogo, opciones, materias, onGuardar, onCerrar, trabajando }) {
  const [v, setV] = useState(() => ({
    nombre: materia?.nombre ?? '',
    codigo: materia?.codigo ?? '',
    descripcion: materia?.descripcion ?? '',
    carreraId: materia?.carreraId ?? '',
    planId: materia?.planId ?? '',
    anio: materia?.anio ?? 1,
    cuatrimestre: materia?.cuatrimestre ?? 1,
    cargaHoraria: materia?.cargaHoraria ?? '',
    modalidad: materia?.modalidad ?? opciones.modalidades[0],
    cupo: materia?.cupo ?? '',
    activa: materia?.activa ?? true,
    cursar: {
      modo: materia?.correlativas?.modo ?? 'todas',
      requisitos: (materia?.correlativas?.requisitos ?? []).map((r) => ({
        materiaId: r.id,
        condicion: r.condicion,
      })),
    },
    rendir: {
      modo: materia?.correlativasRendir?.modo ?? 'todas',
      requisitos: (materia?.correlativasRendir?.requisitos ?? []).map((r) => ({
        materiaId: r.id,
        condicion: r.condicion,
      })),
    },
  }));

  const cambio = (c) => setV((x) => ({ ...x, ...c }));

  // Los planes dependen de la carrera: mostrar todos obligaría a saber de
  // memoria cuál va con cuál.
  const planes = catalogo.planes.filter(
    (p) => p.activo && String(p.carreraId) === String(v.carreraId)
  );

  // Una correlativa tiene que ser del mismo plan, y nunca ella misma
  const candidatas = materias.filter(
    (m) => String(m.planId) === String(v.planId) && m.id !== materia?.id
  );

  const falta = !v.nombre.trim() || !v.codigo.trim() || !v.carreraId || !v.planId;

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
            nombre: v.nombre.trim(),
            codigo: v.codigo.trim(),
            descripcion: v.descripcion.trim() || null,
            carreraId: Number(v.carreraId),
            planId: Number(v.planId),
            anio: Number(v.anio),
            cuatrimestre: Number(v.cuatrimestre),
            cargaHoraria: v.cargaHoraria === '' ? null : Number(v.cargaHoraria),
            modalidad: v.modalidad,
            cupo: v.cupo === '' ? null : Number(v.cupo),
            activa: v.activa,
            correlativas: { cursar: v.cursar, rendir: v.rendir },
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

        <h3>{materia ? 'Editar la materia' : 'Nueva materia'}</h3>

        <div className="editor-fila">
          <label>
            <span>Nombre *</span>
            <input
              type="text"
              value={v.nombre}
              maxLength={150}
              autoFocus
              placeholder="Programación II"
              onChange={(e) => cambio({ nombre: e.target.value })}
            />
          </label>
          <label>
            <span>Código *</span>
            <input
              type="text"
              value={v.codigo}
              maxLength={20}
              placeholder="PROG-2"
              onChange={(e) => cambio({ codigo: e.target.value })}
            />
          </label>
        </div>

        <label>
          <span>
            Descripción <small>opcional</small>
          </span>
          <textarea
            rows={2}
            value={v.descripcion}
            maxLength={600}
            placeholder="De qué trata la materia"
            onChange={(e) => cambio({ descripcion: e.target.value })}
          />
        </label>

        <div className="editor-fila">
          <label>
            <span>Carrera *</span>
            <Desplegable
              valor={String(v.carreraId)}
              opciones={[
                { valor: '', nombre: 'Elegí la carrera' },
                ...catalogo.carreras
                  .filter((c) => c.activa)
                  .map((c) => ({ valor: String(c.id), nombre: c.nombre })),
              ]}
              onCambiar={(x) => cambio({ carreraId: x, planId: '' })}
              etiqueta="Carrera"
            />
          </label>
          <label>
            <span>Plan de estudio *</span>
            <Desplegable
              valor={String(v.planId)}
              opciones={[
                { valor: '', nombre: v.carreraId ? 'Elegí el plan' : 'Elegí antes la carrera' },
                ...planes.map((p) => ({ valor: String(p.id), nombre: p.nombre })),
              ]}
              onCambiar={(x) => cambio({ planId: x })}
              etiqueta="Plan de estudio"
            />
          </label>
        </div>

        <div className="editor-fila">
          <label>
            <span>Año de cursado</span>
            <Desplegable
              valor={String(v.anio)}
              opciones={[1, 2, 3, 4, 5, 6, 7].map((n) => ({
                valor: String(n),
                nombre: `${n}.º año`,
              }))}
              onCambiar={(x) => cambio({ anio: x })}
              etiqueta="Año"
            />
          </label>
          <label>
            <span>Período</span>
            <Desplegable
              valor={String(v.cuatrimestre)}
              opciones={CUATRIMESTRES.map((x) => ({ valor: String(x.valor), nombre: x.nombre }))}
              onCambiar={(x) => cambio({ cuatrimestre: x })}
              etiqueta="Período"
            />
          </label>
        </div>

        <div className="editor-fila">
          <label>
            <span>
              Carga horaria <small>opcional</small>
            </span>
            <input
              type="number"
              min={1}
              max={1000}
              value={v.cargaHoraria}
              placeholder="96"
              onChange={(e) => cambio({ cargaHoraria: e.target.value })}
            />
          </label>
          <label>
            <span>Modalidad</span>
            <Desplegable
              valor={v.modalidad}
              opciones={opciones.modalidades.map((m) => ({ valor: m, nombre: m }))}
              onCambiar={(x) => cambio({ modalidad: x })}
              etiqueta="Modalidad"
            />
          </label>
        </div>

        <div className="editor-fila">
          <label>
            <span>
              Cupo <small>vacío = sin límite</small>
            </span>
            <input
              type="number"
              placeholder="Sin límite"
              min={1}
              max={1000}
              value={v.cupo}
              onChange={(e) => cambio({ cupo: e.target.value })}
            />
          </label>
          {/* La clase va en el input: `.interruptor` es la casilla dibujada a
              mano, no una caja que la envuelva. Y una etiqueta dentro de otra
              no es HTML válido: el clic no sabría a cuál de las dos responde. */}
          <label className="campo-interruptor">
            <span>Estado</span>
            <span className="interruptor-fila">
              <input
                type="checkbox"
                className="interruptor"
                checked={v.activa}
                onChange={(e) => cambio({ activa: e.target.checked })}
              />
              <span className="interruptor-texto">{v.activa ? 'Activa' : 'Inactiva'}</span>
            </span>
          </label>
        </div>

        {/* ---------- Correlatividades ---------- */}
        {v.planId ? (
          <>
            <Correlatividades
              titulo="Para cursar"
              ayuda="Qué tiene que tener el estudiante antes de poder inscribirse a cursarla."
              grupo={v.cursar}
              materias={candidatas}
              condiciones={opciones.condiciones}
              modos={opciones.modos}
              onCambiar={(g) => cambio({ cursar: g })}
            />
            <Correlatividades
              titulo="Para rendir el final"
              ayuda="Lo habitual es pedir aprobada la materia que para cursar alcanzaba con tener regular."
              grupo={v.rendir}
              materias={candidatas}
              condiciones={opciones.condiciones}
              modos={opciones.modos}
              onCambiar={(g) => cambio({ rendir: g })}
            />
          </>
        ) : (
          <p className="nota-bloque">
            <IconoAdvertencia width={14} height={14} />
            Elegí la carrera y el plan para poder cargar las correlatividades: solo pueden ser
            materias del mismo plan.
          </p>
        )}

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={trabajando}>
            Cancelar
          </button>
          <button type="submit" className="boton-principal" disabled={trabajando || falta}>
            {materia ? 'Guardar cambios' : 'Crear la materia'}
          </button>
        </div>
      </form>
    </div>
  );
}

/** La ficha completa de una materia. */
function Detalle({ materia, onCerrar, onEditar }) {
  const a = materia.actividad;
  return (
    <div
      className="correccion-fondo"
      onClick={(e) => e.target === e.currentTarget && onCerrar()}
      role="presentation"
    >
      <section className="correccion ancha" role="dialog" aria-modal="true">
        <button type="button" className="correccion-cerrar" onClick={onCerrar} aria-label="Cerrar">
          <IconoCerrar width={18} height={18} />
        </button>

        <h3>{materia.nombre}</h3>
        <p className="correccion-trabajo">
          {materia.codigo} · {materia.carrera} · {materia.plan}
        </p>

        {materia.descripcion && <p className="movimiento-detalle">{materia.descripcion}</p>}

        <div className="movimiento-datos">
          <div className="movimiento-dato">
            <span>Año</span>
            <strong>{materia.anio}.º</strong>
          </div>
          <div className="movimiento-dato">
            <span>Período</span>
            <strong>{nombreCuatrimestre(materia.cuatrimestre)}</strong>
          </div>
          <div className="movimiento-dato">
            <span>Carga horaria</span>
            <strong>{materia.cargaHoraria ? `${materia.cargaHoraria} h` : '—'}</strong>
          </div>
          <div className="movimiento-dato">
            <span>Modalidad</span>
            <strong>{materia.modalidad ?? '—'}</strong>
          </div>
          <div className="movimiento-dato">
            <span>Cupo</span>
            <strong>{materia.cupo ?? 'Sin límite'}</strong>
          </div>
          <div className="movimiento-dato">
            <span>Estudiantes inscriptos</span>
            <strong>{a.inscriptos}</strong>
          </div>
        </div>

        <div className="movimiento-cambio">
          <div>
            <h4>Para cursar</h4>
            {materia.correlativas.requisitos.length === 0 ? (
              <p className="texto-suave">Sin requisitos.</p>
            ) : (
              <ul className="movimiento-valores">
                {materia.correlativas.requisitos.map((r) => (
                  <li key={r.id}>
                    <span>{r.codigo}</span>
                    <strong>
                      {r.nombre} · {r.condicion}
                    </strong>
                  </li>
                ))}
              </ul>
            )}
            {materia.correlativas.requisitos.length > 1 && (
              <small className="texto-suave">
                {materia.correlativas.modo === 'todas' ? 'Todas' : 'Alcanza con una'}
              </small>
            )}
          </div>
          <div>
            <h4>Para rendir</h4>
            {materia.correlativasRendir.requisitos.length === 0 ? (
              <p className="texto-suave">Sin requisitos.</p>
            ) : (
              <ul className="movimiento-valores">
                {materia.correlativasRendir.requisitos.map((r) => (
                  <li key={r.id}>
                    <span>{r.codigo}</span>
                    <strong>
                      {r.nombre} · {r.condicion}
                    </strong>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <h4 className="panel-titulo">Dónde se dicta</h4>
        {materia.comisiones.length === 0 ? (
          <p className="vacio">Todavía no se dicta en ninguna comisión.</p>
        ) : (
          <ul className="catalogo">
            {materia.comisiones.map((c) => (
              <li key={c.id} className="fila-catalogo">
                <div className="fila-texto">
                  <strong>{c.nombre}</strong>
                  <small>
                    {c.turno ? `Turno ${c.turno} · ` : ''}
                    {c.docentes.length > 0 ? c.docentes.join(' · ') : 'Sin docente asignado'}
                  </small>
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar}>
            Cerrar
          </button>
          {onEditar && (
            <button type="button" className="boton-principal" onClick={onEditar}>
              Editar la materia
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

export default function Materias({ catalogo }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [escrito, setEscrito] = useState('');
  const [filtros, setFiltros] = useState({
    q: '',
    carreraId: '',
    planId: '',
    anio: '',
    estado: '',
    orden: '',
  });
  const [pagina, setPagina] = useState(1);
  const [formulario, setFormulario] = useState(null);
  const [viendo, setViendo] = useState(null);
  const [aBorrar, setABorrar] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  // Se espera a que pare de teclear, como en la Biblioteca
  useEffect(() => {
    const reloj = setTimeout(() => {
      setFiltros((f) => (f.q === escrito ? f : { ...f, q: escrito }));
      setPagina(1);
    }, 350);
    return () => clearTimeout(reloj);
  }, [escrito]);

  const traer = useCallback(() => {
    obtenerMaterias(filtros)
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, [filtros]);

  useEffect(traer, [traer]);

  async function accionar(accion, exito) {
    setTrabajando(true);
    try {
      await accion();
      setFormulario(null);
      setABorrar(null);
      setViendo(null);
      traer();
      avisar(exito);
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

  function cambiarFiltro(campo, valor) {
    setFiltros((f) => ({ ...f, [campo]: valor, ...(campo === 'carreraId' ? { planId: '' } : {}) }));
    setPagina(1);
  }

  const hayFiltros = useMemo(
    () => Object.values(filtros).some(Boolean) || Boolean(escrito),
    [filtros, escrito]
  );

  if (error) return <p className="aviso-error">{error}</p>;
  if (!datos) return <p className="texto-suave">Cargando…</p>;

  const todas = datos.materias;
  const paginas = Math.max(1, Math.ceil(todas.length / POR_PAGINA));
  const visibles = todas.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA);

  const planes = catalogo.planes.filter(
    (p) => !filtros.carreraId || String(p.carreraId) === filtros.carreraId
  );

  return (
    <>
      <div className="filtros-plan">
        <label className="barra-busqueda">
          <IconoBuscar />
          <input
            type="search"
            value={escrito}
            placeholder="Buscar por nombre o código"
            onChange={(e) => setEscrito(e.target.value)}
          />
        </label>

        <Desplegable
          valor={filtros.carreraId}
          opciones={[
            { valor: '', nombre: 'Todas las carreras' },
            ...catalogo.carreras.map((c) => ({ valor: String(c.id), nombre: c.nombre })),
          ]}
          onCambiar={(v) => cambiarFiltro('carreraId', v)}
          etiqueta="Carrera"
        />
        <Desplegable
          valor={filtros.planId}
          opciones={[
            { valor: '', nombre: 'Todos los planes' },
            ...planes.map((p) => ({ valor: String(p.id), nombre: p.nombre })),
          ]}
          onCambiar={(v) => cambiarFiltro('planId', v)}
          etiqueta="Plan"
        />
        <Desplegable
          valor={filtros.anio}
          opciones={[
            { valor: '', nombre: 'Todos los años' },
            ...[1, 2, 3, 4, 5, 6, 7].map((n) => ({ valor: String(n), nombre: `${n}.º año` })),
          ]}
          onCambiar={(v) => cambiarFiltro('anio', v)}
          etiqueta="Año"
        />
        <Desplegable
          valor={filtros.estado}
          opciones={[
            { valor: '', nombre: 'Activas e inactivas' },
            { valor: 'activas', nombre: 'Solo activas' },
            { valor: 'inactivas', nombre: 'Solo inactivas' },
          ]}
          onCambiar={(v) => cambiarFiltro('estado', v)}
          etiqueta="Estado"
        />
        <Desplegable
          valor={filtros.orden}
          opciones={ORDENES}
          onCambiar={(v) => cambiarFiltro('orden', v)}
          etiqueta="Ordenar"
        />

        {hayFiltros && (
          <button
            type="button"
            className="boton-suave"
            onClick={() => {
              setFiltros({ q: '', carreraId: '', planId: '', anio: '', estado: '', orden: '' });
              setEscrito('');
            }}
          >
            Limpiar filtros
          </button>
        )}

        {datos.puedeAdministrar && (
          <button
            type="button"
            className="boton-principal"
            onClick={() => setFormulario({ materia: null })}
          >
            <IconoMas width={16} height={16} />
            Nueva materia
          </button>
        )}
      </div>

      {todas.length === 0 ? (
        <p className="vacio">
          {hayFiltros
            ? 'Ninguna materia coincide con los filtros.'
            : 'Todavía no hay materias cargadas. Creá la primera con «Nueva materia».'}
        </p>
      ) : (
        <div className="tabla-auditoria-caja">
          <table className="tabla-auditoria tabla-materias">
            <thead>
              <tr>
                <th>Materia</th>
                <th>Carrera y plan</th>
                <th>Año</th>
                <th>Horas</th>
                <th>Correlativas</th>
                <th>Estado</th>
                <th><span className="oculto">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((m) => (
                <tr key={m.id} className={m.activa ? undefined : 'inactiva'}>
                  <td>
                    <button
                      type="button"
                      className="materia-nombre"
                      onClick={() => setViendo(m)}
                      title="Ver la ficha"
                    >
                      <strong>{m.nombre}</strong>
                      <small className="texto-suave">{m.codigo}</small>
                    </button>
                  </td>
                  <td>
                    {m.carrera ?? '—'}
                    <small className="texto-suave">{m.plan ?? 'Sin plan'}</small>
                  </td>
                  <td>
                    {m.anio}.º
                    <small className="texto-suave">{nombreCuatrimestre(m.cuatrimestre)}</small>
                  </td>
                  <td>{m.cargaHoraria ? `${m.cargaHoraria} h` : '—'}</td>
                  <td>
                    {m.correlativas.requisitos.length + m.correlativasRendir.requisitos.length === 0
                      ? '—'
                      : `${m.correlativas.requisitos.length} para cursar · ${m.correlativasRendir.requisitos.length} para rendir`}
                  </td>
                  <td>
                    <span className={`resultado ${m.activa ? 'exito' : 'fallo'}`}>
                      {m.activa ? 'Activa' : 'Inactiva'}
                    </span>
                  </td>
                  <td>
                    {datos.puedeAdministrar && (
                      <span className="acciones-editor">
                        <button
                          type="button"
                          onClick={() => setFormulario({ materia: m })}
                          title="Editar"
                          aria-label={`Editar ${m.nombre}`}
                        >
                          <IconoLapiz width={14} height={14} />
                        </button>
                        <button
                          type="button"
                          className="peligro"
                          onClick={() => setABorrar(m)}
                          title="Dar de baja o eliminar"
                          aria-label={`Dar de baja ${m.nombre}`}
                        >
                          <IconoPapelera width={14} height={14} />
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {paginas > 1 && (
        <div className="biblioteca-paginas">
          <button
            type="button"
            className="boton-suave"
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
            disabled={pagina <= 1}
          >
            Anterior
          </button>
          <span className="texto-suave">
            Página {pagina} de {paginas} · {todas.length} materias
          </span>
          <button
            type="button"
            className="boton-suave"
            onClick={() => setPagina((p) => Math.min(paginas, p + 1))}
            disabled={pagina >= paginas}
          >
            Siguiente
          </button>
        </div>
      )}

      {viendo && (
        <Detalle
          materia={viendo}
          onCerrar={() => setViendo(null)}
          onEditar={
            datos.puedeAdministrar
              ? () => {
                setFormulario({ materia: viendo });
                setViendo(null);
              }
              : null
          }
        />
      )}

      {formulario && (
        <Formulario
          materia={formulario.materia}
          catalogo={catalogo}
          opciones={datos}
          materias={todas}
          trabajando={trabajando}
          onCerrar={() => setFormulario(null)}
          onGuardar={(valores) =>
            accionar(
              () =>
                formulario.materia
                  ? editarMateria(formulario.materia.id, valores)
                  : crearMateria(valores),
              formulario.materia ? 'Materia actualizada.' : 'Materia creada.'
            )
          }
        />
      )}

      {aBorrar && (
        <Confirmacion
          titulo="¿Qué hacemos con esta materia?"
          mensaje={
            aBorrar.actividad.inscriptos ||
              aBorrar.actividad.historial ||
              aBorrar.actividad.mesas ||
              aBorrar.actividad.dictados ||
              aBorrar.actividad.esCorrelativaDe.length
              ? 'Tiene actividad académica, así que no se elimina: queda inactiva. Deja de ofrecerse para nuevas inscripciones, pero los historiales, las actas y las correlatividades que la mencionan siguen en pie.'
              : 'No tiene ninguna actividad todavía, así que se elimina del todo.'
          }
          detalles={[
            { etiqueta: 'Materia', valor: `${aBorrar.codigo} · ${aBorrar.nombre}` },
            { etiqueta: 'Inscriptos', valor: String(aBorrar.actividad.inscriptos) },
            {
              etiqueta: 'Es correlativa de',
              valor: aBorrar.actividad.esCorrelativaDe.join(', ') || 'ninguna',
            },
          ]}
          textoConfirmar="Sí, continuar"
          peligro
          trabajando={trabajando}
          onConfirmar={() => accionar(() => borrarMateria(aBorrar.id), 'Listo.')}
          onCancelar={() => setABorrar(null)}
        />
      )}
    </>
  );
}
