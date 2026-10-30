// Datos de prueba. Se reemplazarán por la base de datos cuando se defina.

export const cursos = [
  {
    id: 1,
    codigo: 'PROG-2',
    nombre: 'Programación II',
    periodo: '2026 – 2.º cuatrimestre',
    color: '#4f6bed',
    favorito: true,
  },
  {
    id: 2,
    codigo: 'BD-1',
    nombre: 'Bases de Datos',
    periodo: '2026 – 2.º cuatrimestre',
    color: '#1f9d7a',
    favorito: true,
  },
  {
    id: 3,
    codigo: 'IS-1',
    nombre: 'Ingeniería de Software',
    periodo: '2026 – 2.º cuatrimestre',
    color: '#d9822b',
    favorito: false,
  },
];

export const actividad = [
  {
    id: 1,
    grupo: 'importante',
    tipo: 'entrega',
    titulo: 'Trabajo práctico 3',
    curso: 'Programación II',
    fecha: '2026-10-31T16:00:00',
  },
  {
    id: 2,
    grupo: 'proximo',
    tipo: 'entrega',
    titulo: 'Modelo entidad-relación',
    curso: 'Bases de Datos',
    fecha: '2026-11-05T16:00:00',
  },
  {
    id: 3,
    grupo: 'hoy',
    tipo: 'anuncio',
    titulo: 'La clase de hoy pasa al aula 12',
    curso: 'Ingeniería de Software',
    fecha: '2026-10-30T09:00:00',
  },
  {
    id: 4,
    grupo: 'reciente',
    tipo: 'nota',
    titulo: 'Nota publicada: Parcial 1',
    curso: 'Programación II',
    fecha: '2026-10-27T12:00:00',
  },
];
