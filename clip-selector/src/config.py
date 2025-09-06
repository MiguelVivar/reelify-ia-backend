import os
from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Whisper Configuration
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    
    # Viral Detection Configuration - using string env vars that get parsed
    viral_keywords_str: str = "oferta,descuento,quiero,increíble,gratis,limitado,exclusivo,promoción,rebaja,outlet"
    emotion_keywords_str: str = "amor,odio,feliz,triste,enojado,sorprendido,emocionado,increíble,wow,genial"
    min_viral_score: float = 0.3
    
    # Clips Storage
    clips_input_dir: str = "/app/clips/raw"
    clips_output_dir: str = "/app/clips/viral"
    
    # Service Configuration
    service_name: str = "clip-selector"
    service_host: str = "0.0.0.0"
    service_port: int = 8002
    
    # Logging
    log_level: str = "INFO"
    
    # Temp directory
    temp_dir: str = "/tmp/clip_processing"
    
    @property
    def viral_keywords(self) -> List[str]:
        """Parse viral keywords from string environment variable"""
        return [keyword.strip() for keyword in self.viral_keywords_str.split(',') if keyword.strip()]
    
    @property
    def emotion_keywords(self) -> List[str]:
        """Parse emotion keywords from string environment variable"""
        return [keyword.strip() for keyword in self.emotion_keywords_str.split(',') if keyword.strip()]
    
    class Config:
        env_file = ".env"
        # Map environment variables to our internal field names
        fields = {
            'viral_keywords_str': {'env': 'VIRAL_KEYWORDS'},
            'emotion_keywords_str': {'env': 'EMOTION_KEYWORDS'}
        }

settings = Settings()
