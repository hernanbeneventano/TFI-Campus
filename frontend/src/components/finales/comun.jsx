// Piezas que comparten las tres pantallas de Finales del docente.
//
// Lo que ya existía se reutiliza y no se vuelve a escribir: las fechas salen
// de `services/fechas.js`, los avisos de `services/avisos.js` y los carteles
// de reconfirmación de `components/Confirmacion.jsx`, que son los mismos que
// usan las pantallas del alumno. Acá queda solo lo que es propio de la
// gestión: el taco de almanaque, el estado de una mesa y la exportación.

import { useEffect } from 'react';
import { IconoCerrar } from '../Iconos.jsx';
import { fechaCorta } from '../../services/fechas.js';

// ---------- Fechas ----------
// Las de siempre están en `services/fechas.js` (fechaConDia, fechaLarga,
// fechaCorta, enDias). Acá solo quedan las dos formas que esas no cubren.
const formatoMes = new Intl.DateTimeFormat('es-AR', { month: 'short' });
const formatoSemana = new Intl.DateTimeFormat('es-AR', { weekday: 'short' });
const formatoNumerico = new Intl.DateTimeFormat('es-AR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

/** "03/12/2026": para donde no entra el mes con letras —una celda de la
 *  tabla, un desplegable, una columna del CSV— y para que Excel la lea como
 *  fecha. En el resto de la pantalla se usan las de `services/fechas.js`. */
export const fechaNumerica = (iso) => (iso ? formatoNumerico.format(new Date(iso)) : null);

// Las partes del "taco de almanaque" de cada mesa
export function partesFecha(iso) {
  const fecha = new Date(iso);
  return {
    dia: fecha.getDate(),
    mes: formatoMes.format(fecha).replace('.', ''),
    semana: formatoSemana.format(fecha).replace('.', ''),
  };
}

// ISO → "2026-12-03" en la hora local, para los <input type="date">
export function aCampoFecha(iso) {
  const f = new Date(iso);
  const dos = (n) => String(n).padStart(2, '0');
  return `${f.getFullYear()}-${dos(f.getMonth() + 1)}-${dos(f.getDate())}`;
}

export const horario = (mesa) => `${mesa.desde} a ${mesa.hasta} h`;

// ---------- Estado de una mesa ----------
// Un solo texto por mesa, del más importante al menos: una cancelada no
// necesita decir que la inscripción está cerrada.
//
// Las clases son las mismas que usan las pantallas del alumno
// (`.estado-final`): verde lo terminado, ámbar lo que está a mitad de camino,
// el color principal lo accionable y gris lo que ya no se puede.
export function estadoMesa(mesa) {
  if (mesa.estado === 'cancelada') return { clase: 'cancelada', texto: 'Cancelada' };
  if (mesa.actaCerrada) return { clase: 'hecho', texto: 'Acta cerrada' };
  if (mesa.tomada) return { clase: 'espera', texto: 'Acta abierta' };
  if (mesa.periodo === 'abierta')
    return { clase: 'puede', texto: `Inscripción abierta hasta el ${fechaCorta(mesa.inscripcionHasta)}` };
  if (mesa.periodo === 'por-abrir')
    return { clase: 'espera', texto: `Inscripción desde el ${fechaCorta(mesa.inscripcionDesde)}` };
  return { clase: 'apagado', texto: 'Inscripción cerrada' };
}

export function EstadoMesa({ mesa }) {
  const { clase, texto } = estadoMesa(mesa);
  return <span className={`estado-final ${clase}`}>{texto}</span>;
}

// ---------- Condición del alumno en la materia ----------
// Sale del historial académico, así que son las mismas palabras que usa la
// pantalla de inscripción a materias, con sus mismas clases
// (`.estado-materia`). "En curso" lleva dos palabras, por eso hace falta el
// mapa y no alcanza con pasar la condición a minúsculas.
const CLASES_CONDICION = {
  Aprobada: 'aprobada',
  Regular: 'regular',
  'En curso': 'cursando',
  Libre: 'libre',
};

export function Condicion({ condicion }) {
  return (
    <span className={`estado-materia ${CLASES_CONDICION[condicion] ?? 'libre'}`}>{condicion}</span>
  );
}

// El resultado de un final: aprobado, desaprobado o ausente. Mismas clases
// que la tabla de notas del alumno.
export function Resultado({ resultado }) {
  const texto = resultado || 'Sin cargar';
  return <span className={`condicion ${resultado ? resultado.toLowerCase() : 'falta'}`}>{texto}</span>;
}

// ---------- Ventana superpuesta ----------
// Para los formularios: el de la mesa y el motivo de una cancelación. Lo que
// es solo confirmar —cerrar un acta— usa `Confirmacion`, el cartel que ya
// tenían las pantallas del alumno.
//
// Misma caja que el formulario de aportes de la Biblioteca: fondo oscurecido,
// se cierra con la X, con Escape o tocando afuera, y la página de atrás no se
// mueve mientras está abierta.
export function Ventana({ titulo, bajada, onCerrar, ocupado = false, onEnviar, children, className = '' }) {
  useEffect(() => {
    function alTeclado(e) {
      if (e.key === 'Escape' && !ocupado) onCerrar();
    }
    document.addEventListener('keydown', alTeclado);
    const antes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', alTeclado);
      document.body.style.overflow = antes;
    };
  }, [onCerrar, ocupado]);

  return (
    <div className="lector-fondo" onClick={() => !ocupado && onCerrar()} role="presentation">
      <form
        className={`lector aporte ${className}`.trim()}
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          onEnviar?.();
        }}
        aria-label={titulo}
        noValidate
      >
        <button
          type="button"
          className="lector-cerrar"
          onClick={onCerrar}
          disabled={ocupado}
          aria-label="Cerrar"
        >
          <IconoCerrar />
        </button>
        <header className="aporte-cabecera">
          <h2>{titulo}</h2>
          {bajada && <p className="texto-suave">{bajada}</p>}
        </header>
        {children}
      </form>
    </div>
  );
}

// ---------- Nombre de la materia ----------
// El punto lleva el color del módulo de esa materia, el mismo que usa en
// Módulos y en el Calendario. Una materia sin cursada abierta no tiene color
// propio: ahí el punto va en el oscuro de la interfaz.
export function NombreMateria({ materia }) {
  return (
    <span className="finales-materia">
      <span
        className="finales-punto"
        style={{ background: materia.color || 'var(--oscuro)' }}
        aria-hidden="true"
      />
      <small>{materia.codigo}</small>
      <strong>{materia.nombre}</strong>
    </span>
  );
}

// ---------- Exportar ----------
// CSV con punto y coma y la marca BOM: así Excel en castellano lo abre con
// las columnas separadas y las tildes bien, sin pasar por "importar datos".
export function descargarCsv(nombre, columnas, filas) {
  const celda = (valor) => `"${String(valor ?? '').replaceAll('"', '""')}"`;
  const texto = [columnas, ...filas].map((fila) => fila.map(celda).join(';')).join('\r\n');
  const archivo = new Blob(['﻿', texto], { type: 'text/csv;charset=utf-8' });
  const enlace = document.createElement('a');
  enlace.href = URL.createObjectURL(archivo);
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
}
