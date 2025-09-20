#!/bin/bash
DOCKER_IMAGE_NAME=$(basename "$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)")

echo "启动服务中..."
docker-compose up -d --build
echo "服务启动完成！"
echo "访问 http://localhost 查看应用"
echo "访问 http://localhost/health 查看健康检查"
docker-compose ps | grep "$DOCKER_IMAGE_NAME" | grep -v "grep"
