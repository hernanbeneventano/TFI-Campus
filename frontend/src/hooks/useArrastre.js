// Reordenar una lista arrastrando, con la caja siguiendo al dedo y las
// demás corriéndose de lugar.
//
// **Por qué no el arrastre del navegador.** El de HTML5 (`draggable`) dibuja
// una copia fantasma, no deja animar nada y obliga a tomar el elemento de un
// asa chica. Con eventos de puntero se agarra la caja entera, se la ve
// moverse y las otras se acomodan con una transición: el usuario entiende
// dónde va a caer antes de soltar.
//
// Cómo funciona: al apretar se miden todas las cajas una vez. Después, cada
// movimiento del puntero solo cambia `transform`, que el navegador resuelve
// sin rehacer el diseño de la página. Al soltar se avisa de dónde a dónde
// fue, y quien lo use se encarga de guardarlo.

import { useCallback, useEffect, useRef, useState } from 'react';

// Menos que esto es un clic, no un arrastre: sin este margen, abrir una
// carpeta con el mouse apenas tembloroso la movería de lugar.
const MINIMO = 6;

export default function useArrastre({ alSoltar, activo = true }) {
  // { desde, hasta, delta } mientras se arrastra, o null
  const [arrastre, setArrastre] = useState(null);
  // Lo que no puede vivir en el estado porque cambia en cada pixel
  const datos = useRef(null);

  const terminar = useCallback(() => {
    const d = datos.current;
    datos.current = null;
    setArrastre(null);
    if (!d || !d.arrancado) return;

    // Al soltar, el navegador manda un `click` sobre lo que estaba debajo.
    // Como se arrastra tomando la cabecera —que abre la carpeta—, ese clic
    // la abriría o cerraría cada vez que se mueve algo. Se come uno solo, y
    // en fase de captura para llegar antes que nadie.
    const comerClic = (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
    };
    window.addEventListener('click', comerClic, { capture: true, once: true });
    // Si no llegó a haber clic (se soltó fuera), no queda el escucha colgado
    setTimeout(() => window.removeEventListener('click', comerClic, true), 0);

    if (d.hasta !== d.desde) alSoltar(d.desde, d.hasta);
  }, [alSoltar]);

  // Depende de si hay arrastre, no del objeto: si dependiera del objeto, los
  // escuchas se desengancharían y volverían a engancharse en cada pixel.
  const hayArrastre = Boolean(arrastre);

  useEffect(() => {
    if (!hayArrastre) return;

    function alMover(e) {
      const d = datos.current;
      if (!d) return;

      const delta = e.clientY - d.y0;
      if (!d.arrancado) {
        if (Math.abs(delta) < MINIMO) return;
        d.arrancado = true;
      }
      // Dónde está ahora el centro de la caja que se arrastra
      const centro = d.cajas[d.desde].centro + delta;

      // El destino es la posición de la caja cuyo centro quedó más cerca
      let hasta = d.desde;
      for (let i = 0; i < d.cajas.length; i++) {
        if (i === d.desde) continue;
        const caja = d.cajas[i];
        if (i < d.desde && centro < caja.centro) {
          hasta = Math.min(hasta, i);
        } else if (i > d.desde && centro > caja.centro) {
          hasta = Math.max(hasta, i);
        }
      }

      d.hasta = hasta;
      // `moviendo` recién se enciende acá: hasta que no se supera el mínimo,
      // apretar no cambia ni un pixel. Si no, un clic para abrir una carpeta
      // le aplicaría transformaciones sin que se note, y cualquier cosa que
      // mire si el elemento está quieto lo ve temblar.
      setArrastre({ desde: d.desde, hasta, delta, moviendo: true });
    }

    function alSoltarPuntero() {
      terminar();
    }

    function alTeclado(e) {
      // Escape cancela: la lista vuelve como estaba
      if (e.key === 'Escape' && datos.current) {
        datos.current.hasta = datos.current.desde;
        terminar();
      }
    }

    window.addEventListener('pointermove', alMover);
    window.addEventListener('pointerup', alSoltarPuntero);
    window.addEventListener('pointercancel', alSoltarPuntero);
    window.addEventListener('keydown', alTeclado);
    return () => {
      window.removeEventListener('pointermove', alMover);
      window.removeEventListener('pointerup', alSoltarPuntero);
      window.removeEventListener('pointercancel', alSoltarPuntero);
      window.removeEventListener('keydown', alTeclado);
    };
  }, [hayArrastre, terminar]);

  /**
   * Se engancha al `onPointerDown` de cada caja.
   * @param indice su posición en la lista
   * @param elemento el nodo de la caja, para poder medir a sus hermanas
   */
  const tomar = useCallback(
    (indice, elemento, e) => {
      // Solo el botón principal del mouse.
      if (!activo || e.button !== 0) return;

      // Se agarra la caja entera, también por su cabecera —que es un botón—,
      // porque eso es lo natural: se toma lo que se ve. Lo único excluido
      // son los controles que hacen otra cosa con el clic: las acciones del
      // editor, el chip que abre las entregas, los campos.
      if (e.target.closest('.acciones-editor, a, input, select, textarea, [role="button"]')) {
        return;
      }

      const hermanas = [...elemento.parentElement.children].filter((n) =>
        n.classList.contains(elemento.classList[0])
      );
      const cajas = hermanas.map((n) => {
        const r = n.getBoundingClientRect();
        return { alto: r.height, centro: r.top + r.height / 2 };
      });

      datos.current = {
        desde: indice,
        hasta: indice,
        y0: e.clientY,
        cajas,
        arrancado: false,
      };
      // Todavía no se mueve nada: solo queda anotado qué se tomó
      setArrastre({ desde: indice, hasta: indice, delta: 0, moviendo: false });
    },
    [activo]
  );

  /**
   * El estilo de la caja número `indice` mientras hay un arrastre en curso.
   * La que se arrastra sigue al puntero; las de en medio se corren una
   * posición para abrir el hueco.
   */
  function estiloDe(indice) {
    if (!arrastre?.moviendo) return undefined;
    const { desde, hasta, delta } = arrastre;
    const d = datos.current;
    if (!d) return undefined;

    if (indice === desde) {
      return {
        transform: `translateY(${delta}px)`,
        // Sin transición: tiene que ir pegada al puntero
        transition: 'none',
        zIndex: 5,
        position: 'relative',
      };
    }

    // Las de en medio se corren el alto de la que se está moviendo
    const altoMovida = d.cajas[desde]?.alto ?? 0;
    const separacion = 10; // el gap de la lista, para que no se superpongan
    if (indice > desde && indice <= hasta) {
      return { transform: `translateY(${-(altoMovida + separacion)}px)` };
    }
    if (indice < desde && indice >= hasta) {
      return { transform: `translateY(${altoMovida + separacion}px)` };
    }
    return { transform: 'translateY(0)' };
  }

  return {
    arrastre,
    tomar,
    estiloDe,
    /** true si esa caja es la que se está arrastrando */
    esLaMovida: (indice) => Boolean(arrastre?.moviendo && arrastre.desde === indice),
    /** true mientras haya un arrastre en curso */
    arrastrando: Boolean(arrastre?.moviendo),
  };
}
