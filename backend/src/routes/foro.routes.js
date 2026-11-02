import { Router } from 'express';
import {
  listarTemas,
  obtenerTema,
  crearTema,
  responder,
  votar,
  seguir,
} from '../controllers/foro.controller.js';

const router = Router();

router.get('/', listarTemas);
router.post('/', crearTema);
router.get('/:id', obtenerTema);
router.post('/:id', responder);
router.post('/:id/seguir', seguir);
router.post('/:id/mensajes/:mensajeId/voto', votar);

export default router;
