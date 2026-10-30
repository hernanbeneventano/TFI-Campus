import { cursos } from '../data/mock.js';

export function listarCursos(req, res) {
  res.json(cursos);
}

export function obtenerCurso(req, res) {
  const curso = cursos.find((c) => c.id === Number(req.params.id));
  if (!curso) {
    return res.status(404).json({ error: 'Curso no encontrado' });
  }
  res.json(curso);
}
