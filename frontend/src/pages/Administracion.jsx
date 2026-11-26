// Administración: lo que maneja la institución, en un solo lugar.
//
// Antes estaba repartido —la estructura y las cuentas escondidas como
// pestañas de Ajustes, el registro de actividad suelto en el menú— y eso
// mezclaba dos cosas distintas: Ajustes es *tu* cuenta, Administración es *el
// campus*. Ahora cada una está donde se la busca.
//
// Qué pestañas se ven lo dice el servidor (`puedeAdministrar`, `puedeAsignar`),
// no esta pantalla. El reparto no es casual: el administrador **construye** la
// estructura —carreras, sedes, planes, comisiones— y el supervisor
// **distribuye** gente dentro de ella.
//
// La vista va en la URL (`/administracion/estructura`) y no en el estado: son
// pantallas a las que se manda un enlace ("fijate en Cuentas"), al revés que
// las pestañas de un módulo.

import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { obtenerMiPerfil, obtenerInstitucion } from '../services/api.js';
import Encabezado from '../components/Encabezado.jsx';
import Panel from '../components/ajustes/Panel.jsx';
import Estructura from '../components/ajustes/Estructura.jsx';
import Estudiantes from '../components/ajustes/Estudiantes.jsx';
import Cuentas from '../components/ajustes/Cuentas.jsx';
import Academico from '../components/ajustes/Academico.jsx';
import Auditoria from './Auditoria.jsx';
import {
  IconoPanel,
  IconoModulos,
  IconoPersonas,
  IconoAjustes,
  IconoActividad,
  IconoAdvertencia,
  IconoCalendario,
} from '../components/Iconos.jsx';

import useTitulo from '../hooks/useTitulo';
export default function Administracion() {
  useTitulo('Administración');
  const { vista } = useParams();
  const navegar = useNavigate();

  const [perfil, setPerfil] = useState(null);
  const [institucion, setInstitucion] = useState(null);
  const [error, setError] = useState(null);

  const traer = useCallback(() => {
    obtenerMiPerfil().then(setPerfil).catch((e) => setError(e.message));
    obtenerInstitucion().then(setInstitucion).catch(() => setInstitucion(null));
  }, []);

  useEffect(traer, [traer]);

  if (error) return <p className="aviso-error">{error}</p>;
  if (!perfil || !institucion) {
    return (
      <div className="pagina">
        <Encabezado titulo="Administración" descripcion="La estructura y la gente del campus" />
        <p className="texto-suave">Cargando…</p>
      </div>
    );
  }

  const SECCIONES = [
    {
      // Primero el panel: la pregunta de quien entra es "¿qué hay que hacer
      // hoy?", no "¿qué carreras hay?".
      id: 'panel',
      nombre: 'Panel',
      Icono: IconoPanel,
      visible: institucion.puedeAsignar,
      descripcion: 'Cómo viene la institución y qué hay que atender.',
    },
    {
      id: 'estructura',
      nombre: 'Estructura',
      Icono: IconoModulos,
      visible: institucion.puedeAdministrar,
      descripcion: 'Carreras, sedes, planes de estudio y comisiones.',
    },
    {
      // Después de la estructura y antes de la gente: primero se define
      // cuándo se cursa, después quién.
      id: 'academico',
      nombre: 'Académico',
      Icono: IconoCalendario,
      visible: institucion.puedeAsignar,
      descripcion: 'El período de inscripción, la asistencia y el calendario de la facultad.',
    },
    {
      id: 'estudiantes',
      nombre: 'Estudiantes',
      Icono: IconoPersonas,
      visible: institucion.puedeAsignar,
      descripcion: 'En qué carrera, sede y comisión está cada estudiante.',
    },
    {
      id: 'cuentas',
      nombre: 'Cuentas',
      Icono: IconoAjustes,
      visible: institucion.puedeAsignar,
      descripcion: 'Las personas del campus, sus roles y el estado de su cuenta.',
    },
    {
      id: 'actividad',
      nombre: 'Actividad',
      Icono: IconoActividad,
      visible: institucion.puedeAsignar,
      descripcion: 'Qué hizo cada uno, cuándo y qué cambió. El registro no se edita ni se borra.',
    },
  ].filter((s) => s.visible);

  // Sin ninguna sección visible no hay nada que administrar. Igual el
  // servidor contestaría que no: esto es para explicarlo, no para impedirlo.
  if (SECCIONES.length === 0) {
    return (
      <div className="pagina">
        <Encabezado titulo="Administración" />
        <div className="biblioteca-vacio">
          <IconoAdvertencia width={34} height={34} />
          <h3>No podés administrar el campus</h3>
          <p className="texto-suave">
            Este apartado es para la administración y la supervisión de la institución.
          </p>
        </div>
      </div>
    );
  }

  const actual = SECCIONES.find((s) => s.id === vista) ?? SECCIONES[0];

  return (
    <div className="pagina">
      <Encabezado titulo="Administración" descripcion={actual.descripcion} />

      <nav className="pestanas" aria-label="Secciones de Administración">
        {SECCIONES.map(({ id, nombre, Icono }) => (
          <button
            key={id}
            type="button"
            className={actual.id === id ? 'pestana activa' : 'pestana'}
            aria-current={actual.id === id}
            onClick={() => navegar(`/administracion/${id}`)}
          >
            <Icono width={16} height={16} />
            {nombre}
          </button>
        ))}
      </nav>

      <div className="cuerpo-ajustes">
        {actual.id === 'panel' && <Panel />}
        {actual.id === 'estructura' && (
          <Estructura datos={institucion} onCambio={setInstitucion} />
        )}
        {actual.id === 'academico' && <Academico />}
        {actual.id === 'estudiantes' && <Estudiantes catalogo={institucion} />}
        {actual.id === 'cuentas' && <Cuentas yo={perfil.perfil} />}
        {/* El registro de actividad trae su propia cabecera y sus filtros: acá
            entra entero, sin recortarlo. */}
        {actual.id === 'actividad' && <Auditoria dentroDeAdministracion />}
      </div>
    </div>
  );
}
