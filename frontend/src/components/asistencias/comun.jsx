// Las piezas que comparten las pantallas de asistencia.
//
// El semáforo es la idea central: verde si está dentro del cupo de faltas,
// ámbar si le quedan pocas, rojo si ya lo pasó. Mira **las faltas que le
// quedan**, no el porcentaje de lo dictado hasta hoy: con 40 clases
// previstas y 8 faltas de 10, el alumno va por debajo del 75 % *ahora* pero
// asistiendo al resto termina regular, y decirle que está perdido sería
// desinformarlo.

import { IconoCheckCirculo, IconoAdvertencia, IconoReloj } from '../Iconos.jsx';

export const ESTADOS = {
  presente: { texto: 'Presente', clase: 'presente', corto: 'P' },
  ausente: { texto: 'Ausente', clase: 'ausente', corto: 'A' },
  justificada: { texto: 'Justificada', clase: 'justificada', corto: 'J' },
};

export const SITUACION = {
  'al día': { clase: 'al-dia', Icono: IconoCheckCirculo, texto: 'Al día' },
  'en riesgo': { clase: 'en-riesgo', Icono: IconoAdvertencia, texto: 'En riesgo' },
  'por debajo': { clase: 'por-debajo', Icono: IconoAdvertencia, texto: 'Por debajo' },
  'sin clases': { clase: 'sin-clases', Icono: IconoReloj, texto: 'Sin clases' },
};

/** La etiqueta de cómo viene alguien. */
export function Situacion({ estado, chica = false }) {
  const { clase, Icono, texto } = SITUACION[estado] ?? SITUACION['sin clases'];
  return (
    <span className={`situacion ${clase} ${chica ? 'chica' : ''}`}>
      <Icono width={chica ? 13 : 15} height={chica ? 13 : 15} />
      {texto}
    </span>
  );
}

/** El estado de una persona en una clase concreta. */
export function EstadoAsistencia({ estado, sinRegistrar = 'Sin tomar' }) {
  if (!estado) return <span className="estado-asistencia vacio">{sinRegistrar}</span>;
  const { texto, clase } = ESTADOS[estado] ?? ESTADOS.ausente;
  return <span className={`estado-asistencia ${clase}`}>{texto}</span>;
}

/**
 * La barra de asistencia, con la marca del mínimo exigido.
 *
 * La marca es lo que convierte el número en una respuesta: 68 % no dice
 * nada hasta que se ve de qué lado del 75 % cae.
 */
export function BarraAsistencia({ porcentaje, minimo, estado }) {
  const valor = porcentaje ?? 0;
  const { clase } = SITUACION[estado] ?? SITUACION['sin clases'];
  return (
    <div className="barra-asistencia" title={`${valor}% · mínimo ${minimo}%`}>
      <div className={`barra-asistencia-relleno ${clase}`} style={{ width: `${valor}%` }} />
      <span className="barra-asistencia-minimo" style={{ left: `${minimo}%` }} aria-hidden="true" />
    </div>
  );
}

/** Una tarjeta de número, de las que encabezan los paneles. */
export function Dato({ valor, etiqueta, variante = '' }) {
  return (
    <div className={`dato-asistencia ${variante}`}>
      <strong>{valor}</strong>
      <small>{etiqueta}</small>
    </div>
  );
}
