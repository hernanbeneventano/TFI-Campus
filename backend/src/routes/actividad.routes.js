import { Router } from 'express';
import { listarActividad } from '../controllers/actividad.controller.js';

const router = Router();

router.get('/', listarActividad);

export default router;
