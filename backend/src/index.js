import 'dotenv/config';
import express from 'express';
import cors from 'cors';

import cursosRoutes from './routes/cursos.routes.js';
import tareasRoutes from './routes/tareas.routes.js';
import mensajesRoutes from './routes/mensajes.routes.js';
import novedadesRoutes from './routes/novedades.routes.js';
import calendarioRoutes from './routes/calendario.routes.js';
import foroRoutes from './routes/foro.routes.js';
import { usuarioActual, conPresencia, resumenDeNovedades } from './data/mock.js';
import { manejarErrores, rutaNoEncontrada } from './middleware/errores.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors({ origin: process.env.FRONTEND_URL || 'http://localhost:5173' }));
app.use(express.json());

// Ruta para comprobar que el servidor funciona
app.get('/api/salud', (req, res) => {
  res.json({ estado: 'ok', app: 'CampusTFI' });
});

// Usuario que inició sesión (por ahora fijo, hasta tener el login)
app.get('/api/me', (req, res) => {
  res.json(conPresencia(usuarioActual));
});

// Cuántas cosas nuevas hay en cada apartado del menú
app.get('/api/contadores', (req, res) => {
  res.json(resumenDeNovedades(usuarioActual.id));
});

app.use('/api/cursos', cursosRoutes);
app.use('/api/tareas', tareasRoutes);
app.use('/api/mensajes', mensajesRoutes);
app.use('/api/novedades', novedadesRoutes);
app.use('/api/calendario', calendarioRoutes);
app.use('/api/foro', foroRoutes);

app.use(rutaNoEncontrada);
app.use(manejarErrores);

app.listen(PORT, () => {
  console.log(`CampusTFI backend en http://localhost:${PORT}`);
});
