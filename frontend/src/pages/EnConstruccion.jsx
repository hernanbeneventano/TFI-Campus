import Encabezado from '../components/Encabezado.jsx';

import useTitulo from '../hooks/useTitulo';
// Página provisoria para las secciones que todavía no están hechas
export default function EnConstruccion({ titulo }) {
  useTitulo(titulo);
  return (
    <div className="pagina">
      <Encabezado titulo={titulo} descripcion="Esta sección está en construcción." />
    </div>
  );
}
