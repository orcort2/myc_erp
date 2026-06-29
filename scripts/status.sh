#!/bin/bash

echo "========================================"
echo "        MYC SYSTEM STATUS"
echo "========================================"

echo "Backend puerto 8000:"
lsof -i :8000 || echo "No hay proceso en 8000"

echo "----------------------------------------"

echo "Frontend puerto 5173:"
lsof -i :5173 || echo "No hay proceso en 5173"

echo "----------------------------------------"

echo "Git:"
cd /Users/saulcortes/Desktop/myc_erp || exit 1
git branch --show-current
git status --short

echo "========================================"
