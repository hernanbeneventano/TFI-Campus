// Alta y edición de un elemento dentro de una sección.
//
// Los cuatro tipos piden cosas distintas, así que el formulario cambia según
// el que se elija. Al editar, el tipo no se puede cambiar: convertir una
// página en un trabajo no significa nada, y si fuera un trabajo se llevaría
// puestas las entregas y las notas. Para eso se borra y se crea el que va.

import { useEffect, useRef, useState } from 'react';
import {
  IconoPagina,
  IconoArchivo,
  IconoTarea,
  IconoTablero,
  IconoModulos,
  IconoUbicacion,
  IconoSubir,
  IconoNotas,
  IconoMas,
  IconoCerrar,
  IconoPapelera,
} from '../Iconos.jsx';

const TIPOS = [
  { id: 'pagina', nombre: 'Página', Icono: IconoPagina, ayuda: 'Un texto para leer en el campus' },
  { id: 'archivo', nombre: 'Archivo', Icono: IconoArchivo, ayuda: 'Un apunte, una clase, un PDF' },
  { id: 'tarea', nombre: 'Trabajo', Icono: IconoTarea, ayuda: 'Una entrega con fecha' },
  { id: 'tablero', nombre: 'Tablero', Icono: IconoTablero, ayuda: 'Un espacio de consultas' },
];

const FORMATOS = ['PDF', 'Video', 'Documento', 'Presentación', 'Planilla', 'Imagen', 'Enlace'];

// El <input type="datetime-local"> quiere "AAAA-MM-DDTHH:MM" en hora local
function paraElCampo(iso) {
  if (!iso) return '';
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return '';
  const dos = (n) => String(n).padStart(2, '0');
  return `${f.getFullYear()}-${dos(f.getMonth() + 1)}-${dos(f.getDate())}T${dos(
    f.getHours()
  )}:${dos(f.getMinutes())}`;
}

function porDefecto() {
  // Una semana a las 23:59, que es lo que se pone casi siempre
  const f = new Date();
  f.setDate(f.getDate() + 7);
  f.setHours(23, 59, 0, 0);
  return paraElCampo(f.toISOString());
}

export default function FormularioElemento({ elemento, onGuardar, onCancelar, trabajando }) {
  const editando = Boolean(elemento);
  const [tipo, setTipo] = useState(elemento?.tipo ?? 'archivo');
  const [titulo, setTitulo] = useState(elemento?.titulo ?? '');
  const [cuerpo, setCuerpo] = useState(
    Array.isArray(elemento?.cuerpo) ? elemento.cuerpo.join('\n\n') : ''
  );
  const [formato, setFormato] = useState(elemento?.formato ?? 'PDF');
  const [tamano, setTamano] = useState(elemento?.tamano ?? '');
  const [fechaLimite, setFechaLimite] = useState(
    elemento?.fechaLimite ? paraElCampo(elemento.fechaLimite) : porDefecto()
  );
  const [consigna, setConsigna] = useState(elemento?.consigna ?? '');

  // Dónde se rinde y cómo se corrige. Un presencial no tiene nada que subir:
  // la nota la carga el docente al cerrar. Un cuestionario se corrige solo.
  const [modalidad, setModalidad] = useState(elemento?.modalidad ?? 'virtual');
  const [comoSeResuelve, setComoSeResuelve] = useState(
    elemento?.formato && elemento.formato !== 'presencial' ? elemento.formato : 'entrega'
  );
  const [preguntas, setPreguntas] = useState(
    elemento?.preguntas?.length
      ? elemento.preguntas
      : [{ texto: '', opciones: ['', ''], correcta: 0, puntaje: 1 }]
  );

  function cambiarPregunta(i, cambio) {
    setPreguntas((lista) => lista.map((p, n) => (n === i ? { ...p, ...cambio } : p)));
  }

  function cambiarOpcion(i, j, valor) {
    setPreguntas((lista) =>
      lista.map((p, n) =>
        n === i ? { ...p, opciones: p.opciones.map((o, m) => (m === j ? valor : o)) } : p
      )
    );
  }

  const primero = useRef(null);
  useEffect(() => {
    primero.current?.focus();
  }, []);

  function enviar(e) {
    e.preventDefault();
    if (!titulo.trim()) return;

    const datos = { titulo: titulo.trim() };
    if (!editando) datos.tipo = tipo;

    if (tipo === 'pagina') datos.cuerpo = cuerpo;
    if (tipo === 'archivo') {
      datos.formato = formato;
      datos.tamano = tamano.trim() || null;
    }
    if (tipo === 'tarea') {
      // El campo da hora local; el backend guarda ISO
      datos.fechaLimite = new Date(fechaLimite).toISOString();
      datos.consigna = consigna.trim() || null;
      datos.modalidad = modalidad;
      datos.formato = modalidad === 'presencial' ? 'presencial' : comoSeResuelve;
      if (datos.formato === 'cuestionario') {
        datos.preguntas = preguntas.map((p) => ({
          texto: p.texto.trim(),
          opciones: p.opciones.map((o) => o.trim()),
          correcta: p.correcta,
          puntaje: p.puntaje ?? 1,
        }));
      }
    }
    onGuardar(datos);
  }

  const esCuestionario =
    tipo === 'tarea' && modalidad === 'virtual' && comoSeResuelve === 'cuestionario';

  const cuestionarioIncompleto =
    esCuestionario &&
    preguntas.some(
      (p) => !p.texto.trim() || p.opciones.length < 2 || p.opciones.some((o) => !o.trim())
    );

  const falta =
    !titulo.trim() ||
    (tipo === 'pagina' && !cuerpo.trim()) ||
    (tipo === 'tarea' && !fechaLimite) ||
    cuestionarioIncompleto;

  return (
    <form className="editor-elemento" onSubmit={enviar}>
      {!editando && (
        <fieldset className="editor-tipos">
          <legend>¿Qué querés agregar?</legend>
          <div>
            {TIPOS.map(({ id, nombre, Icono, ayuda }) => (
              <label key={id} className={tipo === id ? 'tipo elegido' : 'tipo'} title={ayuda}>
                <input
                  type="radio"
                  name="tipo"
                  value={id}
                  checked={tipo === id}
                  onChange={() => setTipo(id)}
                />
                <Icono width={18} height={18} />
                <strong>{nombre}</strong>
                <small>{ayuda}</small>
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <label>
        <span>Título</span>
        <input
          ref={primero}
          type="text"
          value={titulo}
          maxLength={120}
          placeholder={
            tipo === 'tarea' ? 'Trabajo práctico 4: Árboles' : 'Clase 3: Recorridos en árboles'
          }
          onChange={(e) => setTitulo(e.target.value)}
        />
      </label>

      {tipo === 'pagina' && (
        <label>
          <span>
            Texto <small>una línea en blanco separa los párrafos</small>
          </span>
          <textarea
            rows={7}
            value={cuerpo}
            onChange={(e) => setCuerpo(e.target.value)}
            placeholder={'Lo que quieras contarles.\n\nOtro párrafo.'}
          />
        </label>
      )}

      {tipo === 'archivo' && (
        <div className="editor-fila">
          <label>
            <span>Formato</span>
            <select value={formato} onChange={(e) => setFormato(e.target.value)}>
              {FORMATOS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>
              Tamaño o duración <small>opcional</small>
            </span>
            <input
              type="text"
              value={tamano}
              maxLength={30}
              placeholder="420 KB · 45 min"
              onChange={(e) => setTamano(e.target.value)}
            />
          </label>
        </div>
      )}

      {tipo === 'tarea' && (
        <>
          <fieldset className="editor-tipos compacto">
            <legend>¿Dónde se rinde?</legend>
            <div>
              <label className={modalidad === 'virtual' ? 'tipo elegido' : 'tipo'}>
                <input
                  type="radio"
                  name="modalidad"
                  checked={modalidad === 'virtual'}
                  onChange={() => setModalidad('virtual')}
                />
                <IconoModulos width={18} height={18} />
                <strong>Virtual</strong>
                <small>Se resuelve en el campus</small>
              </label>
              <label className={modalidad === 'presencial' ? 'tipo elegido' : 'tipo'}>
                <input
                  type="radio"
                  name="modalidad"
                  checked={modalidad === 'presencial'}
                  onChange={() => setModalidad('presencial')}
                />
                <IconoUbicacion width={18} height={18} />
                <strong>Presencial</strong>
                <small>Se rinde en el aula</small>
              </label>
            </div>
          </fieldset>

          {modalidad === 'virtual' && (
            <fieldset className="editor-tipos compacto">
              <legend>¿Cómo lo resuelven?</legend>
              <div>
                <label className={comoSeResuelve === 'entrega' ? 'tipo elegido' : 'tipo'}>
                  <input
                    type="radio"
                    name="como-se-resuelve"
                    checked={comoSeResuelve === 'entrega'}
                    onChange={() => setComoSeResuelve('entrega')}
                  />
                  <IconoSubir width={18} height={18} />
                  <strong>Entrega</strong>
                  <small>Suben un archivo y lo corregís vos</small>
                </label>
                <label className={comoSeResuelve === 'cuestionario' ? 'tipo elegido' : 'tipo'}>
                  <input
                    type="radio"
                    name="como-se-resuelve"
                    checked={comoSeResuelve === 'cuestionario'}
                    onChange={() => setComoSeResuelve('cuestionario')}
                  />
                  <IconoNotas width={18} height={18} />
                  <strong>Cuestionario</strong>
                  <small>Opción múltiple, se corrige solo</small>
                </label>
              </div>
            </fieldset>
          )}

          <label>
            <span>Fecha y hora de entrega</span>
            <input
              type="datetime-local"
              value={fechaLimite}
              onChange={(e) => setFechaLimite(e.target.value)}
            />
          </label>
          <label>
            <span>
              Consigna <small>opcional</small>
            </span>
            <textarea
              rows={3}
              value={consigna}
              onChange={(e) => setConsigna(e.target.value)}
              placeholder={
                modalidad === 'presencial'
                  ? 'Dónde, qué llevar, qué entra.'
                  : 'Qué tienen que entregar y cómo se corrige.'
              }
            />
          </label>

          {esCuestionario && (
            <div className="editor-preguntas">
              <h4>
                Preguntas <small>{preguntas.length}</small>
              </h4>
              {preguntas.map((p, i) => (
                <fieldset key={i} className="pregunta">
                  <legend>Pregunta {i + 1}</legend>
                  {preguntas.length > 1 && (
                    <button
                      type="button"
                      className="pregunta-quitar"
                      onClick={() => setPreguntas((l) => l.filter((_, n) => n !== i))}
                      title="Quitar la pregunta"
                      aria-label={`Quitar la pregunta ${i + 1}`}
                    >
                      <IconoPapelera width={14} height={14} />
                    </button>
                  )}

                  <input
                    type="text"
                    value={p.texto}
                    maxLength={500}
                    placeholder="¿Qué les preguntás?"
                    onChange={(e) => cambiarPregunta(i, { texto: e.target.value })}
                  />

                  {/* El radio marca cuál es la correcta: así se ve de un
                      vistazo y no hay que elegirla en otro control aparte. */}
                  <ul className="opciones">
                    {p.opciones.map((o, j) => (
                      <li key={j}>
                        <label title="Marcar como la correcta">
                          <input
                            type="radio"
                            name={`correcta-${i}`}
                            checked={p.correcta === j}
                            onChange={() => cambiarPregunta(i, { correcta: j })}
                          />
                          <span className="marca" aria-hidden="true" />
                        </label>
                        <input
                          type="text"
                          value={o}
                          maxLength={200}
                          placeholder={`Opción ${j + 1}`}
                          onChange={(e) => cambiarOpcion(i, j, e.target.value)}
                        />
                        {p.opciones.length > 2 && (
                          <button
                            type="button"
                            onClick={() =>
                              cambiarPregunta(i, {
                                opciones: p.opciones.filter((_, m) => m !== j),
                                correcta: p.correcta > j ? p.correcta - 1 : p.correcta,
                              })
                            }
                            title="Quitar la opción"
                            aria-label={`Quitar la opción ${j + 1}`}
                          >
                            <IconoCerrar width={13} height={13} />
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>

                  {p.opciones.length < 6 && (
                    <button
                      type="button"
                      className="boton-agregar chico"
                      onClick={() => cambiarPregunta(i, { opciones: [...p.opciones, ''] })}
                    >
                      <IconoMas width={14} height={14} />
                      Agregar una opción
                    </button>
                  )}
                </fieldset>
              ))}

              <button
                type="button"
                className="boton-agregar"
                onClick={() =>
                  setPreguntas((l) => [
                    ...l,
                    { texto: '', opciones: ['', ''], correcta: 0, puntaje: 1 },
                  ])
                }
              >
                <IconoMas width={16} height={16} />
                Agregar una pregunta
              </button>
            </div>
          )}
        </>
      )}

      <div className="editor-botones">
        <button type="button" className="boton-suave" onClick={onCancelar} disabled={trabajando}>
          Cancelar
        </button>
        <button type="submit" className="boton-principal" disabled={trabajando || falta}>
          {editando ? 'Guardar cambios' : 'Agregar'}
        </button>
      </div>
    </form>
  );
}
