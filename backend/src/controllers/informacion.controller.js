import { avisos } from '../data/mock.js';

// Avisos de la facultad, del más nuevo al más viejo
export function listarAvisos(req, res) {
  res.json([...avisos].sort((a, b) => new Date(b.fecha) - new Date(a.fecha)));
}
