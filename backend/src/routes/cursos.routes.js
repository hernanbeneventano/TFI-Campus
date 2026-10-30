import { Router } from 'express';
import { listarCursos, obtenerCurso } from '../controllers/cursos.controller.js';

const router = Router();

router.get('/', listarCursos);
router.get('/:id', obtenerCurso);

export default router;
