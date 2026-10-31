import { Router } from 'express';
import { listarPendientes } from '../controllers/tareas.controller.js';

const router = Router();

router.get('/pendientes', listarPendientes);

export default router;
