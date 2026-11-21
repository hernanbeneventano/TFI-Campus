// Mirar un documento sin bajarlo: PDF y Word, dentro del campus.
//
// Antes el PDF iba en un `<iframe>` apuntado al archivo, para que lo dibujara
// el visor del navegador. No funcionaba, y no por un detalle: el servidor
// manda el archivo con `Content-Security-Policy: sandbox` y el iframe llevaba
// `sandbox=""`, las dos cosas puestas a propósito para que un PDF con
// JavaScript adentro no pudiera hacer nada. Con eso Chrome no arranca su
// visor y muestra «Chrome ha bloqueado esta página». Aflojar el sandbox lo
// habría arreglado entregándole el documento al navegador para que lo
// ejecute, que es justo lo que no se quería.
//
// Acá lo dibujamos **nosotros**: se piden los bytes y se los pinta en un
// canvas con pdf.js. El documento nunca se abre como documento, así que no
// hay scripts que correr ni sandbox que aflojar, y de paso se ve igual en
// todos los navegadores.
//
// Word va por el mismo camino con mammoth, que lo pasa a HTML. Es lo que
// figuraba como pendiente —«los navegadores no saben mostrar DOCX»—: no hace
// falta que sepan, ni convertirlo en el servidor.

import { useCallback, useEffect, useRef, useState } from 'react';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import {
  IconoArchivo,
  IconoDescargar,
  IconoImprimir,
  IconoPantallaCompleta,
  IconoSalirPantallaCompleta,
} from './Iconos.jsx';

// pdf.js y mammoth pesan más que todo el resto del campus junto, y la mayoría
// de las pantallas no abren un documento nunca. Se piden al abrir el primero:
// el navegador los guarda y el segundo ya es inmediato.
let _pdfjs = null;
async function cargarPdfjs() {
  if (!_pdfjs) {
    _pdfjs = await import('pdfjs-dist');
    _pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
  }
  return _pdfjs;
}

export const TIPO_PDF = 'application/pdf';
export const TIPO_DOCX =
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

/** Si este archivo se puede mirar acá adentro. */
export function sePuedeVer(archivo) {
  return Boolean(archivo?.url) && (archivo.tipo === TIPO_PDF || archivo.tipo === TIPO_DOCX);
}

// Cuánto más grande se dibuja el canvas que el lugar que ocupa: el texto de
// un PDF a 1:1 se ve lavado en una pantalla con mucha densidad.
const NITIDEZ = 2;

// El 100% es la hoja entrando entera de ancho en el lugar que hay. Desde ahí
// se agranda para leer la letra chica y se achica para ver la página entera.
// Lo más ancho que se dibuja una hoja al 100%, en píxeles.
const ANCHO_COMODO = 940;

const ZOOM_MIN = 0.5;
const ZOOM_MAX = 3;
const ZOOM_PASO = 0.25;

/** El HTML que devuelve mammoth, sin nada que pueda ejecutarse.
 *
 * Mammoth no inventa scripts, pero el documento lo escribió otra persona y
 * sus hipervínculos salen tal cual: un `href="javascript:…"` dentro de un
 * apunte alcanzaría para correr código en el campus. Se recorta a lo que un
 * texto necesita y nada más.
 */
function limpiar(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');

  doc.querySelectorAll('script, style, iframe, object, embed, link').forEach((n) => n.remove());

  doc.querySelectorAll('*').forEach((nodo) => {
    for (const attr of [...nodo.attributes]) {
      if (attr.name.toLowerCase().startsWith('on')) nodo.removeAttribute(attr.name);
    }
    const href = nodo.getAttribute('href');
    if (href && !/^(https?:|mailto:|#)/i.test(href.trim())) nodo.removeAttribute('href');
    // Mammoth trae las imágenes del documento como `data:`; cualquier otra
    // cosa sería un pedido a un servidor ajeno desde la pantalla del alumno.
    const src = nodo.getAttribute('src');
    if (src && !/^data:image\//i.test(src.trim())) nodo.removeAttribute('src');
    if (nodo.tagName === 'A') {
      nodo.setAttribute('rel', 'noopener noreferrer');
      nodo.setAttribute('target', '_blank');
    }
  });

  return doc.body.innerHTML;
}

export default function VisorDocumento({ archivo, descarga }) {
  const marco = useRef(null);
  const hojas = useRef(null);
  const lienzos = useRef([]);
  // Una copia de los bytes para imprimir: pdf.js se queda con el original
  // (lo transfiere al worker y acá queda vacío).
  const bytesPdf = useRef(null);

  const [documento, setDocumento] = useState(null); // el PDF abierto
  const [texto, setTexto] = useState(''); // el Word pasado a HTML
  const [estado, setEstado] = useState('cargando');
  const [error, setError] = useState('');
  const [pagina, setPagina] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [completa, setCompleta] = useState(false);

  const esPdf = archivo?.tipo === TIPO_PDF;
  const url = archivo?.url;
  const paginas = documento?.numPages ?? 0;

  // ---------- abrir el archivo (una vez) ----------
  useEffect(() => {
    if (!url) return undefined;
    let vigente = true;
    let abierto = null;

    (async () => {
      setEstado('cargando');
      setError('');
      setDocumento(null);
      setTexto('');
      try {
        const r = await fetch(url);
        if (!r.ok) throw new Error('No se pudo leer el archivo.');
        const bytes = await r.arrayBuffer();
        if (!vigente) return;

        if (!esPdf) {
          const mammoth = await import('mammoth/mammoth.browser.js');
          const { value } = await (mammoth.default ?? mammoth).convertToHtml({
            arrayBuffer: bytes,
          });
          if (!vigente) return;
          setTexto(limpiar(value));
          setEstado('listo');
          return;
        }

        bytesPdf.current = bytes.slice(0);
        const pdfjs = await cargarPdfjs();
        if (!vigente) return;

        abierto = await pdfjs.getDocument({
          data: bytes,
          // Un PDF puede traer JavaScript adentro. No se le da lugar para
          // correrlo: acá solo se lee la parte dibujable.
          isEvalSupported: false,
        }).promise;
        if (!vigente) {
          abierto.destroy();
          return;
        }
        setDocumento(abierto);
      } catch (e) {
        if (vigente) {
          setError(e.message || 'No se pudo mostrar el archivo.');
          setEstado('error');
        }
      }
    })();

    return () => {
      vigente = false;
      abierto?.destroy();
    };
  }, [url, esPdf]);

  // ---------- dibujar las páginas (al abrir y al cambiar el zoom) ----------
  useEffect(() => {
    if (!documento) return undefined;
    let vigente = true;

    (async () => {
      const lugar = hojas.current;
      if (!lugar) return;
      lugar.textContent = '';
      lienzos.current = [];

      // Al 100% la hoja ocupa el lugar que hay, hasta el ancho de una hoja
      // cómoda de leer: estirada a lo ancho de una pantalla grande la línea
      // se vuelve larguísima y hay que barrer la cabeza para leerla. Lo que
      // sobra queda de margen oscuro a los costados, como en cualquier
      // lector, y el zoom la lleva más allá si hace falta.
      const disponible = Math.min(Math.max(240, lugar.clientWidth - 48), ANCHO_COMODO);

      for (let n = 1; n <= documento.numPages; n += 1) {
        // eslint-disable-next-line no-await-in-loop
        const hoja = await documento.getPage(n);
        if (!vigente) return;

        const base = hoja.getViewport({ scale: 1 });
        const ancho = disponible * zoom;
        const vista = hoja.getViewport({ scale: (ancho / base.width) * NITIDEZ });

        const lienzo = document.createElement('canvas');
        lienzo.className = 'documento-pagina';
        lienzo.width = Math.floor(vista.width);
        lienzo.height = Math.floor(vista.height);
        lienzo.style.width = `${ancho}px`;
        lienzo.dataset.pagina = String(n);
        lienzo.setAttribute('aria-label', `Página ${n} de ${documento.numPages}`);
        lugar.appendChild(lienzo);
        lienzos.current.push(lienzo);

        // eslint-disable-next-line no-await-in-loop
        await hoja.render({ canvasContext: lienzo.getContext('2d'), viewport: vista }).promise;
        if (!vigente) return;
        if (n === 1) setEstado('listo');
      }
    })();

    return () => {
      vigente = false;
    };
  }, [documento, zoom]);

  // ---------- en qué página va ----------
  useEffect(() => {
    // El que se desplaza es el contenedor de afuera: el de adentro solo
    // apila las hojas.
    const lugar = hojas.current?.parentElement;
    if (!lugar || !esPdf) return undefined;

    let pedido = null;
    function mirar() {
      pedido = null;
      const corte = lugar.getBoundingClientRect().top + 80;
      let actual = 1;
      for (const lienzo of lienzos.current) {
        if (lienzo.getBoundingClientRect().top <= corte) actual = Number(lienzo.dataset.pagina);
      }
      setPagina(actual);
    }
    function alDesplazar() {
      if (pedido === null) pedido = requestAnimationFrame(mirar);
    }

    lugar.addEventListener('scroll', alDesplazar, { passive: true });
    return () => {
      lugar.removeEventListener('scroll', alDesplazar);
      if (pedido !== null) cancelAnimationFrame(pedido);
    };
  }, [esPdf, documento]);

  // ---------- pantalla completa ----------
  useEffect(() => {
    function alCambiar() {
      setCompleta(document.fullscreenElement === marco.current);
    }
    document.addEventListener('fullscreenchange', alCambiar);
    return () => document.removeEventListener('fullscreenchange', alCambiar);
  }, []);

  const irA = useCallback((n) => {
    const destino = lienzos.current[Math.min(Math.max(1, n), lienzos.current.length) - 1];
    destino?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }, []);

  function pantallaCompleta() {
    if (document.fullscreenElement) document.exitFullscreen();
    else marco.current?.requestFullscreen?.();
  }

  // Imprimir abre el PDF en una pestaña nueva y el navegador ofrece su
  // diálogo. Va desde un `blob:` armado con los bytes que ya tenemos: el
  // archivo del servidor viaja con el sandbox puesto justamente para que no
  // se abra solo, y esto es lo mismo que bajarlo y abrirlo a mano, pero sin
  // dejar el archivo en la máquina.
  function imprimir() {
    if (!bytesPdf.current) return;
    const blob = new Blob([bytesPdf.current], { type: TIPO_PDF });
    const direccion = URL.createObjectURL(blob);
    window.open(direccion, '_blank', 'noopener');
    setTimeout(() => URL.revokeObjectURL(direccion), 60000);
  }

  if (!url) return null;

  return (
    <div className={completa ? 'documento a-pantalla-completa' : 'documento'} ref={marco}>
      <div className="documento-barra">
        <span className="documento-nombre" title={archivo.nombre}>
          <IconoArchivo width={15} height={15} />
          {archivo.nombre}
        </span>

        {esPdf && paginas > 0 && (
          <span className="documento-paginas">
            <input
              type="number"
              min={1}
              max={paginas}
              value={pagina}
              onChange={(e) => {
                const n = Number(e.target.value);
                setPagina(n);
                if (n >= 1 && n <= paginas) irA(n);
              }}
              aria-label="Ir a la página"
            />
            <small>/ {paginas}</small>
          </span>
        )}

        {esPdf && (
          <span className="documento-zoom">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(ZOOM_MIN, z - ZOOM_PASO))}
              disabled={zoom <= ZOOM_MIN}
              aria-label="Achicar"
            >
              −
            </button>
            <small>{Math.round(zoom * 100)}%</small>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(ZOOM_MAX, z + ZOOM_PASO))}
              disabled={zoom >= ZOOM_MAX}
              aria-label="Agrandar"
            >
              +
            </button>
          </span>
        )}

        {/* Bajarlo o imprimirlo van arriba y a la derecha, con su nombre:
            son lo que se hace con el documento, y un ícono solo obliga a
            adivinar cuál es cuál. */}
        <span className="documento-acciones">
          {esPdf && (
            <button type="button" className="documento-accion" onClick={imprimir}>
              <IconoImprimir width={15} height={15} />
              <span>Imprimir</span>
            </button>
          )}
          {descarga && (
            <a className="documento-accion" href={descarga} download={archivo.nombre}>
              <IconoDescargar width={15} height={15} />
              <span>Descargar</span>
            </a>
          )}
          <button
            type="button"
            onClick={pantallaCompleta}
            title={completa ? 'Salir de pantalla completa' : 'Pantalla completa'}
            aria-label={completa ? 'Salir de pantalla completa' : 'Pantalla completa'}
          >
            {completa ? (
              <IconoSalirPantallaCompleta width={16} height={16} />
            ) : (
              <IconoPantallaCompleta width={16} height={16} />
            )}
          </button>
        </span>
      </div>

      {estado === 'error' ? (
        <p className="aviso-error documento-error">
          {error} Se puede descargar con el botón de abajo.
        </p>
      ) : (
        <div className={esPdf ? 'documento-hojas oscuro' : 'documento-hojas'}>
          {estado === 'cargando' && (
            <p className="documento-esperando">Abriendo el documento…</p>
          )}
          {/* Las hojas del PDF las cuelga pdf.js a mano, así que este nodo va
              vacío en el JSX: si React le pusiera hijos, los dos escribirían
              en el mismo lugar y el que perdiera dejaría la pantalla rota. */}
          {esPdf ? (
            <div ref={hojas} className="documento-pdf" />
          ) : (
            // El HTML viene de `limpiar`, que ya sacó todo lo ejecutable.
            // eslint-disable-next-line react/no-danger
            <article className="documento-word" dangerouslySetInnerHTML={{ __html: texto }} />
          )}
        </div>
      )}

    </div>
  );
}
