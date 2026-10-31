import { useEffect, useState } from 'react';
import { obtenerActividad } from '../services/api.js';
import Encabezado from '../components/Encabezado.jsx';

const titulos = {
  importante: 'Importante',
  proximo: 'Próximo',
  hoy: 'Hoy',
  reciente: 'Reciente',
};

function formatearFecha(iso) {
  return new Date(iso).toLocaleString('es-AR', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Actividad() {
  const [grupos, setGrupos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerActividad().then(setGrupos).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="pagina">
      <Encabezado titulo="Actividad" descripcion="Novedades y vencimientos de todos tus módulos" />

      {error && <p className="error">No se pudo cargar la actividad. ¿Está corriendo el backend?</p>}
      {!error && !grupos && <p className="texto-suave">Cargando…</p>}

      {grupos &&
        Object.entries(titulos).map(([clave, titulo]) => (
          <div key={clave} className="grupo">
            <h2 className={clave === 'importante' ? 'grupo-titulo urgente' : 'grupo-titulo'}>{titulo}</h2>
            {grupos[clave].length === 0 ? (
              <p className="texto-suave">Nada por ahora.</p>
            ) : (
              <ul className="lista">
                {grupos[clave].map((item) => (
                  <li key={item.id} className="lista-item">
                    <div>
                      <strong>{item.titulo}</strong>
                      <p className="texto-suave">{item.curso}</p>
                    </div>
                    <span className="texto-suave">{formatearFecha(item.fecha)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
    </div>
  );
}
