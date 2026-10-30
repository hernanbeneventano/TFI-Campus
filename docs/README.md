# CampusTFI

Campus virtual web pensado para ser intuitivo y fácil de usar, para estudiantes y docentes.

> Estado: **base inicial del proyecto**. Solo incluye la estructura de carpetas y un esqueleto mínimo que funciona. La base de datos y gran parte de las funciones todavía no están implementadas.

## Estructura

```
campustfi/
├── frontend/          Interfaz web (React + Vite)
│   └── src/
│       ├── components/   Piezas reutilizables (menú lateral, tarjetas...)
│       ├── pages/        Pantallas (Actividad, Cursos, Notas)
│       ├── services/     Llamadas a la API del backend
│       └── styles/       Estilos globales y colores
├── equipo/            Información del equipo y planificación de hitos
├── backend/           API (Node.js + Express)
│   └── src/
│       ├── routes/       Rutas de la API
│       ├── controllers/  Lógica de cada ruta
│       ├── data/         Datos de prueba (hasta definir la base de datos)
│       └── middleware/   Funciones intermedias (errores, autenticación...)
└── docs/              Documentación del proyecto
```

## Requisitos

- [Node.js](https://nodejs.org/) 20 o superior (incluye npm)

## Cómo levantarlo

Abrir dos terminales.

**1. Backend** (queda en http://localhost:3000)

```bash
cd backend
npm install
cp .env.example .env
npm run dev
```

**2. Frontend** (queda en http://localhost:5173)

```bash
cd frontend
npm install
npm run dev
```

Luego abrir http://localhost:5173 en el navegador.

## Qué hay hecho

- [x] Estructura de carpetas
- [x] Servidor con rutas de prueba: `/api/salud`, `/api/cursos`, `/api/actividad`
- [x] Interfaz con menú lateral y tres pantallas: Actividad, Cursos y Notas
- [ ] Base de datos (a definir)
- [ ] Inicio de sesión y roles
- [ ] Entregas, rúbricas y correcciones
- [ ] Anuncios, calendario y demás secciones
