import { Router } from 'express';
import {
  listarConversaciones,
  obtenerConversacion,
  enviarMensaje,
  abrirConversacion,
  listarContactos,
} from '../controllers/mensajes.controller.js';

const router = Router();

router.get('/', listarConversaciones);
router.post('/', abrirConversacion);
// Antes de '/:id', si no 'contactos' se tomaría como un id
router.get('/contactos', listarContactos);
router.get('/:id', obtenerConversacion);
router.post('/:id', enviarMensaje);

export default router;
