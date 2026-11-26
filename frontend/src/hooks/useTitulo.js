import { useEffect } from 'react';

const MARCA = 'CampusTFI';

/**
 * El título de la pestaña del navegador: «Calendario · CampusTFI».
 *
 * Con varias pestañas del campus abiertas, todas decían «CampusTFI» y no
 * había forma de saber cuál era cuál sin entrar. Cada página lo llama con su
 * nombre; la de un módulo, con el nombre de la materia apenas lo tiene.
 *
 * Sin texto (todavía cargando) queda solo la marca.
 */
export default function useTitulo(texto) {
  useEffect(() => {
    document.title = texto ? `${texto} · ${MARCA}` : MARCA;
  }, [texto]);
}
