# CampusTFI

Campus virtual para estudiantes y docentes, con una interfaz
React y una API en Python.

## Estructura

- `frontend/`: interfaz React 18 y Vite.
- `backend/`: API FastAPI y sus datos de prueba.
- `docs/`: decisiones técnicas y especificación OpenAPI.
- `equipo/`: información del equipo y planificación.

## Requisitos

- Python 3.11 o superior.
- Node.js 20 o superior (incluye npm), para el frontend.

## Cómo levantarlo en Windows

Abrir dos terminales desde la carpeta del proyecto.

**1. Backend** (http://localhost:3000):

```powershell
cd backend
python -m venv .venv  # solo la primera vez
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m app.main
```

**2. Frontend** (http://localhost:5173):

```powershell
cd frontend
npm install
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm run dev
```

Abrir http://localhost:5173. Vite redirige las llamadas `/api` al backend.
FastAPI publica documentación interactiva en http://localhost:3000/docs y
http://localhost:3000/redoc.

Para completar `frontend/.env.local`, copiá la configuración de la app web en
Firebase Console → Configuración del proyecto → General → Tus apps. Ese archivo
es local y no se sube a Git; `frontend/.env.example` solo documenta los nombres
de las variables que necesita el frontend.

Para conectar Firestore, guardá la clave de servicio en
`backend/firebase-key.json` (Git la ignora) y consultá la guía de
[configuración del backend](backend/README.md). La conexión se comprueba en
`http://localhost:3000/api/salud/firestore`; los datos de las pantallas todavía
usan memoria y requieren una migración aparte.

## Estado

La API incluye módulos, tareas, mensajería, novedades, calendario, foro y
biblioteca. Los datos siguen siendo de prueba y viven en memoria; todavía no
hay autenticación real ni persistencia en una base de datos.

Ver [decisiones técnicas](docs/decisiones-tecnicas.md) y la
[especificación de la API](docs/api/openapi.yaml).
