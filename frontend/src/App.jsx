import { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

import MenuLateral from './components/MenuLateral.jsx';
import Modulos from './pages/Modulos.jsx';
import Modulo from './pages/Modulo.jsx';
import Actividad from './pages/Actividad.jsx';
import Mensajes from './pages/Mensajes.jsx';
import Informacion from './pages/Informacion.jsx';
import EnConstruccion from './pages/EnConstruccion.jsx';
import { obtenerUsuarioActual, obtenerContadores } from './services/api.js';

export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [novedades, setNovedades] = useState(null);
  const { pathname } = useLocation();

  useEffect(() => {
    obtenerUsuarioActual().then(setUsuario).catch(() => setUsuario(null));
  }, []);

  // Se vuelven a contar al cambiar de apartado: así, por ejemplo, al salir de
  // Mensajes el contador ya refleja lo que se acaba de leer.
  useEffect(() => {
    obtenerContadores().then(setNovedades).catch(() => setNovedades(null));
  }, [pathname]);

  return (
    <div className="layout">
      <MenuLateral usuario={usuario} novedades={novedades} />
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Navigate to="/modulos" replace />} />
          <Route path="/informacion" element={<Informacion />} />
          <Route path="/actividad" element={<Actividad />} />
          <Route path="/modulos" element={<Modulos />} />
          <Route path="/modulos/:id" element={<Modulo />} />
          <Route path="/mensajes" element={<Mensajes />} />
          <Route path="*" element={<EnConstruccion titulo="Página no encontrada" />} />
        </Routes>
      </main>
    </div>
  );
}
