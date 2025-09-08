"""
Modelos Pydantic relacionados con video para KickAPI
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class OptimizedVideoRequest(BaseModel):
    """Modelo de solicitud para optimización de video"""
    video_url: str
    quality: str = "medium"  # baja, media, alta, ultra, tiktok, instagram, youtube
    platform: str = "general"  # general, tiktok, instagram, youtube, facebook

    # Funcionalidad de división
    split: bool = False  # Cuando es True, divide el video en dos mitades verticales (izquierda, derecha)

    # Opciones de subtítulos
    add_subtitles: bool = False
    subtitle_language: str = "auto"  # auto, es, en, fr, etc.

    # Filtros de mejora de video
    apply_denoise: bool = False
    apply_sharpen: bool = False
    sharpen_strength: float = 0.3  # 0.1-1.0
    apply_stabilization: bool = False

    # Corrección de color
    apply_color_correction: bool = False
    brightness: float = 0.0  # -1.0 a 1.0
    contrast: float = 1.0    # 0.1 a 3.0
    saturation: float = 1.0  # 0.0 a 3.0
    gamma: float = 1.0       # 0.1 a 3.0

    # Ajustes técnicos
    custom_bitrate: Optional[str] = None  # p. ej., "5000k"
    target_fps: int = 30

    # Mejora de audio
    audio_enhancement: bool = False


class VideoFilterOptions(BaseModel):
    """Opciones de filtros de video"""
    denoise: bool = False
    sharpen: bool = False
    sharpen_strength: float = 0.3
    stabilize: bool = False
    color_correction: bool = False
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    gamma: float = 1.0


class VideoInfo(BaseModel):
    """Modelo de información del video"""
    duration: float = 0
    width: int = 0
    height: int = 0
    fps: float = 0
    bitrate: int = 0
    has_audio: bool = False
    codec: str = "unknown"
    aspect_ratio: str = "unknown"


class ProcessingStats(BaseModel):
    """Estadísticas de procesamiento de video"""
    original_size: int
    final_size: int
    size_reduction: float
    original_resolution: str
    final_resolution: str
    original_fps: float
    final_fps: float
    filters_applied: int
    subtitles_generated: bool


class VideoCache(BaseModel):
    """Modelo de caché de video"""
    status: str
    video_url: str
    quality: str
    platform: str
    processing_options: Dict[str, Any]
    filters_applied: List[str]
    add_subtitles: bool
    created_at: float
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    conversion_time: Optional[float] = None
    base_name: str
    completed_at: Optional[float] = None
    temp_dir: Optional[str] = None
    filename: Optional[str] = None
    original_info: Optional[VideoInfo] = None
    final_info: Optional[VideoInfo] = None
    compression_ratio: Optional[float] = None
    processing_stats: Optional[ProcessingStats] = None
    error: Optional[str] = None
