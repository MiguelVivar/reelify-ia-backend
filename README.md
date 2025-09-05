# Reelify IA - Sistema de Microservicios para Clips Virales

Sistema escalable de dos microservicios en Python con FastAPI para procesar videos y generar clips virales usando IA. Integra **auto-highlighter**, **Whisper**, y análisis semántico para identificar y crear contenido viral automáticamente.

## 🏗️ Arquitectura

### Microservicio A: `clip-generator`
- **Puerto**: 8001
- **Función**: Genera clips iniciales desde videos públicos usando auto-highlighter
- **Storage**: Archivos locales en volúmenes Docker
- **Tecnologías**: Python 3.11, FastAPI, auto-highlighter, FFmpeg, MoviePy

### Microservicio B: `clip-selector`  
- **Puerto**: 8002
- **Función**: Selecciona clips virales usando Whisper y análisis semántico
- **Storage**: Archivos locales en volúmenes Docker
- **Tecnologías**: Python 3.11, FastAPI, Whisper, transformers, spaCy

### Infraestructura
- **Storage**: Volúmenes Docker locales (sin MinIO)
- **Descargas**: URLs públicas sin autenticación
- **Containerización**: Docker + Docker Compose
- **Networking**: Bridge network personalizada

## 📁 Estructura del Proyecto

```
Reelify IA/
├── clip-generator/
│   ├── src/
│   │   ├── main.py              # FastAPI app principal
│   │   ├── routes.py            # Endpoints REST
│   │   ├── service.py           # Lógica de negocio
│   │   ├── video_processor.py   # Procesamiento con auto-highlighter
│   │   ├── minio_service.py     # Cliente MinIO/S3
│   │   ├── models.py            # Modelos Pydantic
│   │   └── config.py            # Configuración
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
├── clip-selector/
│   ├── src/
│   │   ├── main.py              # FastAPI app principal
│   │   ├── routes.py            # Endpoints REST
│   │   ├── service.py           # Lógica de negocio
│   │   ├── viral_analyzer.py    # Análisis viral con Whisper
│   │   ├── whisper_service.py   # Cliente Whisper
│   │   ├── minio_service.py     # Cliente MinIO/S3
│   │   ├── models.py            # Modelos Pydantic
│   │   └── config.py            # Configuración
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
├── docker/
│   ├── docker-compose.yml
│   └── .env.example
└── README.md
```

## 🚀 Instalación y Despliegue

### Prerrequisitos
- Docker y Docker Compose
- Mínimo 4GB RAM disponible
- Mínimo 10GB espacio en disco

### 1. Clonar y configurar

```bash
cd "C:\Users\HP\Documents\REPOSITORIOS\TRABAJO\Asumarket\Reelify IA"

# Copiar variables de entorno
cp docker/.env.example docker/.env
```

### 2. Levantar servicios

```bash
cd docker
docker-compose up -d
```

### 3. Verificar servicios

```bash
# Verificar estado
docker-compose ps

# Ver logs
docker-compose logs -f clip-generator
docker-compose logs -f clip-selector
```

### 4. Acceso a servicios

- **Clip Generator**: http://localhost:8001
- **Clip Selector**: http://localhost:8002
- **MinIO Console**: http://localhost:9001 (admin/minioadmin)
- **MinIO API**: http://localhost:9000

## 📡 Documentación API

### Microservicio A: Clip Generator

#### `POST /api/v1/generate-initial-clips`

Genera clips iniciales desde un video usando auto-highlighter.

**Request:**
```json
{
  "video_url": "https://storage.asumarket.com/agentetiktok/clip_01K3WWB7PBAYVG69PD0QVBRAM1"
}
```

**Response:**
```json
{
  "status": "success",
  "clips": [
    {
      "url": "/clips/raw/clip_1.mp4",
      "start": 40,
      "end": 70,
      "duration": 30
    },
    {
      "url": "/clips/raw/clip_2.mp4", 
      "start": 120,
      "end": 180,
      "duration": 60
    }
  ],
  "message": "Generated 2 clips successfully"
}
```

**Descargar clips generados:**
```
GET http://localhost:8001/clips/raw/clip_1.mp4
```

### Microservicio B: Clip Selector

#### `POST /api/v1/select-viral-clips`

Selecciona clips virales usando Whisper y análisis semántico.

**Request:**
```json
{
  "clips": [
    { "url": "/clips/raw/clip_1.mp4" },
    { "url": "https://example.com/external_clip.mp4" }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "viral_clips": [
    {
      "url": "/clips/viral/clip_1_viral.mp4",
      "keywords": ["descuento", "quiero"],
      "duration": 45,
      "viral_score": 0.78,
      "transcript": "Quiero aprovechar este descuento increíble..."
    }
  ],
  "message": "Selected 1 viral clips from 2 input clips"
}
```

**Descargar clips virales:**
```
GET http://localhost:8002/clips/viral/clip_1_viral.mp4
```

## 🧪 Testing

### 1. Test con curl

```bash
# Test Clip Generator
curl -X POST "http://localhost:8001/api/v1/generate-initial-clips" \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://storage.asumarket.com/agentetiktok/test_video.mp4"}'

# Test Clip Selector  
curl -X POST "http://localhost:8002/api/v1/select-viral-clips" \
  -H "Content-Type: application/json" \
  -d '{"clips": [{"url": "https://storage.asumarket.com/agentetiktok/clips/raw/clip_1.mp4"}]}'
```

### 2. Test con Python

```python
import requests

# Test Clip Generator
response = requests.post(
    "http://localhost:8001/api/v1/generate-initial-clips",
    json={"video_url": "https://storage.asumarket.com/agentetiktok/test_video.mp4"}
)
print("Clip Generator:", response.json())

# Test Clip Selector
response = requests.post(
    "http://localhost:8002/api/v1/select-viral-clips", 
    json={"clips": [{"url": "https://storage.asumarket.com/agentetiktok/clips/raw/clip_1.mp4"}]}
)
print("Clip Selector:", response.json())
```

## ⚙️ Configuración

### Variables de Entorno

#### Clip Generator (.env)
```env
SERVICE_PORT=8001
LOG_LEVEL=INFO
TEMP_DIR=/tmp/video_processing
CLIPS_OUTPUT_DIR=/app/clips/raw
MAX_CLIP_DURATION=180
MIN_CLIP_DURATION=15
```

#### Clip Selector (.env)
```env
SERVICE_PORT=8002
LOG_LEVEL=INFO
TEMP_DIR=/tmp/clip_processing
CLIPS_INPUT_DIR=/app/clips/raw
CLIPS_OUTPUT_DIR=/app/clips/viral
WHISPER_MODEL=base
VIRAL_KEYWORDS=oferta,descuento,quiero,increíble,gratis
EMOTION_KEYWORDS=amor,odio,feliz,triste,emocionado
MIN_VIRAL_SCORE=0.3
```

### Configuración de Palabras Clave Virales

Puedes personalizar las palabras clave que el sistema busca:

```env
# Palabras comerciales
VIRAL_KEYWORDS=oferta,descuento,promoción,rebaja,gratis,limitado,exclusivo,outlet

# Palabras emocionales  
EMOTION_KEYWORDS=increíble,wow,genial,perfecto,amor,odio,feliz,emocionado,sorprendido
```

## 🔧 Troubleshooting

### Problemas Comunes

1. **Error de conexión a storage**
   ```bash
   docker-compose logs clip-generator
   docker-compose logs clip-selector
   ```

2. **Whisper model download issues**
   ```bash
   docker-compose exec clip-selector python -c "import whisper; whisper.load_model('base')"
   ```

3. **FFmpeg errors**
   ```bash
   docker-compose exec clip-generator ffmpeg -version
   ```

4. **Memory issues**
   - Aumentar memoria Docker a 6GB+
   - Usar modelo Whisper más pequeño: `WHISPER_MODEL=tiny`

5. **Archivos no encontrados**
   - Verificar que los volúmenes Docker estén montados correctamente
   - Revisar permisos de archivos

### Logs y Debugging

```bash
# Ver logs en tiempo real
docker-compose logs -f

# Logs específicos de un servicio
docker-compose logs clip-generator
docker-compose logs clip-selector

# Entrar a contenedor para debugging
docker-compose exec clip-generator bash
docker-compose exec clip-selector bash
```

## 📈 Escalabilidad y Producción

### Horizontal Scaling

```yaml
# docker-compose.yml para múltiples instancias
clip-generator:
  scale: 3
  deploy:
    replicas: 3

clip-selector:  
  scale: 2
  deploy:
    replicas: 2
```

### Load Balancer (nginx)

```nginx
upstream clip_generator {
    server clip-generator-1:8001;
    server clip-generator-2:8001; 
    server clip-generator-3:8001;
}

upstream clip_selector {
    server clip-selector-1:8002;
    server clip-selector-2:8002;
}
```

### Monitoring

```yaml
# Añadir Prometheus + Grafana
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

## 🛡️ Seguridad

### Producción

1. **Cambiar credenciales por defecto**
2. **Usar HTTPS/TLS**
3. **Configurar firewall**
4. **Implementar rate limiting**
5. **Usar secrets management**

```yaml
# docker-compose.prod.yml
secrets:
  minio_access_key:
    external: true
  minio_secret_key:
    external: true
```

## 📚 Algoritmos y IA

### Auto-highlighter (Clip Generator)
- **Análisis de audio**: RMS energy, spectral centroid, zero-crossing rate
- **Detección de beats**: librosa beat tracking
- **Análisis visual**: diferencias entre frames, detección de cambios de escena
- **Clustering**: agrupación de momentos emocionantes

### Whisper + Análisis Viral (Clip Selector)
- **Transcripción**: Whisper OpenAI para audio a texto
- **NLP**: análisis de palabras clave y emociones
- **Scoring viral**: algoritmo de puntuación basado en:
  - Densidad de palabras clave
  - Variedad de categorías (comercial/emocional)
  - Longitud óptima del texto
  - Patrones de engagement

### FunClip-like Selection
- **Momentos clave**: identificación de segmentos con mayor potencial viral
- **Optimización de duración**: selección de clips de duración óptima
- **Compilación inteligente**: combinación de múltiples momentos

## 🤝 Contribución

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

## 🆘 Soporte

Para soporte técnico:
- **Issues**: GitHub Issues
- **Email**: soporte@asumarket.com  
- **Documentación**: [Wiki del proyecto](https://github.com/asumarket/reelify-ia/wiki)

---

**Desarrollado con ❤️ para Asumarket por el equipo de Reelify IA**
