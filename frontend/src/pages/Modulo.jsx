import { useEffect, useMemo, useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { obtenerModulo, obtenerUsuarioActual } from '../services/api.js';
import { leerCompletados, guardarCompletados, calcularAvance } from '../services/progreso.js';
import { hace } from '../services/fechas.js';
import CarpetaModulo from '../components/CarpetaModulo.jsx';
import PestanasModulo from '../components/PestanasModulo.jsx';
import PanelModulo from '../components/PanelModulo.jsx';
import VisorItem from '../components/VisorItem.jsx';
import {
  IconoVolver,
  IconoBuscar,
  IconoModulos,
  IconoAnuncio,
  IconoPersonas,
  IconoNotas,
  IconoUsuario,
  IconoEstudiante,
  IconoMensaje,
} from '../components/Iconos.jsx';

function formatearFecha(iso) {
  return new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long' });
}

function Anuncios({ anuncios }) {
  if (anuncios.length === 0) {
    return <p className="texto-suave">Todavía no hay anuncios en este módulo.</p>;
  }
  return (
    <ul className="anuncios">
      {anuncios.map((a) => (
        <li key={a.id} className="anuncio">
          <h3>{a.titulo}</h3>
          <small className="texto-suave">
            {a.autor} · {formatearFecha(a.fecha)}
          </small>
          <p>{a.cuerpo}</p>
        </li>
      ))}
    </ul>
  );
}

const textoEstado = {
  conectado: 'Conectado',
  ausente: 'Ausente',
  desconectado: 'Desconectado',
};

function Participantes({ participantes, yo }) {
  return (
    <ul className="participantes">
      {participantes.map((p) => (
        <li key={p.id} className="participante">
          <span
            className={`docente-avatar avatar-estado ${p.estado}`}
            title={textoEstado[p.estado]}
          >
            {p.rol === 'Estudiante' ? <IconoEstudiante /> : <IconoUsuario />}
          </span>
          <div>
            <strong>{p.nombre}</strong>
            <small>{p.rol}</small>
          </div>

          {/* A uno mismo no tiene sentido escribirse */}
          {p.id !== yo && (
            <Link
              to={`/mensajes?con=${p.id}`}
              className="participante-mensaje"
              title={`Escribirle a ${p.nombre}`}
              aria-label={`Escribirle a ${p.nombre}`}
            >
              <IconoMensaje />
            </Link>
          )}

          <div className="participante-acceso">
            <small>Último acceso</small>
            <small>{hace(p.ultimoAcceso)}</small>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function Modulo() {
  const { id } = useParams();
  // ?tarea=N llega desde el panel de tareas pendientes: abre esa entrega.
  // Queda en la URL, así el enlace sigue sirviendo si se recarga o se comparte.
  const tareaPedida = useSearchParams()[0].get('tarea');

  const [datos, setDatos] = useState(null);
  const [yo, setYo] = useState(null);
  const [error, setError] = useState(null);

  const [pestana, setPestana] = useState('contenido');
  const [busqueda, setBusqueda] = useState('');

  // Carpetas abiertas (por id) y elemento que se está viendo en pantalla completa
  const [abiertas, setAbiertas] = useState([]);
  const [viendo, setViendo] = useState(null);

  // Recursos marcados como completados (se guardan en el navegador)
  const [completados, setCompletados] = useState(leerCompletados);

  useEffect(() => {
    obtenerUsuarioActual().then((u) => setYo(u.id)).catch(() => setYo(null));
  }, []);

  useEffect(() => {
    setDatos(null);
    setViendo(null);
    setPestana('contenido');
    setBusqueda('');
    obtenerModulo(id)
      .then((d) => {
        setDatos(d);

        // La primera carpeta arranca abierta
        const abrir = d.carpetas.length ? [d.carpetas[0].id] : [];

        // Si se vino desde una tarea pendiente, se abre su entrega y se
        // despliega la carpeta donde está. Va acá y no en otro efecto para
        // que no pise lo que deja este al terminar de cargar.
        if (tareaPedida) {
          for (const carpeta of d.carpetas) {
            const item = carpeta.items.find(
              (i) => i.tipo === 'tarea' && String(i.tareaId) === tareaPedida
            );
            if (item) {
              setViendo({ carpeta, item });
              if (!abrir.includes(carpeta.id)) abrir.push(carpeta.id);
              break;
            }
          }
        }

        setAbiertas(abrir);
      })
      .catch((e) => setError(e.message));
  }, [id, tareaPedida]);

  // Al buscar se muestran solo las carpetas con coincidencias, y adentro solo
  // los elementos que coinciden (salvo que coincida el nombre de la carpeta).
  const carpetasVisibles = useMemo(() => {
    if (!datos) return [];
    const texto = busqueda.trim().toLowerCase();
    if (!texto) return datos.carpetas;

    return datos.carpetas
      .map((carpeta) => {
        const coincideCarpeta =
          carpeta.titulo.toLowerCase().includes(texto) ||
          (carpeta.descripcion ?? '').toLowerCase().includes(texto);
        if (coincideCarpeta) return carpeta;
        const items = carpeta.items.filter((i) => i.titulo.toLowerCase().includes(texto));
        return items.length ? { ...carpeta, items } : null;
      })
      .filter(Boolean);
  }, [datos, busqueda]);

  const avance = useMemo(
    () => calcularAvance(datos ? datos.carpetas.flatMap((c) => c.items) : [], completados),
    [datos, completados]
  );

  function alternarCompletado(idItem) {
    setCompletados((lista) => {
      const siguiente = lista.includes(idItem)
        ? lista.filter((x) => x !== idItem)
        : [...lista, idItem];
      guardarCompletados(siguiente);
      return siguiente;
    });
  }

  function alternarCarpeta(idCarpeta) {
    setAbiertas((lista) =>
      lista.includes(idCarpeta) ? lista.filter((x) => x !== idCarpeta) : [...lista, idCarpeta]
    );
  }

  if (error) {
    return (
      <div className="pagina">
        <p className="error">No se pudo cargar el módulo. ¿Está corriendo el backend?</p>
        <Link to="/modulos" className="volver">
          <IconoVolver />
          Volver a Módulos
        </Link>
      </div>
    );
  }

  if (!datos) {
    return (
      <div className="pagina">
        <p className="texto-suave">Cargando…</p>
      </div>
    );
  }

  const { curso, anuncios, participantes, cursada, proximas } = datos;
  const buscando = busqueda.trim().length > 0;

  const pestanas = [
    { clave: 'contenido', nombre: 'Contenido', Icono: IconoModulos },
    { clave: 'anuncios', nombre: 'Anuncios', Icono: IconoAnuncio, cantidad: anuncios.length },
    { clave: 'participantes', nombre: 'Participantes', Icono: IconoPersonas },
    { clave: 'notas', nombre: 'Notas', Icono: IconoNotas },
  ];

  return (
    <div className="pagina">
      {viendo && (
        <VisorItem
          curso={curso}
          carpeta={viendo.carpeta}
          item={viendo.item}
          onCerrar={() => setViendo(null)}
        />
      )}

      <Link to="/modulos" className="volver">
        <IconoVolver />
        Módulos
      </Link>

      <header className="modulo-encabezado">
        <small>{curso.codigo}</small>
        <h1>{curso.nombre}</h1>
        <p>
          {curso.docente} · {curso.periodo}
        </p>
      </header>

      <PestanasModulo pestanas={pestanas} actual={pestana} onCambiar={setPestana} />

      <div className="pagina-cuerpo">
        <section className="pagina-principal" key={pestana}>
          {pestana === 'contenido' && (
            <>
              <div className="modulo-barra">
                <h2>Contenido</h2>
                <label className="barra-busqueda">
                  <IconoBuscar />
                  <input
                    type="search"
                    placeholder="Buscar en el módulo"
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                  />
                </label>
              </div>

              {carpetasVisibles.length === 0 ? (
                <p className="texto-suave">No hay nada que coincida con la búsqueda.</p>
              ) : (
                <div className="carpetas">
                  {carpetasVisibles.map((carpeta) => (
                    <CarpetaModulo
                      key={carpeta.id}
                      carpeta={carpeta}
                      // Mientras se busca, las carpetas con resultados van abiertas
                      abierta={buscando || abiertas.includes(carpeta.id)}
                      onAlternar={() => alternarCarpeta(carpeta.id)}
                      onAbrirItem={(c, item) => setViendo({ carpeta: c, item })}
                      completados={completados}
                      onCompletar={alternarCompletado}
                    />
                  ))}
                </div>
              )}
            </>
          )}

          {pestana === 'anuncios' && (
            <>
              <div className="modulo-barra">
                <h2>Anuncios</h2>
              </div>
              <Anuncios anuncios={anuncios} />
            </>
          )}

          {pestana === 'participantes' && (
            <>
              <div className="modulo-barra">
                <h2>Participantes</h2>
              </div>
              <Participantes participantes={participantes} yo={yo} />
            </>
          )}

          {pestana === 'notas' && (
            <>
              <div className="modulo-barra">
                <h2>Notas</h2>
              </div>
              <p className="texto-suave">
                Las calificaciones se van a ver acá cuando estén las entregas y la corrección.
              </p>
            </>
          )}
        </section>

        <PanelModulo
          curso={curso}
          participantes={participantes}
          cursada={cursada}
          proximas={proximas}
          avance={avance}
        />
      </div>
    </div>
  );
}
