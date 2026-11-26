# CampusTFI

Campus virtual para estudiantes y docentes, con una interfaz
React y una API en Python.

## Estructura

- `frontend/`: interfaz React 18 y Vite.
- `backend/`: el campus. API en Python, servida por Django.
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

## Despliegue

Las dos mitades van a lugares distintos y se encuentran por configuración.

**La interfaz, en GitHub Pages.** La publica
[`.github/workflows/pages.yml`](.github/workflows/pages.yml) en cada empuje a
`main` que toque `frontend/`. Pages sirve archivos estáticos: lo que sube es el
resultado de `npm run build` y nada más. Las carpetas `backend/` y
`backend-node/` quedan en el repositorio pero no se copian ni se ejecutan.

Hace falta configurar, una vez:

| Dónde | Qué |
| --- | --- |
| Settings › Pages › Source | `GitHub Actions` |
| Settings › Variables › `VITE_API_URL` | la dirección pública del servidor, sin barra final |
| Settings › Secrets › `VITE_FIREBASE_*` | las siete de `frontend/.env.local` |

**El servidor, aparte.** En el servicio donde se aloje hay que poner
`FRONTEND_URL` con el origen de Pages (`https://<usuario>.github.io`, sin la
ruta del repositorio), o el navegador rechaza cada respuesta por origen
cruzado. Y `PERMITIR_USUARIO_SIN_TOKEN` en `no`, que es como viene.

Dos cosas que conviene tener presentes:

- **El sitio no vive en la raíz del dominio** sino en `/<repositorio>/`. De eso
  se ocupa `base` en `vite.config.js`, y el router lo lee de
  `import.meta.env.BASE_URL`, así que hay un solo lugar que lo decide. Una ruta
  de archivo escrita fija dentro del JavaScript se rompe: Vite reescribe las de
  `index.html` y las del CSS, pero no las cadenas del código.
- **Pages no reescribe rutas.** Al entrar directo a `/modulos/3` busca ese
  archivo y contesta 404, así que el flujo de trabajo deja una copia de
  `index.html` como `404.html` y la aplicación se carga igual.

Sin `VITE_API_URL` la interfaz pide `/api` al propio Pages y no hay nadie
atendiendo: se ve la pantalla de inicio de sesión y nada funciona. Es el primer
síntoma a mirar si el sitio carga pero está vacío.

## Estado

La API incluye módulos, tareas, mensajería, novedades, calendario, foro,
biblioteca, administración académica, asistencia y finales. Django atiende las
rutas y el backend persiste en Firestore cuando está configurado; los datos de
ejemplo se usan para desarrollo y pruebas.

Ver [decisiones técnicas](docs/decisiones-tecnicas.md) y la
[especificación de la API](docs/api/openapi.yaml).
