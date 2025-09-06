import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Video Processing
    temp_dir: str = os.getenv("TEMP_DIR", "/tmp/video_processing")
    max_clip_duration: int = int(os.getenv("MAX_CLIP_DURATION", "180"))
    min_clip_duration: int = int(os.getenv("MIN_CLIP_DURATION", "15"))
    
    # Clip Output Dimensions (for TikTok/Instagram Reels)
    clip_width: int = int(os.getenv("CLIP_WIDTH", "1080"))
    clip_height: int = int(os.getenv("CLIP_HEIGHT", "1920"))
    
    # Clips Storage
    clips_output_dir: str = os.getenv("CLIPS_OUTPUT_DIR", "/app/clips/raw")
    
    # Service Configuration
    service_name: str = os.getenv("SERVICE_NAME", "clip-generator")
    service_host: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    service_port: int = int(os.getenv("SERVICE_PORT", "8001"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"

settings = Settings()
