@echo off
REM Script para inicializar y ejecutar el sistema completo en Windows

echo 🎬 Iniciando Reelify IA - Sistema de Clips Virales
echo =================================================

REM Verificar si Docker está corriendo
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Docker no está corriendo. Por favor inicia Docker Desktop.
    pause
    exit /b 1
)

REM Verificar si Docker Compose está disponible
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Docker Compose no está instalado.
    pause
    exit /b 1
)

echo 📁 Creando directorios temporales...

REM Crear directorios temporales
if not exist "C:\tmp\video_processing" mkdir "C:\tmp\video_processing"
if not exist "C:\tmp\clip_processing" mkdir "C:\tmp\clip_processing"

REM Cambiar al directorio docker
cd docker

echo 🐳 Construyendo e iniciando servicios...

REM Construir e iniciar servicios
docker-compose up -d --build

echo ⏳ Esperando que los servicios estén listos...

REM Esperar a que los servicios estén listos
timeout /t 30 /nobreak >nul

echo.
echo 🎉 ¡Sistema Reelify IA iniciado exitosamente!
echo.
echo 📡 Endpoints disponibles:
echo    • Clip Generator: http://localhost:8001
echo    • Clip Selector:  http://localhost:8002
echo.
echo 📖 Documentación API:
echo    • http://localhost:8001/docs
echo    • http://localhost:8002/docs
echo.
echo � Descarga de clips:
echo    • Clips generados: http://localhost:8001/clips/raw/{filename}
echo    • Clips virales:   http://localhost:8002/clips/viral/{filename}
echo.
echo 📊 Para ver logs: docker-compose logs -f
echo 🛑 Para detener:  docker-compose down
echo.
pause
