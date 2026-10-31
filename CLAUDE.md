# CampusTFI: contexto del proyecto

Campus virtual web (LMS) para el Trabajo Final Integrador de FaCENA – UNNE.
Integrantes: **Sosa Santiago Rafael** (frontend, diseño) y **Beneventano Hernán** (backend, base de datos).
Nombre provisorio: CampusTFI.

## Idea
Muchos campus universitarios son poco estéticos y difíciles de entender: cuesta ver dónde está cada cosa
y cómo hacer cada tarea. CampusTFI busca una experiencia más intuitiva y un diseño visual cuidado,
para estudiantes y docentes. Inspiración propia; Blackboard es solo una referencia más.

## Stack
- Frontend: React 18 + Vite + React Router (`frontend/`)
- Backend: Node.js + Express (`backend/`)
- Base de datos: **todavía no definida** (propuesta: PostgreSQL + Prisma). Hoy se usan datos de prueba en `backend/src/data/mock.js`.
- Futuro: bcrypt + jsonwebtoken (login), multer (subida de archivos).
- Todo en JavaScript. Código, nombres y textos de la interfaz en **español**.

## Estructura
```
frontend/src/
  components/  MenuLateral, Encabezado, BarraHerramientas, TarjetaModulo, PanelTareas, Iconos (SVG propios)
  pages/       Modulos (principal), Actividad, EnConstruccion (Información y Mensajes)
  services/    api.js: todas las llamadas al backend (Vite redirige /api a localhost:3000)
  styles/      global.css: paleta en variables CSS en :root
backend/src/
  routes/ → controllers/ → data/mock.js     middleware/errores.js
  Rutas: GET /api/salud, /api/me, /api/cursos, /api/cursos/:id, /api/actividad, /api/tareas/pendientes
equipo/        información del equipo y planificación de hitos
```

## Diseño
Paleta (usar siempre las variables de `global.css`):
- Prussian Blue `#031D44`: menú lateral
- Space Indigo `#1F2444`: textos y botones
- Smart Blue `#4A6FA5`: color principal y acentos
- Alice Blue `#DBE9EE`: recuadros y paneles
- Bright Snow `#F9F9F9`: fondo
- `#B23A48` solo para lo atrasado/urgente

Layout de la pantalla Módulos (según boceto): menú lateral a la izquierda (logo, Información,
Actividad, Módulos, Mensajes, usuario abajo) · encabezado con el nombre del apartado · barra
(vista tarjetas/lista, búsqueda, filtro Fechas, filtro Apartados especiales = favoritos) · grilla de
módulos · panel derecho con tareas pendientes recientes y atrasadas. Responsive: en celular el menú
pasa arriba con 4 botones.

## Planificación (21 días)
1. Definición: alcance, stack, modelo ER, endpoints, wireframes.
2. Base y cursos: login con roles, CRUD de cursos, dashboard y navegación.
3. Tareas y notas: entregas con archivos, calificaciones, vistas de notas.
4. Testing, validaciones, pulido responsive y presentación.

Alcance de la primera versión: login y roles, cursos e inscripciones, contenido por semana,
tareas con entrega de archivos, corrección con nota y comentario, Actividad, Notas, anuncios.
Queda para después: control de plagio/IA, foro, mensajes, grupos, rúbricas detalladas, mails.

## Cómo levantar
```
cd backend && npm install && cp .env.example .env && npm run dev    # http://localhost:3000
cd frontend && npm install && npm run dev                          # http://localhost:5173
```

## Pendiente inmediato
- Elegir y configurar la base de datos.
- Pantalla interior de un módulo (esperando boceto).
- Login y roles.
