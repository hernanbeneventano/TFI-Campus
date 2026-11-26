# Backend de CampusTFI

El backend principal está implementado con **Django**. Las rutas se registran
en URLconf y se sirven mediante su aplicación ASGI, con Uvicorn como servidor.

## Requisitos

Python 3.11 o superior.

## Puesta en marcha

Desde PowerShell, en la raíz del proyecto:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m app.main
```

El servidor escucha en `http://127.0.0.1:3000`. Para desarrollo, la recarga
automática está activada por defecto y se puede apagar con
`RECARGA_AUTOMATICA=no`.

## Firestore y archivos

Para conectar Firestore, guardá la clave de cuenta de servicio en
`backend/firebase-key.json` (excluida de Git) o configurá
`GOOGLE_APPLICATION_CREDENTIALS` en `.env`. `FIRESTORE_ACTIVO=no` desactiva la
persistencia y deja el campus en memoria.

Los archivos se almacenan en Cloudflare R2 cuando está configurado. Consultá
`.env.example` para las variables disponibles; las credenciales reales no se
suben al repositorio.

## Pruebas

Las pruebas del backend se ejecutan desde `backend/`:

```powershell
python -m pruebas.servidor
python -m pruebas.banco
```

La primera verifica la aplicación ASGI, el middleware, los errores HTTP y las
169 rutas registradas. El banco compara las respuestas y el estado del campus
con la grabación de referencia del contrato
(`pruebas/banco/grabaciones/contrato.json.gz`), que es un fixture de pruebas y
no una implementación de servidor.

La especificación OpenAPI mantenida en el repositorio está en
[`../docs/api/openapi.yaml`](../docs/api/openapi.yaml); no se genera en tiempo
de ejecución.
