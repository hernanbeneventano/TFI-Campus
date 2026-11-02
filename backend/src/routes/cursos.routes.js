import { Router } from 'express';
import {
  listarCursos,
  obtenerCurso,
  obtenerModulo,
  alternarFavorito,
} from '../controllers/cursos.controller.js';

const router = Router();

router.get('/', listarCursos);
router.get('/:id', obtenerCurso);
router.get('/:id/modulo', obtenerModulo);
router.post('/:id/favorito', alternarFavorito);

export default router;
