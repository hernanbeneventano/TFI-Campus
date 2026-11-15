// Ajustes: tu cuenta y nada más.
//
// Lo que maneja la institución —la estructura, los estudiantes, las cuentas de
// los demás y el registro de actividad— vive en **Administración**, que es un
// apartado aparte. Son dos cosas distintas y estaban mezcladas: Ajustes es
// *tu* cuenta, Administración es *el campus*.

import { useCallback, useEffect, useState } from 'react';
import { obtenerMiPerfil } from '../services/api.js';
import Encabezado from '../components/Encabezado.jsx';
import MiPerfil from '../components/ajustes/MiPerfil.jsx';

export default function Ajustes() {
  const [perfil, setPerfil] = useState(null);
  const [error, setError] = useState(null);

  const traer = useCallback(() => {
    obtenerMiPerfil().then(setPerfil).catch((e) => setError(e.message));
  }, []);

  useEffect(traer, [traer]);

  if (error) return <p className="aviso-error">{error}</p>;

  return (
    <div className="pagina">
      <Encabezado titulo="Ajustes" descripcion="Tus datos y los de tu cuenta." />

      <div className="cuerpo-ajustes">
        {perfil ? (
          <MiPerfil datos={perfil} onGuardado={setPerfil} />
        ) : (
          <p className="texto-suave">Cargando…</p>
        )}
      </div>
    </div>
  );
}
