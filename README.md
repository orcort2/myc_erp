# ERP MYC

Version actual: ERP MYC v0.2.0 - Clientes Finalizado

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
