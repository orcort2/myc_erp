#!/bin/bash

echo "Deteniendo MYC SYSTEM..."

BACKEND_PIDS=$(lsof -ti :8000)
FRONTEND_PIDS=$(lsof -ti :5173)

if [ -n "$BACKEND_PIDS" ]; then
  kill $BACKEND_PIDS
  echo "Backend detenido."
else
  echo "Backend no estaba corriendo."
fi

if [ -n "$FRONTEND_PIDS" ]; then
  kill $FRONTEND_PIDS
  echo "Frontend detenido."
else
  echo "Frontend no estaba corriendo."
fi

echo "Listo."
