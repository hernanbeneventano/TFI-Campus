import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Desde dónde se piden los archivos del sitio. En desarrollo y en cualquier
// despliegue que ocupe la raíz del dominio es `/`. En GitHub Pages el sitio
// no vive en la raíz sino en /TFI-Campus/, así que los archivos hay que
// pedirlos desde ahí o el navegador los busca donde no están y la página
// queda en blanco sin decir por qué.
//
// Se toma del entorno y no se escribe fija para que `npm run build` siga
// sirviendo para probar en local. El flujo de trabajo de Pages la define.
// `import.meta.env.BASE_URL` devuelve este mismo valor dentro de la
// aplicación, y de ahí lo lee el router: así hay un solo lugar que lo decide.
const base = process.env.VITE_BASE || '/';

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    port: 5173,
    // Las peticiones a /api se redirigen al backend
    proxy: {
      '/api': 'http://localhost:3000',
    },
  },
});
