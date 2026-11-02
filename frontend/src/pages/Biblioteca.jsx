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
} from '../services/api.js';
import Encabezado from '../components/Encabezado.jsx';
import Desplegable from '../components/Desplegable.jsx';
import TarjetaLibro, { nombreEstado } from '../components/TarjetaLibro.jsx';
import DetalleLibro from '../components/DetalleLibro.jsx';
import FormularioAporte from '../components/FormularioAporte.jsx';
import { hace } from '../services/fechas.js';
import { IconoBuscar, IconoSubir, IconoAdvertencia, IconoLibro } from '../components/Iconos.jsx';

const campos = [
  { valor: 'todo', nombre: 'En todo' },
  { valor: 'titulo', nombre: 'Título' },
  { valor: 'autor', nombre: 'Autor' },
  { valor: 'isbn', nombre: 'ISBN' },
  { valor: 'tema', nombre: 'Tema' },
];

const fuentes = [
  { valor: 'todo', nombre: 'Campus y catálogos' },
  { valor: 'campus', nombre: 'Solo el campus' },
  { valor: 'externos', nombre: 'Solo catálogos externos' },
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
  fuente: 'todo',
  categoria: '',
  tipo: '',
  carrera: '',
  materia: '',
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
  const [aviso, setAviso] = useState(null);

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
    () => Object.keys(FILTROS_VACIOS).some((c) => filtros[c] !== FILTROS_VACIOS[c]),
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

  function moderar(material, accion) {
    const motivo =
      accion === 'rechazar'
        ? window.prompt(`¿Por qué se rechaza "${material.titulo}"?\nQuien lo subió va a ver este motivo.`)
        : null;
    if (accion === 'rechazar' && !motivo?.trim()) return;

    const hacer = accion === 'aprobar' ? aprobarMaterial(material.id) : rechazarMaterial(material.id, motivo);
    hacer
      .then(() => {
        setAviso(accion === 'aprobar' ? 'Material aprobado' : 'Material rechazado');
        setTimeout(() => setAviso(null), 2500);
        traerOtra();
        obtenerOpcionesBiblioteca().then(setOpciones).catch(() => {});
      })
      .catch((e) => setError(e.message));
  }

  const pestanas = [
    { id: 'catalogo', nombre: 'Catálogo' },
    { id: 'favoritos', nombre: 'Guardados' },
    { id: 'aportes', nombre: 'Mis aportes' },
    ...(opciones?.puedeModerar
      ? [{ id: 'revision', nombre: 'Revisión', cuenta: opciones.pendientes }]
      : []),
  ];

  const propios = resultado?.materiales ?? [];
  const externos = resultado?.externos ?? [];
  const sinNada = !cargando && propios.length === 0 && externos.length === 0;

  return (
    <div className="pagina">
      <Encabezado
        titulo="Biblioteca"
        descripcion="Explorá libros y recursos para aprender, estudiar y compartir conocimientos"
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
            Aportar material
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
      {aviso && <p className="biblioteca-aviso">{aviso}</p>}

      {pestana === 'catalogo' && (
        <>
          {/* ---------- Categorías ---------- */}
          <div className="biblioteca-categorias">
            <button
              type="button"
              className={filtros.categoria === '' ? 'chip activo' : 'chip'}
              onClick={() => cambiarFiltro('categoria', '')}
            >
              Todas
              <small>{opciones?.total ?? 0}</small>
            </button>
            {(opciones?.categorias ?? [])
              .filter((c) => c.cuantos > 0 || c.id === filtros.categoria)
              .map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={filtros.categoria === c.id ? 'chip activo' : 'chip'}
                  onClick={() => cambiarFiltro('categoria', filtros.categoria === c.id ? '' : c.id)}
                >
                  {c.nombre}
                  <small>{c.cuantos}</small>
                </button>
              ))}
          </div>

          {/* ---------- Filtros ---------- */}
          <div className="biblioteca-filtros">
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
              valor={filtros.carrera}
              opciones={[
                { valor: '', nombre: 'Todas las carreras' },
                ...(opciones?.carreras ?? []).map((c) => ({ valor: c, nombre: c })),
              ]}
              onCambiar={(v) => cambiarFiltro('carrera', v)}
              etiqueta="Carrera"
            />
            <Desplegable
              valor={filtros.materia}
              opciones={[
                { valor: '', nombre: 'Todas las materias' },
                ...(opciones?.materias ?? []).map((m) => ({ valor: m, nombre: m })),
              ]}
              onCambiar={(v) => cambiarFiltro('materia', v)}
              etiqueta="Materia"
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
                  En el campus <small>{resultado.total}</small>
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
                  {filtros.fuente === 'campus'
                    ? 'Probá buscando también en los catálogos externos.'
                    : 'Probá con otras palabras, o sacá algún filtro.'}
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
                Lo que subas pasa primero por un docente y después aparece en el catálogo.
              </p>
              {opciones?.puedeAportar && (
                <button type="button" className="boton-principal" onClick={() => setAportando(true)}>
                  <IconoSubir width={18} height={18} />
                  Aportar material
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
              <p className="texto-suave">Cuando alguien aporte material, aparece acá.</p>
            </div>
          )}
          <ul className="aportes-lista">
            {(otraLista?.materiales ?? []).map((m) => (
              <li key={m.id} className="aporte-fila revision">
                <button type="button" className="aporte-fila-titulo" onClick={() => setAbierto(m)}>
                  <strong>{m.titulo}</strong>
                  <small>
                    {m.subidoPorNombre} · {hace(m.creado)}
                    {m.tieneArchivo ? ` · ${m.archivo.nombre}` : ''}
                  </small>
                </button>
                <div className="aporte-fila-acciones">
                  <button
                    type="button"
                    className="boton-suave"
                    onClick={() => moderar(m, 'rechazar')}
                  >
                    Rechazar
                  </button>
                  <button
                    type="button"
                    className="boton-principal"
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

      {aportando && (
        <FormularioAporte
          opciones={opciones}
          onCerrar={() => setAportando(false)}
          onListo={() => {
            setAportando(false);
            setAviso(
              opciones?.puedeModerar
                ? 'Material publicado'
                : 'Aporte enviado. Un docente lo va a revisar.'
            );
            setTimeout(() => setAviso(null), 4000);
            setPestana('aportes');
            obtenerOpcionesBiblioteca().then(setOpciones).catch(() => {});
          }}
        />
      )}
    </div>
  );
}
