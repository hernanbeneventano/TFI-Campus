import { useState } from 'react';
import Desplegable from '../Desplegable.jsx';
import { IconoAdvertencia, IconoCandado } from '../Iconos.jsx';
import { crearMesa, editarMesa } from '../../services/api.js';
import { Ventana, aCampoFecha } from './comun.jsx';

// Una fecha para un <input type="date">, corrida n días. Ojo: no es el
// `enDias` de services/fechas.js, que devuelve "en 5 días" para leer.
const campoEnDias = (n) => {
  const f = new Date();
  f.setDate(f.getDate() + n);
  return aCampoFecha(f.toISOString());
};

function restarDias(campoFecha, n) {
  const [a, m, d] = campoFecha.split('-').map(Number);
  return aCampoFecha(new Date(a, m - 1, d - n).toISOString());
}

// Lo que cambia para los inscriptos: si se toca algo de esto, se los avisa
const CLAVES_REPROGRAMACION = ['fecha', 'desde', 'hasta', 'lugar', 'modalidad'];

// Crear una mesa, o modificar / reprogramar una existente.
// Valida acá para avisar rápido; la validación que vale es la del servidor.
export default function FormularioMesa({ opciones, mesa, onCerrar, onListo }) {
  const editando = Boolean(mesa);

  const [datos, setDatos] = useState(() =>
    mesa
      ? {
          materiaId: String(mesa.materia.id),
          llamado: mesa.llamado,
          fecha: aCampoFecha(mesa.fecha),
          desde: mesa.desde,
          hasta: mesa.hasta,
          modalidad: mesa.modalidad,
          instancia: mesa.instancia,
          lugar: mesa.lugar,
          inscripcionDesde: aCampoFecha(mesa.inscripcionDesde),
          inscripcionHasta: aCampoFecha(mesa.inscripcionHasta),
          cupo: mesa.cupo ?? '',
          tribunal: mesa.tribunal.map((t) => t.id),
        }
      : {
          materiaId: String(opciones.materias[0]?.id ?? ''),
          llamado: '',
          fecha: campoEnDias(30),
          desde: '16:00',
          hasta: '19:00',
          modalidad: opciones.modalidades[0],
          instancia: opciones.instancias[0],
          lugar: '',
          inscripcionDesde: campoEnDias(0),
          inscripcionHasta: campoEnDias(27),
          cupo: '',
          tribunal: [],
        }
  );
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const cambiar = (campo) => (valor) => setDatos((d) => ({ ...d, [campo]: valor }));
  const alEscribir = (campo) => (e) => cambiar(campo)(e.target.value);

  // El titular de la materia va siempre en el tribunal
  const titularId = editando
    ? mesa.tribunal[0]?.id
    : opciones.materias.find((m) => String(m.id) === datos.materiaId)?.docenteId;

  function alternarIntegrante(id) {
    setDatos((d) => ({
      ...d,
      tribunal: d.tribunal.includes(id) ? d.tribunal.filter((t) => t !== id) : [...d.tribunal, id],
    }));
  }

  // Al mover la fecha del examen, el cierre de la inscripción la acompaña
  // si había quedado en el mismo día o después.
  function cambiarFecha(e) {
    const fecha = e.target.value;
    setDatos((d) => ({
      ...d,
      fecha,
      inscripcionHasta:
        fecha && d.inscripcionHasta >= fecha ? restarDias(fecha, 2) : d.inscripcionHasta,
    }));
  }

  const reprograma =
    editando &&
    mesa.inscriptos > 0 &&
    CLAVES_REPROGRAMACION.some((k) =>
      k === 'fecha' ? datos.fecha !== aCampoFecha(mesa.fecha) : datos[k] !== mesa[k]
    );

  function revisar() {
    if (!datos.materiaId) return 'Elegí la materia.';
    if (!datos.llamado.trim()) return 'Poné el nombre del llamado.';
    if (!datos.fecha || !datos.inscripcionDesde || !datos.inscripcionHasta)
      return 'Completá las fechas.';
    if (!datos.desde || !datos.hasta) return 'Completá el horario.';
    if (datos.desde >= datos.hasta) return 'La hora de fin tiene que ser posterior a la de inicio.';
    if (datos.fecha <= campoEnDias(0) && new Date(`${datos.fecha}T${datos.desde}`) <= new Date())
      return 'La mesa tiene que ser en el futuro.';
    if (datos.inscripcionDesde > datos.inscripcionHasta)
      return 'La inscripción no puede cerrar antes de abrir.';
    if (datos.inscripcionHasta >= datos.fecha)
      return 'La inscripción tiene que cerrar antes del día del examen.';
    if (!datos.lugar.trim())
      return datos.modalidad === 'Virtual' ? 'Poné el enlace de la sala virtual.' : 'Poné el aula o el lugar.';
    if (datos.cupo !== '') {
      const cupo = Number(datos.cupo);
      if (!Number.isInteger(cupo) || cupo < 1) return 'El cupo tiene que ser un número entero, o quedar vacío.';
      if (editando && cupo < mesa.inscriptos)
        return `Ya hay ${mesa.inscriptos} inscriptos: el cupo no puede ser menor.`;
    }
    return null;
  }

  async function guardar() {
    const problema = revisar();
    if (problema) {
      setError(problema);
      return;
    }
    setGuardando(true);
    setError(null);
    const cuerpo = {
      ...datos,
      materiaId: Number(datos.materiaId),
      cupo: datos.cupo === '' ? null : Number(datos.cupo),
    };
    try {
      if (editando) {
        await editarMesa(mesa.id, cuerpo);
        onListo(
          reprograma
            ? `Mesa reprogramada. Se les avisó a ${mesa.inscriptos} inscriptos por mensaje.`
            : 'Cambios guardados.'
        );
      } else {
        await crearMesa(cuerpo);
        onListo('Mesa creada.');
      }
    } catch (e) {
      setError(e.message);
      setGuardando(false);
    }
  }

  const otrosDocentes = opciones.docentes.filter((p) => p.id !== titularId);
  const titular = opciones.docentes.find((p) => p.id === titularId);

  return (
    <Ventana
      titulo={editando ? 'Modificar la mesa' : 'Nueva mesa de examen'}
      bajada={
        editando
          ? `${mesa.materia.codigo} · ${mesa.materia.nombre}`
          : 'Los alumnos la ven en sus fechas en cuanto abre la inscripción.'
      }
      onCerrar={onCerrar}
      ocupado={guardando}
      onEnviar={guardar}
    >
      <div className="aporte-campos">
        {!editando && (
          <label className="ancho-completo">
            <span>Materia *</span>
            <Desplegable
              valor={datos.materiaId}
              opciones={opciones.materias.map((m) => ({
                valor: String(m.id),
                nombre: `${m.codigo} · ${m.nombre}`,
              }))}
              onCambiar={cambiar('materiaId')}
              etiqueta="Materia"
            />
          </label>
        )}

        <label className="ancho-completo">
          <span>Llamado *</span>
          <input
            type="text"
            value={datos.llamado}
            onChange={alEscribir('llamado')}
            maxLength={80}
            placeholder="Turno diciembre · 1.er llamado"
          />
        </label>

        <fieldset className="finales-grupo-campos ancho-completo">
          <legend>Cuándo</legend>
          <label>
            <span>Fecha del examen *</span>
            <input type="date" value={datos.fecha} min={campoEnDias(0)} onChange={cambiarFecha} />
          </label>
          <label>
            <span>Desde *</span>
            <input type="time" value={datos.desde} onChange={alEscribir('desde')} />
          </label>
          <label>
            <span>Hasta *</span>
            <input type="time" value={datos.hasta} onChange={alEscribir('hasta')} />
          </label>
        </fieldset>

        <label>
          <span>Modalidad *</span>
          <Desplegable
            valor={datos.modalidad}
            opciones={opciones.modalidades.map((m) => ({ valor: m, nombre: m }))}
            onCambiar={cambiar('modalidad')}
            etiqueta="Modalidad"
          />
        </label>

        <label>
          <span>Instancia *</span>
          <Desplegable
            valor={datos.instancia}
            opciones={opciones.instancias.map((m) => ({ valor: m, nombre: m }))}
            onCambiar={cambiar('instancia')}
            etiqueta="Instancia"
          />
        </label>

        <label className="ancho-completo">
          <span>{datos.modalidad === 'Virtual' ? 'Enlace de la sala *' : 'Aula o lugar *'}</span>
          <input
            type="text"
            value={datos.lugar}
            onChange={alEscribir('lugar')}
            maxLength={120}
            placeholder={datos.modalidad === 'Virtual' ? 'https://…' : 'Aula Magna, Lab. 3…'}
          />
        </label>

        <fieldset className="finales-grupo-campos ancho-completo">
          <legend>Inscripción</legend>
          <label>
            <span>Abre *</span>
            <input type="date" value={datos.inscripcionDesde} onChange={alEscribir('inscripcionDesde')} />
          </label>
          <label>
            <span>Cierra *</span>
            <input
              type="date"
              value={datos.inscripcionHasta}
              max={datos.fecha ? restarDias(datos.fecha, 1) : undefined}
              onChange={alEscribir('inscripcionHasta')}
            />
          </label>
          <label>
            <span>Cupo</span>
            <input
              type="number"
              min={editando ? Math.max(1, mesa.inscriptos) : 1}
              max={500}
              value={datos.cupo}
              onChange={alEscribir('cupo')}
              placeholder="Sin límite"
            />
          </label>
        </fieldset>

        <div className="ancho-completo finales-tribunal">
          <span className="aporte-etiqueta">Tribunal</span>
          <div className="biblioteca-categorias">
            {titular && (
              <span className="chip activo finales-fijo" title="El titular de la materia integra siempre el tribunal">
                <IconoCandado width={13} height={13} />
                {titular.nombre}
              </span>
            )}
            {otrosDocentes.map((p) => {
              const esta = datos.tribunal.includes(p.id);
              return (
                <button
                  key={p.id}
                  type="button"
                  className={esta ? 'chip activo' : 'chip'}
                  onClick={() => alternarIntegrante(p.id)}
                  aria-pressed={esta}
                >
                  {p.nombre}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {reprograma && (
        <p className="finales-advertencia">
          <IconoAdvertencia width={18} height={18} />
          Cambiaste cuándo, dónde o cómo se toma. A los {mesa.inscriptos} inscriptos les llega un
          mensaje con los datos nuevos.
        </p>
      )}

      {error && (
        <p className="error aporte-error" role="alert">
          <IconoAdvertencia width={16} height={16} />
          {error}
        </p>
      )}

      <div className="aporte-pie">
        <button type="button" className="boton-suave" onClick={onCerrar} disabled={guardando}>
          Cancelar
        </button>
        <button type="submit" className="boton-principal" disabled={guardando}>
          {guardando ? 'Guardando…' : editando ? (reprograma ? 'Reprogramar' : 'Guardar cambios') : 'Crear mesa'}
        </button>
      </div>
    </Ventana>
  );
}
