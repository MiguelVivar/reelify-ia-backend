# 🐳 Dockerfile para KickAPI Ultra Avanzado con FFmpeg y Whisper
# Imagen base con Python optimizada
FROM python:3.11-slim

# Información del mantenedor
LABEL maintainer="KickAPI Team"
LABEL description="API avanzada para procesamiento de clips con FFmpeg y subtítulos IA"
LABEL version="2.0.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema y FFmpeg completo
RUN apt-get update && apt-get install -y \
    # FFmpeg completo con todas las librerías
    ffmpeg \
    # Herramientas de desarrollo necesarias para compilar paquetes Python
    build-essential \
    gcc \
    g++ \
    # Git para descargar modelos de Whisper
    git \
    # Herramientas de red
    curl \
    wget \
    # Librerías adicionales para FFmpeg
    libavcodec-extra \
    libavformat-dev \
    libavfilter-dev \
    libavdevice-dev \
    # Librerías para audio
    libportaudio2 \
    libsndfile1 \
    # Librerías adicionales necesarias
    libmagic1 \
    libffi-dev \
    # Limpieza de cache
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verificar que FFmpeg esté instalado correctamente
RUN ffmpeg -version && ffprobe -version

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements.txt primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar las dependencias principales
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Instalar PyTorch CPU optimizado (necesario para Whisper)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Instalar dependencias del requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Instalar OpenAI Whisper con dependencias optimizadas
RUN pip install --no-cache-dir openai-whisper

# Pre-descargar modelo base de Whisper para acelerar primera ejecución
RUN python -c "import whisper; whisper.load_model('base')" || echo "Whisper model will be downloaded on first use"

# Copiar el código de la aplicación
COPY . .

# Crear directorios necesarios para procesamiento
RUN mkdir -p /app/converted_videos /app/temp /tmp/whisper_cache /tmp/video_processing

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash kickapi && \
    chown -R kickapi:kickapi /app /tmp/whisper_cache /tmp/video_processing && \
    chmod +x /app/main.py

# Cambiar a usuario no-root
USER kickapi

# Configurar variables de entorno para Whisper y cache
ENV WHISPER_CACHE_DIR=/tmp/whisper_cache
ENV HF_HOME=/tmp/huggingface_cache
ENV TRANSFORMERS_CACHE=/tmp/transformers_cache

# Exponer el puerto configurado
EXPOSE ${SERVICE_PORT:-8003}

# Healthcheck para verificar que la API funciona
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-8003}/health || exit 1

# Comando para ejecutar la aplicación con configuración optimizada
CMD ["python", "-u", "main.py"]

# Metadatos adicionales
LABEL org.opencontainers.image.source="https://github.com/MiguelVivar/KickApi"
LABEL org.opencontainers.image.description="API avanzada para procesamiento de clips con FFmpeg y subtítulos automáticos"
LABEL org.opencontainers.image.licenses="MIT"
