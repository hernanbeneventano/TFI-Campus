export default function TarjetaCurso({ curso }) {
  return (
    <article className="tarjeta">
      <div className="tarjeta-banda" style={{ background: curso.color }} />
      <div className="tarjeta-cuerpo">
        <span className="tarjeta-codigo">{curso.codigo}</span>
        <h3>{curso.nombre}</h3>
        <p className="texto-suave">{curso.periodo}</p>
      </div>
    </article>
  );
}
