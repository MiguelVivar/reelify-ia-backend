import os
from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Configuración de Whisper
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    
    # Configuración de detección viral - variables de entorno en forma de cadena que se analizan
    viral_keywords_str: str = "oferta,descuento,quiero,increíble,gratis,limitado,exclusivo,promoción,rebaja,outlet"
    emotion_keywords_str: str = "amor,odio,feliz,triste,enojado,sorprendido,emocionado,increíble,wow,genial"
    min_viral_score: float = 0.3
    
    # Almacenamiento de clips
    clips_input_dir: str = "/app/clips/raw"
    clips_output_dir: str = "/app/clips/viral"
    
    # Configuración del servicio
    service_name: str = "clip-selector"
    service_host: str = "0.0.0.0"
    service_port: int = 8002
    
    # Registro (logging)
    log_level: str = "INFO"
    
    # Directorio temporal
    temp_dir: str = "/tmp/clip_processing"
    
    @property
    def viral_keywords(self) -> List[str]:
        """Analiza las palabras clave virales desde la variable de entorno en forma de cadena"""
        return [keyword.strip() for keyword in self.viral_keywords_str.split(',') if keyword.strip()]
    
    @property
    def emotion_keywords(self) -> List[str]:
        """Analiza las palabras clave de emoción desde la variable de entorno en forma de cadena"""
        return [keyword.strip() for keyword in self.emotion_keywords_str.split(',') if keyword.strip()]
    
    class Config:
        env_file = ".env"
        # Mapear variables de entorno a los nombres de campo internos
        fields = {
            'viral_keywords_str': {'env': 'VIRAL_KEYWORDS'},
            'emotion_keywords_str': {'env': 'EMOTION_KEYWORDS'}
        }

settings = Settings()
