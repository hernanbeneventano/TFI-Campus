import { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

import MenuLateral from './components/MenuLateral.jsx';
import Modulos from './pages/Modulos.jsx';
import Modulo from './pages/Modulo.jsx';
import Mensajes from './pages/Mensajes.jsx';
import Novedades from './pages/Novedades.jsx';
import Calendario from './pages/Calendario.jsx';
import Foro from './pages/Foro.jsx';
import Biblioteca from './pages/Biblioteca.jsx';
import Ajustes from './pages/Ajustes.jsx';
import Login from './pages/Login.jsx';
import EnConstruccion from './pages/EnConstruccion.jsx';
import { obtenerUsuarioActual, obtenerContadores } from './services/api.js';

export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [contadores, setContadores] = useState(null);
  const { pathname } = useLocation();

  useEffect(() => {
    function traerUsuario() {
      obtenerUsuarioActual().then(setUsuario).catch(() => setUsuario(null));
    }
    traerUsuario();
    window.addEventListener('campustfi:perfil', traerUsuario);
    return () => window.removeEventListener('campustfi:perfil', traerUsuario);
  }, []);

  // Se vuelven a contar al cambiar de apartado: así, por ejemplo, al salir de
  // Mensajes el contador ya refleja lo que se acaba de leer.
  useEffect(() => {
    obtenerContadores().then(setContadores).catch(() => setContadores(null));
  }, [pathname]);

  // El inicio de sesión ocupa la pantalla entera: no lleva menú lateral.
  if (pathname === '/login') {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
      </Routes>
    );
  }

  return (
    <div className="layout">
      <MenuLateral usuario={usuario} contadores={contadores} />
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Navigate to="/novedades" replace />} />
          <Route path="/novedades" element={<Novedades />} />
          <Route path="/modulos" element={<Modulos />} />
          <Route path="/modulos/:id" element={<Modulo />} />
          <Route path="/calendario" element={<Calendario />} />
          <Route path="/foro" element={<Foro />} />
          <Route path="/mensajes" element={<Mensajes />} />
          <Route path="/biblioteca" element={<Biblioteca />} />
          <Route path="/ajustes" element={<Ajustes />} />
          <Route path="*" element={<EnConstruccion titulo="Página no encontrada" />} />
        </Routes>
      </main>
    </div>
  );
}
