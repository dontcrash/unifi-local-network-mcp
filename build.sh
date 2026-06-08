#!/usr/bin/env sh
set -eu

IMAGE_NAME="${IMAGE_NAME:-unifi-network-mcp:local}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
export IMAGE_NAME

docker compose -f "$COMPOSE_FILE" up --build -d --force-recreate
