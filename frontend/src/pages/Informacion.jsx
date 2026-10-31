import { useEffect, useState } from 'react';
import { obtenerAvisos } from '../services/api.js';
import { hace } from '../services/fechas.js';
import Encabezado from '../components/Encabezado.jsx';

const DIAS_NUEVO = 7;

function esNuevo(iso) {
  return Date.now() - new Date(iso) < DIAS_NUEVO * 24 * 60 * 60 * 1000;
}

export default function Informacion() {
  const [avisos, setAvisos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerAvisos().then(setAvisos).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="pagina">
      <Encabezado
        titulo="Información"
        descripcion="Avisos de la facultad: inscripciones, biblioteca, becas y campus"
      />

      {error && <p className="error">No se pudo cargar la información. ¿Está corriendo el backend?</p>}
      {!error && !avisos && <p className="texto-suave">Cargando…</p>}

      <ul className="anuncios">
        {avisos?.map((a) => (
          <li key={a.id} className="anuncio">
            <div className="aviso-cabecera">
              <span className="aviso-categoria">{a.categoria}</span>
              {esNuevo(a.fecha) && <span className="aviso-nuevo">Nuevo</span>}
              <small className="texto-suave">{hace(a.fecha)}</small>
            </div>
            <h3>{a.titulo}</h3>
            <p>{a.cuerpo}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
