"""
Módulo de configuración principal para KickAPI
"""
import os
from typing import Optional


class Config:
    """Configuración de la aplicación"""
    
    # Configuración de la aplicación
    APP_NAME = "Kick API"
    APP_DESCRIPTION = "API para obtener clips y videos de canales de Kick.com"
    APP_VERSION = "2.0.0"
    
    # Configuración del servidor
    HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
    PORT = int(os.getenv("SERVICE_PORT", "8003"))
    
    # Configuración de directorios
    CONVERTED_VIDEOS_DIR = os.getenv("CONVERTED_VIDEOS_DIR", "converted_videos")
    TEMP_DIR = os.getenv("TEMP_DIR", "temp")
    
    # Configuración de caché
    CACHE_EXPIRY_SECONDS = int(os.getenv("CACHE_EXPIRY_SECONDS", "3600"))  # 1 hora
    CLEANUP_INTERVAL_SECONDS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "300"))  # 5 minutos
    
    # Configuración de procesamiento de video
    DEFAULT_QUALITY = os.getenv("DEFAULT_QUALITY", "medium")
    DEFAULT_PLATFORM = os.getenv("DEFAULT_PLATFORM", "general")
    DEFAULT_FPS = int(os.getenv("DEFAULT_FPS", "30"))
    
    # Configuración de Whisper
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")  # Usar el modelo tiny por velocidad
    WHISPER_TIMEOUT = int(os.getenv("WHISPER_TIMEOUT", "180"))  # 3 minutos para videos más largos
    
    # Configuración de FFmpeg
    FFMPEG_TIMEOUT = int(os.getenv("FFMPEG_TIMEOUT", "300"))  # 5 minutos
    CHUNK_SIZE = 1024 * 1024  # 1 MB
    
    # Configuración de tiempo de espera de solicitudes
    DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "120"))  # segundos
    
    # URLs de microservicios
    CLIP_GENERATOR_URL = os.getenv("CLIP_GENERATOR_URL", "http://clip-generator:8001")
    # CLIP_SELECTOR_URL eliminado - microservicio deprecado
    
    @classmethod
    def get_converted_videos_path(cls) -> str:
        """Obtener la ruta absoluta para el directorio de videos convertidos"""
        return os.path.abspath(cls.CONVERTED_VIDEOS_DIR)
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Crear los directorios necesarios si no existen"""
        os.makedirs(cls.CONVERTED_VIDEOS_DIR, exist_ok=True)
        os.makedirs(cls.TEMP_DIR, exist_ok=True)


# Configuración de niveles de calidad
QUALITY_SETTINGS = {
    "low": {
        "crf": "28", 
        "preset": "fast", 
        "scale": "720:1280",
        "bitrate": "1200k",
        "maxrate": "1800k",
        "bufsize": "2400k",
        "audio_bitrate": "96k"
    },
    "medium": {
        "crf": "23", 
        "preset": "medium", 
        "scale": "1080:1920",
        "bitrate": "2800k",
        "maxrate": "4200k", 
        "bufsize": "5600k",
        "audio_bitrate": "128k"
    },
    "high": {
        "crf": "20", 
        "preset": "medium", 
        "scale": "1080:1920",
        "bitrate": "5000k",
        "maxrate": "7500k",
        "bufsize": "10000k",
        "audio_bitrate": "192k"
    },
    "ultra": {
        "crf": "16", 
        "preset": "slow", 
        "scale": "1080:1920",
        "bitrate": "8000k",
        "maxrate": "12000k",
        "bufsize": "16000k",
        "audio_bitrate": "256k"
    },
    "tiktok": {
        "crf": "22",
        "preset": "medium",
        "scale": "1080:1920", 
        "bitrate": "2500k",
        "maxrate": "3500k",
        "bufsize": "5000k",
        "audio_bitrate": "128k"
    },
    "instagram": {
        "crf": "21",
        "preset": "medium", 
        "scale": "1080:1920",
        "bitrate": "3200k",
        "maxrate": "4800k",
        "bufsize": "6400k",
        "audio_bitrate": "160k"
    },
    "youtube": {
        "crf": "20",
        "preset": "medium",
        "scale": "1080:1920",
        "bitrate": "4000k",
        "maxrate": "6000k",
        "bufsize": "8000k",
        "audio_bitrate": "192k"
    }
}

# Mapeo de optimización por plataforma
PLATFORM_MAPPINGS = {
    "tiktok": "tiktok",
    "instagram": "instagram", 
    "facebook": "instagram",  # Facebook Reels usa la configuración de Instagram
    "youtube": "youtube",     # Optimizado para YouTube Shorts
    "general": None  # Usar la calidad proporcionada tal cual
}

# Encabezados HTTP para descargas de video
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
