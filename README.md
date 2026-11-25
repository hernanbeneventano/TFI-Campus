# CampusTFI

Campus virtual para estudiantes y docentes, con una interfaz
React y una API en Python.

## Estructura

- `frontend/`: interfaz React 18 y Vite.
- `backend/`: el campus. API en Python, servida exclusivamente por Django.
- `backend-node/`: el servicio de catálogos externos (Google Books y Open
  Library). Es el segundo backend, y está en Node porque es la única parte sin
  datos propios: ver [su README](backend-node/README.md).
- `docs/`: decisiones técnicas y especificación OpenAPI.
- `equipo/`: información del equipo y planificación.

## Requisitos

- Python 3.11 o superior.
- Node.js 22.15 o superior (incluye npm), para el frontend y para
  `backend-node/`.

## Cómo levantarlo en Windows

Abrir tres terminales desde la carpeta del proyecto. El campus funciona sin la
tercera: lo único que no se puede sin ella es buscar en catálogos externos, y la
pantalla lo avisa.

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

**3. Catálogos externos** (http://127.0.0.1:4000), opcional:

```powershell
cd backend-node
npm install
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm start
```

Abrir http://localhost:5173. Vite redirige las llamadas `/api` al backend
Django. La especificación OpenAPI está en
[`docs/api/openapi.yaml`](docs/api/openapi.yaml).

El navegador no le habla nunca a `backend-node`: le habla al campus, que ya sabe
quién es y si tiene permiso, y el campus le pregunta a ese servicio. Por eso
escucha en 127.0.0.1 y no hace falta configurar nada en el frontend.

Para completar `frontend/.env.local`, copiá la configuración de la app web en
Firebase Console → Configuración del proyecto → General → Tus apps. Ese archivo
es local y no se sube a Git; `frontend/.env.example` solo documenta los nombres
de las variables que necesita el frontend.

Para conectar Firestore, guardá la clave de servicio en
`backend/firebase-key.json` (Git la ignora) y consultá la guía de
[configuración del backend](backend/README.md). La API de salud está en
`http://localhost:3000/api/salud`.

## Estado

La API incluye módulos, tareas, mensajería, novedades, calendario, foro,
biblioteca, administración académica, asistencia y finales. Django atiende las
rutas y el backend persiste en Firestore cuando está configurado; los datos de
ejemplo se usan para desarrollo y pruebas.

Ver [decisiones técnicas](docs/decisiones-tecnicas.md) y la
[especificación de la API](docs/api/openapi.yaml).
