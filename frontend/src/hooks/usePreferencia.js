import { useEffect, useState } from 'react';
import { alCambiarPreferencias } from '../services/preferencias.js';

// Lee una preferencia y se mantiene al día: si se cambia desde Ajustes, el
// componente que la usa se entera sin tener que recargar la página.
export default function usePreferencia(leer) {
  const [valor, setValor] = useState(leer);

  useEffect(() => alCambiarPreferencias(() => setValor(leer())), [leer]);

  return [valor, setValor];
}
