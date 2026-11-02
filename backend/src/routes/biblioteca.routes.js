import { Router } from 'express';
import express from 'express';
import {
  opcionesBiblioteca,
  listarMateriales,
  misAportes,
  pendientes,
  obtenerFavoritos,
  obtenerMaterial,
  crearMaterial,
  subirArchivo,
  descargarArchivo,
  editarMaterial,
  borrarMaterial,
  aprobarMaterial,
  rechazarMaterial,
  agregarFavorito,
  quitarFavorito,
} from '../controllers/biblioteca.controller.js';

const router = Router();

// El archivo llega en base64 dentro del JSON, así que esta ruta necesita un
// límite más alto que el del resto de la app (100 kB). Va solo acá: no hay
// motivo para que el foro pueda recibir 20 MB.
const MAX_MB = Number(process.env.BIBLIOTECA_MAX_MB) || 15;
const jsonGrande = express.json({ limit: `${Math.ceil(MAX_MB * 1.4)}mb` });

// Las rutas con nombre fijo van antes que /:id; si no, "favoritos" se
// tomaría como el id de un material (mismo cuidado que en mensajes).
router.get('/opciones', opcionesBiblioteca);
router.get('/mis-aportes', misAportes);
router.get('/pendientes', pendientes);
router.get('/favoritos', obtenerFavoritos);

router.get('/', listarMateriales);
router.post('/', crearMaterial);

router.get('/:id', obtenerMaterial);
router.patch('/:id', editarMaterial);
router.delete('/:id', borrarMaterial);

router.post('/:id/archivo', jsonGrande, subirArchivo);
router.get('/:id/archivo', descargarArchivo);

router.post('/:id/aprobar', aprobarMaterial);
router.post('/:id/rechazar', rechazarMaterial);

router.post('/:id/favorito', agregarFavorito);
router.delete('/:id/favorito', quitarFavorito);

export default router;
