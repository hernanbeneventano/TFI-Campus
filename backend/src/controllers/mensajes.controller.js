import {
  conversaciones,
  usuarioActual,
  buscarPersona,
  conPresencia,
  nuevoIdMensaje,
  nuevoIdConversacion,
  contactosDe,
} from '../data/mock.js';

// Mientras no haya login, el que escribe es siempre el usuario de prueba.
const YO = usuarioActual.id;

function esMia(conversacion) {
  return conversacion.entre.includes(YO);
}

// La otra persona de la conversación, con su estado de presencia
function elOtro(conversacion) {
  const otroId = conversacion.entre.find((id) => id !== YO);
  const persona = buscarPersona(otroId);
  return persona ? conPresencia(persona) : null;
}

function sinLeer(conversacion) {
  return conversacion.mensajes.filter((m) => m.deId !== YO && !m.leido).length;
}

function resumir(conversacion) {
  return {
    id: conversacion.id,
    con: elOtro(conversacion),
    ultimo: conversacion.mensajes.at(-1) ?? null,
    sinLeer: sinLeer(conversacion),
  };
}

// Las conversaciones del usuario, de la más reciente a la más vieja
export function listarConversaciones(req, res) {
  const lista = conversaciones
    .filter(esMia)
    .map(resumir)
    .sort((a, b) => new Date(b.ultimo?.fecha ?? 0) - new Date(a.ultimo?.fecha ?? 0));

  res.json({ conversaciones: lista, sinLeer: lista.reduce((t, c) => t + c.sinLeer, 0) });
}

// La gente de los módulos del usuario, para la búsqueda del panel de charlas
export function listarContactos(req, res) {
  res.json(contactosDe(YO).map((c) => ({ ...conPresencia(c), modulos: c.modulos })));
}

// Una conversación con todos sus mensajes. Abrirla la da por leída.
export function obtenerConversacion(req, res) {
  const conversacion = conversaciones.find((c) => c.id === Number(req.params.id));
  if (!conversacion || !esMia(conversacion)) {
    return res.status(404).json({ error: 'Conversación no encontrada' });
  }

  for (const mensaje of conversacion.mensajes) {
    if (mensaje.deId !== YO) mensaje.leido = true;
  }

  res.json({ id: conversacion.id, con: elOtro(conversacion), mensajes: conversacion.mensajes });
}

export function enviarMensaje(req, res) {
  const conversacion = conversaciones.find((c) => c.id === Number(req.params.id));
  if (!conversacion || !esMia(conversacion)) {
    return res.status(404).json({ error: 'Conversación no encontrada' });
  }

  const texto = (req.body?.texto ?? '').trim();

  // Por ahora de los adjuntos solo se guarda el nombre y el tamaño: todavía
  // no hay dónde subir el archivo (eso llega con multer).
  const adjuntos = Array.isArray(req.body?.adjuntos)
    ? req.body.adjuntos
        .slice(0, 5)
        .map((a) => ({ nombre: String(a?.nombre ?? '').slice(0, 120), tamano: Number(a?.tamano) || 0 }))
        .filter((a) => a.nombre)
    : [];

  if (!texto && adjuntos.length === 0) {
    return res.status(400).json({ error: 'El mensaje no puede estar vacío' });
  }

  const mensaje = {
    id: nuevoIdMensaje(),
    deId: YO,
    texto,
    adjuntos,
    fecha: new Date().toISOString(),
    leido: true,
  };
  conversacion.mensajes.push(mensaje);

  res.status(201).json(mensaje);
}

// Abre la conversación con alguien. Si ya existe, devuelve esa misma.
export function abrirConversacion(req, res) {
  const paraId = Number(req.body?.paraId);
  const persona = buscarPersona(paraId);

  if (!persona || paraId === YO) {
    return res.status(400).json({ error: 'No se puede abrir una conversación con esa persona' });
  }

  let conversacion = conversaciones.find((c) => esMia(c) && c.entre.includes(paraId));
  if (!conversacion) {
    conversacion = { id: nuevoIdConversacion(), entre: [YO, paraId], mensajes: [] };
    conversaciones.push(conversacion);
  }

  res.json({ id: conversacion.id, con: elOtro(conversacion), mensajes: conversacion.mensajes });
}
