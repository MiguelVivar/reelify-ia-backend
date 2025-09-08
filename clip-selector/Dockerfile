# Usar imagen slim de Python 3.11
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para mejor caché
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Omitir descarga del modelo spacy para versión mock
# RUN python -m spacy download es_core_news_sm

# Copiar código fuente
COPY src/ ./src/
COPY .env .

# Crear directorio temporal
RUN mkdir -p /tmp/clip_processing

# Exponer puerto
EXPOSE 8002

# Ejecutar la aplicación
CMD ["python", "src/main.py"]
