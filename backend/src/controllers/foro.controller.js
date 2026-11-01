import {
  temasForo,
  cursos,
  usuarioActual,
  buscarPersona,
  nuevoIdTema,
  nuevoIdMensajeForo,
} from '../data/mock.js';

// Mientras no haya login, el que publica es siempre el usuario de prueba.
const YO = usuarioActual.id;

function autorDe(id) {
  const persona = buscarPersona(id);
  return persona ? { id: persona.id, nombre: persona.nombre, rol: persona.rol } : null;
}

function cursoDe(id) {
  const curso = cursos.find((c) => c.id === id);
  return curso ? { id: curso.id, nombre: curso.nombre, codigo: curso.codigo, color: curso.color } : null;
}

// En la lista no hacen falta los mensajes, solo cuántos hay y cuándo fue el último
function resumir(tema) {
  const ultimo = tema.mensajes.at(-1);
  return {
    id: tema.id,
    titulo: tema.titulo,
    curso: cursoDe(tema.cursoId),
    autor: autorDe(tema.autorId),
    fecha: tema.fecha,
    respuestas: Math.max(tema.mensajes.length - 1, 0),
    ultimaActividad: ultimo?.fecha ?? tema.fecha,
    ultimoAutor: ultimo ? autorDe(ultimo.autorId) : null,
  };
}

// Los temas, de la última actividad hacia atrás, y las asignaturas que tienen
// alguno para poder filtrar.
export function listarTemas(req, res) {
  const temas = temasForo
    .map(resumir)
    .sort((a, b) => new Date(b.ultimaActividad) - new Date(a.ultimaActividad));

  const asignaturas = cursos
    .map((curso) => ({
      ...cursoDe(curso.id),
      temas: temas.filter((t) => t.curso?.id === curso.id).length,
    }))
    .filter((a) => a.temas > 0);

  res.json({ temas, asignaturas });
}

export function obtenerTema(req, res) {
  const tema = temasForo.find((t) => t.id === Number(req.params.id));
  if (!tema) {
    return res.status(404).json({ error: 'Tema no encontrado' });
  }

  res.json({
    id: tema.id,
    titulo: tema.titulo,
    curso: cursoDe(tema.cursoId),
    autor: autorDe(tema.autorId),
    fecha: tema.fecha,
    mensajes: tema.mensajes.map((m) => ({ ...m, autor: autorDe(m.autorId) })),
  });
}

export function crearTema(req, res) {
  const cursoId = Number(req.body?.cursoId);
  const titulo = (req.body?.titulo ?? '').trim();
  const texto = (req.body?.texto ?? '').trim();

  if (!cursoDe(cursoId)) {
    return res.status(400).json({ error: 'Hay que elegir una asignatura' });
  }
  if (!titulo || !texto) {
    return res.status(400).json({ error: 'El tema necesita un título y una consulta' });
  }

  const ahora = new Date().toISOString();
  const tema = {
    id: nuevoIdTema(),
    cursoId,
    titulo,
    autorId: YO,
    fecha: ahora,
    mensajes: [{ id: nuevoIdMensajeForo(), autorId: YO, texto, fecha: ahora }],
  };
  temasForo.push(tema);

  res.status(201).json(resumir(tema));
}

export function responder(req, res) {
  const tema = temasForo.find((t) => t.id === Number(req.params.id));
  if (!tema) {
    return res.status(404).json({ error: 'Tema no encontrado' });
  }

  const texto = (req.body?.texto ?? '').trim();
  if (!texto) {
    return res.status(400).json({ error: 'La respuesta no puede estar vacía' });
  }

  const mensaje = {
    id: nuevoIdMensajeForo(),
    autorId: YO,
    texto,
    fecha: new Date().toISOString(),
  };
  tema.mensajes.push(mensaje);

  res.status(201).json({ ...mensaje, autor: autorDe(YO) });
}
