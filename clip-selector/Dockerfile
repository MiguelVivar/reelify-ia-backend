# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Skip spacy model download for mock version
# RUN python -m spacy download es_core_news_sm

# Copy source code
COPY src/ ./src/
COPY .env .

# Create temp directory
RUN mkdir -p /tmp/clip_processing

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "src/main.py"]
