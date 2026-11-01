import { Router } from 'express';
import {
  listarPublicaciones,
  crearPublicacion,
  editarPublicacion,
  reaccionar,
} from '../controllers/novedades.controller.js';

const router = Router();

router.get('/', listarPublicaciones);
router.post('/', crearPublicacion);
router.put('/:id', editarPublicacion);
router.post('/:id/reaccion', reaccionar);

export default router;
