import os
from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Whisper Configuration
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    
    # Viral Detection Configuration
    viral_keywords: List[str] = os.getenv("VIRAL_KEYWORDS", "oferta,descuento,quiero,increíble,gratis,limitado,exclusivo,promoción,rebaja,outlet").split(",")
    emotion_keywords: List[str] = os.getenv("EMOTION_KEYWORDS", "amor,odio,feliz,triste,enojado,sorprendido,emocionado,increíble,wow,genial").split(",")
    min_viral_score: float = float(os.getenv("MIN_VIRAL_SCORE", "0.3"))
    
    # Clips Storage
    clips_input_dir: str = os.getenv("CLIPS_INPUT_DIR", "/app/clips/raw")
    clips_output_dir: str = os.getenv("CLIPS_OUTPUT_DIR", "/app/clips/viral")
    
    # Service Configuration
    service_name: str = os.getenv("SERVICE_NAME", "clip-selector")
    service_host: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    service_port: int = int(os.getenv("SERVICE_PORT", "8002"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Temp directory
    temp_dir: str = os.getenv("TEMP_DIR", "/tmp/clip_processing")
    
    class Config:
        env_file = ".env"

settings = Settings()
