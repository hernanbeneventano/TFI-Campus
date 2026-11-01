import { publicaciones, usuarioActual, buscarPersona, nuevoIdPublicacion } from '../data/mock.js';

// Las únicas reacciones posibles
export const REACCIONES = ['leido', 'util', 'dudas'];

// Mientras no haya login, el que publica es siempre el usuario de prueba.
const YO = usuarioActual.id;

// Solo los docentes publican y editan; los estudiantes leen.
function puedePublicar(personaId) {
  return buscarPersona(personaId)?.rol === 'Docente';
}

// Las reacciones salen contadas, nunca con la lista de quiénes reaccionaron:
// el que lee ve cuántos fueron y cuál puso él, y nada más.
function resumirReacciones(publicacion) {
  const cuenta = {};
  for (const tipo of REACCIONES) {
    cuenta[tipo] = (publicacion.reacciones?.[tipo] ?? []).length;
  }
  const mia = REACCIONES.find((tipo) => (publicacion.reacciones?.[tipo] ?? []).includes(YO));
  return { cuenta, miReaccion: mia ?? null };
}

function conAutor(publicacion) {
  const autor = buscarPersona(publicacion.autorId);
  const { reacciones, ...sinQuienes } = publicacion;
  return {
    ...sinQuienes,
    ...resumirReacciones(publicacion),
    autor: autor ? { id: autor.id, nombre: autor.nombre, rol: autor.rol } : null,
    // Para que el frontend sepa si mostrarle el botón de editar
    puedeEditar: puedePublicar(YO) && publicacion.autorId === YO,
  };
}

// La anclada va siempre primera; el resto, de la más nueva a la más vieja.
export function listarPublicaciones(req, res) {
  res.json({
    publicaciones: [...publicaciones]
      .sort((a, b) => Number(b.anclada) - Number(a.anclada) || new Date(b.fecha) - new Date(a.fecha))
      .map(conAutor),
    puedePublicar: puedePublicar(YO),
  });
}

// Solo puede haber una destacada a la vez
function anclarSolo(id) {
  for (const p of publicaciones) p.anclada = p.id === id;
}

export function crearPublicacion(req, res) {
  if (!puedePublicar(YO)) {
    return res.status(403).json({ error: 'Solo los docentes pueden publicar novedades' });
  }

  const titulo = (req.body?.titulo ?? '').trim();
  const cuerpo = (req.body?.cuerpo ?? '').trim();
  const categoria = (req.body?.categoria ?? 'Académico').trim();
  const ambito = (req.body?.ambito ?? 'Institucional').trim();
  // Por ahora la imagen es una direccion: todavia no hay donde subir archivos
  const imagen = (req.body?.imagen ?? '').trim() || null;

  if (!titulo || !cuerpo) {
    return res.status(400).json({ error: 'La novedad necesita un título y un texto' });
  }

  const publicacion = {
    id: nuevoIdPublicacion(),
    autorId: YO,
    ambito,
    categoria,
    titulo,
    cuerpo,
    imagen,
    fecha: new Date().toISOString(),
    editada: null,
    anclada: false,
    reacciones: { leido: [], util: [], dudas: [] },
  };
  publicaciones.push(publicacion);

  if (req.body?.anclada) anclarSolo(publicacion.id);

  res.status(201).json(conAutor(publicacion));
}

export function editarPublicacion(req, res) {
  const publicacion = publicaciones.find((p) => p.id === Number(req.params.id));
  if (!publicacion) {
    return res.status(404).json({ error: 'Novedad no encontrada' });
  }
  if (!puedePublicar(YO) || publicacion.autorId !== YO) {
    return res.status(403).json({ error: 'Solo quien la publicó puede editarla' });
  }

  const titulo = (req.body?.titulo ?? '').trim();
  const cuerpo = (req.body?.cuerpo ?? '').trim();
  if (!titulo || !cuerpo) {
    return res.status(400).json({ error: 'La novedad necesita un título y un texto' });
  }

  publicacion.titulo = titulo;
  publicacion.cuerpo = cuerpo;
  publicacion.imagen = (req.body?.imagen ?? '').trim() || null;
  publicacion.editada = new Date().toISOString();

  if (req.body?.anclada) anclarSolo(publicacion.id);
  else if (publicacion.anclada) publicacion.anclada = false;

  res.json(conAutor(publicacion));
}


// Reaccionar, o sacar la reacción si se toca la misma de nuevo. Cada persona
// tiene una sola: poner otra reemplaza la anterior.
export function reaccionar(req, res) {
  const publicacion = publicaciones.find((p) => p.id === Number(req.params.id));
  if (!publicacion) {
    return res.status(404).json({ error: 'Novedad no encontrada' });
  }

  const tipo = req.body?.tipo ?? null;
  if (tipo !== null && !REACCIONES.includes(tipo)) {
    return res.status(400).json({ error: 'Esa reacción no existe' });
  }

  publicacion.reacciones ??= { leido: [], util: [], dudas: [] };

  const yaEstaba = REACCIONES.find((t) => publicacion.reacciones[t].includes(YO));
  for (const t of REACCIONES) {
    publicacion.reacciones[t] = publicacion.reacciones[t].filter((id) => id !== YO);
  }

  // Tocar la que ya estaba puesta la saca
  if (tipo && tipo !== yaEstaba) {
    publicacion.reacciones[tipo].push(YO);
  }

  res.json(conAutor(publicacion));
}
