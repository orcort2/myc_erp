# ERP MYC

Version actual: ERP MYC v0.4.0 - Datos de Certificados

Base del sistema ERP MYC para controlar el flujo completo:

```text
Lead -> Cotizacion -> Agenda -> Llamado -> Orden de servicio -> Hoja de campo -> Certificado -> Calidad -> Finanzas -> Liberacion -> Encuesta
```

## Stack

- Backend: FastAPI.
- Base de datos: PostgreSQL.
- Frontend: React con Vite.
- Archivos: carpetas controladas en `storage/`.

## Estructura

```text
backend/
frontend/
storage/
docs/
```

## Desarrollo backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Desarrollo frontend

```bash
cd frontend
npm install
npm run dev
```

## Motor de Resoluciones — API pública v1

La primera interfaz institucional está disponible bajo
`/api/public/resolution-engine/v1`. Requiere credencial de consumidor,
organización y correlación; las altas requieren además `Idempotency-Key`.

```text
GET  /api/public/resolution-engine/v1/capabilities
POST /api/public/resolution-engine/v1/resolutions
GET  /api/public/resolution-engine/v1/resolutions
GET  /api/public/resolution-engine/v1/resolutions/{public_id}
GET  /api/developers/resolution-engine
```

El cliente oficial es `backend/myc_resolution_sdk` y consume exclusivamente
HTTP. El contrato y la guía están en
`docs/architecture/resolution-engine/26_PUBLIC_API_SDK.md`.
