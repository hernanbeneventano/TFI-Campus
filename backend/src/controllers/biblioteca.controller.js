import {
  materiales,
  categorias,
  carreras,
  favoritosBiblioteca,
  moderacionBiblioteca,
  cursos,
  usuarioActual,
  buscarPersona,
  nuevoIdMaterial,
  nuevoIdModeracion,
  guardarArchivo,
  leerArchivo,
  borrarArchivo,
  TIPOS_MATERIAL,
} from '../data/mock.js';
import { buscarLibrosExternos, obtenerLibroExterno } from '../services/librosExternos.js';

// Mientras no haya login, el que consulta y aporta es siempre el usuario de
// prueba, igual que en el resto de los controladores.
const YO = usuarioActual.id;

// La facultad todavía no tiene un rol de administrador: en `personas` solo
// hay Estudiante y Docente. Hasta que exista, **modera el docente**, que es
// quien responde por el material de su cátedra. El día que se agregue el rol,
// alcanza con cambiar esta función.
function puedeModerar(personaId) {
  return buscarPersona(personaId)?.rol === 'Docente';
}

// Subir material lo puede hacer cualquiera: los aportes de estudiantes no se
// publican solos, quedan esperando moderación.
function puedeAportar(personaId) {
  return Boolean(buscarPersona(personaId));
}

// Un material pendiente o rechazado lo ven quien lo subió y los docentes;
// nadie más. Así un aporte sin revisar no aparece en el catálogo.
function puedeVer(material, personaId) {
  if (material.estado === 'aprobado') return true;
  return material.subidoPor === personaId || puedeModerar(personaId);
}

function puedeEditar(material, personaId) {
  return material.subidoPor === personaId || puedeModerar(personaId);
}

// ---------- Límite de pedidos ----------
// Freno simple contra el abuso de la búsqueda externa y de la subida. En
// memoria y por persona, que es lo que se puede hacer sin login ni Redis.
const golpes = new Map();

function dentroDelLimite(clave, cuantos, ventanaMs) {
  const ahora = Date.now();
  const previos = (golpes.get(clave) ?? []).filter((t) => ahora - t < ventanaMs);
  if (previos.length >= cuantos) {
    golpes.set(clave, previos);
    return false;
  }
  previos.push(ahora);
  golpes.set(clave, previos);
  return true;
}

// ---------- Presentación ----------
function nombreCategoria(id) {
  return categorias.find((c) => c.id === id)?.nombre ?? 'Otros materiales';
}

function conDatos(material, personaId = YO) {
  const quien = buscarPersona(material.subidoPor);
  const esFavorito = favoritosBiblioteca.some(
    (f) => f.personaId === personaId && String(f.materialId) === String(material.id)
  );

  return {
    ...material,
    // El archivo se describe, pero sus bytes nunca viajan en el listado:
    // se piden aparte, con el control de acceso puesto.
    archivo: material.archivo
      ? { nombre: material.archivo.nombre, tamano: material.archivo.tamano, tipo: material.archivo.tipo }
      : null,
    tieneArchivo: Boolean(material.archivo),
    externo: false,
    fuente: 'campus',
    nombreFuente: material.editorial || 'Biblioteca del campus',
    nombreCategoria: nombreCategoria(material.categoria),
    subidoPorNombre: quien?.nombre ?? 'Alguien del campus',
    favorito: esFavorito,
    puedeEditar: puedeEditar(material, personaId),
    puedeModerar: puedeModerar(personaId),
  };
}

// ---------- Búsqueda en la biblioteca propia ----------
function sinTildes(texto) {
  return (texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();
}

function coincide(material, texto, campo) {
  if (!texto) return true;
  const buscado = sinTildes(texto);

  const donde = {
    titulo: [material.titulo],
    autor: [material.autor],
    isbn: [material.isbn],
    tema: [material.materia, nombreCategoria(material.categoria), material.descripcion],
    todo: [
      material.titulo,
      material.autor,
      material.isbn,
      material.descripcion,
      material.materia,
      material.carrera,
      material.editorial,
      nombreCategoria(material.categoria),
    ],
  };

  return (donde[campo] ?? donde.todo).some((valor) => sinTildes(valor).includes(buscado));
}

function ordenar(lista, orden) {
  const copia = [...lista];
  if (orden === 'titulo') return copia.sort((a, b) => a.titulo.localeCompare(b.titulo, 'es'));
  if (orden === 'autor') {
    return copia.sort((a, b) => (a.autor ?? '').localeCompare(b.autor ?? '', 'es'));
  }
  // Por defecto, lo más nuevo arriba
  return copia.sort((a, b) => new Date(b.creado) - new Date(a.creado));
}

function filtrarPropios(req, personaId) {
  const {
    q = '',
    campo = 'todo',
    categoria = '',
    tipo = '',
    carrera = '',
    materia = '',
    idioma = '',
    estado = '',
    orden = 'fecha',
  } = req.query;

  return ordenar(
    materiales.filter((m) => {
      if (!puedeVer(m, personaId)) return false;
      // Sin filtro de estado, el catálogo muestra solo lo aprobado: los
      // propios pendientes se consultan desde "Mis aportes".
      if (estado ? m.estado !== estado : m.estado !== 'aprobado') return false;
      if (categoria && m.categoria !== categoria) return false;
      if (tipo && m.tipo !== tipo) return false;
      if (carrera && m.carrera !== carrera) return false;
      if (materia && m.materia !== materia) return false;
      if (idioma && m.idioma !== idioma) return false;
      return coincide(m, q.trim(), campo);
    }),
    orden
  );
}

function paginar(lista, req) {
  const pagina = Math.max(1, Number(req.query.pagina) || 1);
  const porPagina = Math.min(48, Math.max(1, Number(req.query.porPagina) || 12));
  const desde = (pagina - 1) * porPagina;
  return {
    pagina,
    porPagina,
    total: lista.length,
    paginas: Math.max(1, Math.ceil(lista.length / porPagina)),
    recortada: lista.slice(desde, desde + porPagina),
  };
}

// ---------- Rutas ----------

// Los datos que necesita la pantalla para armar los filtros, en una llamada:
// categorías con cuántos hay, carreras, materias, tipos e idiomas.
export function opcionesBiblioteca(req, res) {
  const visibles = materiales.filter((m) => m.estado === 'aprobado');
  const cuantos = (predicado) => visibles.filter(predicado).length;

  res.json({
    categorias: categorias.map((c) => ({
      ...c,
      cuantos: cuantos((m) => m.categoria === c.id),
    })),
    carreras,
    // Las materias salen de los cursos del campus más las que ya tengan los
    // materiales, para que el filtro no se quede corto.
    materias: [
      ...new Set([...cursos.map((c) => c.nombre), ...materiales.map((m) => m.materia).filter(Boolean)]),
    ].sort((a, b) => a.localeCompare(b, 'es')),
    tipos: TIPOS_MATERIAL,
    idiomas: [...new Set(visibles.map((m) => m.idioma).filter(Boolean))].sort(),
    total: visibles.length,
    puedeAportar: puedeAportar(YO),
    puedeModerar: puedeModerar(YO),
    pendientes: puedeModerar(YO) ? materiales.filter((m) => m.estado === 'pendiente').length : 0,
  });
}

// Catálogo. `fuente` elige dónde buscar: campus, externos o las dos.
export async function listarMateriales(req, res, next) {
  try {
    const fuente = req.query.fuente ?? 'todo';
    const texto = (req.query.q ?? '').trim();

    const propios = fuente === 'externos' ? [] : filtrarPropios(req, YO);
    const { recortada, ...paginacion } = paginar(propios, req);

    const respuesta = {
      materiales: recortada.map((m) => conDatos(m)),
      ...paginacion,
      externos: [],
      fuentes: [],
    };

    // Los catálogos externos solo se consultan si hay algo que buscar: no
    // tiene sentido pedirles "todo", y además cuentan contra el límite.
    const buscarAfuera = fuente !== 'campus' && texto.length >= 2;
    if (buscarAfuera) {
      if (!dentroDelLimite(`buscar:${YO}`, 30, 60_000)) {
        respuesta.fuentes = [{ estado: 'limite', nombre: 'Catálogos externos' }];
        return res.json(respuesta);
      }

      try {
        const { libros, fuentes } = await buscarLibrosExternos({
          texto,
          campo: req.query.campo ?? 'todo',
          idioma: req.query.idioma || null,
        });
        // Marcar los que ya están en favoritos, igual que los propios
        respuesta.externos = libros.map((l) => ({
          ...l,
          favorito: favoritosBiblioteca.some(
            (f) => f.personaId === YO && String(f.materialId) === String(l.id)
          ),
        }));
        respuesta.fuentes = fuentes;
      } catch (e) {
        // Que se caigan las dos APIs no puede dejar sin biblioteca al campus
        respuesta.fuentes = [{ estado: 'error', nombre: 'Catálogos externos', error: String(e.message) }];
      }
    }

    res.json(respuesta);
  } catch (e) {
    next(e);
  }
}

// Los aportes de quien pregunta, con su estado y el motivo si lo rechazaron
export function misAportes(req, res) {
  const mios = materiales.filter((m) => m.subidoPor === YO);
  res.json({
    materiales: ordenar(mios, 'fecha').map((m) => ({
      ...conDatos(m),
      historial: moderacionBiblioteca
        .filter((h) => h.materialId === m.id)
        .map((h) => ({ ...h, moderador: buscarPersona(h.moderadorId)?.nombre ?? null })),
    })),
  });
}

// La cola de moderación. Solo para quien modera.
export function pendientes(req, res) {
  if (!puedeModerar(YO)) {
    return res.status(403).json({ error: 'Solo los docentes pueden revisar los aportes' });
  }
  const cola = materiales.filter((m) => m.estado === 'pendiente');
  res.json({ materiales: ordenar(cola, 'fecha').map((m) => conDatos(m)) });
}

export function obtenerFavoritos(req, res) {
  const mios = favoritosBiblioteca.filter((f) => f.personaId === YO);

  // Los favoritos pueden ser propios o externos: los propios se resuelven
  // acá y de los externos se devuelve el identificador, que la pantalla usa
  // para volver a pedirlos si hace falta.
  const propios = mios
    .map((f) => materiales.find((m) => String(m.id) === String(f.materialId)))
    .filter((m) => m && puedeVer(m, YO))
    .map((m) => conDatos(m));

  const externos = mios
    .filter((f) => String(f.materialId).includes(':'))
    .map((f) => ({ id: f.materialId, creado: f.creado }));

  res.json({ materiales: propios, externos });
}

export async function obtenerMaterial(req, res, next) {
  try {
    const { id } = req.params;

    // Un id con dos puntos es de un catálogo externo ("google:xxx")
    if (String(id).includes(':')) {
      const libro = await obtenerLibroExterno(id);
      if (!libro) return res.status(404).json({ error: 'No se encontró ese libro' });
      return res.json({
        ...libro,
        favorito: favoritosBiblioteca.some(
          (f) => f.personaId === YO && String(f.materialId) === String(id)
        ),
        relacionados: [],
      });
    }

    const material = materiales.find((m) => m.id === Number(id));
    if (!material) return res.status(404).json({ error: 'Material no encontrado' });
    if (!puedeVer(material, YO)) {
      return res.status(403).json({ error: 'Ese material todavía no está disponible' });
    }

    // Material relacionado: de la misma materia o categoría, sin repetirse
    const relacionados = materiales
      .filter(
        (m) =>
          m.id !== material.id &&
          m.estado === 'aprobado' &&
          (m.materia === material.materia || m.categoria === material.categoria)
      )
      .slice(0, 4)
      .map((m) => conDatos(m));

    res.json({
      ...conDatos(material),
      relacionados,
      historial: moderacionBiblioteca
        .filter((h) => h.materialId === material.id)
        .map((h) => ({ ...h, moderador: buscarPersona(h.moderadorId)?.nombre ?? null })),
    });
  } catch (e) {
    next(e);
  }
}

// ---------- Aportar ----------
function leerCampos(cuerpo) {
  const texto = (valor) => (valor ?? '').toString().trim();
  return {
    titulo: texto(cuerpo?.titulo),
    autor: texto(cuerpo?.autor),
    descripcion: texto(cuerpo?.descripcion),
    tipo: texto(cuerpo?.tipo) || 'otro',
    carrera: texto(cuerpo?.carrera),
    materia: texto(cuerpo?.materia),
    anio: texto(cuerpo?.anio),
    idioma: texto(cuerpo?.idioma) || 'es',
    isbn: texto(cuerpo?.isbn),
    categoria: texto(cuerpo?.categoria) || 'otros',
    editorial: texto(cuerpo?.editorial),
    enlace: texto(cuerpo?.enlace),
    licencia: texto(cuerpo?.licencia),
    portada: texto(cuerpo?.portada),
  };
}

function validar(campos, cuerpo, { exigirAutorizacion }) {
  if (!campos.titulo) return 'El material necesita un título';
  if (campos.titulo.length > 200) return 'El título es demasiado largo';
  if (!TIPOS_MATERIAL.includes(campos.tipo)) return 'Ese tipo de material no existe';
  if (!categorias.some((c) => c.id === campos.categoria)) return 'Esa categoría no existe';
  if (campos.isbn && !/^[0-9Xx-]{10,17}$/.test(campos.isbn)) return 'Ese ISBN no parece válido';

  // Solo http(s): un enlace "javascript:" en la ficha sería un agujero
  for (const [nombre, valor] of [['enlace', campos.enlace], ['portada', campos.portada]]) {
    if (!valor) continue;
    try {
      const url = new URL(valor);
      if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        return `El ${nombre} tiene que ser una dirección http o https`;
      }
    } catch {
      return `El ${nombre} no es una dirección válida`;
    }
  }

  // Compartir material ajeno sin permiso es el riesgo principal de todo esto
  if (exigirAutorizacion && cuerpo?.autorizado !== true) {
    return 'Hay que confirmar que tenés autorización para compartir el material';
  }
  return null;
}

export function crearMaterial(req, res) {
  if (!puedeAportar(YO)) {
    return res.status(403).json({ error: 'No tenés permiso para aportar material' });
  }
  if (!dentroDelLimite(`aportar:${YO}`, 10, 60 * 60_000)) {
    return res.status(429).json({ error: 'Demasiados aportes seguidos. Probá de nuevo en un rato.' });
  }

  const campos = leerCampos(req.body);
  const problema = validar(campos, req.body, { exigirAutorizacion: true });
  if (problema) return res.status(400).json({ error: problema });

  // Quien modera publica directo; el resto espera revisión
  const estado = puedeModerar(YO) ? 'aprobado' : 'pendiente';

  const material = {
    id: nuevoIdMaterial(),
    ...campos,
    isbn: campos.isbn || null,
    editorial: campos.editorial || null,
    enlace: campos.enlace || null,
    portada: campos.portada || null,
    licencia: campos.licencia || null,
    anio: campos.anio || null,
    descripcion: campos.descripcion || null,
    autor: campos.autor || buscarPersona(YO)?.nombre || null,
    archivo: null,
    subidoPor: YO,
    estado,
    moderadoPor: estado === 'aprobado' ? YO : null,
    motivo: null,
    creado: new Date().toISOString(),
    actualizado: new Date().toISOString(),
  };

  materiales.push(material);

  if (estado === 'aprobado') {
    moderacionBiblioteca.push({
      id: nuevoIdModeracion(),
      materialId: material.id,
      moderadorId: YO,
      accion: 'aprobado',
      motivo: 'Publicado por quien modera',
      fecha: material.creado,
    });
  }

  res.status(201).json(conDatos(material));
}

// ---------- El archivo ----------
// Tamaño máximo, configurable. Lo que llega es base64, que ocupa un tercio
// más que el archivo original: el límite se compara contra los bytes reales.
const MAX_MB = Number(process.env.BIBLIOTECA_MAX_MB) || 15;
const MAX_BYTES = MAX_MB * 1024 * 1024;

// Solo formatos de lectura. Nada de ejecutables ni de cosas que el navegador
// pueda correr: ni .exe, ni .js, ni .html, ni .svg.
const FORMATOS = {
  pdf: { mime: 'application/pdf', firma: (b) => b.subarray(0, 5).toString('latin1') === '%PDF-' },
  epub: {
    mime: 'application/epub+zip',
    // Un EPUB es un ZIP: tiene que empezar con PK y declarar su mimetype
    firma: (b) =>
      b.subarray(0, 2).toString('latin1') === 'PK' &&
      b.subarray(0, 200).toString('latin1').includes('application/epub+zip'),
  },
};

// El nombre que mande el navegador no se usa tal cual: podría traer una ruta
// ("../../algo") o caracteres que rompan la cabecera de la descarga.
function nombreSeguro(nombre, extension) {
  const base = String(nombre ?? 'material')
    .split(/[\\/]/)
    .pop()
    .replace(/\.[^.]*$/, '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-zA-Z0-9 _-]/g, '')
    .trim()
    .slice(0, 80);
  return `${base || 'material'}.${extension}`;
}

export function subirArchivo(req, res) {
  const material = materiales.find((m) => m.id === Number(req.params.id));
  if (!material) return res.status(404).json({ error: 'Material no encontrado' });
  if (!puedeEditar(material, YO)) {
    return res.status(403).json({ error: 'Solo quien lo subió puede cambiar el archivo' });
  }
  if (!dentroDelLimite(`subir:${YO}`, 20, 60 * 60_000)) {
    return res.status(429).json({ error: 'Demasiadas subidas seguidas. Probá de nuevo en un rato.' });
  }

  const extension = String(req.body?.extension ?? '').toLowerCase().replace(/^\./, '');
  const formato = FORMATOS[extension];
  if (!formato) {
    const aceptados = Object.keys(FORMATOS).map((e) => e.toUpperCase());
    return res.status(415).json({
      error: `Solo se aceptan archivos ${aceptados.join(' y ')}`,
    });
  }

  // El tipo que declara el navegador tiene que coincidir con la extensión…
  const declarado = String(req.body?.tipo ?? '');
  if (declarado && declarado !== formato.mime) {
    return res.status(415).json({ error: 'El tipo del archivo no coincide con su extensión' });
  }

  let bytes;
  try {
    bytes = Buffer.from(String(req.body?.contenido ?? ''), 'base64');
  } catch {
    return res.status(400).json({ error: 'No se pudo leer el archivo' });
  }

  if (bytes.length === 0) return res.status(400).json({ error: 'El archivo está vacío' });
  if (bytes.length > MAX_BYTES) {
    return res.status(413).json({ error: `El archivo supera los ${MAX_MB} MB` });
  }
  // …y el contenido real tiene que ser lo que dice ser. La extensión sola no
  // prueba nada: cualquiera renombra un .exe a .pdf.
  if (!formato.firma(bytes)) {
    return res.status(415).json({ error: `El archivo no es un ${extension.toUpperCase()} válido` });
  }

  guardarArchivo(material.id, bytes);
  material.archivo = {
    nombre: nombreSeguro(req.body?.nombre, extension),
    tamano: bytes.length,
    tipo: formato.mime,
  };
  // Si el archivo está alojado acá, el enlace externo sobra
  material.enlace = null;
  material.actualizado = new Date().toISOString();

  res.status(201).json(conDatos(material));
}

// La descarga pasa por el control de acceso: un pendiente no se baja aunque
// alguien adivine el id.
export function descargarArchivo(req, res) {
  const material = materiales.find((m) => m.id === Number(req.params.id));
  if (!material) return res.status(404).json({ error: 'Material no encontrado' });
  if (!puedeVer(material, YO)) {
    return res.status(403).json({ error: 'Ese material todavía no está disponible' });
  }

  const bytes = leerArchivo(material.id);
  if (!bytes || !material.archivo) {
    return res.status(404).json({ error: 'Este material no tiene un archivo alojado en el campus' });
  }

  res.setHeader('Content-Type', material.archivo.tipo);
  res.setHeader('Content-Length', bytes.length);
  // Siempre como descarga y sin dejar que el navegador adivine el tipo:
  // un archivo de otra persona no se abre dentro del campus.
  res.setHeader('Content-Disposition', `attachment; filename="${material.archivo.nombre}"`);
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.send(bytes);
}

export function editarMaterial(req, res) {
  const material = materiales.find((m) => m.id === Number(req.params.id));
  if (!material) return res.status(404).json({ error: 'Material no encontrado' });
  if (!puedeEditar(material, YO)) {
    return res.status(403).json({ error: 'Solo quien lo subió o un docente puede editarlo' });
  }

  const campos = leerCampos({ ...material, ...req.body });
  const problema = validar(campos, req.body, { exigirAutorizacion: false });
  if (problema) return res.status(400).json({ error: problema });

  Object.assign(material, {
    ...campos,
    isbn: campos.isbn || null,
    editorial: campos.editorial || null,
    enlace: material.archivo ? null : campos.enlace || null,
    portada: campos.portada || null,
    licencia: campos.licencia || null,
    anio: campos.anio || null,
    descripcion: campos.descripcion || null,
    actualizado: new Date().toISOString(),
  });

  // Si lo edita quien lo subió y no modera, vuelve a la cola: el texto que
  // se aprobó ya no es el que está.
  if (!puedeModerar(YO) && material.estado === 'aprobado') {
    material.estado = 'pendiente';
    material.moderadoPor = null;
  }

  res.json(conDatos(material));
}

export function borrarMaterial(req, res) {
  const indice = materiales.findIndex((m) => m.id === Number(req.params.id));
  if (indice === -1) return res.status(404).json({ error: 'Material no encontrado' });

  const material = materiales[indice];
  if (!puedeEditar(material, YO)) {
    return res.status(403).json({ error: 'Solo quien lo subió o un docente puede retirarlo' });
  }

  materiales.splice(indice, 1);
  borrarArchivo(material.id);
  // Los favoritos que apuntaban ahí quedarían colgados
  for (let i = favoritosBiblioteca.length - 1; i >= 0; i--) {
    if (String(favoritosBiblioteca[i].materialId) === String(material.id)) {
      favoritosBiblioteca.splice(i, 1);
    }
  }

  res.json({ retirado: material.id });
}

// ---------- Moderación ----------
function moderar(req, res, accion) {
  if (!puedeModerar(YO)) {
    return res.status(403).json({ error: 'Solo los docentes pueden moderar la biblioteca' });
  }

  const material = materiales.find((m) => m.id === Number(req.params.id));
  if (!material) return res.status(404).json({ error: 'Material no encontrado' });

  const motivo = (req.body?.motivo ?? '').trim();
  // Rechazar sin decir por qué no le sirve a nadie: quien aportó no sabe
  // qué corregir.
  if (accion === 'rechazado' && !motivo) {
    return res.status(400).json({ error: 'Hay que indicar el motivo del rechazo' });
  }

  material.estado = accion;
  material.moderadoPor = YO;
  material.motivo = motivo || null;
  material.actualizado = new Date().toISOString();

  moderacionBiblioteca.push({
    id: nuevoIdModeracion(),
    materialId: material.id,
    moderadorId: YO,
    accion,
    motivo: motivo || null,
    fecha: material.actualizado,
  });

  res.json(conDatos(material));
}

export const aprobarMaterial = (req, res) => moderar(req, res, 'aprobado');
export const rechazarMaterial = (req, res) => moderar(req, res, 'rechazado');

// ---------- Favoritos ----------
// Vale tanto para un material propio como para un libro externo: el id
// externo ("google:xxx") es estable y se guarda tal cual.
export function agregarFavorito(req, res) {
  const { id } = req.params;
  const esExterno = String(id).includes(':');

  if (!esExterno) {
    const material = materiales.find((m) => m.id === Number(id));
    if (!material) return res.status(404).json({ error: 'Material no encontrado' });
    if (!puedeVer(material, YO)) {
      return res.status(403).json({ error: 'Ese material todavía no está disponible' });
    }
  }

  const clave = esExterno ? String(id) : Number(id);
  const yaEsta = favoritosBiblioteca.some(
    (f) => f.personaId === YO && String(f.materialId) === String(clave)
  );
  if (!yaEsta) {
    favoritosBiblioteca.push({ personaId: YO, materialId: clave, creado: new Date().toISOString() });
  }

  res.status(201).json({ id: clave, favorito: true });
}

export function quitarFavorito(req, res) {
  const { id } = req.params;
  const indice = favoritosBiblioteca.findIndex(
    (f) => f.personaId === YO && String(f.materialId) === String(id)
  );
  if (indice !== -1) favoritosBiblioteca.splice(indice, 1);

  res.json({ id, favorito: false });
}
