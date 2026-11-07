import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { obtenerCalendario } from '../services/api.js';
import { leerTiposCalendario, guardarTiposCalendario } from '../services/preferencias.js';
import Encabezado from '../components/Encabezado.jsx';
import { IconoFlecha, IconoTarea, IconoNotas, IconoModulos, IconoAnuncio } from '../components/Iconos.jsx';

const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

const iconoPorTipo = {
  entrega: IconoTarea,
  examen: IconoNotas,
  clase: IconoModulos,
  evento: IconoAnuncio,
};

const nombrePorTipo = {
  entrega: 'Entrega',
  examen: 'Examen',
  clase: 'Clase',
  evento: 'Evento',
};

// El orden en que aparecen los filtros
const TIPOS = [
  { clave: 'entrega', nombre: 'Entregas' },
  { clave: 'examen', nombre: 'Exámenes' },
  { clave: 'clase', nombre: 'Clases' },
  { clave: 'evento', nombre: 'Eventos' },
];

// --- Fechas, siempre en hora local ---
function clave(fecha) {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

// El lunes de la semana a la que pertenece una fecha
function lunesDe(fecha) {
  const d = new Date(fecha);
  const desplazamiento = d.getDay() === 0 ? 6 : d.getDay() - 1;
  d.setDate(d.getDate() - desplazamiento);
  d.setHours(0, 0, 0, 0);
  return d;
}

// La grilla del mes arranca el lunes de la semana del día 1 y termina el
// domingo de la semana del último día: por eso aparecen días del mes vecino.
function rangoVisible(fecha, vista) {
  if (vista === 'semana') {
    const desde = lunesDe(fecha);
    const hasta = new Date(desde);
    hasta.setDate(hasta.getDate() + 6);
    return { desde, hasta };
  }

  const primero = new Date(fecha.getFullYear(), fecha.getMonth(), 1);
  const ultimo = new Date(fecha.getFullYear(), fecha.getMonth() + 1, 0);
  const desde = lunesDe(primero);
  const hasta = lunesDe(ultimo);
  hasta.setDate(hasta.getDate() + 6);
  return { desde, hasta };
}

function diasEntre(desde, hasta) {
  const dias = [];
  const d = new Date(desde);
  while (d <= hasta) {
    dias.push(new Date(d));
    d.setDate(d.getDate() + 1);
  }
  return dias;
}

// Mayúscula solo en la primera letra: "capitalize" del CSS también se la
// pondría a los "de" del medio.
function conMayuscula(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function tituloDelPeriodo(fecha, vista, desde, hasta) {
  if (vista === 'mes') {
    return conMayuscula(fecha.toLocaleDateString('es-AR', { month: 'long', year: 'numeric' }));
  }
  const mismoMes = desde.getMonth() === hasta.getMonth();
  const inicio = desde.toLocaleDateString('es-AR', mismoMes ? { day: 'numeric' } : { day: 'numeric', month: 'short' });
  const fin = hasta.toLocaleDateString('es-AR', { day: 'numeric', month: 'short', year: 'numeric' });
  return `${inicio} al ${fin}`;
}

function Evento({ evento, conDetalle }) {
  const Icono = iconoPorTipo[evento.tipo] ?? IconoAnuncio;

  // En la vista mensual la celda es angosta: a las clases les alcanza con el
  // código de la materia, que entra entero. Que es una clase ya lo dicen el
  // ícono y el color, y el título completo está en el globito de ayuda.
  const etiqueta =
    !conDetalle && evento.tipo === 'clase' && evento.codigo
      ? evento.codigo
      : evento.titulo;

  const contenido = (
    <>
      <span className="evento-icono" style={{ color: evento.color }}>
        <Icono width={14} height={14} />
      </span>
      <span className="evento-texto">
        <strong>{etiqueta}</strong>
        {conDetalle && (
          <small>
            {evento.desde}
            {evento.hasta && evento.hasta !== evento.desde ? ` a ${evento.hasta}` : ''}
            {evento.lugar ? ` · ${evento.lugar}` : ''}
            {evento.curso ? ` · ${evento.curso}` : ''}
          </small>
        )}
      </span>
    </>
  );

  const ayuda = `${nombrePorTipo[evento.tipo]}${evento.curso ? ` · ${evento.curso}` : ''}${
    evento.desde ? ` · ${evento.desde}` : ''
  }`;

  // Las entregas llevan a la pantalla de entrega del módulo
  if (evento.tipo === 'entrega' && evento.cursoId) {
    return (
      <Link
        to={`/modulos/${evento.cursoId}?tarea=${evento.tareaId}`}
        className={`evento tipo-${evento.tipo}`}
        title={ayuda}
      >
        {contenido}
      </Link>
    );
  }

  return (
    <div className={`evento tipo-${evento.tipo}`} title={ayuda}>
      {contenido}
    </div>
  );
}

export default function Calendario() {
  const [vista, setVista] = useState('mes');
  const [ancla, setAncla] = useState(() => new Date());
  const [eventos, setEventos] = useState(null);
  const [tipos, setTipos] = useState(leerTiposCalendario);
  const [error, setError] = useState(null);

  const { desde, hasta } = useMemo(() => rangoVisible(ancla, vista), [ancla, vista]);
  const dias = useMemo(() => diasEntre(desde, hasta), [desde, hasta]);
  const hoy = clave(new Date());

  useEffect(() => {
    setEventos(null);
    obtenerCalendario(clave(desde), clave(hasta))
      .then(setEventos)
      .catch((e) => setError(e.message));
  }, [desde, hasta]);

  // Cuántos hay de cada tipo en el período, para mostrarlo en los filtros
  const cuantosPorTipo = useMemo(() => {
    const cuenta = {};
    for (const evento of eventos ?? []) {
      cuenta[evento.tipo] = (cuenta[evento.tipo] ?? 0) + 1;
    }
    return cuenta;
  }, [eventos]);

  // Los eventos visibles, agrupados por día para no recorrer la lista en
  // cada celda del calendario
  const porDia = useMemo(() => {
    const mapa = new Map();
    for (const evento of eventos ?? []) {
      if (!tipos.includes(evento.tipo)) continue;
      if (!mapa.has(evento.dia)) mapa.set(evento.dia, []);
      mapa.get(evento.dia).push(evento);
    }
    return mapa;
  }, [eventos, tipos]);

  const visibles = useMemo(
    () => (eventos ?? []).filter((e) => tipos.includes(e.tipo)).length,
    [eventos, tipos]
  );

  function alternarTipo(clave) {
    setTipos((actuales) => {
      // No se pueden apagar todos: dejaría el calendario sin sentido
      const siguiente = actuales.includes(clave)
        ? actuales.filter((t) => t !== clave)
        : [...actuales, clave];
      const definitivo = siguiente.length ? siguiente : actuales;
      guardarTiposCalendario(definitivo);
      return definitivo;
    });
  }

  function verTodo() {
    const todos = TIPOS.map((t) => t.clave);
    guardarTiposCalendario(todos);
    setTipos(todos);
  }

  function mover(pasos) {
    setAncla((actual) => {
      const d = new Date(actual);
      if (vista === 'mes') d.setMonth(d.getMonth() + pasos, 1);
      else d.setDate(d.getDate() + pasos * 7);
      return d;
    });
  }

  return (
    <div className="pagina">
      <Encabezado
        titulo="Calendario"
        descripcion="Entregas, exámenes, clases y eventos de la facultad"
      />

      <div className="calendario-barra">
        <div className="calendario-mover">
          <button type="button" onClick={() => mover(-1)} aria-label="Anterior">
            <IconoFlecha style={{ transform: 'rotate(180deg)' }} />
          </button>
          <button type="button" onClick={() => setAncla(new Date())} className="boton-suave">
            Hoy
          </button>
          <button type="button" onClick={() => mover(1)} aria-label="Siguiente">
            <IconoFlecha />
          </button>
        </div>

        <h2 className="calendario-periodo">{tituloDelPeriodo(ancla, vista, desde, hasta)}</h2>

        <div className="barra-vista" role="group" aria-label="Cómo ver el calendario">
          <button
            type="button"
            className={vista === 'mes' ? 'activo' : ''}
            onClick={() => setVista('mes')}
          >
            Mes
          </button>
          <button
            type="button"
            className={vista === 'semana' ? 'activo' : ''}
            onClick={() => setVista('semana')}
          >
            Semana
          </button>
        </div>
      </div>

      {/* Qué cosas mostrar: se puede dejar solo clases, solo entregas, etc. */}
      <div className="calendario-filtros">
        <button
          type="button"
          className={tipos.length === TIPOS.length ? 'filtro todo activo' : 'filtro todo'}
          onClick={verTodo}
        >
          Ver todo
        </button>
        {TIPOS.map(({ clave, nombre }) => (
          <button
            key={clave}
            type="button"
            // "tipo-" en el prefijo: si no, la clase "evento" del filtro
            // chocaría con la de los eventos de la grilla
            className={tipos.includes(clave) ? `filtro tipo-${clave} activo` : `filtro tipo-${clave}`}
            onClick={() => alternarTipo(clave)}
            aria-pressed={tipos.includes(clave)}
          >
            <span className="filtro-punto" />
            {nombre}
            <small>{cuantosPorTipo[clave] ?? 0}</small>
          </button>
        ))}
      </div>

      {error && <p className="error">No se pudo cargar el calendario. ¿Está corriendo el backend?</p>}

      {/* La `key` con la vista la vuelve a montar: con eso la grilla entra
          con su animación en vez de cambiar de golpe. */}
      <div key={vista} className={vista === 'mes' ? 'calendario mes' : 'calendario semana'}>
        {DIAS.map((dia) => (
          <div key={dia} className="calendario-dia-nombre">
            {dia}
          </div>
        ))}

        {dias.map((dia) => {
          const k = clave(dia);
          const delMes = dia.getMonth() === ancla.getMonth();
          const deHoy = k === hoy;
          const delDia = porDia.get(k) ?? [];

          return (
            <div
              key={k}
              className={[
                'calendario-celda',
                vista === 'mes' && !delMes ? 'fuera' : '',
                deHoy ? 'hoy' : '',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              <div className="calendario-numero">
                {vista === 'semana' && (
                  <span className="calendario-nombre-corto">
                    {dia.toLocaleDateString('es-AR', { weekday: 'short' })}
                  </span>
                )}
                <span>{dia.getDate()}</span>
              </div>

              <div className="calendario-eventos">
                {delDia.map((evento) => (
                  <Evento key={evento.id} evento={evento} conDetalle={vista === 'semana'} />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {eventos && visibles === 0 && (
        <p className="texto-suave">No hay nada de lo que elegiste en este período.</p>
      )}
    </div>
  );
}
