#!/bin/bash

cd /Users/saulcortes/Desktop/myc_erp || exit 1

echo "Configurando frontend local..."
cp frontend/.env.dev frontend/.env.local

echo "Levantando backend..."
cd backend || exit 1
../venv/bin/uvicorn app.main:app --reload &
BACKEND_PID=$!

echo "Backend PID: $BACKEND_PID"

echo "Levantando frontend..."
cd ../frontend || exit 1
npm run dev

echo "Cerrando backend..."
kill $BACKEND_PID