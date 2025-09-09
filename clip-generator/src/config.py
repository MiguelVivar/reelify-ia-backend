import os
from pathlib import Path

# Cargar variables de entorno desde .env si existe
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ.setdefault(key, value)

class Settings:
    # Procesamiento de video
    temp_dir: str = os.getenv("TEMP_DIR", "/tmp/video_processing")
    max_clip_duration: int = int(os.getenv("MAX_CLIP_DURATION", "180"))
    min_clip_duration: int = int(os.getenv("MIN_CLIP_DURATION", "15"))
    
    # Dimensiones de los clips
    clip_width: int = int(os.getenv("CLIP_WIDTH", "1080"))
    clip_height: int = int(os.getenv("CLIP_HEIGHT", "1920"))

    # Almacenamiento de clips
    clips_output_dir: str = os.getenv("CLIPS_OUTPUT_DIR", "/app/clips/raw")

    # OpenRouter API Configuration
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-chat")
    
    # Video Analysis Configuration
    analysis_segment_duration: int = int(os.getenv("ANALYSIS_SEGMENT_DURATION", "30"))
    max_analysis_segments: int = int(os.getenv("MAX_ANALYSIS_SEGMENTS", "20"))
    highlight_threshold: float = float(os.getenv("HIGHLIGHT_THRESHOLD", "0.7"))

    # Configuración del servicio
    service_name: str = os.getenv("SERVICE_NAME", "clip-generator")
    service_host: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    service_port: int = int(os.getenv("SERVICE_PORT", "8001"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
