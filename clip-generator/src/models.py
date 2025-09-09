from pydantic import BaseModel
from typing import List, Optional

class VideoRequest(BaseModel):
    video_url: str

class ClipMetadata(BaseModel):
    # Metadatos del clip con URL de acceso pero sin datos binarios
    clip_id: str  # ID único del clip para referencia
    url: str  # URL para acceder al clip bajo demanda
    start: float
    end: float
    duration: float
    width: int = 1080
    height: int = 1920
    format: str = "vertical"
    ai_score: Optional[float] = None
    ai_reason: Optional[str] = None

class ClipGenerationResponse(BaseModel):
    status: str
    clips: List[ClipMetadata]
    message: Optional[str] = None
    analysis_method: Optional[str] = None  # "deepseek_ai" o "fallback"
    total_video_duration: Optional[float] = None

class ErrorResponse(BaseModel):
    status: str
    error: str
    details: Optional[str] = None
