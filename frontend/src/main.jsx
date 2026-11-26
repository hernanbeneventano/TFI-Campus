import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import App from './App.jsx';
import './styles/global.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* La base la decide `base` en vite.config.js y Vite la expone acá, así
        que el router y los archivos del sitio no pueden discrepar. En
        desarrollo vale `/`; en GitHub Pages, `/TFI-Campus/`. */}
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
