import { useEffect, useState } from 'react';

// Presencia del usuario que está navegando, mirando lo que hace en la página:
// conectado mientras se mueve, ausente si deja de usarla un rato, y
// desconectado si se va a otra pestaña o minimiza.
//
// Los demás participantes no se pueden saber desde acá: su estado lo calcula
// el backend a partir del último acceso. Cuando haya sesiones de verdad, esto
// debería avisarle al servidor en vez de quedarse solo en la pantalla.

const EVENTOS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'];

export default function usePresencia(minutosParaAusente = 5) {
  const [estado, setEstado] = useState('conectado');

  useEffect(() => {
    const limite = minutosParaAusente * 60000;
    let ultimaSenal = Date.now();

    function revisar() {
      if (document.hidden) {
        setEstado('desconectado');
        return;
      }
      setEstado(Date.now() - ultimaSenal > limite ? 'ausente' : 'conectado');
    }

    // Se anota la actividad sin tocar el estado en cada movimiento del mouse;
    // solo si estaba ausente conviene volver enseguida.
    function anotar() {
      ultimaSenal = Date.now();
      setEstado((actual) => (actual === 'conectado' ? actual : 'conectado'));
    }

    revisar();
    const reloj = setInterval(revisar, 15000);
    EVENTOS.forEach((e) => window.addEventListener(e, anotar, { passive: true }));
    document.addEventListener('visibilitychange', revisar);

    return () => {
      clearInterval(reloj);
      EVENTOS.forEach((e) => window.removeEventListener(e, anotar));
      document.removeEventListener('visibilitychange', revisar);
    };
  }, [minutosParaAusente]);

  return estado;
}
