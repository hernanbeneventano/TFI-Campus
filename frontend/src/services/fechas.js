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
