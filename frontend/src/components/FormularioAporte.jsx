import { useEffect, useRef, useState } from 'react';
import { aportarMaterial, subirArchivoMaterial } from '../services/api.js';
import Desplegable from './Desplegable.jsx';
import { IconoCerrar, IconoAdjuntar, IconoAdvertencia } from './Iconos.jsx';

// Lo mismo que acepta el backend. Acá se revisa para avisar rápido; la
// comprobación que vale (incluida la de los bytes del archivo) es la de allá.
const FORMATOS = {
  pdf: 'application/pdf',
  epub: 'application/epub+zip',
};
const MAX_MB = 15;
const ACEPTADOS = Object.keys(FORMATOS).map((e) => e.toUpperCase());

const tipos = [
  { valor: 'apunte', nombre: 'Apunte' },
  { valor: 'resumen', nombre: 'Resumen' },
  { valor: 'libro', nombre: 'Libro' },
  { valor: 'manual', nombre: 'Manual' },
  { valor: 'guia', nombre: 'Guía' },
  { valor: 'ejercicio', nombre: 'Ejercicios' },
  { valor: 'otro', nombre: 'Otro' },
];

const idiomas = [
  { valor: 'es', nombre: 'Español' },
  { valor: 'en', nombre: 'Inglés' },
  { valor: 'pt', nombre: 'Portugués' },
  { valor: 'fr', nombre: 'Francés' },
];

function pesoLegible(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} kB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FormularioAporte({ opciones, onCerrar, onListo }) {
  const [datos, setDatos] = useState({
    titulo: '',
    autor: '',
    descripcion: '',
    tipo: 'apunte',
    carrera: opciones?.carreras?.[0] ?? '',
    materia: '',
    anio: '',
    idioma: 'es',
    isbn: '',
    categoria: opciones?.categorias?.[0]?.id ?? 'otros',
    enlace: '',
    licencia: '',
    portada: '',
  });
  const [archivo, setArchivo] = useState(null);
  const [autorizado, setAutorizado] = useState(false);
  const [avance, setAvance] = useState(null);
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const campoArchivo = useRef(null);

  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !guardando) onCerrar();
    }
    document.addEventListener('keydown', alTeclado);
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
  }, [onCerrar, guardando]);

  const cambiar = (campo) => (valor) => setDatos((d) => ({ ...d, [campo]: valor }));

  function elegirArchivo(e) {
    const elegido = e.target.files?.[0];
    setError(null);
    if (!elegido) {
      setArchivo(null);
      return;
    }

    const extension = elegido.name.split('.').pop()?.toLowerCase();
    if (!FORMATOS[extension]) {
      setError(`Solo se aceptan archivos ${ACEPTADOS.join(' y ')}`);
      e.target.value = '';
      return;
    }
    // El navegador a veces no sabe el tipo (type vacío): eso no es motivo
    // para rechazarlo, el backend igual mira los bytes.
    if (elegido.type && elegido.type !== FORMATOS[extension]) {
      setError('El tipo del archivo no coincide con su extensión');
      e.target.value = '';
      return;
    }
    if (elegido.size === 0) {
      setError('El archivo está vacío');
      e.target.value = '';
      return;
    }
    if (elegido.size > MAX_MB * 1024 * 1024) {
      setError(`El archivo supera los ${MAX_MB} MB`);
      e.target.value = '';
      return;
    }

    setArchivo(elegido);
  }

  async function enviar(e) {
    e.preventDefault();
    setError(null);

    if (!datos.titulo.trim()) {
      setError('El material necesita un título');
      return;
    }
    if (!autorizado) {
      setError('Hay que confirmar que tenés autorización para compartir el material');
      return;
    }
    if (!archivo && !datos.enlace.trim()) {
      setError('Subí el archivo o indicá el enlace a la fuente original');
      return;
    }

    setGuardando(true);
    try {
      // Primero la ficha, después el archivo: así el backend ya tiene a qué
      // material asociarlo y puede comprobar los permisos una sola vez.
      const material = await aportarMaterial({ ...datos, autorizado: true });

      if (archivo) {
        setAvance(0);
        await subirArchivoMaterial(material.id, archivo, setAvance);
      }

      onListo?.(material);
    } catch (fallo) {
      setError(fallo.message);
      setGuardando(false);
      setAvance(null);
    }
  }

  return (
    <div className="lector-fondo" onClick={() => !guardando && onCerrar()} role="presentation">
      <form
        className="lector aporte"
        onClick={(e) => e.stopPropagation()}
        onSubmit={enviar}
        aria-label="Aportar material a la biblioteca"
      >
        <button
          type="button"
          className="lector-cerrar"
          onClick={onCerrar}
          disabled={guardando}
          aria-label="Cerrar"
        >
          <IconoCerrar />
        </button>

        <header className="aporte-cabecera">
          <h2>Aportar material</h2>
          <p className="texto-suave">
            Lo que subas queda esperando que un docente lo revise antes de aparecer en el catálogo.
          </p>
        </header>

        <div className="aporte-campos">
          <label className="ancho-completo">
            <span>Título del material *</span>
            <input
              type="text"
              value={datos.titulo}
              onChange={(e) => cambiar('titulo')(e.target.value)}
              maxLength={200}
              required
            />
          </label>

          <label>
            <span>Autor</span>
            <input
              type="text"
              value={datos.autor}
              onChange={(e) => cambiar('autor')(e.target.value)}
              placeholder="Si lo dejás vacío va tu nombre"
            />
          </label>

          <label>
            <span>Tipo</span>
            <Desplegable
              valor={datos.tipo}
              opciones={tipos}
              onCambiar={cambiar('tipo')}
              etiqueta="Tipo de material"
            />
          </label>

          <label className="ancho-completo">
            <span>Descripción</span>
            <textarea
              rows={3}
              value={datos.descripcion}
              onChange={(e) => cambiar('descripcion')(e.target.value)}
              placeholder="De qué trata y para qué sirve"
            />
          </label>

          <label>
            <span>Carrera</span>
            <Desplegable
              valor={datos.carrera}
              opciones={(opciones?.carreras ?? []).map((c) => ({ valor: c, nombre: c }))}
              onCambiar={cambiar('carrera')}
              etiqueta="Carrera"
            />
          </label>

          <label>
            <span>Materia</span>
            <Desplegable
              valor={datos.materia}
              opciones={[
                { valor: '', nombre: 'Sin materia' },
                ...(opciones?.materias ?? []).map((m) => ({ valor: m, nombre: m })),
              ]}
              onCambiar={cambiar('materia')}
              etiqueta="Materia"
            />
          </label>

          <label>
            <span>Categoría</span>
            <Desplegable
              valor={datos.categoria}
              opciones={(opciones?.categorias ?? []).map((c) => ({ valor: c.id, nombre: c.nombre }))}
              onCambiar={cambiar('categoria')}
              etiqueta="Categoría"
            />
          </label>

          <label>
            <span>Idioma</span>
            <Desplegable
              valor={datos.idioma}
              opciones={idiomas}
              onCambiar={cambiar('idioma')}
              etiqueta="Idioma"
            />
          </label>

          <label>
            <span>Año o nivel</span>
            <input
              type="text"
              value={datos.anio}
              onChange={(e) => cambiar('anio')(e.target.value)}
              placeholder="2.º año"
            />
          </label>

          <label>
            <span>ISBN</span>
            <input
              type="text"
              value={datos.isbn}
              onChange={(e) => cambiar('isbn')(e.target.value)}
              placeholder="Si es un libro publicado"
            />
          </label>

          {/* ---------- El archivo ---------- */}
          <div className="aporte-archivo ancho-completo">
            <span className="aporte-etiqueta">Archivo</span>

            <input
              type="file"
              ref={campoArchivo}
              accept=".pdf,.epub,application/pdf,application/epub+zip"
              onChange={elegirArchivo}
              hidden
            />

            {archivo ? (
              <div className="aporte-ficha-archivo">
                <IconoAdjuntar width={18} height={18} />
                <span>
                  <strong>{archivo.name}</strong>
                  <small>{pesoLegible(archivo.size)}</small>
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setArchivo(null);
                    if (campoArchivo.current) campoArchivo.current.value = '';
                  }}
                  disabled={guardando}
                  aria-label="Quitar el archivo"
                >
                  <IconoCerrar width={16} height={16} />
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="boton-suave"
                onClick={() => campoArchivo.current?.click()}
              >
                <IconoAdjuntar width={16} height={16} />
                Elegir un PDF o EPUB
              </button>
            )}

            <small className="texto-suave">
              Hasta {MAX_MB} MB. Si no tenés derecho a alojar el archivo, dejalo vacío y poné abajo
              el enlace a la fuente original.
            </small>
          </div>

          <label className="ancho-completo">
            <span>Enlace a la fuente original</span>
            <input
              type="url"
              value={datos.enlace}
              onChange={(e) => cambiar('enlace')(e.target.value)}
              placeholder="https://…"
              disabled={Boolean(archivo)}
            />
          </label>

          <label>
            <span>Licencia o referencia</span>
            <input
              type="text"
              value={datos.licencia}
              onChange={(e) => cambiar('licencia')(e.target.value)}
              placeholder="CC BY 4.0, material de cátedra…"
            />
          </label>

          <label>
            <span>Portada (dirección)</span>
            <input
              type="url"
              value={datos.portada}
              onChange={(e) => cambiar('portada')(e.target.value)}
              placeholder="https://…"
            />
          </label>
        </div>

        <label className="aporte-autorizacion">
          <input
            type="checkbox"
            className="interruptor"
            checked={autorizado}
            onChange={(e) => setAutorizado(e.target.checked)}
          />
          <span>
            <strong>Tengo autorización para compartir este material</strong>
            <small>
              Es mío, es de dominio público, su licencia lo permite, o la cátedra lo autorizó.
              Subir material protegido sin permiso no está permitido.
            </small>
          </span>
        </label>

        {error && (
          <p className="error aporte-error">
            <IconoAdvertencia width={16} height={16} />
            {error}
          </p>
        )}

        {avance !== null && (
          <div className="aporte-avance" role="status">
            <div className="barra-pista">
              <div className="barra-relleno" style={{ width: `${avance}%` }} />
            </div>
            <small>{avance < 100 ? `Subiendo… ${avance}%` : 'Guardando en el servidor…'}</small>
          </div>
        )}

        <div className="aporte-pie">
          <button type="button" className="boton-suave" onClick={onCerrar} disabled={guardando}>
            Cancelar
          </button>
          <button type="submit" className="boton-principal" disabled={guardando}>
            {guardando ? 'Enviando…' : 'Enviar aporte'}
          </button>
        </div>
      </form>
    </div>
  );
}
