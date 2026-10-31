// Recuadro superior con el nombre del apartado actual
export default function Encabezado({ titulo, descripcion }) {
  return (
    <header className="encabezado">
      <h1>{titulo}</h1>
      {descripcion && <p>{descripcion}</p>}
    </header>
  );
}
