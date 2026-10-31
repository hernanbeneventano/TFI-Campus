import { tareas, cursos, carpetasDeCurso } from '../data/mock.js';

// La carpeta donde vive una tarea, con todo lo que hay que completar adentro.
// El frontend lo usa para mostrar el "1 de 2" del apartado: cuenta los
// recursos que el alumno marcó más las tareas que ya entregó.
function apartadoDe(curso, tareaId) {
  for (const carpeta of carpetasDeCurso(curso)) {
    if (!carpeta.items.some((i) => i.tipo === 'tarea' && i.tareaId === tareaId)) continue;
    return {
      titulo: carpeta.titulo,
      items: carpeta.items.map((i) =>
        i.tipo === 'tarea' ? { id: i.id, tipo: i.tipo, entregada: i.entregada } : { id: i.id, tipo: i.tipo }
      ),
    };
  }
  return null;
}

// Tareas sin entregar, separadas en próximas (todavía en fecha) y atrasadas.
export function listarPendientes(req, res) {
  const ahora = new Date();

  const pendientes = tareas
    .filter((t) => !t.entregada)
    .map((t) => {
      const curso = cursos.find((c) => c.id === t.cursoId);
      return {
        ...t,
        curso: curso?.nombre,
        color: curso?.color,
        apartado: curso ? apartadoDe(curso, t.id) : null,
      };
    });

  const recientes = pendientes
    .filter((t) => new Date(t.fechaLimite) >= ahora)
    .sort((a, b) => new Date(a.fechaLimite) - new Date(b.fechaLimite));

  const atrasadas = pendientes
    .filter((t) => new Date(t.fechaLimite) < ahora)
    .sort((a, b) => new Date(a.fechaLimite) - new Date(b.fechaLimite));

  res.json({ recientes, atrasadas });
}
