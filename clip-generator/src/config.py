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
    max_clip_duration: int = int(os.getenv("MAX_CLIP_DURATION", "75"))  # Reducido para viral
    min_clip_duration: int = int(os.getenv("MIN_CLIP_DURATION", "20"))  # Aumentado para engagement
    
    # Dimensiones de los clips optimizadas para móvil
    clip_width: int = int(os.getenv("CLIP_WIDTH", "1080"))
    clip_height: int = int(os.getenv("CLIP_HEIGHT", "1920"))

    # Almacenamiento temporal de clips (auto-limpieza)
    temp_clips_expiry: int = int(os.getenv("TEMP_CLIPS_EXPIRY", "3600"))  # 1 hora por defecto

    # OpenRouter API Configuration
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-chat")
    
    # Video Analysis Configuration - Optimizado para viralidad
    analysis_segment_duration: int = int(os.getenv("ANALYSIS_SEGMENT_DURATION", "30"))  # Segmentos más cortos para precisión
    max_analysis_segments: int = int(os.getenv("MAX_ANALYSIS_SEGMENTS", "40"))  # Más segmentos para análisis detallado
    highlight_threshold: float = float(os.getenv("HIGHLIGHT_THRESHOLD", "0.8"))  # Threshold más alto para máxima selectividad
    
    # Configuración avanzada para análisis viral
    viral_score_threshold: float = float(os.getenv("VIRAL_SCORE_THRESHOLD", "0.75"))  # Score mínimo para consideración viral
    max_clips_per_video: int = int(os.getenv("MAX_CLIPS_PER_VIDEO", "3"))  # Máximo clips por video para selectividad
    min_clip_separation_seconds: int = int(os.getenv("MIN_CLIP_SEPARATION_SECONDS", "120"))  # Separación mínima entre clips
    
    # Duración óptima para contenido viral (rangos)
    optimal_viral_duration_min: int = int(os.getenv("OPTIMAL_VIRAL_DURATION_MIN", "25"))
    optimal_viral_duration_max: int = int(os.getenv("OPTIMAL_VIRAL_DURATION_MAX", "45"))
    
    # Configuración de engagement y retención
    hook_analysis_duration: int = int(os.getenv("HOOK_ANALYSIS_DURATION", "5"))  # Primeros N segundos para analizar hook
    retention_target_percentage: float = float(os.getenv("RETENTION_TARGET_PERCENTAGE", "0.8"))  # Target de retención
    
    # Pesos para algoritmo de scoring viral
    emotional_weight: float = float(os.getenv("EMOTIONAL_WEIGHT", "0.25"))
    engagement_weight: float = float(os.getenv("ENGAGEMENT_WEIGHT", "0.20"))
    shareability_weight: float = float(os.getenv("SHAREABILITY_WEIGHT", "0.20"))
    hook_weight: float = float(os.getenv("HOOK_WEIGHT", "0.15"))
    memorability_weight: float = float(os.getenv("MEMORABILITY_WEIGHT", "0.10"))
    retention_weight: float = float(os.getenv("RETENTION_WEIGHT", "0.10"))

    # Configuración del servicio
    service_name: str = os.getenv("SERVICE_NAME", "clip-generator")
    service_host: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    service_port: int = int(os.getenv("SERVICE_PORT", "8001"))
    
    # Configuración de descarga (SIN timeout para videos largos)
    download_chunk_size: int = int(os.getenv("DOWNLOAD_CHUNK_SIZE", "524288"))  # 512KB chunks (más estable)
    max_video_size_mb: int = int(os.getenv("MAX_VIDEO_SIZE_MB", "5120"))  # 5GB máximo
    progress_log_interval: int = int(os.getenv("PROGRESS_LOG_INTERVAL", "50"))  # Log cada 50MB
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
