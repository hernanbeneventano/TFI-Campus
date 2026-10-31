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
