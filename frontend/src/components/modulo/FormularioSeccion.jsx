// Alta y edición de una sección del módulo (lo que el alumno ve como "Semana 2").
//
// El mismo formulario sirve para las dos cosas: con `seccion` edita, sin ella
// crea. Son dos campos, no vale la pena tener dos pantallas casi iguales.

import { useEffect, useRef, useState } from 'react';

export default function FormularioSeccion({ seccion, onGuardar, onCancelar, trabajando }) {
  const [titulo, setTitulo] = useState(seccion?.titulo ?? '');
  const [descripcion, setDescripcion] = useState(seccion?.descripcion ?? '');
  const primero = useRef(null);

  // Al abrirlo, el foco va al título: es lo primero que se escribe
  useEffect(() => {
    primero.current?.focus();
  }, []);

  function enviar(e) {
    e.preventDefault();
    if (!titulo.trim()) return;
    onGuardar({ titulo: titulo.trim(), descripcion: descripcion.trim() || null });
  }

  return (
    <form className="editor-seccion" onSubmit={enviar}>
      <label>
        <span>Nombre de la sección</span>
        <input
          ref={primero}
          type="text"
          value={titulo}
          maxLength={120}
          placeholder="Semana 3: Árboles binarios"
          onChange={(e) => setTitulo(e.target.value)}
        />
      </label>

      <label>
        <span>
          Descripción <small>opcional</small>
        </span>
        <input
          type="text"
          value={descripcion}
          maxLength={300}
          placeholder="Qué se ve en esta sección"
          onChange={(e) => setDescripcion(e.target.value)}
        />
      </label>

      <div className="editor-botones">
        <button type="button" className="boton-suave" onClick={onCancelar} disabled={trabajando}>
          Cancelar
        </button>
        <button
          type="submit"
          className="boton-principal"
          disabled={trabajando || !titulo.trim()}
        >
          {seccion ? 'Guardar cambios' : 'Crear sección'}
        </button>
      </div>
    </form>
  );
}
