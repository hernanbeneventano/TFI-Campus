import { cursos, tareas, clases, eventos } from '../data/mock.js';

// Día en formato AAAA-MM-DD, en hora local. Es la clave con la que el
// frontend agrupa los eventos en las celdas del calendario.
function claveDia(fecha) {
  const d = new Date(fecha);
  const mes = String(d.getMonth() + 1).padStart(2, '0');
  const dia = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mes}-${dia}`;
}

function datosDelCurso(cursoId) {
  const curso = cursos.find((c) => c.id === cursoId);
  return { curso: curso?.nombre, codigo: curso?.codigo, color: curso?.color, cursoId };
}

// Las clases son semanales: se repiten en cada fecha del rango que caiga en
// su día de la semana.
function clasesEnRango(desde, hasta) {
  const expandidas = [];
  const dia = new Date(desde);
  dia.setHours(0, 0, 0, 0);

  while (dia <= hasta) {
    // getDay() da 0 para domingo; en los datos el lunes es 1
    const diaSemana = dia.getDay() === 0 ? 7 : dia.getDay();

    for (const clase of clases.filter((c) => c.dia === diaSemana)) {
      const info = datosDelCurso(clase.cursoId);
      expandidas.push({
        id: `clase-${clase.cursoId}-${claveDia(dia)}`,
        tipo: 'clase',
        titulo: `Clase de ${info.curso}`,
        dia: claveDia(dia),
        fecha: new Date(dia).toISOString(),
        desde: clase.desde,
        hasta: clase.hasta,
        lugar: clase.aula,
        ...info,
      });
    }

    dia.setDate(dia.getDate() + 1);
  }

  return expandidas;
}

// Todo lo que pasa entre dos fechas: entregas, exámenes, clases y eventos.
export function listarCalendario(req, res) {
  const desde = req.query.desde ? new Date(req.query.desde) : new Date();
  const hasta = req.query.hasta ? new Date(req.query.hasta) : new Date();

  if (Number.isNaN(desde.getTime()) || Number.isNaN(hasta.getTime()) || hasta < desde) {
    return res.status(400).json({ error: 'Rango de fechas inválido' });
  }

  desde.setHours(0, 0, 0, 0);
  hasta.setHours(23, 59, 59, 999);

  const entregas = tareas.map((t) => ({
    id: `entrega-${t.id}`,
    tipo: 'entrega',
    titulo: t.titulo,
    tareaId: t.id,
    entregada: t.entregada,
    dia: claveDia(t.fechaLimite),
    fecha: t.fechaLimite,
    desde: new Date(t.fechaLimite).toTimeString().slice(0, 5),
    ...datosDelCurso(t.cursoId),
  }));

  const fijos = eventos.map((e) => ({
    ...e,
    id: `${e.tipo}-${e.id}`,
    dia: claveDia(e.fecha),
    ...(e.cursoId ? datosDelCurso(e.cursoId) : {}),
  }));

  const todo = [...entregas, ...fijos, ...clasesEnRango(desde, hasta)]
    .filter((e) => {
      const cuando = new Date(e.fecha);
      return cuando >= desde && cuando <= hasta;
    })
    .sort((a, b) => a.dia.localeCompare(b.dia) || (a.desde ?? '').localeCompare(b.desde ?? ''));

  res.json(todo);
}
