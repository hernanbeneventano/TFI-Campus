import { tareas, cursos } from '../data/mock.js';

// Tareas sin entregar, separadas en próximas (todavía en fecha) y atrasadas.
export function listarPendientes(req, res) {
  const ahora = new Date();

  const pendientes = tareas
    .filter((t) => !t.entregada)
    .map((t) => {
      const curso = cursos.find((c) => c.id === t.cursoId);
      return { ...t, curso: curso?.nombre, color: curso?.color };
    });

  const recientes = pendientes
    .filter((t) => new Date(t.fechaLimite) >= ahora)
    .sort((a, b) => new Date(a.fechaLimite) - new Date(b.fechaLimite));

  const atrasadas = pendientes
    .filter((t) => new Date(t.fechaLimite) < ahora)
    .sort((a, b) => new Date(a.fechaLimite) - new Date(b.fechaLimite));

  res.json({ recientes, atrasadas });
}
