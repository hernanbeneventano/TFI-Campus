# Backend de CampusTFI (Python)

Servidor de la interfaz de programación, con **FastAPI**. Mantiene las llamadas
HTTP del frontend y cuenta con rutas de compatibilidad para Actividad e
Información.

## Requisitos

Python 3.11 o superior.

## Puesta en marcha

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Guardá la clave de cuenta de servicio de Firebase como
`backend/firebase-key.json` (está excluida de Git) o configurá
`GOOGLE_APPLICATION_CREDENTIALS` en `.env` con su ruta absoluta. La clave debe
pertenecer al mismo proyecto Firebase donde creaste Firestore. El backend
inicializa el cliente al arrancar; `GET /api/salud/firestore` comprueba el
acceso con una consulta de solo lectura.

## Levantarlo

```powershell
python -m app.main
```

Queda en http://localhost:3000, que es adonde apunta el proxy de Vite. Se
reinicia solo al guardar un archivo.

El equivalente explícito, por si hace falta cambiar algo:

```powershell
python -m uvicorn app.main:app --port 3000 --reload
```

## Documentación de las rutas

Con el servidor levantado, FastAPI genera la documentación interactiva:

- **http://localhost:3000/docs** — Swagger, con un botón para probar cada ruta
- **http://localhost:3000/redoc** — la misma información, en formato de lectura
- **http://localhost:3000/openapi.json** — la especificación, para importar en Postman

## Si `pip install` falla por los certificados

En equipos con un antivirus que inspecciona el tráfico HTTPS (Avast, por
ejemplo) o detrás del proxy de una institución, pip falla así:

```
SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: unable to get local issuer certificate'))
```

No es un problema de red. Lo que pasa es que ese intermediario vuelve a
firmar los certificados con una raíz propia, que está en el almacén del
sistema operativo pero no en el paquete de Mozilla que trae pip.

La solución no es desactivar la verificación, sino darle a pip las
autoridades en las que confía el sistema. En Windows:

```bash
python -c "import ssl; open('ca-sistema.pem','w').write(''.join(ssl.DER_cert_to_PEM_cert(c) for s in ('ROOT','CA') for c,e,t in ssl.enum_certificates(s) if e=='x509_asn'))"
pip install --cert ca-sistema.pem -r requirements.txt
```

El servidor ya contempla esto por su cuenta: `app/servicios/libros_externos.py`
construye su contexto TLS con `ssl.create_default_context()`, que usa el
almacén del sistema. Sin eso, las consultas a Google Books y Open Library
fallarían en estos equipos.

## Estructura

```
app/
├── main.py                      Rutas generales, CORS y manejo de errores
├── datos.py                     Capa de datos: lo único que cambia con Firestore
├── datos_iniciales.json         Datos de prueba
├── servicios/
│   └── libros_externos.py       Google Books y Open Library, en paralelo
└── rutas/
    ├── cursos.py                Módulos y la pantalla de un módulo
    ├── tareas.py                Pendientes y atrasadas
    ├── calendario.py            Entregas, exámenes, clases y eventos
    ├── mensajes.py              Conversaciones de a dos
    ├── novedades.py             Muro, con reacciones anónimas
    ├── foro.py                  Consultas por asignatura
    └── biblioteca.py            Catálogo, aportes, moderación y archivos
```

La conexión a Firestore está inicializada, pero las rutas de la aplicación aún
leen y modifican datos en memoria desde `datos.py`. La migración de cada
colección y sus operaciones es un paso posterior; consultar Firestore no cambia
todavía los datos que ve la aplicación.

## Pruebas

Todavía no se incluye un conjunto automatizado de pruebas. Con el servidor
levantado, se pueden comprobar las rutas y sus respuestas en `/docs`; la
especificación exportable también está en `../docs/api/openapi.yaml`.

## Estado

Los datos viven en memoria y se reinician con el servidor. Todavía no hay
inicio de sesión: todas las operaciones se resuelven como si las hiciera un
usuario de prueba fijo. Ver `../docs/decisiones-tecnicas.md` para el detalle
de por qué.
