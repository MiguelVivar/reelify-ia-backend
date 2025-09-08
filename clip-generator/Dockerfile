# Use Python 3.11 slim image
FROM python:3.11-slim

# Setear directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY .env .

# Crear directorio temporal
RUN mkdir -p /tmp/video_processing

# Exponer puerto
EXPOSE 8001

# Ejecutar la aplicación
CMD ["python", "src/main.py"]
