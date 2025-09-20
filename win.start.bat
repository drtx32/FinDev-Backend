@echo off
chcp 65001
setlocal enabledelayedexpansion

:: 获取当前脚本所在的一级文件夹名称（作为镜像名）
for %%i in ("%~dp0.") do set "DOCKER_IMAGE_NAME=%%~ni"

echo "启动服务中..."
docker-compose up -d --build
echo "服务启动完成！"
echo "访问 http://localhost 查看应用"
echo "访问 http://localhost/health 查看健康检查"
docker-compose ps | findstr /i "!DOCKER_IMAGE_NAME!" | findstr /v "findstr"
endlocal
