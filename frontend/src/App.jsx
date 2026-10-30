import { Routes, Route, Navigate } from 'react-router-dom';

import MenuLateral from './components/MenuLateral.jsx';
import Actividad from './pages/Actividad.jsx';
import Cursos from './pages/Cursos.jsx';
import Notas from './pages/Notas.jsx';

export default function App() {
  return (
    <div className="layout">
      <MenuLateral />
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Navigate to="/actividad" replace />} />
          <Route path="/actividad" element={<Actividad />} />
          <Route path="/cursos" element={<Cursos />} />
          <Route path="/notas" element={<Notas />} />
          <Route path="*" element={<p>Página no encontrada.</p>} />
        </Routes>
      </main>
    </div>
  );
}
