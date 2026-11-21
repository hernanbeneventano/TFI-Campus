// La estructura académica: carreras, sedes, planes y comisiones.
//
// Es lo que construye el administrador y sobre lo que después trabaja todo
// el campus. Nada viene cargado de fábrica: lo que se ve acá lo creó alguien
// desde esta misma pantalla.
//
// Las cuatro listas se ven y se editan igual —misma tarjeta, mismo
// formulario, mismos botones—, así que comparten un componente en vez de
// repetirse cuatro veces con diferencias de detalle.

import { useMemo, useState } from 'react';
import {
  crearCarrera, editarCarrera, borrarCarrera,
  crearSede, editarSede, borrarSede,
  crearPlan, editarPlan, borrarPlan,
  crearComision, editarComision, borrarComision,
} from '../../services/api.js';
import { avisar } from '../../services/avisos.js';
import Confirmacion from '../Confirmacion.jsx';
import Comision from './Comision.jsx';
import Materias from './Materias.jsx';
import { IconoMas, IconoLapiz, IconoPapelera } from '../Iconos.jsx';

function Fila({ titulo, detalle, usos, activo, onEditar, onBorrar, extra }) {
  return (
    <li className={activo ? 'fila-catalogo' : 'fila-catalogo inactiva'}>
      <div className="fila-texto">
        <strong>{titulo}</strong>
        {detalle && <small>{detalle}</small>}
        {!activo && <small className="fila-baja">Dada de baja</small>}
      </div>

      {usos && <span className="fila-usos">{usos}</span>}

      {extra}

      <span className="acciones-editor">
        <button type="button" onClick={onEditar} title="Editar" aria-label={`Editar ${titulo}`}>
          <IconoLapiz width={14} height={14} />
        </button>
        <button
          type="button"
          className="peligro"
          onClick={onBorrar}
          title="Dar de baja"
          aria-label={`Dar de baja ${titulo}`}
        >
          <IconoPapelera width={14} height={14} />
        </button>
      </span>
    </li>
  );
}

/** Un formulario de alta o edición, armado desde una lista de campos. */
function Formulario({ campos, valores, onCambiar, onGuardar, onCancelar, trabajando, editando }) {
  const falta = campos.some((c) => c.obligatorio && !String(valores[c.id] ?? '').trim());

  return (
    <form
      className="editor-seccion"
      onSubmit={(e) => {
        e.preventDefault();
        onGuardar();
      }}
    >
      {campos.map((campo) => (
        <label key={campo.id}>
          <span>
            {campo.etiqueta}
            {!campo.obligatorio && <small> opcional</small>}
          </span>
          {campo.opciones ? (
            <select
              value={valores[campo.id] ?? ''}
              onChange={(e) => onCambiar({ [campo.id]: e.target.value })}
            >
              <option value="">Elegí una opción</option>
              {campo.opciones.map((o) => (
                <option key={o.valor} value={o.valor}>
                  {o.nombre}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={campo.tipo ?? 'text'}
              value={valores[campo.id] ?? ''}
              maxLength={campo.maximo ?? 150}
              placeholder={campo.ejemplo}
              onChange={(e) => onCambiar({ [campo.id]: e.target.value })}
            />
          )}
        </label>
      ))}

      <div className="editor-botones">
        <button type="button" className="boton-suave" onClick={onCancelar} disabled={trabajando}>
          Cancelar
        </button>
        <button type="submit" className="boton-principal" disabled={trabajando || falta}>
          {editando ? 'Guardar cambios' : 'Crear'}
        </button>
      </div>
    </form>
  );
}

export default function Estructura({ datos, onCambio }) {
  const [vista, setVista] = useState('carreras');
  const [formulario, setFormulario] = useState(null);
  const [valores, setValores] = useState({});
  const [aConfirmar, setAConfirmar] = useState(null);
  // La comisión cuyo cuadro de materias se está mirando
  const [comision, setComision] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  const { carreras, sedes, planes, comisiones, turnos } = datos;

  // Las comisiones, agrupadas por carrera y en el orden en que vienen. El
  // nombre ya dice el año ("2.º año - Comisión A"), así que con la carrera
  // alcanza: no hace falta un tercer nivel.
  const porCarrera = useMemo(() => {
    const mapa = new Map();
    for (const c of comisiones) {
      const clave = c.carrera || 'Sin carrera';
      if (!mapa.has(clave)) mapa.set(clave, []);
      mapa.get(clave).push(c);
    }
    return [...mapa.entries()]
      .sort(([a], [b]) => a.localeCompare(b, 'es'))
      .map(([carrera, suyas]) => ({ carrera, suyas }));
  }, [comisiones]);

  async function accionar(accion, exito) {
    setTrabajando(true);
    try {
      onCambio(await accion());
      setFormulario(null);
      setAConfirmar(null);
      avisar(exito);
    } catch (e) {
      avisar(e.message, 'error');
      setAConfirmar(null);
    } finally {
      setTrabajando(false);
    }
  }

  function abrir(que, elemento) {
    setFormulario({ que, id: elemento?.id });
    setValores(
      elemento
        ? {
          ...elemento,
          carreraId: elemento.carreraId ?? '',
          sedeId: elemento.sedeId ?? '',
          planId: elemento.planId ?? '',
        }
        : {}
    );
  }

  const opcionesCarrera = carreras
    .filter((c) => c.activa)
    .map((c) => ({ valor: c.id, nombre: c.nombre }));
  const opcionesSede = sedes
    .filter((s) => s.activa)
    .map((s) => ({ valor: s.id, nombre: s.nombre }));

  const CAMPOS = {
    carreras: [
      { id: 'nombre', etiqueta: 'Nombre de la carrera', obligatorio: true,
        ejemplo: 'Tecnicatura Universitaria en Programación' },
      { id: 'codigo', etiqueta: 'Código', maximo: 20, ejemplo: 'TUP' },
    ],
    sedes: [
      { id: 'nombre', etiqueta: 'Nombre de la sede', obligatorio: true, ejemplo: 'UTN Goya' },
      { id: 'ciudad', etiqueta: 'Ciudad', ejemplo: 'Goya' },
    ],
    planes: [
      { id: 'carreraId', etiqueta: 'Carrera', obligatorio: true, opciones: opcionesCarrera },
      { id: 'nombre', etiqueta: 'Nombre del plan', obligatorio: true, ejemplo: 'Plan 2023' },
      { id: 'anio', etiqueta: 'Año', tipo: 'number', ejemplo: '2023' },
    ],
    comisiones: [
      { id: 'carreraId', etiqueta: 'Carrera', obligatorio: true, opciones: opcionesCarrera },
      { id: 'planId', etiqueta: 'Plan de estudio',
        opciones: planes
          .filter((p) => p.activo && String(p.carreraId) === String(valores.carreraId))
          .map((p) => ({ valor: p.id, nombre: p.nombre })) },
      { id: 'sedeId', etiqueta: 'Sede', obligatorio: true, opciones: opcionesSede },
      { id: 'nombre', etiqueta: 'Nombre', obligatorio: true, ejemplo: '1.º año - Comisión A' },
      { id: 'anio', etiqueta: 'Año de la carrera', tipo: 'number', ejemplo: '1' },
      { id: 'turno', etiqueta: 'Turno',
        opciones: turnos.map((t) => ({ valor: t, nombre: t })) },
    ],
  };

  const ALTAS = {
    carreras: crearCarrera, sedes: crearSede, planes: crearPlan, comisiones: crearComision,
  };
  const EDICIONES = {
    carreras: editarCarrera, sedes: editarSede, planes: editarPlan, comisiones: editarComision,
  };
  const BAJAS = {
    carreras: borrarCarrera, sedes: borrarSede, planes: borrarPlan, comisiones: borrarComision,
  };

  function guardar() {
    const datosLimpios = { ...valores };
    for (const clave of ['carreraId', 'sedeId', 'planId', 'anio']) {
      if (datosLimpios[clave] === '') datosLimpios[clave] = null;
      else if (datosLimpios[clave] != null) datosLimpios[clave] = Number(datosLimpios[clave]);
    }
    const que = formulario.que;
    accionar(
      () =>
        formulario.id
          ? EDICIONES[que](formulario.id, datosLimpios)
          : ALTAS[que](datosLimpios),
      formulario.id ? 'Cambios guardados.' : 'Creado.'
    );
  }

  function pedirBaja(que, elemento, usos) {
    setAConfirmar({
      titulo: '¿Lo das de baja?',
      mensaje: usos
        ? 'Está en uso, así que no se elimina: queda dado de baja y deja de ofrecerse, pero lo que ya depende de él sigue funcionando.'
        : 'No lo usa nada todavía, así que se elimina del todo.',
      detalles: [{ etiqueta: 'Nombre', valor: elemento.nombre }],
      ejecutar: () => accionar(() => BAJAS[que](elemento.id), 'Dado de baja.'),
    });
  }

  const PESTANAS = [
    { id: 'carreras', nombre: 'Carreras', cantidad: carreras.length },
    { id: 'sedes', nombre: 'Sedes', cantidad: sedes.length },
    { id: 'planes', nombre: 'Planes', cantidad: planes.length },
    { id: 'comisiones', nombre: 'Comisiones', cantidad: comisiones.length },
    // Las materias son del plan, no de la comisión: el plan dice qué hay que
    // cursar y en qué orden, y ahí viven las correlatividades.
    { id: 'materias', nombre: 'Materias' },
  ];

  return (
    <>
      <nav className="pestanas" aria-label="Estructura académica">
        {PESTANAS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={vista === p.id ? 'pestana activa' : 'pestana'}
            onClick={() => {
              setVista(p.id);
              setFormulario(null);
            }}
          >
            {p.nombre}
            <small className="pestana-cantidad">{p.cantidad}</small>
          </button>
        ))}
      </nav>

      {vista !== 'materias' && (
        <div className="barra-asistencias">
          {!formulario && (
            <button type="button" className="boton-principal" onClick={() => abrir(vista)}>
              <IconoMas width={16} height={16} />
              Agregar
            </button>
          )}
        </div>
      )}

      {/* Materias trae su propia barra: tiene filtros y su botón de alta */}
      {vista === 'materias' && <Materias catalogo={datos} />}

      {formulario && (
        <Formulario
          campos={CAMPOS[formulario.que]}
          valores={valores}
          editando={Boolean(formulario.id)}
          trabajando={trabajando}
          onCambiar={(c) => setValores((v) => ({ ...v, ...c }))}
          onGuardar={guardar}
          onCancelar={() => setFormulario(null)}
        />
      )}

      <ul className="catalogo">
        {vista === 'carreras' &&
          carreras.map((c) => (
            <Fila
              key={c.id}
              titulo={c.nombre}
              detalle={c.codigo}
              activo={c.activa}
              usos={`${c.usos.materias} materias · ${c.usos.estudiantes} estudiantes`}
              onEditar={() => abrir('carreras', c)}
              onBorrar={() => pedirBaja('carreras', c, c.usos.estudiantes + c.usos.materias)}
            />
          ))}

        {vista === 'sedes' &&
          sedes.map((s) => (
            <Fila
              key={s.id}
              titulo={s.nombre}
              detalle={s.ciudad}
              activo={s.activa}
              usos={`${s.comisiones} comisiones`}
              onEditar={() => abrir('sedes', s)}
              onBorrar={() => pedirBaja('sedes', s, s.comisiones)}
            />
          ))}

        {vista === 'planes' &&
          planes.map((p) => (
            <Fila
              key={p.id}
              titulo={p.nombre}
              detalle={p.carrera}
              activo={p.activo}
              usos={`${p.materias} materias`}
              onEditar={() => abrir('planes', p)}
              onBorrar={() => pedirBaja('planes', p, p.materias)}
            />
          ))}

        {/* Las comisiones van agrupadas por carrera: con tres carreras de
            seis comisiones cada una, dieciocho filas seguidas obligan a leer
            el subtítulo de cada una para saber de cuál es. */}
        {vista === 'comisiones' &&
          porCarrera.map(({ carrera, suyas }) => (
            <li key={carrera} className="grupo-comisiones">
              <h4 className="comision-carrera">
                {carrera}
                <small>
                  {suyas.length} {suyas.length === 1 ? 'comisión' : 'comisiones'}
                </small>
              </h4>
              <ul className="catalogo">
                {suyas.map((c) => (
                  <Fila
                    key={c.id}
                    titulo={c.nombre}
                    detalle={`${c.sede}${c.turno ? ` · turno ${c.turno}` : ''}`}
                    activo={c.activa}
                    usos={`${c.estudiantes} estudiantes`}
                    onEditar={() => abrir('comisiones', c)}
                    onBorrar={() => pedirBaja('comisiones', c, c.estudiantes)}
                    extra={
                      <button
                        type="button"
                        className="boton-suave"
                        onClick={() => setComision(c.id)}
                      >
                        Materias y docentes
                      </button>
                    }
                  />
                ))}
              </ul>
            </li>
          ))}
      </ul>

      {comision && (
        <Comision comisionId={comision} onCerrar={() => setComision(null)} />
      )}

      {aConfirmar && (
        <Confirmacion
          titulo={aConfirmar.titulo}
          mensaje={aConfirmar.mensaje}
          detalles={aConfirmar.detalles}
          textoConfirmar="Sí, dar de baja"
          peligro
          trabajando={trabajando}
          onConfirmar={aConfirmar.ejecutar}
          onCancelar={() => setAConfirmar(null)}
        />
      )}
    </>
  );
}
