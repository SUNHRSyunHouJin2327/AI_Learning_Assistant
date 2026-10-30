#!/usr/bin/env bash
# Run on the ECS server (Ubuntu/Debian). Installs Docker, logs in to ACR, starts the app.
# Usage: AILA_IMAGE=<registry>/<namespace>/ai-learning-assistant:v1 bash ecs-setup.sh
set -euo pipefail
: "${AILA_IMAGE:?set AILA_IMAGE}"
echo "ECS CPU architecture: $(uname -m)"
if ! command -v docker >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-v2 || sudo apt-get install -y docker.io docker-compose-plugin
  sudo systemctl enable --now docker
fi
mkdir -p ~/ai-agent/data ~/ai-agent/workspace
cd ~/ai-agent
[ -f compose.yml ] || { echo "Copy deploy/compose.ecs.yml here as compose.yml first"; exit 1; }
printf 'AILA_IMAGE=%s\n' "$AILA_IMAGE" > .env
chmod 600 .env
if [ ! -f data/model-secrets.env ]; then
  read -r -s -p 'Qwen API key (input hidden, Enter to skip): ' KEY; echo
  [ -n "$KEY" ] && { printf 'MODEL_API_KEY=%s\n' "$KEY" > data/model-secrets.env; chmod 600 data/model-secrets.env; }
fi
sudo docker login "${AILA_IMAGE%%/*}"
sudo docker compose -p ai-learning-assistant pull
sudo docker compose -p ai-learning-assistant up -d
sleep 15
sudo docker ps
curl -fsS http://127.0.0.1:14242/health && echo
