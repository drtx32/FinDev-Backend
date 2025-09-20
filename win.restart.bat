@echo off
chcp 65001
setlocal enabledelayedexpansion

:: 获取当前脚本所在的一级文件夹名称（作为镜像名）
for %%i in ("%~dp0.") do set "DOCKER_IMAGE_NAME=%%~ni"

echo "重启服务中..."
docker-compose down
docker-compose up -d --build

echo "服务已重启"
docker-compose ps | findstr /i "!DOCKER_IMAGE_NAME!" | findstr /v "findstr"
endlocal
pause