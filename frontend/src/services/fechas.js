// Tiempo transcurrido en palabras: "recién", "hace 12 min", "hace 2 horas",
// "hace 3 días", "hace 2 meses".
export function hace(iso) {
  if (!iso) return null;

  const minutos = Math.round((Date.now() - new Date(iso)) / 60000);
  if (minutos < 1) return 'recién';
  if (minutos < 60) return `hace ${minutos} min`;

  const horas = Math.round(minutos / 60);
  if (horas < 24) return `hace ${horas} ${horas === 1 ? 'hora' : 'horas'}`;

  const dias = Math.round(horas / 24);
  if (dias < 30) return `hace ${dias} ${dias === 1 ? 'día' : 'días'}`;

  const meses = Math.round(dias / 30);
  return `hace ${meses} ${meses === 1 ? 'mes' : 'meses'}`;
}

// Fechas absolutas, para lo que tiene día fijo: una mesa de examen no se
// entiende como "en 12 días", se entiende como "jueves 27 de noviembre".
const conDia = new Intl.DateTimeFormat('es-AR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
});

const sinDia = new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'long' });

const conAnio = new Intl.DateTimeFormat('es-AR', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
});

export function fechaConDia(iso) {
  return iso ? conDia.format(new Date(iso)) : null;
}

export function fechaCorta(iso) {
  return iso ? sinDia.format(new Date(iso)) : null;
}

export function fechaLarga(iso) {
  return iso ? conAnio.format(new Date(iso)) : null;
}

/** Cuántos días faltan: negativo si ya pasó, 0 si es hoy. */
export function diasHasta(iso) {
  if (!iso) return null;
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const dia = new Date(iso);
  dia.setHours(0, 0, 0, 0);
  return Math.round((dia - hoy) / 86400000);
}

/** "hoy", "mañana", "en 5 días", "hace 3 días" */
export function enDias(iso) {
  const dias = diasHasta(iso);
  if (dias === null) return null;
  if (dias === 0) return 'hoy';
  if (dias === 1) return 'mañana';
  if (dias === -1) return 'ayer';
  if (dias > 0) return `en ${dias} días`;
  return `hace ${-dias} días`;
}
