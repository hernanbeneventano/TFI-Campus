import 'dotenv/config';
import express from 'express';
import cors from 'cors';

import cursosRoutes from './routes/cursos.routes.js';
import tareasRoutes from './routes/tareas.routes.js';
import mensajesRoutes from './routes/mensajes.routes.js';
import novedadesRoutes from './routes/novedades.routes.js';
import calendarioRoutes from './routes/calendario.routes.js';
import foroRoutes from './routes/foro.routes.js';
import bibliotecaRoutes from './routes/biblioteca.routes.js';
import { usuarioActual, personas, conPresencia, resumenDeNovedades } from './data/mock.js';
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

// Editar el propio perfil. El rol no se toca desde acá: lo define la
// facultad, no la persona.
app.put('/api/me', (req, res) => {
  const nombre = (req.body?.nombre ?? '').trim();
  const apellido = (req.body?.apellido ?? '').trim();
  const correo = (req.body?.correo ?? '').trim();

  if (!nombre || !apellido) {
    return res.status(400).json({ error: 'El nombre y el apellido no pueden estar vacíos' });
  }
  if (correo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo)) {
    return res.status(400).json({ error: 'Ese correo no parece válido' });
  }

  usuarioActual.nombre = nombre;
  usuarioActual.apellido = apellido;
  usuarioActual.correo = correo;

  // La lista de personas tiene el nombre completo: hay que mantenerla igual
  const persona = personas.find((p) => p.id === usuarioActual.id);
  if (persona) persona.nombre = `${nombre} ${apellido}`;

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
app.use('/api/biblioteca', bibliotecaRoutes);

app.use(rutaNoEncontrada);
app.use(manejarErrores);

app.listen(PORT, () => {
  console.log(`CampusTFI backend en http://localhost:${PORT}`);
});
