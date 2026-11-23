import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { entrar, recuperarContrasena, hayConfiguracion } from '../services/sesion.js';
import { cuentasRecordadas, olvidarCuenta, recordarCuenta } from '../services/cuentasRecordadas.js';
import { obtenerUsuarioActual } from '../services/api.js';
import {
  Logo,
  IconoCorreo,
  IconoCandado,
  IconoOjo,
  IconoOjoTachado,
  IconoAdvertencia,
  IconoCheckCirculo,
  IconoFlecha,
  IconoCerrar,
} from '../components/Iconos.jsx';
import Avatar from '../components/Avatar.jsx';

import useTitulo from '../hooks/useTitulo';
// Lo que gana quien tiene cuenta, en la mitad derecha. No es relleno: quien
// llega sin cuenta necesita saber a quién pedirla.
const VENTAJAS = [
  'Todo el material de tus materias, organizado por semana',
  'Las entregas y los exámenes en un solo calendario',
  'Consultas a tus docentes sin salir del campus',
  'Una biblioteca con el material de la cátedra y catálogos públicos',
];

export default function Login() {
  useTitulo('Iniciar sesión');
  const [correo, setCorreo] = useState('');
  // Las cuentas con las que ya se entró en este equipo. Se leen una sola vez:
  // no cambian mientras la pantalla está abierta, salvo que se borre una.
  const [recordadas, setRecordadas] = useState(() => cuentasRecordadas());
  const [abiertas, setAbiertas] = useState(false);
  const [contrasena, setContrasena] = useState('');
  const [recordarme, setRecordarme] = useState(true);
  const [verContrasena, setVerContrasena] = useState(false);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [entrando, setEntrando] = useState(false);

  const navegar = useNavigate();
  const ubicacion = useLocation();
  const campoCorreo = useRef(null);
  // Al elegir una cuenta de la lista el foco salta a la contraseña: el correo
  // ya está puesto y es lo único que queda por escribir.
  const campoContrasena = useRef(null);

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

      try {
        const yo = await obtenerUsuarioActual();
        recordarCuenta({
          correo: yo.correo ?? correo.trim(),
          nombre: [yo.nombre, yo.apellido].filter(Boolean).join(' ') || null,
          foto: yo.foto ?? null,
          rol: yo.rol ?? null,
        });
      } catch {
        // Sin los datos, se recuerda al menos el correo
        recordarCuenta({ correo: correo.trim() });
      }

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

            {/* Las cuentas de este equipo. Se guarda el correo y la cara,
                nunca la contraseña: sirve para reconocer de quién es la
                cuenta, no para entrar sin escribirla. */}
            {recordadas.length > 0 && (
              <div className={abiertas ? 'acceso-cuentas abiertas' : 'acceso-cuentas'}>
                {/* Plegado por omisión: lo normal es entrar con la cuenta que
                    ya está escrita, y una lista siempre abierta empuja los
                    campos fuera de la vista. */}
                <button
                  type="button"
                  className="acceso-cuentas-abrir"
                  onClick={() => setAbiertas((v) => !v)}
                  aria-expanded={abiertas}
                >
                  <IconoFlecha width={13} height={13} />
                  Sesiones anteriores
                  <small>{recordadas.length}</small>
                </button>

                {/* Se abre animando la altura, el mismo truco que las
                    carpetas de un módulo: así no hay que medirla. */}
                <div className="acceso-cuentas-panel">
                  <ul inert={abiertas ? undefined : ''}>
                  {recordadas.map((c) => (
                    <li key={c.correo} className={c.correo === correo ? 'elegida' : undefined}>
                      <button
                        type="button"
                        className="acceso-cuenta"
                        onClick={() => {
                          setCorreo(c.correo);
                          campoContrasena.current?.focus();
                        }}
                        disabled={entrando}
                      >
                        <Avatar persona={c} tamano={32} />
                        <span>
                          <strong>{c.nombre ?? c.correo}</strong>
                          <small>{c.correo}</small>
                        </span>
                      </button>
                      <button
                        type="button"
                        className="acceso-cuenta-olvidar"
                        title={`Olvidar ${c.correo} en este equipo`}
                        aria-label={`Olvidar ${c.correo}`}
                        disabled={entrando}
                        onClick={() => {
                          olvidarCuenta(c.correo);
                          setRecordadas(cuentasRecordadas());
                        }}
                      >
                        <IconoCerrar width={13} height={13} />
                      </button>
                    </li>
                  ))}
                  </ul>
                </div>
              </div>
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
                  ref={campoContrasena}
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
