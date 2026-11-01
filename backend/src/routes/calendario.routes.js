import { Router } from 'express';
import { listarCalendario } from '../controllers/calendario.controller.js';

const router = Router();

router.get('/', listarCalendario);

export default router;
