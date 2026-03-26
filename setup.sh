#!/usr/bin/env bash
set -euo pipefail

echo "→ JackBot — Predictive Service Setup"

# Verificar pré-requisitos
for cmd in java docker; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERRO: '$cmd' não encontrado. Instale antes de continuar."; exit 1; }
done

# Verificar versão do Java (≥ 21)
JAVA_VER=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d. -f1)
if [ "$JAVA_VER" -lt 21 ] 2>/dev/null; then
  echo "ERRO: Java 21+ necessário (encontrado: Java $JAVA_VER)"
  exit 1
fi

# Copiar .env se não existir
if [ ! -f .env ]; then
  cp .env.example .env
  echo "→ .env criado a partir de .env.example"
fi

# Build e subida
docker compose up -d --build

# Aguardar health
echo "→ Aguardando serviço ficar saudável (máx 60s)..."
for i in $(seq 1 12); do
  if curl -sf http://localhost:8080/actuator/health 2>/dev/null | grep -q '"UP"'; then
    echo "✓ Serviço disponível em http://localhost:8080"
    echo "✓ Swagger UI: http://localhost:8080/swagger-ui.html"
    exit 0
  fi
  sleep 5
done

echo "⚠ Timeout: serviço ainda não respondeu. Verifique: docker compose logs predictive-service"
exit 1
