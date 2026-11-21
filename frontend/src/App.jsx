import { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

import MenuLateral from './components/MenuLateral.jsx';
import Avisos from './components/Avisos.jsx';
import Modulos from './pages/Modulos.jsx';
import Modulo from './pages/Modulo.jsx';
import Mensajes from './pages/Mensajes.jsx';
import Novedades from './pages/Novedades.jsx';
import Calendario from './pages/Calendario.jsx';
import Foro from './pages/Foro.jsx';
import Biblioteca from './pages/Biblioteca.jsx';
import Finales from './pages/Finales.jsx';
import Asistencias from './pages/Asistencias.jsx';
import InscripcionMaterias from './pages/InscripcionMaterias.jsx';
import Ajustes from './pages/Ajustes.jsx';
import Auditoria from './pages/Auditoria.jsx';
import Administracion from './pages/Administracion.jsx';
import Login from './pages/Login.jsx';
import EnConstruccion from './pages/EnConstruccion.jsx';
import Permitido from './components/Permitido.jsx';
import { obtenerUsuarioActual, obtenerContadores } from './services/api.js';
import { alCambiarSesion } from './services/sesion.js';
import { cerrarSiElServidorReinicio } from './services/instancia.js';

export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [contadores, setContadores] = useState(null);
  // Quién está conectado en Firebase. `undefined` mientras no se sabe: al
  // arrancar, la sesión guardada tarda un instante en restaurarse, y mandar
  // al login en ese instante echaría a alguien que sí tiene sesión.
  const [sesion, setSesion] = useState(undefined);
  const { pathname } = useLocation();

  useEffect(() => {
    function traerUsuario() {
      obtenerUsuarioActual().then(setUsuario).catch(() => setUsuario(null));
    }

    // Hay que esperar a Firebase: al arrancar, la sesión guardada tarda un
    // instante en restaurarse y hasta entonces no hay token. Si se pregunta
    // antes, el servidor contesta como el usuario de prueba y el menú queda
    // con la identidad equivocada —un estudiante veía el menú del
    // administrador hasta recargar—.
    //
    // `alCambiarSesion` avisa una vez al arrancar y después en cada entrada y
    // salida, así que sirve para las dos cosas.
    // Si el servidor se reinició desde la última visita, la sesión que haya
    // quedado en el navegador ya no vale: se cierra y se arranca del login.
    // Las cuentas recordadas no se tocan.
    cerrarSiElServidorReinicio();

    const dejarDeEscuchar = alCambiarSesion((cuenta) => {
      setSesion(cuenta);
      if (cuenta) traerUsuario();
      else setUsuario(null);
    });
    window.addEventListener('campustfi:perfil', traerUsuario);
    return () => {
      dejarDeEscuchar();
      window.removeEventListener('campustfi:perfil', traerUsuario);
    };
  }, []);

  // Se vuelven a contar al cambiar de apartado: así, por ejemplo, al salir de
  // Mensajes el contador ya refleja lo que se acaba de leer.
  useEffect(() => {
    obtenerContadores().then(setContadores).catch(() => setContadores(null));
  }, [pathname, usuario]);

  // Mientras Firebase restaura la sesión no se muestra nada: ni el campus
  // —no se sabe de quién— ni el login —puede que ya haya sesión—.
  if (sesion === undefined && pathname !== '/login') {
    return <div className="layout cargando" aria-busy="true" />;
  }

  // Sin sesión no se entra. El servidor comprueba lo mismo y responde 401:
  // esto es para que la pantalla lleve al login en vez de quedar vacía.
  //
  // Se recuerda a dónde quería ir, así después de entrar cae ahí y no
  // siempre en Novedades.
  if (!sesion && pathname !== '/login') {
    return <Navigate to="/login" replace state={{ desde: pathname }} />;
  }

  // El inicio de sesión ocupa la pantalla entera: no lleva menú lateral.
  if (pathname === '/login') {
    return (
      <>
        <Routes>
          <Route path="/login" element={<Login />} />
        </Routes>
        <Avisos />
      </>
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
          {/* Va antes que /modulos/:id para que "inscripciones" no se tome
              como el identificador de un módulo */}
          <Route
            path="/modulos/inscripciones"
            element={
              <Permitido usuario={usuario} roles={['Estudiante']}>
                <InscripcionMaterias />
              </Permitido>
            }
          />
          <Route path="/modulos/:id" element={<Modulo />} />
          {/* Finales: las tres pantallas del estudiante o las tres del docente,
              según el rol. Sin vista, la propia pantalla manda a la primera
              del rol que corresponda, que no es la misma para los dos. */}
          <Route path="/finales" element={<Finales usuario={usuario} />} />
          <Route path="/finales/:vista" element={<Finales usuario={usuario} />} />
          {/* Las dos pantallas de Asistencias. Sin vista, va al panel */}
          <Route path="/asistencias" element={<Navigate to="/asistencias/panel" replace />} />
          <Route path="/asistencias/:vista" element={<Asistencias />} />
          <Route path="/calendario" element={<Calendario />} />
          <Route path="/foro" element={<Foro />} />
          <Route path="/mensajes" element={<Mensajes />} />
          <Route path="/biblioteca" element={<Biblioteca />} />
          <Route path="/ajustes" element={<Ajustes />} />
          <Route
            path="/auditoria"
            element={
              <Permitido usuario={usuario} roles={['Administrador', 'Supervisor', 'Docente']}>
                <Auditoria />
              </Permitido>
            }
          />
          <Route
            path="/administracion"
            element={<Navigate to="/administracion/panel" replace />}
          />
          <Route
            path="/administracion/:vista"
            element={
              <Permitido usuario={usuario} roles={['Administrador', 'Supervisor']}>
                <Administracion />
              </Permitido>
            }
          />
          <Route path="*" element={<EnConstruccion titulo="Página no encontrada" />} />
        </Routes>
      </main>
      {/* Fuera de <main>: se superpone a todo y no pertenece a la pantalla */}
      <Avisos />
    </div>
  );
}
