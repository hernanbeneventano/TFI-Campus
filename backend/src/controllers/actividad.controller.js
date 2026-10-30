import { actividad } from '../data/mock.js';

// Devuelve la actividad agrupada: importante, próximo, hoy y reciente
export function listarActividad(req, res) {
  const grupos = { importante: [], proximo: [], hoy: [], reciente: [] };
  for (const item of actividad) {
    grupos[item.grupo]?.push(item);
  }
  res.json(grupos);
}
