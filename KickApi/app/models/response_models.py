"""
Modelos de respuesta Pydantic para KickAPI
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class ProcessVideoResponse(BaseModel):
    """Modelo de respuesta para el procesamiento de video"""
    success: bool
    video_id: str
    status: str
    download_url: str
    video_url: str
    status_url: str
    # Tiempo estimado de procesamiento (opcional, en formato legible)
    estimated_time: Optional[str] = None
    # Calidad solicitada/obtenida (opcional)
    quality: Optional[str] = None
    # Plataforma de origen (opcional)
    platform: Optional[str] = None
    # Opciones de procesamiento utilizadas (opcional)
    processing_options: Optional[Dict[str, Any]] = None
    # Optimización aplicada (opcional)
    optimizations: Optional[Dict[str, Any]] = None
    # Mensaje adicional o de error (opcional)
    message: Optional[str] = None


class VideoStatusResponse(BaseModel):
    """Modelo de respuesta para el estado del video"""
    video_id: str
    status: str
    # Calidad final (opcional)
    quality: Optional[str] = None
    # Marca de tiempo de creación (opcional, en segundos desde epoch)
    created_at: Optional[float] = None
    # URL de descarga (opcional)
    download_url: Optional[str] = None
    # URL pública del video (opcional)
    video_url: Optional[str] = None
    # Tamaño del archivo en bytes (opcional)
    file_size: Optional[int] = None
    # Tiempo de conversión en segundos (opcional)
    conversion_time: Optional[float] = None
    # Indica si el video está listo para descarga/reproducción
    ready: bool = False
    # Mensaje de error si existe (opcional)
    error: Optional[str] = None
    # Mensaje informativo adicional (opcional)
    message: Optional[str] = None
