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
import { obtenerUsuarioActual, obtenerContadores } from './services/api.js';
import { alCambiarSesion, hayConfiguracion } from './services/sesion.js';

// Firebase tarda unos milisegundos en decir si hay una sesión guardada. Sin
// este tercer estado la pantalla parpadea: se vería el login un instante y
// después el campus, o al revés.
const AVERIGUANDO = Symbol('averiguando la sesión');

export default function App() {
  const [sesion, setSesion] = useState(AVERIGUANDO);
  const [usuario, setUsuario] = useState(null);
  const [contadores, setContadores] = useState(null);
  const { pathname, state } = useLocation();

  // Quién está conectado, según Firebase. Avisa una vez al arrancar y después
  // en cada cambio: al entrar, al salir y al cambiar de cuenta.
  useEffect(() => alCambiarSesion(setSesion), []);

  // Sin las claves de Firebase (`frontend/.env.local`) no hay sesión posible,
  // así que no se puede exigir iniciarla: el campus se usa como antes, con el
  // usuario de prueba del servidor. Es lo que permite trabajar en el frontend
  // sin tener las claves, y la pantalla de login ya lo avisa.
  const exigeSesion = hayConfiguracion;
  const dentro = exigeSesion ? Boolean(sesion) && sesion !== AVERIGUANDO : true;

  // El perfil se pide recién cuando hay sesión: sin token el servidor
  // responde 401 y no habría nada que mostrar.
  useEffect(() => {
    if (!dentro) {
      setUsuario(null);
      return;
    }

    function traerUsuario() {
      obtenerUsuarioActual()
        .then(setUsuario)
        .catch(() => setUsuario(null));
    }

    traerUsuario();
    window.addEventListener('campustfi:perfil', traerUsuario);
    return () => window.removeEventListener('campustfi:perfil', traerUsuario);
  }, [dentro, sesion]);

  // Se vuelven a contar al cambiar de apartado: así, por ejemplo, al salir de
  // Mensajes el contador ya refleja lo que se acaba de leer.
  useEffect(() => {
    if (!dentro) return;
    obtenerContadores()
      .then(setContadores)
      .catch(() => setContadores(null));
  }, [pathname, dentro]);

  // Mientras Firebase no contesta no se muestra ninguna de las dos cosas
  if (exigeSesion && sesion === AVERIGUANDO) {
    return (
      <div className="abriendo" role="status">
        <span className="abriendo-punto" />
        <span className="abriendo-punto" />
        <span className="abriendo-punto" />
        <span className="oculto">Abriendo el campus…</span>
      </div>
    );
  }

  // El inicio de sesión ocupa la pantalla entera: no lleva menú lateral.
  if (pathname === '/login') {
    // Teniendo la sesión abierta, el login no tiene nada que hacer. Va al
    // mismo lugar que `Login` después de entrar —a dónde iba la persona— y no
    // a Novedades: apenas se inicia la sesión, los dos pueden querer navegar
    // y cuál gana no está definido. Mandando a los dos al mismo lado, da igual.
    if (dentro) return <Navigate to={state?.desde ?? '/novedades'} replace />;

    return (
      <>
        <Routes>
          <Route path="/login" element={<Login />} />
        </Routes>
        <Avisos />
      </>
    );
  }

  // Sin sesión no se ve nada del campus. Se recuerda a dónde iba la persona
  // para devolverla ahí después de entrar: `Login` lee ese `desde`, así que
  // un enlace a una mesa de examen sigue llevando a la mesa.
  if (!dentro) {
    return <Navigate to="/login" replace state={{ desde: pathname }} />;
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
          <Route path="/modulos/inscripciones" element={<InscripcionMaterias />} />
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
          <Route path="/auditoria" element={<Auditoria />} />
          <Route
            path="/administracion"
            element={<Navigate to="/administracion/panel" replace />}
          />
          <Route path="/administracion/:vista" element={<Administracion />} />
          <Route path="*" element={<EnConstruccion titulo="Página no encontrada" />} />
        </Routes>
      </main>
      {/* Fuera de <main>: se superpone a todo y no pertenece a la pantalla */}
      <Avisos />
    </div>
  );
}
