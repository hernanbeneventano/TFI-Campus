import { useEffect, useState } from 'react';
import { obtenerCursos } from '../services/api.js';
import TarjetaCurso from '../components/TarjetaCurso.jsx';

export default function Cursos() {
  const [cursos, setCursos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerCursos().then(setCursos).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">No se pudieron cargar los cursos. ¿Está corriendo el backend?</p>;
  if (!cursos) return <p className="texto-suave">Cargando…</p>;

  return (
    <section>
      <h1>Cursos</h1>
      <div className="grilla">
        {cursos.map((curso) => (
          <TarjetaCurso key={curso.id} curso={curso} />
        ))}
      </div>
    </section>
  );
}
