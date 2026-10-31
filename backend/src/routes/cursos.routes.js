import { Router } from 'express';
import { listarCursos, obtenerCurso, obtenerModulo } from '../controllers/cursos.controller.js';

const router = Router();

router.get('/', listarCursos);
router.get('/:id', obtenerCurso);
router.get('/:id/modulo', obtenerModulo);

export default router;
