import { Router } from 'express';
import { listarAvisos } from '../controllers/informacion.controller.js';

const router = Router();

router.get('/', listarAvisos);

export default router;
