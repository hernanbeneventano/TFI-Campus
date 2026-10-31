// Íconos en SVG. Usan "currentColor", así toman el color del texto.

const base = {
  width: 22,
  height: 22,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
};

export const IconoInformacion = (p) => (
  <svg {...base} {...p}>
    <path d="M3 21h18M4 10h16M12 3l8 5H4l8-5z" />
    <path d="M6 10v8M10 10v8M14 10v8M18 10v8" />
  </svg>
);

export const IconoActividad = (p) => (
  <svg {...base} {...p}>
    <path d="M11 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5" />
    <path d="M17.5 2.5a2.1 2.1 0 0 1 3 3L12 14l-4 1 1-4 8.5-8.5z" />
  </svg>
);

export const IconoModulos = (p) => (
  <svg {...base} {...p}>
    <path d="M2 5c3-1.5 7-1.5 10 0v15c-3-1.5-7-1.5-10 0V5z" />
    <path d="M22 5c-3-1.5-7-1.5-10 0v15c3-1.5 7-1.5 10 0V5z" />
  </svg>
);

export const IconoMensajes = (p) => (
  <svg {...base} {...p}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="M3 7l9 6 9-6" />
  </svg>
);

export const IconoUsuario = (p) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" />
  </svg>
);

export const IconoBuscar = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-4-4" />
  </svg>
);

export const IconoGrilla = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <rect x="3" y="3" width="7" height="7" rx="1.5" />
    <rect x="14" y="3" width="7" height="7" rx="1.5" />
    <rect x="3" y="14" width="7" height="7" rx="1.5" />
    <rect x="14" y="14" width="7" height="7" rx="1.5" />
  </svg>
);

export const IconoLista = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <path d="M8 6h13M8 12h13M8 18h13" />
    <circle cx="3.5" cy="6" r="1" />
    <circle cx="3.5" cy="12" r="1" />
    <circle cx="3.5" cy="18" r="1" />
  </svg>
);

export const IconoEstrella = ({ llena, ...p }) => (
  <svg {...base} width={18} height={18} fill={llena ? 'currentColor' : 'none'} {...p}>
    <path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9L12 3z" />
  </svg>
);

// Logo: birrete sobre un libro abierto
export const Logo = (p) => (
  <svg width={64} height={64} viewBox="0 0 64 64" fill="none" aria-hidden="true" {...p}>
    <path d="M32 8L6 19l26 11 26-11L32 8z" fill="currentColor" />
    <path d="M16 24v9c0 4 7 7 16 7s16-3 16-7v-9l-16 7-16-7z" fill="currentColor" />
    <path d="M52 20v10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    <circle cx="52" cy="32" r="2.5" fill="currentColor" />
    <path
      d="M8 46c8-3 17-3 24 2 7-5 16-5 24-2v8c-8-3-17-3-24 2-7-5-16-5-24-2v-8z"
      fill="currentColor"
    />
  </svg>
);

export const IconoVolver = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <path d="M19 12H5M11 18l-6-6 6-6" />
  </svg>
);

export const IconoCerrar = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <path d="M18 6L6 18M6 6l12 12" />
  </svg>
);

export const IconoFlecha = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <path d="M9 18l6-6-6-6" />
  </svg>
);

export const IconoCarpeta = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
  </svg>
);

export const IconoPagina = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z" />
    <path d="M14 3v5h5M9 13h6M9 17h4" />
  </svg>
);

export const IconoArchivo = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z" />
    <path d="M14 3v5h5" />
  </svg>
);

export const IconoVideo = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="M11 9.5l4 2.5-4 2.5v-5z" />
  </svg>
);

export const IconoTarea = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <path d="M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1z" />
    <path d="M16 5h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2" />
    <path d="M9 13l2 2 4-4" />
  </svg>
);

export const IconoTablero = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M9 4v16M15 4v16" />
  </svg>
);

export const IconoDescargar = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <path d="M12 3v12M7 11l5 5 5-5" />
    <path d="M4 20h16" />
  </svg>
);

export const IconoReloj = (p) => (
  <svg {...base} width={16} height={16} {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </svg>
);

export const IconoAnuncio = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <path d="M3 11v2a1 1 0 0 0 1 1h3l6 4V6l-6 4H4a1 1 0 0 0-1 1z" />
    <path d="M17.5 9a4 4 0 0 1 0 6" />
  </svg>
);

export const IconoPersonas = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <circle cx="9" cy="8" r="3.5" />
    <path d="M2.5 20c1.2-3.3 3.7-5 6.5-5s5.3 1.7 6.5 5" />
    <path d="M16 5.2a3.5 3.5 0 0 1 0 6.6M17.5 15.4c1.7.7 3 2.2 3.8 4.6" />
  </svg>
);

export const IconoNotas = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <path d="M4 19V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" />
    <path d="M8 8h8M8 12h8M8 16h4" />
  </svg>
);

export const IconoAvance = (p) => (
  <svg {...base} width={20} height={20} {...p}>
    <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
  </svg>
);

export const IconoAdvertencia = (p) => (
  <svg {...base} width={15} height={15} {...p}>
    <path d="M10.3 3.8L2.4 17.5a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.8a2 2 0 0 0-3.4 0z" />
    <path d="M12 9.5v4M12 17.2h.01" />
  </svg>
);

// Avatar del alumno: silueta con birrete. Va relleno, no de línea como el resto.
export const IconoEstudiante = (p) => (
  <svg width={22} height={22} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...p}>
    {/* Birrete */}
    <path d="M12 2.2 1.75 6.45a.32.32 0 0 0 0 .6L12 11.3l10.25-4.25a.32.32 0 0 0 0-.6z" />
    {/* Borla colgando a la izquierda */}
    <path d="M3.95 7.2h.5v2.9l.62 3a.22.22 0 0 1-.22.27H3.55a.22.22 0 0 1-.22-.27l.62-3z" />
    {/* Cabeza */}
    <path d="M8.1 8.5v2.2c0 2.6 1.75 4.8 3.9 4.8s3.9-2.2 3.9-4.8V8.5L12 12z" />
    <circle cx="7.6" cy="10.9" r=".95" />
    <circle cx="16.4" cy="10.9" r=".95" />
    {/* Hombros */}
    <path d="m9.15 16.1 2.35 1.85a.8.8 0 0 0 1 0l2.35-1.85 3.25.72a3.1 3.1 0 0 1 2.4 2.65l.42 3.05a1.05 1.05 0 0 1-.94 1.19c-2.48.22-5.16.34-7.98.34s-5.5-.12-7.98-.34a1.05 1.05 0 0 1-.94-1.19l.42-3.05a3.1 3.1 0 0 1 2.4-2.65z" />
  </svg>
);

export const IconoCheckChico = (p) => (
  <svg {...base} width={15} height={15} strokeWidth={2.4} {...p}>
    <path d="M20 6L9 17l-5-5" />
  </svg>
);

// Plegar y desplegar el menú
export const IconoPanel = (p) => (
  <svg {...base} width={19} height={19} {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2.5" />
    <path d="M10 4v16" />
  </svg>
);

export const IconoCampana = (p) => (
  <svg {...base} width={17} height={17} {...p}>
    <path d="M18 8.5a6 6 0 0 0-12 0c0 6-2.2 7.5-2.2 7.5h16.4S18 14.5 18 8.5z" />
    <path d="M13.7 19.5a2 2 0 0 1-3.4 0" />
  </svg>
);

export const IconoAjustes = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <circle cx="12" cy="12" r="3.1" />
    <path d="M19.1 14.5a1.5 1.5 0 0 0 .3 1.66l.05.05a1.9 1.9 0 1 1-2.69 2.69l-.05-.06a1.5 1.5 0 0 0-1.66-.3 1.5 1.5 0 0 0-.9 1.37v.15a1.9 1.9 0 1 1-3.8 0v-.08a1.5 1.5 0 0 0-.98-1.37 1.5 1.5 0 0 0-1.66.3l-.05.06a1.9 1.9 0 1 1-2.69-2.69l.05-.05a1.5 1.5 0 0 0 .3-1.66 1.5 1.5 0 0 0-1.37-.9H3.7a1.9 1.9 0 1 1 0-3.8h.08a1.5 1.5 0 0 0 1.37-.98 1.5 1.5 0 0 0-.3-1.66l-.05-.05A1.9 1.9 0 1 1 7.5 4.5l.05.05a1.5 1.5 0 0 0 1.66.3h.07a1.5 1.5 0 0 0 .9-1.37V3.4a1.9 1.9 0 1 1 3.8 0v.08a1.5 1.5 0 0 0 .9 1.37 1.5 1.5 0 0 0 1.66-.3l.05-.05a1.9 1.9 0 1 1 2.69 2.69l-.05.05a1.5 1.5 0 0 0-.3 1.66v.07a1.5 1.5 0 0 0 1.37.9h.15a1.9 1.9 0 1 1 0 3.8h-.08a1.5 1.5 0 0 0-1.37.9z" />
  </svg>
);

// Puerta de salida
export const IconoSalir = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <path d="M9.5 21H5.5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <path d="M16 16.5l4.5-4.5L16 7.5M20.5 12h-11" />
  </svg>
);

// Globo de conversación, para escribirle a alguien
export const IconoMensaje = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <path d="M20.5 11.5a7.6 7.6 0 0 1-8.5 7.5 9 9 0 0 1-2.4-.4L4.5 20.5l1.4-4.6A7.3 7.3 0 0 1 4.5 11.5 7.6 7.6 0 0 1 12.5 4a7.6 7.6 0 0 1 8 7.5z" />
  </svg>
);

export const IconoEnviar = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <path d="M21 3L10.5 13.5M21 3l-6.8 18-3.7-7.5L3 9.8 21 3z" />
  </svg>
);

// Clip para adjuntar archivos
export const IconoAdjuntar = (p) => (
  <svg {...base} width={18} height={18} {...p}>
    <path d="M21 11.5l-8.8 8.8a5 5 0 0 1-7-7l9-9a3.3 3.3 0 0 1 4.7 4.7l-9 9a1.7 1.7 0 0 1-2.4-2.4l8.3-8.3" />
  </svg>
);
