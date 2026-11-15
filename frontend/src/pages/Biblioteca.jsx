import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  obtenerOpcionesBiblioteca,
  buscarEnBiblioteca,
  obtenerMisAportes,
  obtenerPendientesBiblioteca,
  obtenerFavoritosBiblioteca,
  marcarFavoritoBiblioteca,
  aprobarMaterial,
  rechazarMaterial,
  enlaceDescarga,
} from '../services/api.js';
import { avisar } from '../services/avisos.js';
import Encabezado from '../components/Encabezado.jsx';
import Desplegable from '../components/Desplegable.jsx';
import DesplegableVarios from '../components/DesplegableVarios.jsx';
import TarjetaLibro, { nombreEstado } from '../components/TarjetaLibro.jsx';
import DetalleLibro from '../components/DetalleLibro.jsx';
import FormularioAporte from '../components/FormularioAporte.jsx';
import { hace } from '../services/fechas.js';
import {
  IconoBuscar,
  IconoSubir,
  IconoAdvertencia,
  IconoLibro,
  IconoCerrar,
} from '../components/Iconos.jsx';

const campos = [
  { valor: 'todo', nombre: 'En todo' },
  { valor: 'titulo', nombre: 'Título' },
  { valor: 'autor', nombre: 'Autor' },
  { valor: 'isbn', nombre: 'ISBN' },
  { valor: 'tema', nombre: 'Tema' },
];

// La biblioteca es la de tus materias. Los catálogos externos son otra cosa
// —ayudan a encontrar un libro, no viven acá—, así que hay que pedirlos.
const fuentes = [
  { valor: 'campus', nombre: 'En el campus' },
  { valor: 'externos', nombre: 'Catálogos externos' },
];

const ordenes = [
  { valor: 'fecha', nombre: 'Más recientes' },
  { valor: 'titulo', nombre: 'Por título' },
  { valor: 'autor', nombre: 'Por autor' },
];

const nombreTipoFiltro = {
  libro: 'Libros',
  apunte: 'Apuntes',
  resumen: 'Resúmenes',
  manual: 'Manuales',
  guia: 'Guías',
  ejercicio: 'Ejercicios',
  otro: 'Otros',
};

const idiomas = { es: 'Español', en: 'Inglés', pt: 'Portugués', fr: 'Francés', it: 'Italiano' };

const FILTROS_VACIOS = {
  q: '',
  campo: 'todo',
  fuente: 'campus',
  tipo: '',
  materiaIds: [],
  idioma: '',
  orden: 'fecha',
};

// Mientras llegan los resultados se dibujan recuadros del tamaño de las
// tarjetas, para que la grilla no salte cuando aparecen.
function Esqueletos({ cuantos = 6 }) {
  return (
    <div className="libros-grilla" aria-hidden="true">
      {Array.from({ length: cuantos }, (_, i) => (
        <div key={i} className="libro-tarjeta esqueleto" />
      ))}
    </div>
  );
}

/** Rechazar pide motivo: sin él, quien aportó no sabe qué corregir. */
function MotivoDelRechazo({ material, trabajando, onCerrar, onRechazar }) {
  const [motivo, setMotivo] = useState('');

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !trabajando) onCerrar();
    }
    window.addEventListener('keydown', alTeclado);
    return () => window.removeEventListener('keydown', alTeclado);
  }, [onCerrar, trabajando]);

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
          onRechazar(motivo.trim());
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

        <h3>Rechazar el aporte</h3>
        <p className="correccion-trabajo">
          {material.titulo} · {material.materia}
        </p>

        <label>
          <span>Motivo del rechazo *</span>
          <textarea
            rows={4}
            value={motivo}
            maxLength={500}
            autoFocus
            placeholder="Qué habría que corregir, o por qué no corresponde a la materia"
            onChange={(e) => setMotivo(e.target.value)}
          />
          <small className="texto-suave">
            {material.subidoPorNombre} va a recibir este motivo en Mensajes.
          </small>
        </label>

        <div className="editor-botones">
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={trabajando}>
            Cancelar
          </button>
          <button
            type="submit"
            className="boton-principal peligro"
            disabled={trabajando || !motivo.trim()}
          >
            Rechazar
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Biblioteca() {
  const [opciones, setOpciones] = useState(null);
  const [pestana, setPestana] = useState('catalogo');

  const [filtros, setFiltros] = useState(FILTROS_VACIOS);
  // Lo que se escribe se separa de lo que se busca: la consulta sale recién
  // cuando dejás de escribir, así no se pega a las APIs en cada tecla.
  const [escrito, setEscrito] = useState('');
  const [pagina, setPagina] = useState(1);

  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  const [otraLista, setOtraLista] = useState(null);
  const [abierto, setAbierto] = useState(null);
  const [aportando, setAportando] = useState(false);
  // El aporte que se está por rechazar, mientras se escribe el motivo
  const [rechazando, setRechazando] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  const listaRef = useRef(null);

  useEffect(() => {
    obtenerOpcionesBiblioteca().then(setOpciones).catch((e) => setError(e.message));
  }, []);

  // Esperar a que pare de escribir antes de buscar
  useEffect(() => {
    const reloj = setTimeout(() => {
      setFiltros((f) => (f.q === escrito ? f : { ...f, q: escrito }));
      setPagina(1);
    }, 400);
    return () => clearTimeout(reloj);
  }, [escrito]);

  const buscar = useCallback(() => {
    setCargando(true);
    setError(null);
    buscarEnBiblioteca({ ...filtros, pagina })
      .then(setResultado)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [filtros, pagina]);

  useEffect(() => {
    if (pestana === 'catalogo') buscar();
  }, [buscar, pestana]);

  // Las otras pestañas (favoritos, mis aportes, revisión) son listas simples
  const traerOtra = useCallback(() => {
    const pedir = {
      favoritos: obtenerFavoritosBiblioteca,
      aportes: obtenerMisAportes,
      revision: obtenerPendientesBiblioteca,
    }[pestana];
    if (!pedir) return;

    setCargando(true);
    setError(null);
    pedir()
      .then(setOtraLista)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [pestana]);

  useEffect(() => {
    traerOtra();
  }, [traerOtra]);

  function cambiarFiltro(campo, valor) {
    setFiltros((f) => ({ ...f, [campo]: valor }));
    setPagina(1);
  }

  function limpiar() {
    setFiltros(FILTROS_VACIOS);
    setEscrito('');
    setPagina(1);
  }

  const hayFiltros = useMemo(
    () =>
      Object.keys(FILTROS_VACIOS).some((c) =>
        Array.isArray(FILTROS_VACIOS[c]) ? filtros[c].length > 0 : filtros[c] !== FILTROS_VACIOS[c]
      ),
    [filtros]
  );

  // Marcar un favorito cambia esa tarjeta sola, sin volver a pedir la lista
  function alternarFavorito(libro) {
    const puesto = !libro.favorito;
    marcarFavoritoBiblioteca(libro.id, puesto)
      .then(() => {
        const retocar = (lista) =>
          (lista ?? []).map((l) => (String(l.id) === String(libro.id) ? { ...l, favorito: puesto } : l));

        setResultado((r) =>
          r ? { ...r, materiales: retocar(r.materiales), externos: retocar(r.externos) } : r
        );
        setAbierto((a) => (a && String(a.id) === String(libro.id) ? { ...a, favorito: puesto } : a));
        if (pestana === 'favoritos') traerOtra();
      })
      .catch((e) => setError(e.message));
  }

  function moderar(material, accion, motivo) {
    setTrabajando(true);
    const hacer =
      accion === 'aprobar'
        ? aprobarMaterial(material.id)
        : rechazarMaterial(material.id, motivo);

    hacer
      .then(() => {
        avisar(
          accion === 'aprobar'
            ? `"${material.titulo}" ya está publicado. Quien lo aportó recibió el aviso.`
            : `Aporte rechazado. Quien lo aportó va a ver el motivo.`
        );
        setRechazando(null);
        traerOtra();
        obtenerOpcionesBiblioteca().then(setOpciones).catch(() => {});
      })
      .catch((e) => avisar(e.message, 'error'))
      .finally(() => setTrabajando(false));
  }

  const pestanas = [
    { id: 'catalogo', nombre: 'Catálogo' },
    { id: 'favoritos', nombre: 'Guardados' },
    { id: 'aportes', nombre: 'Mis aportes' },
    ...(opciones?.puedeModerar
      ? [{ id: 'revision', nombre: 'Revisión', cuenta: opciones.pendientes }]
      : []),
  ];

  const misMaterias = opciones?.materias ?? [];
  // Quien supervisa ve el plan entero: ofrecerle veinte materias vacías es
  // ruido. Se queda con las que tienen algo, más las que ya haya elegido.
  // Para el resto, la materia propia se ofrece aunque esté vacía: es la que
  // va a llenar.
  const materiasParaElegir = opciones?.superviso
    ? misMaterias.filter(
      (m) => m.cuantos > 0 || m.pendientes > 0 || filtros.materiaIds.includes(m.id)
    )
    : misMaterias;

  const elegidas = misMaterias.filter((m) => filtros.materiaIds.includes(m.id));

  const propios = resultado?.materiales ?? [];
  const externos = resultado?.externos ?? [];
  const sinNada = !cargando && propios.length === 0 && externos.length === 0;

  return (
    <div className="pagina">
      <Encabezado
        titulo="Biblioteca"
        descripcion="El material de cada una de tus materias, y lo que aportes a ellas"
      />

      <div className="biblioteca-barra">
        <div className="barra-busqueda">
          <IconoBuscar />
          <input
            type="search"
            value={escrito}
            onChange={(e) => setEscrito(e.target.value)}
            placeholder="Buscar por título, autor, ISBN o tema"
            aria-label="Buscar en la biblioteca"
          />
        </div>

        <Desplegable
          valor={filtros.campo}
          opciones={campos}
          onCambiar={(v) => cambiarFiltro('campo', v)}
          etiqueta="Dónde buscar"
        />

        {opciones?.puedeAportar && (
          <button type="button" className="boton-principal" onClick={() => setAportando(true)}>
            <IconoSubir width={18} height={18} />
            {opciones?.publicaDirecto ? 'Subir material' : 'Enviar aporte'}
          </button>
        )}
      </div>

      <nav className="pestanas" aria-label="Secciones de la biblioteca">
        {pestanas.map((p) => (
          <button
            key={p.id}
            type="button"
            className={pestana === p.id ? 'pestana activa' : 'pestana'}
            onClick={() => setPestana(p.id)}
            aria-current={pestana === p.id}
          >
            {p.nombre}
            {p.cuenta > 0 && <small className="pestana-cantidad">{p.cuenta}</small>}
          </button>
        ))}
      </nav>

      {error && <p className="error">{error}</p>}

      {/* Sin materias no hay biblioteca que mostrar: no es un error, es que
          todavía no está inscripto ni tiene cátedra a cargo. */}
      {opciones && misMaterias.length === 0 && (
        <div className="biblioteca-vacio">
          <IconoLibro width={34} height={34} />
          <h3>Todavía no tenés materias</h3>
          <p className="texto-suave">
            La biblioteca se arma por materia: vas a ver el material de las que curses o dictes.
          </p>
        </div>
      )}

      {pestana === 'catalogo' && (
        <>
          {/* ---------- Filtros ---------- */}
          <div className="biblioteca-filtros">
            {/* La materia es el filtro que manda: la biblioteca es una por
                materia, y acá se eligen una, varias o todas. */}
            <DesplegableVarios
              valores={filtros.materiaIds}
              opciones={materiasParaElegir.map((m) => ({
                valor: m.id,
                nombre: m.nombre,
                detalle: m.pendientes > 0 ? `${m.cuantos} · ${m.pendientes} a revisar` : m.cuantos,
              }))}
              onCambiar={(v) => cambiarFiltro('materiaIds', v)}
              etiqueta="Materias"
              textoTodas={opciones?.superviso ? 'Todas las materias' : 'Todas mis materias'}
              className="desplegable-materias"
            />
            <Desplegable
              valor={filtros.fuente}
              opciones={fuentes}
              onCambiar={(v) => cambiarFiltro('fuente', v)}
              etiqueta="Fuente"
            />
            <Desplegable
              valor={filtros.tipo}
              opciones={[
                { valor: '', nombre: 'Todo tipo' },
                ...(opciones?.tipos ?? []).map((t) => ({ valor: t, nombre: nombreTipoFiltro[t] ?? t })),
              ]}
              onCambiar={(v) => cambiarFiltro('tipo', v)}
              etiqueta="Tipo de material"
            />
            <Desplegable
              valor={filtros.idioma}
              opciones={[
                { valor: '', nombre: 'Todos los idiomas' },
                ...(opciones?.idiomas ?? []).map((i) => ({ valor: i, nombre: idiomas[i] ?? i })),
              ]}
              onCambiar={(v) => cambiarFiltro('idioma', v)}
              etiqueta="Idioma"
            />
            <Desplegable
              valor={filtros.orden}
              opciones={ordenes}
              onCambiar={(v) => cambiarFiltro('orden', v)}
              etiqueta="Ordenar"
            />

            {hayFiltros && (
              <button type="button" className="boton-suave" onClick={limpiar}>
                Limpiar filtros
              </button>
            )}
          </div>

          {/* ---------- Resultados ---------- */}
          <section className="biblioteca-resultados" ref={listaRef}>
            {cargando && !resultado && <Esqueletos />}

            {propios.length > 0 && (
              <>
                <h2 className="biblioteca-titulo">
                  {elegidas.length === 1
                    ? elegidas[0].nombre
                    : elegidas.length > 1
                      ? `${elegidas.length} materias`
                      : opciones?.superviso
                        ? 'Todo el material'
                        : 'El material de tus materias'}{' '}
                  <small>{resultado.total}</small>
                </h2>
                <div className="libros-grilla">
                  {propios.map((m, i) => (
                    <TarjetaLibro
                      key={m.id}
                      libro={m}
                      indice={i}
                      onAbrir={setAbierto}
                      onFavorito={alternarFavorito}
                    />
                  ))}
                </div>

                {resultado.paginas > 1 && (
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
                      Página {resultado.pagina} de {resultado.paginas}
                    </span>
                    <button
                      type="button"
                      className="boton-suave"
                      onClick={() => setPagina((p) => Math.min(resultado.paginas, p + 1))}
                      disabled={pagina >= resultado.paginas}
                    >
                      Siguiente
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Qué pasó con cada catálogo externo. Si uno falla se dice, en
                vez de hacer como si no hubiera resultados. */}
            {(resultado?.fuentes ?? [])
              .filter((f) => f.estado !== 'ok')
              .map((f) => (
                <p key={f.nombre} className="biblioteca-fuente-caida">
                  <IconoAdvertencia width={16} height={16} />
                  {f.estado === 'limite'
                    ? 'Demasiadas búsquedas seguidas en los catálogos externos. Esperá un momento.'
                    : `${f.nombre} no respondió. Se muestra el resto.`}
                </p>
              ))}

            {externos.length > 0 && (
              <>
                <h2 className="biblioteca-titulo">
                  En catálogos externos <small>{externos.length}</small>
                </h2>
                <p className="texto-suave biblioteca-nota">
                  Estos libros no están alojados en el campus: cada tarjeta lleva a su fuente, con
                  las opciones de lectura o préstamo que esa fuente ofrezca.
                </p>
                <div className="libros-grilla">
                  {externos.map((l, i) => (
                    <TarjetaLibro
                      key={l.id}
                      libro={l}
                      indice={i}
                      onAbrir={setAbierto}
                      onFavorito={alternarFavorito}
                    />
                  ))}
                </div>
              </>
            )}

            {cargando && resultado && <Esqueletos cuantos={3} />}

            {sinNada && (
              <div className="biblioteca-vacio">
                <IconoLibro width={34} height={34} />
                <h3>No encontramos nada con eso</h3>
                <p className="texto-suave">
                  {filtros.fuente === 'externos'
                    ? 'Probá con otras palabras: se busca en Google Books y Open Library.'
                    : elegidas.length === 1
                      ? `Todavía no hay material cargado en ${elegidas[0].nombre}.`
                      : 'Todavía no hay material, o ningún filtro coincide.'}
                </p>
                {hayFiltros && (
                  <button type="button" className="boton-suave" onClick={limpiar}>
                    Limpiar filtros
                  </button>
                )}
              </div>
            )}
          </section>
        </>
      )}

      {/* ---------- Guardados ---------- */}
      {pestana === 'favoritos' && (
        <section className="biblioteca-resultados">
          {cargando && <Esqueletos cuantos={3} />}
          {!cargando && (otraLista?.materiales?.length ?? 0) === 0 && (
            <div className="biblioteca-vacio">
              <IconoLibro width={34} height={34} />
              <h3>Todavía no guardaste nada</h3>
              <p className="texto-suave">La estrellita de cada tarjeta lo guarda acá.</p>
            </div>
          )}
          {(otraLista?.materiales?.length ?? 0) > 0 && (
            <div className="libros-grilla">
              {otraLista.materiales.map((m, i) => (
                <TarjetaLibro
                  key={m.id}
                  libro={m}
                  indice={i}
                  onAbrir={setAbierto}
                  onFavorito={alternarFavorito}
                />
              ))}
            </div>
          )}
          {(otraLista?.externos?.length ?? 0) > 0 && (
            <p className="texto-suave biblioteca-nota">
              También guardaste {otraLista.externos.length} libro
              {otraLista.externos.length === 1 ? '' : 's'} de catálogos externos. Se ven buscándolos
              en el catálogo.
            </p>
          )}
        </section>
      )}

      {/* ---------- Mis aportes ---------- */}
      {pestana === 'aportes' && (
        <section className="biblioteca-resultados">
          {cargando && <Esqueletos cuantos={2} />}
          {!cargando && (otraLista?.materiales?.length ?? 0) === 0 && (
            <div className="biblioteca-vacio">
              <IconoSubir width={34} height={34} />
              <h3>Todavía no aportaste material</h3>
              <p className="texto-suave">
                Lo que subas pasa primero por el docente de la materia y después aparece en su
                biblioteca.
              </p>
              {opciones?.puedeAportar && (
                <button type="button" className="boton-principal" onClick={() => setAportando(true)}>
                  <IconoSubir width={18} height={18} />
                  {opciones?.publicaDirecto ? 'Subir material' : 'Enviar aporte'}
                </button>
              )}
            </div>
          )}
          <ul className="aportes-lista">
            {(otraLista?.materiales ?? []).map((m) => (
              <li key={m.id} className="aporte-fila">
                <button type="button" className="aporte-fila-titulo" onClick={() => setAbierto(m)}>
                  <strong>{m.titulo}</strong>
                  <small>
                    {[m.nombreCategoria, m.materia].filter(Boolean).join(' · ')} · {hace(m.creado)}
                  </small>
                </button>
                <span className={`libro-estado ${m.estado}`}>{nombreEstado[m.estado]}</span>
                {m.estado === 'rechazado' && m.motivo && (
                  <p className="aporte-motivo">
                    <IconoAdvertencia width={15} height={15} />
                    {m.motivo}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ---------- Revisión (docentes) ---------- */}
      {pestana === 'revision' && (
        <section className="biblioteca-resultados">
          {cargando && <Esqueletos cuantos={2} />}
          {!cargando && (otraLista?.materiales?.length ?? 0) === 0 && (
            <div className="biblioteca-vacio">
              <IconoLibro width={34} height={34} />
              <h3>No hay nada esperando revisión</h3>
              <p className="texto-suave">
              Acá llegan los aportes de las materias que dictás, para aprobarlos o rechazarlos.
            </p>
            </div>
          )}
          <ul className="aportes-lista">
            {(otraLista?.materiales ?? []).map((m) => (
              <li key={m.id} className="aporte-fila revision">
                <button type="button" className="aporte-fila-titulo" onClick={() => setAbierto(m)}>
                  <strong>{m.titulo}</strong>
                  <small>{m.autor ?? 'Sin autor indicado'}</small>
                </button>

                {/* Lo que hace falta para decidir sin abrir la ficha */}
                <dl className="aporte-datos">
                  <div>
                    <dt>Materia</dt>
                    <dd>{m.materia}</dd>
                  </div>
                  <div>
                    <dt>Lo aportó</dt>
                    <dd>{m.subidoPorNombre}</dd>
                  </div>
                  <div>
                    <dt>Enviado</dt>
                    <dd>{hace(m.creado)}</dd>
                  </div>
                  <div>
                    <dt>Archivo</dt>
                    <dd>
                      {m.tieneArchivo ? (
                        <a href={enlaceDescarga(m.id)}>{m.archivo.nombre}</a>
                      ) : m.enlace ? (
                        <a href={m.enlace} target="_blank" rel="noreferrer noopener">
                          Enlace a la fuente
                        </a>
                      ) : (
                        <span className="texto-suave">Sin archivo</span>
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Estado</dt>
                    <dd>
                      <span className={`libro-estado ${m.estado}`}>{nombreEstado[m.estado]}</span>
                    </dd>
                  </div>
                </dl>

                <div className="aporte-fila-acciones">
                  <button
                    type="button"
                    className="boton-suave peligro"
                    disabled={trabajando}
                    onClick={() => setRechazando(m)}
                  >
                    Rechazar
                  </button>
                  <button
                    type="button"
                    className="boton-principal"
                    disabled={trabajando}
                    onClick={() => moderar(m, 'aprobar')}
                  >
                    Aprobar
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {abierto && (
        <DetalleLibro
          libro={abierto}
          onCerrar={() => setAbierto(null)}
          onFavorito={alternarFavorito}
          onAbrir={setAbierto}
          onCambio={() => {
            buscar();
            traerOtra();
          }}
        />
      )}

      {rechazando && (
        <MotivoDelRechazo
          material={rechazando}
          trabajando={trabajando}
          onCerrar={() => setRechazando(null)}
          onRechazar={(motivo) => moderar(rechazando, 'rechazar', motivo)}
        />
      )}

      {aportando && (
        <FormularioAporte
          opciones={opciones}
          materiaSugerida={filtros.materiaIds.length === 1 ? filtros.materiaIds[0] : undefined}
          onCerrar={() => setAportando(false)}
          onListo={(material) => {
            setAportando(false);
            avisar(
              material?.estado === 'aprobado'
                ? 'Material publicado en la biblioteca de la materia.'
                : 'Aporte enviado. El docente de la materia lo va a revisar.'
            );
            setPestana(material?.estado === 'aprobado' ? 'catalogo' : 'aportes');
            obtenerOpcionesBiblioteca().then(setOpciones).catch(() => {});
          }}
        />
      )}
    </div>
  );
}
