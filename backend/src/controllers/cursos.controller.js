import {
  cursos,
  tareas,
  clases,
  eventos,
  carpetasDeCurso,
  anuncios,
  anunciosGenericos,
  participantesDeCurso,
  conPresencia,
  novedadesDeCurso,
} from '../data/mock.js';

const DIAS = ['', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

// El horario semanal del módulo: no aparece en ninguna otra parte de la
// pantalla, hay que ir al calendario para verlo.
function cursadaDe(cursoId) {
  return clases
    .filter((c) => c.cursoId === cursoId)
    .map((c) => ({ dia: DIAS[c.dia], desde: c.desde, hasta: c.hasta, aula: c.aula }));
}

// Lo que se viene en este módulo: entregas sin hacer y exámenes, de lo más
// cercano a lo más lejano. En las carpetas están, pero hay que abrirlas una
// por una para enterarse.
function proximasDe(cursoId) {
  const ahora = new Date();

  const entregas = tareas
    .filter((t) => t.cursoId === cursoId && !t.entregada && new Date(t.fechaLimite) >= ahora)
    .map((t) => ({ tipo: 'entrega', titulo: t.titulo, fecha: t.fechaLimite, tareaId: t.id }));

  const examenes = eventos
    .filter((e) => e.cursoId === cursoId && e.tipo === 'examen' && new Date(e.fecha) >= ahora)
    .map((e) => ({ tipo: 'examen', titulo: e.titulo, fecha: e.fecha, lugar: e.lugar }));

  return [...entregas, ...examenes]
    .sort((a, b) => new Date(a.fecha) - new Date(b.fecha))
    .slice(0, 4);
}

export function listarCursos(req, res) {
  // Cada curso viaja con sus novedades, para la campanita de la tarjeta
  res.json(cursos.map((curso) => ({ ...curso, novedades: novedadesDeCurso(curso) })));
}

export function obtenerCurso(req, res) {
  const curso = cursos.find((c) => c.id === Number(req.params.id));
  if (!curso) {
    return res.status(404).json({ error: 'Curso no encontrado' });
  }
  res.json(curso);
}

// Todo lo que necesita la pantalla de un módulo: el curso, sus carpetas de
// contenido, los anuncios y la gente inscripta.
export function obtenerModulo(req, res) {
  const id = Number(req.params.id);
  const curso = cursos.find((c) => c.id === id);
  if (!curso) {
    return res.status(404).json({ error: 'Curso no encontrado' });
  }

  res.json({
    curso,
    cursada: cursadaDe(id),
    proximas: proximasDe(id),
    carpetas: carpetasDeCurso(curso),
    anuncios: anuncios[id] || anunciosGenericos(curso),
    // El último acceso y el estado de presencia se calculan ahora
    participantes: participantesDeCurso(curso).map(conPresencia),
  });
}


// Marcar o desmarcar un módulo como favorito. Hoy queda en memoria, como el
// resto de los datos; con Firestore pasa a ser por usuario.
export function alternarFavorito(req, res) {
  const curso = cursos.find((c) => c.id === Number(req.params.id));
  if (!curso) {
    return res.status(404).json({ error: 'Curso no encontrado' });
  }

  curso.favorito = !curso.favorito;
  res.json({ ...curso, novedades: novedadesDeCurso(curso) });
}
