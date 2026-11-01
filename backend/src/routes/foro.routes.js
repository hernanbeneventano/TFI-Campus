import { Router } from 'express';
import { listarTemas, obtenerTema, crearTema, responder } from '../controllers/foro.controller.js';

const router = Router();

router.get('/', listarTemas);
router.post('/', crearTema);
router.get('/:id', obtenerTema);
router.post('/:id', responder);

export default router;
