import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { entrar, recuperarContrasena, hayConfiguracion } from '../services/sesion.js';
import {
  Logo,
  IconoCorreo,
  IconoCandado,
  IconoOjo,
  IconoOjoTachado,
  IconoAdvertencia,
  IconoCheckCirculo,
  IconoFlecha,
} from '../components/Iconos.jsx';

// Lo que gana quien tiene cuenta, en la mitad derecha. No es relleno: quien
// llega sin cuenta necesita saber a quién pedirla.
const VENTAJAS = [
  'Todo el material de tus materias, organizado por semana',
  'Las entregas y los exámenes en un solo calendario',
  'Consultas a tus docentes sin salir del campus',
  'Una biblioteca con el material de la cátedra y catálogos públicos',
];

export default function Login() {
  const [correo, setCorreo] = useState('');
  const [contrasena, setContrasena] = useState('');
  const [recordarme, setRecordarme] = useState(true);
  const [verContrasena, setVerContrasena] = useState(false);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [entrando, setEntrando] = useState(false);

  const navegar = useNavigate();
  const ubicacion = useLocation();
  const campoCorreo = useRef(null);

  // El foco arranca en el correo: es lo primero que se completa
  useEffect(() => {
    campoCorreo.current?.focus();
  }, []);

  // A dónde iba la persona antes de que la mandáramos a iniciar sesión
  const destino = ubicacion.state?.desde ?? '/novedades';

  async function enviar(e) {
    e.preventDefault();
    setError(null);
    setAviso(null);

    if (!correo.trim() || !contrasena) {
      setError('Completá el correo y la contraseña.');
      return;
    }

    setEntrando(true);
    try {
      await entrar(correo, contrasena, recordarme);
      navegar(destino, { replace: true });
    } catch (fallo) {
      setError(fallo.message);
      setEntrando(false);
    }
  }

  async function olvide() {
    setError(null);
    setAviso(null);

    if (!correo.trim()) {
      setError('Escribí tu correo y volvé a tocar "¿Olvidaste tu contraseña?".');
      campoCorreo.current?.focus();
      return;
    }

    try {
      await recuperarContrasena(correo);
      setAviso(`Te mandamos un correo a ${correo.trim()} para que la cambies.`);
    } catch (fallo) {
      setError(fallo.message);
    }
  }

  return (
    <div className="acceso">
      <header className="acceso-barra">
        <span className="acceso-marca">
          <Logo width={26} height={26} />
          CampusTFI
        </span>
        <span className="acceso-facultad">Campus virtual</span>
      </header>

      <div className="acceso-cuerpo">
        {/* ---------- Mitad izquierda: la tarjeta ---------- */}
        <section className="acceso-lado oscuro">
          <form className="acceso-tarjeta" onSubmit={enviar} noValidate>
            <span className="acceso-logo" aria-hidden="true">
              <Logo width={30} height={30} />
            </span>

            <h1>Iniciar sesión</h1>
            <p className="acceso-bajada">
              Entrá con tu correo institucional para ver tus materias, entregas y mensajes.
            </p>

            {!hayConfiguracion && (
              <p className="acceso-error" role="alert">
                <IconoAdvertencia width={16} height={16} />
                Falta la configuración de Firebase. Copiá las claves en{' '}
                <code>frontend/.env.local</code>.
              </p>
            )}

            <label className="acceso-campo">
              <span className="acceso-etiqueta">Correo</span>
              <span className="acceso-caja">
                <IconoCorreo />
                <input
                  ref={campoCorreo}
                  type="email"
                  value={correo}
                  onChange={(e) => setCorreo(e.target.value)}
                  placeholder="nombre.apellido@campustfi.edu.ar"
                  autoComplete="username"
                  disabled={entrando}
                />
              </span>
            </label>

            <label className="acceso-campo">
              <span className="acceso-etiqueta">Contraseña</span>
              <span className="acceso-caja">
                <IconoCandado />
                <input
                  type={verContrasena ? 'text' : 'password'}
                  value={contrasena}
                  onChange={(e) => setContrasena(e.target.value)}
                  placeholder="Tu contraseña"
                  autoComplete="current-password"
                  disabled={entrando}
                />
                <button
                  type="button"
                  className="acceso-ver"
                  onClick={() => setVerContrasena((v) => !v)}
                  aria-label={verContrasena ? 'Ocultar la contraseña' : 'Ver la contraseña'}
                  title={verContrasena ? 'Ocultar la contraseña' : 'Ver la contraseña'}
                  tabIndex={-1}
                >
                  {verContrasena ? <IconoOjoTachado /> : <IconoOjo />}
                </button>
              </span>
            </label>

            <div className="acceso-fila">
              <label className="acceso-recordarme">
                <input
                  type="checkbox"
                  checked={recordarme}
                  onChange={(e) => setRecordarme(e.target.checked)}
                  disabled={entrando}
                />
                <span>Mantener la sesión abierta</span>
              </label>

              <button type="button" className="acceso-enlace" onClick={olvide}>
                ¿Olvidaste tu contraseña?
              </button>
            </div>

            {error && (
              <p className="acceso-error" role="alert">
                <IconoAdvertencia width={16} height={16} />
                {error}
              </p>
            )}

            {aviso && (
              <p className="acceso-aviso" role="status">
                <IconoCheckCirculo width={16} height={16} />
                {aviso}
              </p>
            )}

            <button type="submit" className="acceso-boton" disabled={entrando}>
              {entrando ? 'Entrando…' : 'Entrar'}
            </button>

            <p className="acceso-pie">
              ¿No podés entrar? Escribile a la secretaría de la facultad.
            </p>
          </form>
        </section>

        {/* ---------- Mitad derecha: para quien no tiene cuenta ---------- */}
        <section className="acceso-lado foto">
          <div className="acceso-invitacion">
            <p className="acceso-sobretitulo">¿Primera vez acá?</p>
            <h2>Pedí tu cuenta</h2>
            <p className="acceso-bajada">
              Las cuentas las crea la facultad con tu correo institucional. Si todavía no
              tenés la tuya, pedila en la secretaría de tu carrera.
            </p>

            <ul className="acceso-ventajas">
              {VENTAJAS.map((v) => (
                <li key={v}>
                  <IconoCheckCirculo width={17} height={17} />
                  <span>{v}</span>
                </li>
              ))}
            </ul>

            <a
              className="acceso-boton secundario"
              href="https://campustfi.edu.ar/"
              target="_blank"
              rel="noreferrer noopener"
            >
              Ir al sitio del campus
              <IconoFlecha width={16} height={16} />
            </a>
          </div>
        </section>
      </div>
    </div>
  );
}
