# CampusTFI

Campus virtual para estudiantes y docentes de FaCENA – UNNE, con una interfaz
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
npm run dev
```

Abrir http://localhost:5173. Vite redirige las llamadas `/api` al backend.
FastAPI publica documentación interactiva en http://localhost:3000/docs y
http://localhost:3000/redoc.

## Estado

La API incluye módulos, tareas, mensajería, novedades, calendario, foro y
biblioteca. Los datos siguen siendo de prueba y viven en memoria; todavía no
hay autenticación real ni persistencia en una base de datos.

Ver [decisiones técnicas](docs/decisiones-tecnicas.md) y la
[especificación de la API](docs/api/openapi.yaml).
