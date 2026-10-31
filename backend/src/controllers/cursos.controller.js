import {
  cursos,
  carpetasDeCurso,
  anuncios,
  anunciosGenericos,
  participantesDeCurso,
  conPresencia,
  novedadesDeCurso,
} from '../data/mock.js';

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
    carpetas: carpetasDeCurso(curso),
    anuncios: anuncios[id] || anunciosGenericos(curso),
    // El último acceso y el estado de presencia se calculan ahora
    participantes: participantesDeCurso(curso).map(conPresencia),
  });
}
