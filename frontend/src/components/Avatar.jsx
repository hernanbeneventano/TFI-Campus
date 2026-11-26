/**
 * La cara de alguien del campus.
 *
 * Existe para que la foto se vea **en todos lados a la vez**. El avatar
 * aparece en el menú, en el perfil, en los participantes de un módulo, en los
 * mensajes y en el foro, y hasta ahora cada pantalla elegía su ícono por su
 * cuenta. Con la foto de perfil eso serían seis lugares que hay que acordarse
 * de cambiar, y el que se olvide muestra la silueta de alguien que sí subió
 * su foto.
 *
 * Si no hay foto cae en la silueta de siempre: con birrete para el estudiante,
 * de línea para el resto, como está en el resto del diseño.
 */
import { useEffect, useState } from 'react';

import { IconoEstudiante, IconoUsuario } from './Iconos.jsx';
import { urlDeRecurso } from '../services/destino.js';

/** Si esa persona es estudiante, mire como mire la pantalla sus roles. */
function esEstudiante(persona) {
  if (!persona) return false;
  if (Array.isArray(persona.roles)) return persona.roles.includes('Estudiante');
  return persona.rol === 'Estudiante';
}

export default function Avatar({ persona, tamano = 20, className = '' }) {
  // Una foto que no carga —se retiró, o el almacenamiento no responde— no
  // tiene que dejar un recuadro roto: se vuelve a la silueta.
  const [fallo, setFallo] = useState(false);

  // Y si después cambia la foto, se vuelve a intentar. Sin esto, una cara que
  // falló una vez se quedaba en silueta para siempre: justo lo que pasa al
  // subir una foto nueva después de que la anterior diera error.
  useEffect(() => setFallo(false), [persona?.foto]);

  const foto = !fallo ? urlDeRecurso(persona?.foto) : null;
  const Silueta = esEstudiante(persona) ? IconoEstudiante : IconoUsuario;

  if (foto) {
    return (
      <img
        className={`avatar-foto ${className}`.trim()}
        src={foto}
        alt=""
        width={tamano}
        height={tamano}
        loading="lazy"
        onError={() => setFallo(true)}
      />
    );
  }

  return <Silueta width={tamano} height={tamano} className={className || undefined} />;
}
