#!/bin/bash
DOCKER_IMAGE_NAME=$(basename "$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)")

echo "重启服务中..."
docker-compose down
docker-compose up -d --build

echo "服务已重启"
docker-compose ps | grep "$DOCKER_IMAGE_NAME" | grep -v "grep"
