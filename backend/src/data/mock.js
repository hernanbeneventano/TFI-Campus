// Datos de prueba. Se reemplazarán por la base de datos cuando se defina.

// Devuelve una fecha a N días de hoy (negativo = en el pasado), a las 16:00.
// Así los datos de prueba siempre tienen tareas próximas y atrasadas.
function aDias(n) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  d.setHours(16, 0, 0, 0);
  return d.toISOString();
}

// Estado de presencia a partir del último acceso. Mismos cortes que usa el
// frontend para el usuario que está navegando.
export function estadoPorAcceso(iso) {
  const minutos = (Date.now() - new Date(iso)) / 60000;
  if (minutos < 5) return 'conectado';
  if (minutos < 30) return 'ausente';
  return 'desconectado';
}

// Las personas de prueba guardan hace cuántos minutos entraron, no una fecha
// fija: así la fecha se calcula en cada pedido y los estados siguen teniendo
// sentido por más que el servidor lleve horas levantado.
export function conPresencia({ accesoHaceMin, ...persona }) {
  const ultimoAcceso = new Date(Date.now() - accesoHaceMin * 60000).toISOString();
  return { ...persona, ultimoAcceso, estado: estadoPorAcceso(ultimoAcceso) };
}

// El usuario que inició sesión (por ahora fijo). Es la persona 1, pero con
// el nombre partido para mostrarlo en el menú.
export const usuarioActual = {
  id: 1,
  nombre: 'Santiago',
  apellido: 'Sosa',
  rol: 'Estudiante',
  accesoHaceMin: 135,
};

export const cursos = [
  {
    id: 1,
    codigo: 'PROG-2',
    nombre: 'Programación II',
    docente: 'Lic. María Gómez',
    docenteId: 2,
    periodo: '2026 – 2.º cuatrimestre',
    color: '#D80032',
    favorito: true,
  },
  {
    id: 2,
    codigo: 'BD-1',
    nombre: 'Bases de Datos',
    docente: 'Ing. Pablo Ruiz',
    docenteId: 7,
    periodo: '2026 – 2.º cuatrimestre',
    color: '#2B2D42',
    favorito: true,
  },
  {
    id: 3,
    codigo: 'IS-1',
    nombre: 'Ingeniería de Software',
    docente: 'Mgter. Laura Benítez',
    docenteId: 8,
    periodo: '2026 – 2.º cuatrimestre',
    color: '#A4193D',
    favorito: false,
  },
  {
    id: 4,
    codigo: 'RED-1',
    nombre: 'Redes de Computadoras',
    docente: 'Ing. Diego Fernández',
    docenteId: 9,
    periodo: '2026 – 2.º cuatrimestre',
    color: '#4A5068',
    favorito: false,
  },
  {
    id: 5,
    codigo: 'MAT-3',
    nombre: 'Probabilidad y Estadística',
    docente: 'Lic. Ana Martínez',
    docenteId: 10,
    periodo: '2026 – 1.er cuatrimestre',
    color: '#5F6C82',
    favorito: false,
  },
  {
    id: 6,
    codigo: 'ALG-2',
    nombre: 'Algoritmos y Estructuras de Datos',
    docente: 'Lic. Jorge Romero',
    docenteId: 11,
    periodo: '2026 – 1.er cuatrimestre',
    color: '#C41235',
    favorito: false,
  },
];

// `publicada` es cuándo la subió el docente: sirve para marcar las novedades.
export const tareas = [
  { id: 1, cursoId: 1, titulo: 'Trabajo práctico 3: Listas enlazadas', publicada: aDias(-3), fechaLimite: aDias(1), entregada: false },
  { id: 2, cursoId: 2, titulo: 'Modelo entidad-relación', publicada: aDias(-11), fechaLimite: aDias(4), entregada: false },
  { id: 3, cursoId: 3, titulo: 'Documento de requisitos', publicada: aDias(-2), fechaLimite: aDias(9), entregada: false },
  { id: 4, cursoId: 4, titulo: 'Cuestionario: modelo OSI', publicada: aDias(-14), fechaLimite: aDias(-2), entregada: false },
  { id: 5, cursoId: 1, titulo: 'Ejercicios de recursividad', publicada: aDias(-20), fechaLimite: aDias(-5), entregada: false },
  { id: 6, cursoId: 2, titulo: 'Consultas SQL básicas', publicada: aDias(-15), fechaLimite: aDias(-3), entregada: true },
];

export const actividad = [
  { id: 1, grupo: 'importante', tipo: 'entrega', titulo: 'Trabajo práctico 3', curso: 'Programación II', fecha: aDias(1) },
  { id: 2, grupo: 'proximo', tipo: 'entrega', titulo: 'Modelo entidad-relación', curso: 'Bases de Datos', fecha: aDias(4) },
  { id: 3, grupo: 'hoy', tipo: 'anuncio', titulo: 'La clase de hoy pasa al aula 12', curso: 'Ingeniería de Software', fecha: aDias(0) },
  { id: 4, grupo: 'reciente', tipo: 'nota', titulo: 'Nota publicada: Parcial 1', curso: 'Programación II', fecha: aDias(-3) },
];

// Contenido de cada módulo, organizado en carpetas (secciones).
// Tipos de elemento: 'pagina' (texto), 'archivo' (PDF, video…), 'tarea' (enlaza con `tareas`)
// y 'tablero' (columnas de publicaciones, para consultas).
export const contenidos = {
  1: [
    {
      id: 1,
      titulo: 'Información del módulo',
      descripcion: 'Bienvenida, programa y cronograma de la materia',
      items: [
        {
          id: '1-1',
          tipo: 'pagina',
          titulo: 'Bienvenida al módulo',
          cuerpo: [
            '¡Bienvenidos a Programación II! En este módulo vamos a trabajar con estructuras de datos dinámicas, recursividad y una introducción a la programación orientada a objetos.',
            'Cada semana vas a encontrar una carpeta con el material de lectura, los videos de la clase y las actividades. Las entregas se hacen desde el mismo campus.',
            'Ante cualquier duda, usá el tablero de consultas: así las respuestas quedan visibles para todo el curso.',
          ],
        },
        { id: '1-2', tipo: 'archivo', titulo: 'Programa de la materia', formato: 'PDF', tamano: '320 KB' },
        { id: '1-3', tipo: 'archivo', titulo: 'Cronograma de clases y parciales', formato: 'PDF', tamano: '96 KB' },
      ],
    },
    {
      id: 2,
      titulo: 'Semana 1: Recursividad',
      descripcion: 'Funciones recursivas, caso base y pila de llamadas',
      items: [
        { id: '1-4', tipo: 'archivo', titulo: 'Clase 1: Recursividad', formato: 'Video', tamano: '42 min' },
        { id: '1-5', tipo: 'archivo', titulo: 'Apunte: pensar en recursivo', formato: 'PDF', tamano: '1,2 MB' },
        { id: '1-6', tipo: 'tarea', titulo: 'Ejercicios de recursividad', tareaId: 5 },
      ],
    },
    {
      id: 3,
      titulo: 'Semana 2: Listas enlazadas',
      descripcion: 'Nodos, inserción, borrado y recorrido',
      items: [
        { id: '1-7', tipo: 'archivo', titulo: 'Clase 2: Listas enlazadas', formato: 'Video', tamano: '51 min' },
        { id: '1-8', tipo: 'archivo', titulo: 'Diapositivas de la clase', formato: 'PDF', tamano: '2,4 MB' },
        { id: '1-9', tipo: 'tarea', titulo: 'Trabajo práctico 3: Listas enlazadas', tareaId: 1 },
      ],
    },
    {
      id: 4,
      titulo: 'Consultas',
      descripcion: 'Preguntas, comentarios e inquietudes sobre la materia',
      items: [
        {
          id: '1-10',
          tipo: 'tablero',
          titulo: 'Preguntas, comentarios e inquietudes',
          columnas: [
            {
              titulo: 'Preguntas',
              publicaciones: [
                {
                  id: 1,
                  autor: 'Lucía Acosta',
                  fecha: aDias(-1),
                  texto: '¿El TP 3 se puede hacer en grupos de dos o es individual?',
                },
                {
                  id: 2,
                  autor: 'Lic. María Gómez',
                  fecha: aDias(-1),
                  texto: 'Es individual. La defensa oral sí puede ser en el horario de consulta de los jueves.',
                },
              ],
            },
            {
              titulo: 'Comentarios',
              publicaciones: [
                {
                  id: 3,
                  autor: 'Lic. María Gómez',
                  fecha: aDias(-2),
                  texto: 'Ya está subido el video de la clase 2 en la carpeta de la semana.',
                },
              ],
            },
            {
              titulo: 'Inquietudes',
              publicaciones: [
                {
                  id: 4,
                  autor: 'Tomás Herrera',
                  fecha: aDias(-3),
                  texto: 'El apunte de recursividad tiene un error en el ejemplo de Fibonacci (página 4).',
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};

// Contenido mínimo para los módulos que todavía no tienen uno propio
export function contenidoGenerico(curso) {
  const tareasCurso = tareas.filter((t) => t.cursoId === curso.id);
  return [
    {
      id: 1,
      titulo: 'Información del módulo',
      descripcion: 'Bienvenida y programa de la materia',
      items: [
        {
          id: `${curso.id}-1`,
          tipo: 'pagina',
          titulo: 'Bienvenida al módulo',
          cuerpo: [
            `¡Bienvenidos a ${curso.nombre}! Acá vas a encontrar todo el material de la materia organizado por semana.`,
            `Docente a cargo: ${curso.docente}.`,
          ],
        },
        { id: `${curso.id}-2`, tipo: 'archivo', titulo: 'Programa de la materia', formato: 'PDF', tamano: '280 KB' },
      ],
    },
    {
      id: 2,
      titulo: 'Semana 1',
      descripcion: 'Material y actividades de la primera semana',
      items: [
        { id: `${curso.id}-3`, tipo: 'archivo', titulo: 'Clase 1', formato: 'Video', tamano: '45 min' },
        ...tareasCurso.map((t) => ({ id: `${curso.id}-t${t.id}`, tipo: 'tarea', titulo: t.titulo, tareaId: t.id })),
      ],
    },
  ];
}

// Anuncios del docente en cada módulo
export const anuncios = {
  1: [
    {
      id: 1,
      titulo: 'Cambio de aula para la clase del jueves',
      cuerpo: 'La clase del jueves pasa al laboratorio 3. Lleven la notebook con el entorno ya instalado.',
      autor: 'Lic. María Gómez',
      fecha: aDias(-1),
    },
    {
      id: 2,
      titulo: 'Ya está disponible el video de la clase 2',
      cuerpo: 'Lo subí a la carpeta de la Semana 2, junto con las diapositivas.',
      autor: 'Lic. María Gómez',
      fecha: aDias(-2),
    },
    {
      id: 3,
      titulo: 'Fechas de los parciales',
      cuerpo: 'El primer parcial es el 12 de noviembre y el segundo el 10 de diciembre, ambos en el horario de clase.',
      autor: 'Lic. María Gómez',
      fecha: aDias(-8),
    },
  ],
};

// Todas las personas del campus, cada una con su id. Los módulos y los
// mensajes las referencian por ese id en vez de repetir los datos.
export const personas = [
  { id: 1, nombre: 'Santiago Sosa', rol: 'Estudiante', accesoHaceMin: 1 },
  { id: 2, nombre: 'María Gómez', rol: 'Docente', accesoHaceMin: 3 },
  { id: 3, nombre: 'Hernán Beneventano', rol: 'Estudiante', accesoHaceMin: 12 },
  { id: 4, nombre: 'Lucía Acosta', rol: 'Estudiante', accesoHaceMin: 95 },
  { id: 5, nombre: 'Tomás Herrera', rol: 'Estudiante', accesoHaceMin: 60 * 26 },
  { id: 6, nombre: 'Camila Duarte', rol: 'Estudiante', accesoHaceMin: 60 * 24 * 48 },
  { id: 7, nombre: 'Pablo Ruiz', rol: 'Docente', accesoHaceMin: 35 },
  { id: 8, nombre: 'Laura Benítez', rol: 'Docente', accesoHaceMin: 8 },
  { id: 9, nombre: 'Diego Fernández', rol: 'Docente', accesoHaceMin: 60 * 5 },
  { id: 10, nombre: 'Ana Martínez', rol: 'Docente', accesoHaceMin: 60 * 30 },
  { id: 11, nombre: 'Jorge Romero', rol: 'Docente', accesoHaceMin: 60 * 12 },
];

export function buscarPersona(id) {
  return personas.find((p) => p.id === Number(id));
}

// Quiénes están inscriptos en cada módulo. Los módulos sin lista propia usan
// una genérica: su docente y un par de estudiantes.
export const participantes = {
  1: [2, 1, 3, 4, 5, 6],
};

export function participantesDeCurso(curso) {
  const ids = participantes[curso.id] || [curso.docenteId, 1, 3];
  return ids.map(buscarPersona).filter(Boolean);
}

// Para los módulos que todavía no tienen anuncios propios
export function anunciosGenericos(curso) {
  return [
    {
      id: 1,
      titulo: `Bienvenidos a ${curso.nombre}`,
      cuerpo: 'En la carpeta de información está el programa de la materia y el cronograma.',
      autor: curso.docente,
      fecha: aDias(-12),
    },
  ];
}


// Carpetas de un curso con los datos de sus tareas ya resueltos (fecha límite
// y si están entregadas). La usan tanto la pantalla del módulo como el panel
// de tareas pendientes.
export function carpetasDeCurso(curso) {
  const base = contenidos[curso.id] || contenidoGenerico(curso);
  return base.map((carpeta) => ({
    ...carpeta,
    items: carpeta.items.map((item) => {
      if (item.tipo !== 'tarea') return item;
      const tarea = tareas.find((t) => t.id === item.tareaId);
      return { ...item, fechaLimite: tarea?.fechaLimite, entregada: tarea?.entregada ?? false };
    }),
  }));
}


// Novedades de un módulo: lo publicado en la última semana. Es lo que enciende
// la campanita en la tarjeta de Módulos.
const DIAS_NOVEDAD = 7;

export function novedadesDeCurso(curso) {
  const desde = Date.now() - DIAS_NOVEDAD * 24 * 60 * 60 * 1000;

  const anunciosNuevos = (anuncios[curso.id] || anunciosGenericos(curso)).filter(
    (a) => new Date(a.fecha) >= desde
  ).length;

  const tareasNuevas = tareas.filter(
    (t) => t.cursoId === curso.id && !t.entregada && new Date(t.publicada) >= desde
  ).length;

  return { anuncios: anunciosNuevos, tareas: tareasNuevas, total: anunciosNuevos + tareasNuevas };
}

// ===================== Mensajes =====================
// Conversaciones de a dos. Cada una guarda los ids de quienes hablan y los
// mensajes en orden. Viven en memoria: se reinician cuando se reinicia el
// servidor, hasta que haya base de datos.

function haceHoras(n) {
  return new Date(Date.now() - n * 3600000).toISOString();
}

export const conversaciones = [
  {
    id: 1,
    entre: [1, 2],
    mensajes: [
      {
        id: 1,
        deId: 1,
        texto: 'Hola profe, una consulta sobre el TP 3: ¿la lista tiene que ser doblemente enlazada o alcanza con simple?',
        fecha: haceHoras(26),
        leido: true,
      },
      {
        id: 2,
        deId: 2,
        texto: 'Hola Santiago. Con simple alcanza. Si hacés la doble, suma, pero no es obligatorio.',
        fecha: haceHoras(25),
        leido: true,
      },
      {
        id: 3,
        deId: 2,
        texto: 'Ah, y acordate de incluir el informe en el mismo archivo .zip.',
        fecha: haceHoras(3),
        leido: false,
      },
    ],
  },
  {
    id: 2,
    entre: [1, 3],
    mensajes: [
      {
        id: 4,
        deId: 3,
        texto: '¿Arrancaste el modelo entidad-relación? Me está costando la parte de las cardinalidades.',
        fecha: haceHoras(5),
        leido: false,
      },
    ],
  },
  {
    id: 3,
    entre: [1, 4],
    mensajes: [
      {
        id: 5,
        deId: 1,
        texto: 'Lucía, ¿tenés el apunte de recursividad corregido? El de la página 4 tiene el error de Fibonacci.',
        fecha: haceHoras(50),
        leido: true,
      },
      {
        id: 6,
        deId: 4,
        texto: 'Sí, lo subió la profe de nuevo ayer a la carpeta de la semana 1.',
        fecha: haceHoras(48),
        leido: true,
      },
    ],
  },
];

// Para que los ids nuevos no choquen con los de prueba
let proximoIdMensaje = 100;
let proximoIdConversacion = 100;

export function nuevoIdMensaje() {
  return proximoIdMensaje++;
}

export function nuevoIdConversacion() {
  return proximoIdConversacion++;
}

// A quiénes le puede escribir una persona: solo la gente de los módulos en
// los que está, no todo el campus. Cada contacto viene con los módulos que
// comparten, para ubicarlo en la búsqueda.
export function contactosDe(personaId) {
  const porId = new Map();

  for (const curso of cursos) {
    const gente = participantesDeCurso(curso);
    if (!gente.some((p) => p.id === personaId)) continue;

    for (const persona of gente) {
      if (persona.id === personaId) continue;
      if (!porId.has(persona.id)) porId.set(persona.id, { ...persona, modulos: [] });
      porId.get(persona.id).modulos.push(curso.nombre);
    }
  }

  return [...porId.values()];
}

// ===================== Información de la facultad =====================
// Avisos institucionales: inscripciones, biblioteca, becas, campus.
export const avisos = [
  {
    id: 1,
    categoria: 'Inscripciones',
    titulo: 'Inscripción a exámenes finales de noviembre',
    cuerpo:
      'La inscripción abre el 3 de noviembre y cierra 48 horas antes de cada mesa. Se hace desde el SIU, con el usuario de la facultad.',
    fecha: aDias(-1),
  },
  {
    id: 2,
    categoria: 'Biblioteca',
    titulo: 'Nuevo horario de la biblioteca',
    cuerpo:
      'De lunes a viernes de 8 a 20, y los sábados de 9 a 13. La sala de lectura queda abierta hasta las 22 en época de parciales.',
    fecha: aDias(-4),
  },
  {
    id: 3,
    categoria: 'Becas',
    titulo: 'Resultados de las becas de ayuda económica',
    cuerpo:
      'Ya se pueden consultar los resultados en Bienestar Estudiantil. Quienes queden en lista de espera van a recibir un aviso por este mismo campus.',
    fecha: aDias(-9),
  },
  {
    id: 4,
    categoria: 'Campus',
    titulo: 'Corte de agua programado',
    cuerpo:
      'El sábado de 7 a 14 no va a haber agua en el pabellón de aulas por mantenimiento. Las clases de ese día pasan al pabellón central.',
    fecha: aDias(-16),
  },
];

// Lo publicado en la última semana, en cada apartado del menú. Es lo que
// enciende las campanitas del menú lateral.
export function resumenDeNovedades(personaId) {
  const desde = Date.now() - DIAS_NOVEDAD * 24 * 60 * 60 * 1000;

  const modulos = cursos.filter((curso) => novedadesDeCurso(curso).total > 0).length;
  const informacion = avisos.filter((a) => new Date(a.fecha) >= desde).length;

  const mensajes = conversaciones
    .filter((c) => c.entre.includes(personaId))
    .reduce(
      (total, c) => total + c.mensajes.filter((m) => m.deId !== personaId && !m.leido).length,
      0
    );

  return { modulos, mensajes, informacion };
}
