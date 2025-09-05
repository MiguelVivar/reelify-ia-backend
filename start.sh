#!/bin/bash

# Script para inicializar y ejecutar el sistema completo

echo "🎬 Iniciando Reelify IA - Sistema de Clips Virales"
echo "================================================="

# Verificar si Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo. Por favor inicia Docker Desktop."
    exit 1
fi

# Verificar si Docker Compose está disponible
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Error: Docker Compose no está instalado."
    exit 1
fi

# Crear directorio temporal si no existe
mkdir -p /tmp/video_processing
mkdir -p /tmp/clip_processing

echo "📁 Creando directorios temporales..."

# Cambiar al directorio docker
cd docker

echo "🐳 Construyendo e iniciando servicios..."

# Construir e iniciar servicios
docker-compose up -d --build

echo "⏳ Esperando que los servicios estén listos..."

# Esperar a que los servicios estén saludables
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null && curl -s http://localhost:8002/health > /dev/null; then
        echo "✅ Servicios listos!"
        break
    fi
    echo "   Intentando conectar... ($i/30)"
    sleep 10
done

echo ""
echo "🎉 ¡Sistema Reelify IA iniciado exitosamente!"
echo ""
echo "📡 Endpoints disponibles:"
echo "   • Clip Generator: http://localhost:8001"
echo "   • Clip Selector:  http://localhost:8002"
echo "   • MinIO Console:  http://localhost:9001 (minioadmin/minioadmin)"
echo "   • MinIO API:      http://localhost:9000"
echo ""
echo "📖 Documentación API:"
echo "   • http://localhost:8001/docs"
echo "   • http://localhost:8002/docs"
echo ""
echo "📊 Para ver logs: docker-compose logs -f"
echo "🛑 Para detener:  docker-compose down"
