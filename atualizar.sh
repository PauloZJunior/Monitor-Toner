#!/bin/bash
# Monitor de Toner v2 — Atualização
set -e
echo "→ Parando container..."
docker compose down
echo "→ Reconstruindo imagem..."
docker compose build --no-cache
echo "→ Iniciando container..."
docker compose up -d
sleep 2
docker compose ps
echo "✔ Atualização concluída!"
