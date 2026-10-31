// Pestañas de un módulo: Contenido, Anuncios, Participantes y Notas.
export default function PestanasModulo({ pestanas, actual, onCambiar }) {
  return (
    <div className="pestanas" role="tablist" aria-label="Secciones del módulo">
      {pestanas.map(({ clave, nombre, Icono, cantidad }) => (
        <button
          key={clave}
          type="button"
          role="tab"
          aria-selected={actual === clave}
          className={actual === clave ? 'pestana activa' : 'pestana'}
          onClick={() => onCambiar(clave)}
        >
          <Icono />
          <span>{nombre}</span>
          {cantidad > 0 && <small className="pestana-cantidad">{cantidad}</small>}
        </button>
      ))}
    </div>
  );
}
