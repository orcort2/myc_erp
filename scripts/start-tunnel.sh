#!/bin/bash

cd /Users/saulcortes/Desktop/myc_erp || exit 1

echo "Configurando frontend para túnel..."
cp frontend/.env.tunnel frontend/.env.local

echo "Levantando frontend conectado al API público..."
cd frontend || exit 1
npm run dev
