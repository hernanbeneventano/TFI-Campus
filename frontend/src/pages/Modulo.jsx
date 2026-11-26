import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import {
  obtenerModulo,
  obtenerUsuarioActual,
  crearSeccion,
  editarSeccion,
  borrarSeccion,
  moverSeccion,
  crearElemento,
  subirArchivoDeElemento,
  agregarDiaDeClase,
  quitarDiaDeClase,
  editarElemento,
  borrarElemento,
  moverElemento,
  cambiarEntrega,
  publicarAnuncio,
  editarAnuncio,
  borrarAnuncio,
  obtenerSeguimiento,
  obtenerEntregasDeSeccion,
  obtenerNotas,
  guardarNota,
  fijarCierre,
  obtenerMisNotas,
  marcarVisto,
  desmarcarVisto,
} from '../services/api.js';
import { avisar } from '../services/avisos.js';
import useArrastre from '../hooks/useArrastre.js';
import {
  leerCompletados,
  migrarProgresoDelNavegador,
  calcularAvance,
} from '../services/progreso.js';
import { hace } from '../services/fechas.js';
import CarpetaModulo from '../components/CarpetaModulo.jsx';
import PestanasModulo from '../components/PestanasModulo.jsx';
import PanelModulo from '../components/PanelModulo.jsx';
import VisorItem from '../components/VisorItem.jsx';
import Confirmacion from '../components/Confirmacion.jsx';
import FormularioSeccion from '../components/modulo/FormularioSeccion.jsx';
import FormularioElemento from '../components/modulo/FormularioElemento.jsx';
import PanelNotas from '../components/modulo/PanelNotas.jsx';
import MisNotas from '../components/modulo/MisNotas.jsx';
import AsistenciasDelModulo from '../components/asistencias/AsistenciasDelModulo.jsx';
import EntregasSeccion from '../components/modulo/EntregasSeccion.jsx';
import Correccion from '../components/modulo/Correccion.jsx';
import {
  IconoVolver,
  IconoBuscar,
  IconoModulos,
  IconoAnuncio,
  IconoPersonas,
  IconoNotas,
  IconoUsuario,
  IconoEstudiante,
  IconoMensaje,
  IconoLapiz,
  IconoMas,
  IconoPapelera,
  IconoCheckCirculo,
  IconoPresente,
} from '../components/Iconos.jsx';
import Avatar from '../components/Avatar.jsx';

import useTitulo from '../hooks/useTitulo';
function formatearFecha(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long' });
}

// Formulario para publicar o corregir un anuncio del módulo
function FormularioAnuncio({ anuncio, onGuardar, onCancelar, trabajando }) {
  const [titulo, setTitulo] = useState(anuncio?.titulo ?? '');
  const [cuerpo, setCuerpo] = useState(anuncio?.cuerpo ?? '');
  const primero = useRef(null);

  useEffect(() => {
    primero.current?.focus();
  }, []);

  function enviar(e) {
    e.preventDefault();
    if (!titulo.trim() || !cuerpo.trim()) return;
    onGuardar({ titulo: titulo.trim(), cuerpo: cuerpo.trim() });
  }

  return (
    <form className="editor-seccion" onSubmit={enviar}>
      <label>
        <span>Título</span>
        <input
          ref={primero}
          type="text"
          value={titulo}
          maxLength={120}
          placeholder="Cambio de aula para la clase del jueves"
          onChange={(e) => setTitulo(e.target.value)}
        />
      </label>
      <label>
        <span>Anuncio</span>
        <textarea
          rows={4}
          value={cuerpo}
          onChange={(e) => setCuerpo(e.target.value)}
          placeholder="Lo que necesitás que sepa el curso."
        />
      </label>
      <div className="editor-botones">
        <button type="button" className="boton-suave" onClick={onCancelar} disabled={trabajando}>
          Cancelar
        </button>
        <button
          type="submit"
          className="boton-principal"
          disabled={trabajando || !titulo.trim() || !cuerpo.trim()}
        >
          {anuncio ? 'Guardar cambios' : 'Publicar'}
        </button>
      </div>
    </form>
  );
}

function Anuncios({ anuncios, gestionando, onEditar, onBorrar }) {
  if (anuncios.length === 0) {
    return <p className="texto-suave">Todavía no hay anuncios en este módulo.</p>;
  }
  return (
    <ul className="anuncios">
      {anuncios.map((a) => (
        <li key={a.id} className="anuncio">
          <h3>{a.titulo}</h3>
          <small className="texto-suave">
            {a.autor} · {formatearFecha(a.fecha)}
            {a.editado && <> · editado</>}
          </small>
          <p>{a.cuerpo}</p>

          {gestionando && (
            <span className="acciones-editor">
              <button type="button" onClick={() => onEditar(a)} title="Editar el anuncio">
                <IconoLapiz width={14} height={14} />
              </button>
              <button
                type="button"
                className="peligro"
                onClick={() => onBorrar(a)}
                title="Borrar el anuncio"
              >
                <IconoPapelera width={14} height={14} />
              </button>
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

const textoEstado = {
  conectado: 'Conectado',
  ausente: 'Ausente',
  desconectado: 'Desconectado',
};

function Participantes({ participantes, yo }) {
  return (
    <ul className="participantes">
      {participantes.map((p) => (
        <li key={p.id} className="participante">
          <span
            className={`docente-avatar avatar-estado ${p.estado}`}
            title={textoEstado[p.estado]}
          >
            <Avatar persona={p} tamano={26} />
          </span>
          <div>
            <strong>{p.nombre}</strong>
            <small>{p.rol}</small>
          </div>

          {/* A uno mismo no tiene sentido escribirse */}
          {p.id !== yo && (
            <Link
              to={`/mensajes?con=${p.id}`}
              className="participante-mensaje"
              title={`Escribirle a ${p.nombre}`}
              aria-label={`Escribirle a ${p.nombre}`}
            >
              <IconoMensaje />
            </Link>
          )}

          <div className="participante-acceso">
            <small>Último acceso</small>
            <small>{hace(p.ultimoAcceso)}</small>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function Modulo() {
  const { id } = useParams();
  // ?tarea=N llega desde el panel de tareas pendientes: abre esa entrega.
  // Queda en la URL, así el enlace sigue sirviendo si se recarga o se comparte.
  const tareaPedida = useSearchParams()[0].get('tarea');

  const [datos, setDatos] = useState(null);
  const [yo, setYo] = useState(null);
  const [error, setError] = useState(null);

  const [pestana, setPestana] = useState('contenido');
  const [busqueda, setBusqueda] = useState('');
  const buscando = busqueda.trim().length > 0;

  // Carpetas abiertas (por id) y elemento que se está viendo en pantalla completa
  const [abiertas, setAbiertas] = useState([]);
  const [viendo, setViendo] = useState(null);

  // El material que ya vio, según el servidor. Arranca vacío y se pide al
  // abrir: hasta que llegue, las barras muestran cero, que es preferible a
  // mostrar un avance que después cambia.
  const [completados, setCompletados] = useState([]);

  // --- Administración (solo el docente a cargo) ---
  // `editando` es el modo editor: se enciende con el botón y es lo único que
  // hace aparecer los controles. Apagado, el docente ve su módulo como queda.
  const [editando, setEditando] = useState(false);
  const [seguimiento, setSeguimiento] = useState(null);
  const [notas, setNotas] = useState(null);
  // Las propias, para quien no administra el módulo
  const [misNotas, setMisNotas] = useState(null);
  const [trabajando, setTrabajando] = useState(false);
  // El formulario abierto, si hay alguno: { que, seccion, elemento, anuncio }
  const [formulario, setFormulario] = useState(null);
  // Lo que está esperando confirmación antes de borrarse
  const [aConfirmar, setAConfirmar] = useState(null);

  // El detalle de entregas de una sección, y la corrección abierta desde ahí
  const [entregas, setEntregas] = useState(null);
  const [corrigiendo, setCorrigiendo] = useState(null);
  // Sube de a uno con cada nota guardada. El visor de un trabajo lo mira
  // para volver a pedir sus entregas: la nota recién puesta es justo lo que
  // esa lista muestra, y sin esto queda diciendo «Corregir» al lado de algo
  // que ya tiene nota.
  const [versionNotas, setVersionNotas] = useState(0);

  const puedeGestionar = Boolean(datos?.puedeGestionar);
  useTitulo(datos?.curso?.nombre ?? 'Módulo');

  const traerSeguimiento = useCallback(() => {
    obtenerSeguimiento(id).then(setSeguimiento).catch(() => setSeguimiento(null));
  }, [id]);

  // Lo que el alumno ya marcó. Se pide una vez al entrar al módulo, no por
  // carpeta: son los identificadores de todo el campus y pesan nada.
  //
  // De paso sube lo que hubiera quedado en este navegador de cuando el
  // progreso vivía ahí. Es por única vez: después la clave se borra.
  useEffect(() => {
    let vigente = true;
    migrarProgresoDelNavegador()
      .then((tras) => (tras ? tras : leerCompletados()))
      .catch(() => leerCompletados())
      .then((lista) => vigente && setCompletados(lista ?? []))
      .catch(() => vigente && setCompletados([]));
    return () => {
      vigente = false;
    };
  }, [id]);

  useEffect(() => {
    // Hasta que no llega el módulo no se sabe quién es quien mira, y
    // `puedeGestionar` arranca en false: sin esta guarda, el docente —y
    // quien administra— pedía primero las notas del alumno y se llevaba un
    // 403 por un módulo que no cursa.
    if (!datos) return;

    if (!puedeGestionar) {
      setSeguimiento(null);
      setNotas(null);
      obtenerMisNotas(id).then(setMisNotas).catch(() => setMisNotas(null));
      return;
    }
    setMisNotas(null);
    traerSeguimiento();
    obtenerNotas(id).then(setNotas).catch(() => setNotas(null));
  }, [datos, puedeGestionar, id, traerSeguimiento]);

  // Al salir del módulo se apaga el modo editor: volver y encontrarlo
  // encendido sin haberlo pedido confunde.
  useEffect(() => {
    setEditando(false);
    setFormulario(null);
  }, [id]);

  /**
   * Corre una acción de administración y rearma la pantalla con lo que
   * devuelve. Todas las rutas de contenido mandan las carpetas enteras, así
   * que no hace falta volver a pedir el módulo completo.
   */
  /**
   * Guarda el elemento y, si hay archivo, lo sube después.
   *
   * Son dos pasos porque el archivo necesita un elemento al que colgarse: el
   * servidor comprueba los permisos una vez al crearlo y la subida ya sabe a
   * qué pertenece. Es el mismo camino que usa la Biblioteca.
   */
  async function guardarElemento(seccion, elemento, valores, archivo) {
    const respuesta = elemento
      ? await editarElemento(id, seccion.id, elemento.id, valores)
      : await crearElemento(id, seccion.id, valores);

    if (!archivo) return respuesta;

    // Al crear, el elemento nuevo es el último de su sección
    const laSeccion = respuesta.carpetas?.find((c) => c.id === seccion.id);
    const destino = elemento?.id ?? laSeccion?.items?.[laSeccion.items.length - 1]?.id;
    if (!destino) return respuesta;

    return subirArchivoDeElemento(id, seccion.id, destino, archivo);
  }

  async function administrar(accion, exito) {
    setTrabajando(true);
    try {
      const respuesta = await accion();
      setDatos((previo) => ({ ...previo, ...respuesta }));
      setFormulario(null);
      setAConfirmar(null);
      if (exito) avisar(exito);
      // El avance del curso cambia al agregar o sacar material
      traerSeguimiento();
      if (respuesta.carpetas) {
        obtenerNotas(id).then(setNotas).catch(() => {});
      }
    } catch (e) {
      avisar(e.message, 'error');
      setAConfirmar(null);
    } finally {
      setTrabajando(false);
    }
  }

  function pedirBorrado({ titulo, mensaje, detalles, ejecutar }) {
    setAConfirmar({ titulo, mensaje, detalles, ejecutar });
  }

  // Reordenar las secciones arrastrando la caja entera. Mientras se busca no
  // se puede: la lista que se ve está filtrada y las posiciones no son las
  // reales.
  const sueltas = useArrastre({
    activo: editando && !buscando,
    alSoltar: (desde, hasta) =>
      administrar(() => moverSeccion(id, datos.carpetas[desde].id, { posicion: hasta })),
  });

  async function verEntregas(carpeta) {
    setEntregas({ cargando: true });
    try {
      setEntregas(await obtenerEntregasDeSeccion(id, carpeta.id));
    } catch (e) {
      avisar(e.message, 'error');
      setEntregas(null);
    }
  }

  async function guardarCorreccion(valores) {
    setTrabajando(true);
    try {
      setNotas(await guardarNota(id, valores));
      // El panel de entregas quedó viejo: la nota que se acaba de poner
      // cambia el estado del alumno en esa sección.
      if (entregas?.seccion) {
        setEntregas(await obtenerEntregasDeSeccion(id, entregas.seccion.id));
      }
      traerSeguimiento();
      setVersionNotas((v) => v + 1);
      setCorrigiendo(null);
      avisar('Nota guardada.');
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setTrabajando(false);
    }
  }

  useEffect(() => {
    obtenerUsuarioActual().then((u) => setYo(u.id)).catch(() => setYo(null));
  }, []);

  useEffect(() => {
    setDatos(null);
    setViendo(null);
    setPestana('contenido');
    setBusqueda('');
    obtenerModulo(id)
      .then((d) => {
        setDatos(d);

        // La primera carpeta arranca abierta
        const abrir = d.carpetas.length ? [d.carpetas[0].id] : [];

        // Si se vino desde una tarea pendiente, se abre su entrega y se
        // despliega la carpeta donde está. Va acá y no en otro efecto para
        // que no pise lo que deja este al terminar de cargar.
        if (tareaPedida) {
          for (const carpeta of d.carpetas) {
            const item = carpeta.items.find(
              (i) => i.tipo === 'tarea' && String(i.tareaId) === tareaPedida
            );
            if (item) {
              setViendo({ carpeta, item });
              if (!abrir.includes(carpeta.id)) abrir.push(carpeta.id);
              break;
            }
          }
        }

        setAbiertas(abrir);
      })
      .catch((e) => setError(e.message));
  }, [id, tareaPedida]);

  // Al buscar se muestran solo las carpetas con coincidencias, y adentro solo
  // los elementos que coinciden (salvo que coincida el nombre de la carpeta).
  const carpetasVisibles = useMemo(() => {
    if (!datos) return [];
    const texto = busqueda.trim().toLowerCase();
    if (!texto) return datos.carpetas;

    return datos.carpetas
      .map((carpeta) => {
        const coincideCarpeta =
          carpeta.titulo.toLowerCase().includes(texto) ||
          (carpeta.descripcion ?? '').toLowerCase().includes(texto);
        if (coincideCarpeta) return carpeta;
        const items = carpeta.items.filter((i) => i.titulo.toLowerCase().includes(texto));
        return items.length ? { ...carpeta, items } : null;
      })
      .filter(Boolean);
  }, [datos, busqueda]);

  const avance = useMemo(
    () => calcularAvance(datos ? datos.carpetas.flatMap((c) => c.items) : [], completados),
    [datos, completados]
  );

  // Se marca en la pantalla antes de que conteste el servidor: tildar algo
  // tiene que sentirse inmediato. Si el servidor rechaza, se vuelve atrás y
  // se avisa; dejarlo tildado sería mentir.
  async function alternarCompletado(idItem) {
    const estaba = completados.includes(idItem);
    const antes = completados;
    setCompletados((lista) =>
      estaba ? lista.filter((x) => x !== idItem) : [...lista, idItem]
    );
    try {
      const r = estaba
        ? await desmarcarVisto(id, idItem)
        : await marcarVisto(id, idItem);
      setCompletados(r.completados);
    } catch (e) {
      setCompletados(antes);
      avisar(e.message, 'error');
    }
  }

  function alternarCarpeta(idCarpeta) {
    setAbiertas((lista) =>
      lista.includes(idCarpeta) ? lista.filter((x) => x !== idCarpeta) : [...lista, idCarpeta]
    );
  }

  if (error) {
    return (
      <div className="pagina">
        <p className="error">No se pudo cargar el módulo. ¿Está corriendo el backend?</p>
        <Link to="/modulos" className="volver">
          <IconoVolver />
          Volver a Módulos
        </Link>
      </div>
    );
  }

  if (!datos) {
    return (
      <div className="pagina">
        <p className="texto-suave">Cargando…</p>
      </div>
    );
  }

  const { curso, anuncios, participantes, cursada, proximas } = datos;

  const pestanas = [
    { clave: 'contenido', nombre: 'Contenido', Icono: IconoModulos },
    { clave: 'anuncios', nombre: 'Anuncios', Icono: IconoAnuncio, cantidad: anuncios.length },
    { clave: 'participantes', nombre: 'Participantes', Icono: IconoPersonas },
    { clave: 'notas', nombre: 'Notas', Icono: IconoNotas },
    { clave: 'asistencias', nombre: 'Asistencias', Icono: IconoPresente },
  ];

  return (
    <div className="pagina">
      {viendo && (
        <VisorItem
          curso={curso}
          carpeta={viendo.carpeta}
          item={viendo.item}
          gestionando={puedeGestionar}
          versionNotas={versionNotas}
          onCorregir={(alumno, trabajo) =>
            setCorrigiendo({
              alumno,
              trabajo: { id: trabajo.id, titulo: trabajo.titulo },
              nota:
                alumno.nota === null && !alumno.estado
                  ? null
                  : {
                      nota: alumno.nota,
                      estado: alumno.estado,
                      comentario: alumno.devolucion,
                    },
            })
          }
          onCerrar={() => setViendo(null)}
        />
      )}

      <Link to="/modulos" className="volver">
        <IconoVolver />
        Módulos
      </Link>

      <header className="modulo-encabezado">
        <small>{curso.codigo}</small>
        <h1>{curso.nombre}</h1>
        <p>
          {curso.docente} · {curso.periodo}
        </p>
      </header>

      <PestanasModulo pestanas={pestanas} actual={pestana} onCambiar={setPestana} />

      <div className="pagina-cuerpo">
        <section className="pagina-principal" key={pestana}>
          {pestana === 'contenido' && (
            <>
              <div className="modulo-barra">
                <h2>Contenido</h2>
                <label className="barra-busqueda">
                  <IconoBuscar />
                  <input
                    type="search"
                    placeholder="Buscar en el módulo"
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                  />
                </label>

                {puedeGestionar && (
                  <button
                    type="button"
                    className={editando ? 'boton-suave activo' : 'boton-principal'}
                    onClick={() => {
                      setEditando((x) => !x);
                      setFormulario(null);
                    }}
                  >
                    {editando ? (
                      <>
                        <IconoCheckCirculo width={16} height={16} />
                        Listo
                      </>
                    ) : (
                      <>
                        <IconoLapiz width={16} height={16} />
                        Agregar contenido
                      </>
                    )}
                  </button>
                )}
              </div>

              {formulario?.que === 'seccion' && (
                <FormularioSeccion
                  seccion={formulario.seccion}
                  trabajando={trabajando}
                  onCancelar={() => setFormulario(null)}
                  onGuardar={(valores) =>
                    administrar(
                      () =>
                        formulario.seccion
                          ? editarSeccion(id, formulario.seccion.id, valores)
                          : crearSeccion(id, valores),
                      formulario.seccion ? 'Sección actualizada.' : 'Sección creada.'
                    )
                  }
                />
              )}

              {formulario?.que === 'elemento' && (
                <FormularioElemento
                  elemento={formulario.elemento}
                  trabajando={trabajando}
                  onCancelar={() => setFormulario(null)}
                  onGuardar={(valores, archivo) =>
                    administrar(
                      () =>
                        guardarElemento(
                          formulario.seccion,
                          formulario.elemento,
                          valores,
                          archivo
                        ),
                      formulario.elemento ? 'Elemento actualizado.' : 'Elemento agregado.'
                    )
                  }
                />
              )}

              {carpetasVisibles.length === 0 ? (
                <div className="modulo-vacio">
                  {buscando ? (
                    <p className="texto-suave">No hay nada que coincida con la búsqueda.</p>
                  ) : puedeGestionar ? (
                    <>
                      <p className="texto-suave">
                        Este módulo todavía está vacío. Armá la primera sección y después
                        agregale adentro las páginas, los archivos y los trabajos.
                      </p>
                      {/* El botón también va acá: antes vivía solo al final de
                          la lista de secciones, así que en un módulo sin
                          ninguna no había forma de crear la primera. */}
                      {!formulario && (
                        <button
                          type="button"
                          className="boton-principal"
                          onClick={() => {
                            setEditando(true);
                            setFormulario({ que: 'seccion' });
                          }}
                        >
                          <IconoMas width={16} height={16} />
                          Agregar la primera sección
                        </button>
                      )}
                    </>
                  ) : (
                    <p className="texto-suave">
                      Todavía no hay material cargado en este módulo.
                    </p>
                  )}
                </div>
              ) : (
                <div className={sueltas.arrastrando ? 'carpetas moviendo' : 'carpetas'}>
                  {carpetasVisibles.map((carpeta, i) => (
                    <CarpetaModulo
                      key={carpeta.id}
                      carpeta={carpeta}
                      // Mientras se busca, las carpetas con resultados van abiertas
                      abierta={buscando || abiertas.includes(carpeta.id)}
                      onAlternar={() => alternarCarpeta(carpeta.id)}
                      onAbrirItem={(c, item) => setViendo({ carpeta: c, item })}
                      completados={completados}
                      onCompletar={alternarCompletado}
                      gestionando={puedeGestionar}
                      editando={editando}
                      seguimiento={seguimiento?.secciones.find((s) => s.id === carpeta.id)}
                      primera={i === 0}
                      ultima={i === carpetasVisibles.length - 1}
                      onEditarSeccion={(s) => setFormulario({ que: 'seccion', seccion: s })}
                      indice={i}
                      seMueve={sueltas.esLaMovida(i)}
                      estiloArrastre={sueltas.estiloDe(i)}
                      onTomar={sueltas.tomar}
                      onVerEntregas={verEntregas}
                      onMoverSeccion={(s, destino) =>
                        administrar(() => moverSeccion(id, s.id, destino))
                      }
                      onBorrarSeccion={(s) =>
                        pedirBorrado({
                          titulo: '¿Borrás esta sección?',
                          mensaje:
                            s.items.length > 0
                              ? 'Se va con todo lo que tiene adentro. Los trabajos que contenga se borran junto con sus entregas y sus notas.'
                              : 'La sección está vacía, así que no se pierde material.',
                          detalles: [
                            { etiqueta: 'Sección', valor: s.titulo },
                            { etiqueta: 'Contiene', valor: `${s.items.length} elementos` },
                          ],
                          ejecutar: () =>
                            administrar(() => borrarSeccion(id, s.id), 'Sección borrada.'),
                        })
                      }
                      onAgregarElemento={(s) => setFormulario({ que: 'elemento', seccion: s })}
                      onEditarElemento={(s, item) =>
                        setFormulario({ que: 'elemento', seccion: s, elemento: item })
                      }
                      onMoverElemento={(s, item, destino) =>
                        administrar(() => moverElemento(id, s.id, item.id, destino))
                      }
                      onBorrarElemento={(s, item) =>
                        pedirBorrado({
                          titulo: '¿Borrás este elemento?',
                          mensaje:
                            item.tipo === 'tarea'
                              ? 'Es un trabajo: se borran también las entregas y las notas que ya hayas cargado.'
                              : 'El curso deja de verlo en el acto.',
                          detalles: [
                            { etiqueta: 'Elemento', valor: item.titulo },
                            { etiqueta: 'Sección', valor: s.titulo },
                          ],
                          ejecutar: () =>
                            administrar(
                              () => borrarElemento(id, s.id, item.id),
                              'Elemento borrado.'
                            ),
                        })
                      }
                      onAlternarEntrega={(item) =>
                        administrar(
                          () => cambiarEntrega(id, item.tareaId, item.cerrada === true),
                          item.cerrada === true
                            ? 'Entrega reabierta.'
                            : 'Entrega cerrada.'
                        )
                      }
                    />
                  ))}

                  {editando && !formulario && (
                    <button
                      type="button"
                      className="boton-seccion-nueva"
                      onClick={() => setFormulario({ que: 'seccion' })}
                    >
                      <IconoMas width={18} height={18} />
                      Agregar una sección
                    </button>
                  )}
                </div>
              )}
            </>
          )}

          {pestana === 'anuncios' && (
            <>
              <div className="modulo-barra">
                <h2>Anuncios</h2>
                {puedeGestionar && !formulario && (
                  <button
                    type="button"
                    className="boton-principal"
                    onClick={() => setFormulario({ que: 'anuncio' })}
                  >
                    <IconoMas width={16} height={16} />
                    Publicar un anuncio
                  </button>
                )}
              </div>

              {formulario?.que === 'anuncio' && (
                <FormularioAnuncio
                  anuncio={formulario.anuncio}
                  trabajando={trabajando}
                  onCancelar={() => setFormulario(null)}
                  onGuardar={(valores) =>
                    administrar(
                      () =>
                        formulario.anuncio
                          ? editarAnuncio(id, formulario.anuncio.id, valores)
                          : publicarAnuncio(id, valores),
                      formulario.anuncio ? 'Anuncio actualizado.' : 'Anuncio publicado.'
                    )
                  }
                />
              )}

              <Anuncios
                anuncios={anuncios}
                gestionando={puedeGestionar}
                onEditar={(a) => setFormulario({ que: 'anuncio', anuncio: a })}
                onBorrar={(a) =>
                  pedirBorrado({
                    titulo: '¿Borrás este anuncio?',
                    mensaje: 'El curso deja de verlo en el acto.',
                    detalles: [{ etiqueta: 'Anuncio', valor: a.titulo }],
                    ejecutar: () =>
                      administrar(() => borrarAnuncio(id, a.id), 'Anuncio borrado.'),
                  })
                }
              />
            </>
          )}

          {pestana === 'participantes' && (
            <>
              <div className="modulo-barra">
                <h2>Participantes</h2>
              </div>
              <Participantes participantes={participantes} yo={yo} />
            </>
          )}

          {pestana === 'asistencias' && (
            <>
              <div className="modulo-barra">
                <h2>Asistencias</h2>
              </div>
              <AsistenciasDelModulo cursoId={id} puedeGestionar={puedeGestionar} />
            </>
          )}

          {pestana === 'notas' && (
            <>
              <div className="modulo-barra">
                <h2>Notas</h2>
              </div>

              {puedeGestionar ? (
                <PanelNotas
                  datos={notas}
                  trabajando={trabajando}
                  onFijarCierre={(valores) =>
                    administrar(async () => {
                      await fijarCierre(id, valores);
                      setNotas(await obtenerNotas(id));
                      return {};
                    }, 'Condición actualizada.')
                  }
                  onGuardar={(valores) =>
                    administrar(async () => {
                      setNotas(await guardarNota(id, valores));
                      return {};
                    }, 'Nota guardada.')
                  }
                />
              ) : (
                <MisNotas datos={misNotas} />
              )}
            </>
          )}
        </section>

        <PanelModulo
          curso={curso}
          participantes={participantes}
          cursada={cursada}
          proximas={proximas}
          avance={avance}
          seguimiento={puedeGestionar ? seguimiento : null}
          puedeGestionar={puedeGestionar}
          onAgregarClase={(datos) =>
            administrar(() => agregarDiaDeClase(id, datos), 'Día de clase agregado.')
          }
          onQuitarClase={(clase) =>
            administrar(
              () => quitarDiaDeClase(id, clase.diaNumero, clase.desde),
              'Día de clase quitado.'
            )
          }
        />
      </div>

      {entregas && (
        <EntregasSeccion
          datos={entregas.cargando ? null : entregas}
          onCerrar={() => setEntregas(null)}
          onCorregir={(alumno, trabajo) =>
            setCorrigiendo({
              alumno,
              trabajo: { id: trabajo.tareaId, titulo: trabajo.titulo },
              nota:
                trabajo.nota === null && !trabajo.estado
                  ? null
                  : {
                      nota: trabajo.nota,
                      estado: trabajo.estado,
                      comentario: trabajo.devolucion,
                    },
            })
          }
        />
      )}

      {corrigiendo && (
        <Correccion
          alumno={corrigiendo.alumno}
          trabajo={corrigiendo.trabajo}
          nota={corrigiendo.nota}
          estados={notas?.estados ?? ['Aprobado', 'Desaprobado', 'Entregado', 'Sin entregar']}
          trabajando={trabajando}
          onGuardar={guardarCorreccion}
          onCerrar={() => setCorrigiendo(null)}
        />
      )}

      {aConfirmar && (
        <Confirmacion
          titulo={aConfirmar.titulo}
          mensaje={aConfirmar.mensaje}
          detalles={aConfirmar.detalles}
          textoConfirmar="Sí, borrar"
          peligro
          trabajando={trabajando}
          onConfirmar={aConfirmar.ejecutar}
          onCancelar={() => setAConfirmar(null)}
        />
      )}
    </div>
  );
}
