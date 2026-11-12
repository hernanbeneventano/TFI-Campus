// La pila de avisos de arriba a la derecha.
//
// Va montada una sola vez en `App.jsx` y escucha el evento de
// `services/avisos.js`, así cualquier pantalla puede avisar algo sin que
// haya que pasarle una función por props.
//
// Se van solos a los pocos segundos: son la confirmación de que algo salió
// bien, no información que haya que ir a buscar después. Los errores duran
// más, porque hay algo que leer y quizá que rehacer.

import { useCallback, useEffect, useRef, useState } from 'react';
import { alLlegarAviso } from '../services/avisos.js';
import { IconoCheckCirculo, IconoAdvertencia, IconoCerrar } from '../components/Iconos.jsx';

const DURACION = { exito: 4000, error: 7000 };

export default function Avisos() {
  const [avisos, setAvisos] = useState([]);
  // Los temporizadores se guardan para poder cancelarlos al desmontar o al
  // cerrar un aviso a mano; si no, quedan disparando sobre un componente que
  // ya no está.
  const relojes = useRef(new Map());

  const quitar = useCallback((id) => {
    clearTimeout(relojes.current.get(id));
    relojes.current.delete(id);
    setAvisos((lista) => lista.filter((a) => a.id !== id));
  }, []);

  useEffect(() => {
    const dejarDeEscuchar = alLlegarAviso(({ texto, tipo }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setAvisos((lista) => [...lista, { id, texto, tipo }]);
      relojes.current.set(id, setTimeout(() => quitar(id), DURACION[tipo] ?? DURACION.exito));
    });

    const pendientes = relojes.current;
    return () => {
      dejarDeEscuchar();
      for (const reloj of pendientes.values()) clearTimeout(reloj);
      pendientes.clear();
    };
  }, [quitar]);

  if (avisos.length === 0) return null;

  return (
    // `polite` y no `assertive`: es una confirmación, no una urgencia; que el
    // lector de pantalla termine lo que estaba diciendo.
    <div className="avisos" role="status" aria-live="polite">
      {avisos.map(({ id, texto, tipo }) => (
        <div key={id} className={`aviso ${tipo}`}>
          <span className="aviso-icono" aria-hidden="true">
            {tipo === 'error' ? (
              <IconoAdvertencia width={18} height={18} />
            ) : (
              <IconoCheckCirculo width={18} height={18} />
            )}
          </span>
          <p>{texto}</p>
          <button
            type="button"
            className="aviso-cerrar"
            onClick={() => quitar(id)}
            aria-label="Cerrar el aviso"
            title="Cerrar"
          >
            <IconoCerrar width={15} height={15} />
          </button>
        </div>
      ))}
    </div>
  );
}
