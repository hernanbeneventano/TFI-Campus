// Datos de prueba. Se reemplazarán por la base de datos cuando se defina.

// Devuelve una fecha a N días de hoy (negativo = en el pasado), a las 16:00.
// Así los datos de prueba siempre tienen tareas próximas y atrasadas.
function aDias(n) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  d.setHours(16, 0, 0, 0);
  return d.toISOString();
}

export const usuarioActual = {
  id: 1,
  nombre: 'Santiago',
  apellido: 'Sosa',
  rol: 'Estudiante',
};

export const cursos = [
  {
    id: 1,
    codigo: 'PROG-2',
    nombre: 'Programación II',
    docente: 'Lic. María Gómez',
    periodo: '2026 – 2.º cuatrimestre',
    color: '#4A6FA5',
    favorito: true,
  },
  {
    id: 2,
    codigo: 'BD-1',
    nombre: 'Bases de Datos',
    docente: 'Ing. Pablo Ruiz',
    periodo: '2026 – 2.º cuatrimestre',
    color: '#1F2444',
    favorito: true,
  },
  {
    id: 3,
    codigo: 'IS-1',
    nombre: 'Ingeniería de Software',
    docente: 'Mgter. Laura Benítez',
    periodo: '2026 – 2.º cuatrimestre',
    color: '#2E4A7A',
    favorito: false,
  },
  {
    id: 4,
    codigo: 'RED-1',
    nombre: 'Redes de Computadoras',
    docente: 'Ing. Diego Fernández',
    periodo: '2026 – 2.º cuatrimestre',
    color: '#3D5A80',
    favorito: false,
  },
  {
    id: 5,
    codigo: 'MAT-3',
    nombre: 'Probabilidad y Estadística',
    docente: 'Lic. Ana Martínez',
    periodo: '2026 – 1.er cuatrimestre',
    color: '#031D44',
    favorito: false,
  },
  {
    id: 6,
    codigo: 'ALG-2',
    nombre: 'Algoritmos y Estructuras de Datos',
    docente: 'Lic. Jorge Romero',
    periodo: '2026 – 1.er cuatrimestre',
    color: '#5B7DB1',
    favorito: false,
  },
];

export const tareas = [
  { id: 1, cursoId: 1, titulo: 'Trabajo práctico 3: Listas enlazadas', fechaLimite: aDias(1), entregada: false },
  { id: 2, cursoId: 2, titulo: 'Modelo entidad-relación', fechaLimite: aDias(4), entregada: false },
  { id: 3, cursoId: 3, titulo: 'Documento de requisitos', fechaLimite: aDias(9), entregada: false },
  { id: 4, cursoId: 4, titulo: 'Cuestionario: modelo OSI', fechaLimite: aDias(-2), entregada: false },
  { id: 5, cursoId: 1, titulo: 'Ejercicios de recursividad', fechaLimite: aDias(-5), entregada: false },
  { id: 6, cursoId: 2, titulo: 'Consultas SQL básicas', fechaLimite: aDias(-3), entregada: true },
];

export const actividad = [
  { id: 1, grupo: 'importante', tipo: 'entrega', titulo: 'Trabajo práctico 3', curso: 'Programación II', fecha: aDias(1) },
  { id: 2, grupo: 'proximo', tipo: 'entrega', titulo: 'Modelo entidad-relación', curso: 'Bases de Datos', fecha: aDias(4) },
  { id: 3, grupo: 'hoy', tipo: 'anuncio', titulo: 'La clase de hoy pasa al aula 12', curso: 'Ingeniería de Software', fecha: aDias(0) },
  { id: 4, grupo: 'reciente', tipo: 'nota', titulo: 'Nota publicada: Parcial 1', curso: 'Programación II', fecha: aDias(-3) },
];
