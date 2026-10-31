import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import MenuLateral from './components/MenuLateral.jsx';
import Modulos from './pages/Modulos.jsx';
import Actividad from './pages/Actividad.jsx';
import EnConstruccion from './pages/EnConstruccion.jsx';
import { obtenerUsuarioActual } from './services/api.js';

export default function App() {
  const [usuario, setUsuario] = useState(null);

  useEffect(() => {
    obtenerUsuarioActual().then(setUsuario).catch(() => setUsuario(null));
  }, []);

  return (
    <div className="layout">
      <MenuLateral usuario={usuario} />
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Navigate to="/modulos" replace />} />
          <Route path="/informacion" element={<EnConstruccion titulo="Información" />} />
          <Route path="/actividad" element={<Actividad />} />
          <Route path="/modulos" element={<Modulos />} />
          <Route path="/mensajes" element={<EnConstruccion titulo="Mensajes" />} />
          <Route path="*" element={<EnConstruccion titulo="Página no encontrada" />} />
        </Routes>
      </main>
    </div>
  );
}
