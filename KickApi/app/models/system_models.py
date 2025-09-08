"""
Modelos Pydantic del sistema para KickAPI
"""
from pydantic import BaseModel
from typing import Optional, Dict, List


class SystemCapabilities(BaseModel):
    """Modelo de capacidades del sistema"""
    ffmpeg_available: bool
    whisper_available: bool
    ffmpeg_version: Optional[str] = None
    codecs: Optional[Dict[str, bool]] = None
    filters: Optional[Dict[str, bool]] = None
    capabilities: Optional[Dict[str, bool]] = None
    recommendations: List[Dict[str, str]] = []
